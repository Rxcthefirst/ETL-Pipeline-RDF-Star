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
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from pyoxigraph import Store, RdfFormat
import os

# Get the directory of this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Setup templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Global state
store: Optional[Store] = None
load_stats: Dict[str, Any] = {}
data_file: str = "output/batch_simulation/two_batches.trig"


def load_rdf_directory_recursive(directory: str, indent: str = "  "):
    """Recursively load all RDF files from a directory and its subdirectories."""
    global store

    for entry in sorted(os.listdir(directory)):
        filepath = os.path.join(directory, entry)

        if os.path.isdir(filepath):
            # Recursively process subdirectories
            print(f"{indent}[DIR] {entry}/")
            load_rdf_directory_recursive(filepath, indent + "  ")
        else:
            # Process RDF files
            if entry.endswith('.ttl') or entry.endswith('.turtle'):
                try:
                    print(f"{indent}Loading: {entry}")
                    with open(filepath, 'rb') as f:
                        store.load(f, RdfFormat.TURTLE)
                    print(f"{indent}  -> loaded successfully")
                except Exception as e:
                    print(f"{indent}  -> Warning: Failed to load: {e}")
            elif entry.endswith('.owl') or entry.endswith('.rdf') or entry.endswith('.xml'):
                try:
                    print(f"{indent}Loading: {entry}")
                    with open(filepath, 'rb') as f:
                        store.load(f, RdfFormat.RDF_XML)
                    print(f"{indent}  -> loaded successfully")
                except Exception as e:
                    print(f"{indent}  -> Warning: Failed to load: {e}")
            elif entry.endswith('.trig'):
                try:
                    print(f"{indent}Loading: {entry}")
                    with open(filepath, 'rb') as f:
                        store.load(f, RdfFormat.TRIG)
                    print(f"{indent}  -> loaded successfully")
                except Exception as e:
                    print(f"{indent}  -> Warning: Failed to load: {e}")
            elif entry.endswith('.nq') or entry.endswith('.nquads'):
                try:
                    print(f"{indent}Loading: {entry}")
                    with open(filepath, 'rb') as f:
                        store.load(f, RdfFormat.N_QUADS)
                    print(f"{indent}  -> loaded successfully")
                except Exception as e:
                    print(f"{indent}  -> Warning: Failed to load: {e}")
            elif entry.endswith('.nt') or entry.endswith('.ntriples'):
                try:
                    print(f"{indent}Loading: {entry}")
                    with open(filepath, 'rb') as f:
                        store.load(f, RdfFormat.N_TRIPLES)
                    print(f"{indent}  -> loaded successfully")
                except Exception as e:
                    print(f"{indent}  -> Warning: Failed to load: {e}")


def initialize_store(rdf_input_dir: str = None):
    """Load RDF data into PyOxigraph store from rdf-data-input directory."""
    global store, load_stats, data_file

    print("=" * 70)
    print("Initializing Batch SPARQL Endpoint")
    print("=" * 70)

    store = Store()
    start_time = time.time()

    try:
        # Determine RDF input directory - default to rdf-data-input
        input_dir = rdf_input_dir if rdf_input_dir else os.path.join(BASE_DIR, "rdf-data-input")
        data_file = input_dir

        # Recursively load all RDF files from the input directory
        if os.path.exists(input_dir):
            print(f"\nLoading RDF files recursively from: {input_dir}")
            print("  (Place ontologies in /ontologies and instance data in /individuals)\n")
            load_rdf_directory_recursive(input_dir)
        else:
            print(f"\n[WARNING] RDF input directory not found: {input_dir}")
            print("  Creating directory structure...")
            os.makedirs(os.path.join(input_dir, "ontologies"), exist_ok=True)
            os.makedirs(os.path.join(input_dir, "individuals"), exist_ok=True)
            print(f"  Created: {input_dir}/ontologies/")
            print(f"  Created: {input_dir}/individuals/")
            print("\n  Place your RDF files in these directories and restart the server.")

        load_stats['data_loaded'] = True
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
async def home(request: Request):
    """Serve the interactive SPARQL client."""
    return templates.TemplateResponse("sparql_client.html", {"request": request})


@app.get("/info", response_class=HTMLResponse)
async def info():
    """Server information page."""
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


@app.get("/ontologies")
async def get_ontology_index():
    """
    Return indexed ontologies classes and properties from the loaded data.
    This queries the actual RDF store for owl:Class, rdfs:Class definitions
    and their associated properties.
    """
    if store is None:
        raise HTTPException(status_code=500, detail="Store not initialized")

    try:
        # Query for classes (owl:Class and rdfs:Class)
        class_query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?class ?label ?comment ?parent
        WHERE {
            { ?class a owl:Class } UNION { ?class a rdfs:Class }
            OPTIONAL { ?class rdfs:label ?label }
            OPTIONAL { ?class rdfs:comment ?comment }
            OPTIONAL { ?class rdfs:subClassOf ?parent }
            FILTER(!isBlank(?class))
        }
        ORDER BY ?class
        """

        classes = []
        class_results = store.query(class_query)
        for row in class_results:
            class_uri = str(row['class'])
            classes.append({
                'uri': class_uri,
                'label': str(row['label']) if row['label'] else class_uri.split('#')[-1].split('/')[-1],
                'comment': str(row['comment']) if row['comment'] else None,
                'parent': str(row['parent']) if row['parent'] else None
            })

        # Query for object properties
        obj_prop_query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?prop ?label ?domain ?range
        WHERE {
            ?prop a owl:ObjectProperty .
            OPTIONAL { ?prop rdfs:label ?label }
            OPTIONAL { ?prop rdfs:domain ?domain }
            OPTIONAL { ?prop rdfs:range ?range }
            FILTER(!isBlank(?prop))
        }
        ORDER BY ?prop
        """

        object_properties = []
        obj_results = store.query(obj_prop_query)
        for row in obj_results:
            prop_uri = str(row['prop'])
            object_properties.append({
                'uri': prop_uri,
                'label': str(row['label']) if row['label'] else prop_uri.split('#')[-1].split('/')[-1],
                'domain': str(row['domain']) if row['domain'] else None,
                'range': str(row['range']) if row['range'] else None
            })

        # Query for datatype properties
        data_prop_query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?prop ?label ?domain ?range
        WHERE {
            ?prop a owl:DatatypeProperty .
            OPTIONAL { ?prop rdfs:label ?label }
            OPTIONAL { ?prop rdfs:domain ?domain }
            OPTIONAL { ?prop rdfs:range ?range }
            FILTER(!isBlank(?prop))
        }
        ORDER BY ?prop
        """

        datatype_properties = []
        data_results = store.query(data_prop_query)
        for row in data_results:
            prop_uri = str(row['prop'])
            datatype_properties.append({
                'uri': prop_uri,
                'label': str(row['label']) if row['label'] else prop_uri.split('#')[-1].split('/')[-1],
                'domain': str(row['domain']) if row['domain'] else None,
                'range': str(row['range']) if row['range'] else None
            })

        # Also get rdf:Property definitions
        rdf_prop_query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?prop ?label ?domain ?range
        WHERE {
            ?prop a rdf:Property .
            OPTIONAL { ?prop rdfs:label ?label }
            OPTIONAL { ?prop rdfs:domain ?domain }
            OPTIONAL { ?prop rdfs:range ?range }
            FILTER(!isBlank(?prop))
        }
        ORDER BY ?prop
        """

        rdf_results = store.query(rdf_prop_query)
        for row in rdf_results:
            prop_uri = str(row['prop'])
            # Check if already in datatype or object properties
            if not any(p['uri'] == prop_uri for p in datatype_properties + object_properties):
                datatype_properties.append({
                    'uri': prop_uri,
                    'label': str(row['label']) if row['label'] else prop_uri.split('#')[-1].split('/')[-1],
                    'domain': str(row['domain']) if row['domain'] else None,
                    'range': str(row['range']) if row['range'] else None
                })

        return JSONResponse(
            content={
                "classes": classes,
                "objectProperties": object_properties,
                "datatypeProperties": datatype_properties,
                "counts": {
                    "classes": len(classes),
                    "objectProperties": len(object_properties),
                    "datatypeProperties": len(datatype_properties)
                }
            },
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying ontologies: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch SPARQL Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Directory Structure:
  Place your RDF files in the rdf-data-input directory:
  
    rdf-data-input/
    ├── ontologies/     <- Place ontology files here (.ttl, .owl, .rdf)
    └── individuals/    <- Place instance/data files here (.ttl, .trig, .nq)

  All files will be loaded recursively on server startup.

Examples:
    python batch_sparql_server.py
    python batch_sparql_server.py --port 8080
    python batch_sparql_server.py --rdf-input /path/to/custom/rdf-folder
        """
    )
    parser.add_argument("--rdf-input", "-r",
                        default=None,
                        help="Path to RDF input directory (default: ./rdf-data-input)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", "-p", type=int, default=7878, help="Port")

    args = parser.parse_args()

    # Initialize store before starting server
    if not initialize_store(args.rdf_input):
        print("[ERROR] Failed to initialize store. Exiting.")
        return

    print(f"\nStarting server on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop\n")

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
