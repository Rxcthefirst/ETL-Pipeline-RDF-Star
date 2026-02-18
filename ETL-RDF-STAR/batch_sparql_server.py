"""
FastAPI SPARQL Endpoint Server for Batch Testing
=================================================

This server loads the batch simulation data and provides a SPARQL endpoint
for testing temporal queries, point-in-time queries, and batch comparisons.

Usage:
    python batch_sparql_server.py

    # Or with custom data file:
    python batch_sparql_server.py --data output/batch_simulation/two_batches.trig

Endpoints:
    GET/POST /sparql - Execute SPARQL queries
    GET /stats - Server statistics
    GET /batches - List all batches
"""

import argparse
import time
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pyoxigraph import Store, RdfFormat

app = FastAPI(
    title="Batch SPARQL Endpoint",
    description="SPARQL endpoint for temporal knowledge graph batch testing",
    version="1.0.0"
)

# Enable CORS for Postman/browser testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
store: Optional[Store] = None
load_stats: Dict[str, Any] = {}
data_file: str = "output/batch_simulation/two_batches.trig"


def initialize_store(file_path: str):
    """Load RDF data into PyOxigraph store."""
    global store, load_stats, data_file

    data_file = file_path

    print("=" * 70)
    print("Initializing Batch SPARQL Endpoint")
    print("=" * 70)

    store = Store()
    start_time = time.time()

    try:
        print(f"\nLoading data from: {file_path}")
        with open(file_path, 'rb') as f:
            store.load(f, RdfFormat.TRIG)

        load_stats['data_loaded'] = True
        load_stats['data_file'] = file_path
        load_stats['total_quads'] = len(list(store))
        load_stats['load_time'] = time.time() - start_time

        # Count batches - use simpler query
        try:
            batch_query = """
            SELECT ?batch
            WHERE { 
                GRAPH <http://example.org/graph/metadata> {
                    ?batch a <http://example.org/Batch> 
                }
            }
            """
            results = list(store.query(batch_query))
            load_stats['batch_count'] = len(results)
        except Exception as e:
            print(f"Batch count query failed: {e}")
            load_stats['batch_count'] = 0

        # Count named graphs
        graphs = set()
        for quad in store:
            if quad.graph_name:
                graphs.add(str(quad.graph_name))
        load_stats['graph_count'] = len(graphs)
        load_stats['graphs'] = list(graphs)

        print(f"\n[OK] Data loaded successfully")
        print(f"    Total quads: {load_stats['total_quads']:,}")
        print(f"    Named graphs: {load_stats['graph_count']}")
        print(f"    Batches: {load_stats.get('batch_count', 'N/A')}")
        print(f"    Load time: {load_stats['load_time']:.2f}s")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to load data: {e}")
        load_stats['data_loaded'] = False
        load_stats['error'] = str(e)
        return False


@app.get("/", response_class=HTMLResponse)
async def home():
    """Home page with API information."""
    graphs_html = "".join([f"<li><code>{g}</code></li>" for g in load_stats.get('graphs', [])])

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Batch SPARQL Endpoint</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ background: white; padding: 30px; border-radius: 8px; max-width: 900px; margin: auto; }}
            h1 {{ color: #2c3e50; }}
            .endpoint {{ background: #e8f4f8; padding: 15px; border-radius: 4px; margin: 20px 0; }}
            .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
            .stat {{ background: #3498db; color: white; padding: 15px; border-radius: 4px; text-align: center; }}
            .stat-value {{ font-size: 24px; font-weight: bold; }}
            code {{ background: #ecf0f1; padding: 2px 6px; border-radius: 3px; font-size: 12px; }}
            pre {{ background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 4px; overflow-x: auto; }}
            ul {{ list-style: none; padding: 0; }}
            li {{ padding: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔄 Batch SPARQL Endpoint</h1>
            <p>Temporal Knowledge Graph with Batch Management</p>
            
            <div class="endpoint">
                <strong>SPARQL Endpoint:</strong> <code>http://localhost:7878/sparql</code><br>
                <strong>API Docs:</strong> <a href="/docs">/docs</a>
            </div>
            
            <h2>Statistics</h2>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{load_stats.get('total_quads', 0):,}</div>
                    <div>Total Quads</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{load_stats.get('batch_count', 0)}</div>
                    <div>Batches</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{load_stats.get('graph_count', 0)}</div>
                    <div>Named Graphs</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{load_stats.get('load_time', 0):.2f}s</div>
                    <div>Load Time</div>
                </div>
            </div>
            
            <h2>Named Graphs</h2>
            <ul>{graphs_html}</ul>
            
            <h2>Example: Get Active Batch</h2>
            <pre>PREFIX ex: &lt;http://example.org/&gt;
SELECT ?batch ?batchNumber ?status
FROM &lt;http://example.org/graph/metadata&gt;
WHERE {{
    ?batch a ex:Batch ;
           ex:batchNumber ?batchNumber ;
           ex:status ?status .
}}
ORDER BY DESC(?batchNumber)</pre>
            
            <h2>Example: Point-in-Time Query</h2>
            <pre>PREFIX ex: &lt;http://example.org/&gt;
PREFIX schema: &lt;http://schema.org/&gt;

# What was Alice's credit score in Batch 1 (Feb 15)?
SELECT ?score
FROM &lt;http://example.org/batch/2026-02-15T10:00:00Z&gt;
WHERE {{
    ex:customer/C001 schema:creditScore ?score .
}}</pre>
            
            <p style="margin-top: 30px; color: #7f8c8d; border-top: 1px solid #ddd; padding-top: 20px;">
                Data file: <code>{data_file}</code><br>
                Server started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
    </body>
    </html>
    """


@app.get("/stats")
async def get_stats():
    """Return server statistics."""
    return JSONResponse(load_stats)


@app.get("/batches")
async def list_batches():
    """List all batches with their metadata."""
    if store is None:
        raise HTTPException(status_code=500, detail="Store not initialized")

    query = """
    PREFIX ex: <http://example.org/>
    PREFIX dct: <http://purl.org/dc/terms/>
    
    SELECT ?batch ?batchNumber ?status ?created ?description ?quadCount
    FROM <http://example.org/graph/metadata>
    WHERE {
        ?batch a ex:Batch ;
               ex:batchNumber ?batchNumber ;
               ex:status ?status .
        OPTIONAL { ?batch dct:created ?created }
        OPTIONAL { ?batch dct:description ?description }
        OPTIONAL { ?batch ex:quadCount ?quadCount }
    }
    ORDER BY DESC(?batchNumber)
    """

    try:
        results = store.query(query)
        vars = [str(v).lstrip('?') for v in results.variables]

        batches = []
        for row in results:
            batch = {}
            for var in vars:
                val = row[var]
                if val is not None:
                    batch[var] = str(val).strip('"<>')
            batches.append(batch)

        return JSONResponse({
            "count": len(batches),
            "batches": batches
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sparql")
async def sparql_get(query: str = Query(..., description="SPARQL query")):
    """Execute SPARQL query via GET."""
    return await execute_sparql(query)


@app.post("/sparql")
async def sparql_post(request: Request):
    """Execute SPARQL query via POST."""
    content_type = request.headers.get('content-type', '')

    if 'application/sparql-query' in content_type:
        body = await request.body()
        query = body.decode('utf-8')
    elif 'application/x-www-form-urlencoded' in content_type:
        form = await request.form()
        query = form.get('query', '')
    else:
        try:
            json_body = await request.json()
            query = json_body.get('query', '')
        except:
            body = await request.body()
            query = body.decode('utf-8')

    if not query:
        raise HTTPException(status_code=400, detail="No query provided")

    return await execute_sparql(query)


async def execute_sparql(query: str) -> JSONResponse:
    """Execute SPARQL query and return results."""
    if store is None:
        raise HTTPException(status_code=500, detail="Store not initialized")

    try:
        start_time = time.time()

        # Execute query
        query_results = store.query(query)

        # Handle SELECT queries
        if hasattr(query_results, 'variables'):
            vars = [str(v).lstrip('?') for v in query_results.variables]
            results_list = list(query_results)
            query_time = time.time() - start_time

            bindings = []
            for result in results_list:
                binding = {}
                for var in vars:
                    try:
                        value = result[var]
                        if value is not None:
                            value_str = str(value)

                            if value_str.startswith('<') and value_str.endswith('>'):
                                binding[var] = {'type': 'uri', 'value': value_str[1:-1]}
                            elif '^^' in value_str:
                                parts = value_str.split('^^')
                                binding[var] = {
                                    'type': 'literal',
                                    'value': parts[0].strip('"'),
                                    'datatype': parts[1].strip('<>')
                                }
                            elif value_str.startswith('"'):
                                binding[var] = {'type': 'literal', 'value': value_str.strip('"')}
                            elif value_str.startswith('http'):
                                binding[var] = {'type': 'uri', 'value': value_str}
                            else:
                                binding[var] = {'type': 'literal', 'value': value_str}
                    except (KeyError, IndexError):
                        continue

                if binding:
                    bindings.append(binding)

            return JSONResponse({
                "head": {"vars": vars},
                "results": {"bindings": bindings},
                "metadata": {
                    "resultCount": len(bindings),
                    "queryTime": f"{query_time:.3f}s"
                }
            })

        # Handle ASK queries
        elif isinstance(query_results, bool):
            return JSONResponse({"boolean": query_results})

        # Handle CONSTRUCT queries
        else:
            results_list = list(query_results)
            return JSONResponse({
                "triples": [str(t) for t in results_list],
                "count": len(results_list)
            })

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Batch SPARQL Server")
    parser.add_argument("--data", "-d",
                        default="output/batch_simulation/two_batches.trig",
                        help="Path to RDF data file (TriG format)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", "-p", type=int, default=7878, help="Port")

    args = parser.parse_args()

    # Initialize store before starting server
    if not initialize_store(args.data):
        print("[ERROR] Failed to initialize store. Exiting.")
        return

    print(f"\nStarting server on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop\n")

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

