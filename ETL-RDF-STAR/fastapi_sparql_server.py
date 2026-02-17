"""
FastAPI SPARQL Endpoint Server with RDF-star Support
====================================================

This server:
1. Loads OWL ontology for data products
2. Loads RDF-star instance data with reified statements
3. Provides SPARQL endpoint at http://localhost:7878/sparql
4. Supports SPARQL-star queries for provenance and quality metadata

Usage:
    uvicorn fastapi_sparql_server:app --host 0.0.0.0 --port 7878

Then access:
    http://localhost:7878/sparql (GET or POST)
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pyoxigraph import Store, RdfFormat
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

app = FastAPI(title="RDF-star SPARQL Endpoint", version="1.0.0")

# Global store
store: Optional[Store] = None
load_stats: Dict[str, Any] = {}


def initialize_store():
    """Load ontology and instance data into PyOxigraph store"""
    global store, load_stats

    print("="*80)
    print("Initializing PyOxigraph SPARQL Endpoint with RDF-star")
    print("="*80)

    store = Store()
    load_stats = {
        'ontology_loaded': False,
        'instance_loaded': False,
        'total_quads': 0,
        'load_time': 0,
        'datasets_count': 0,
        'activities_count': 0
    }

    start_time = time.time()

    # Load ontology
    try:
        ontology_path = "ontology/data_products_ontology.ttl"
        print(f"\n[1/2] Loading ontology from {ontology_path}...")
        with open(ontology_path, 'rb') as f:
            store.load(f, RdfFormat.TURTLE)
        load_stats['ontology_loaded'] = True
        print(f"      [OK] Ontology loaded successfully")
    except Exception as e:
        print(f"      [ERROR] Failed to load ontology: {e}")
        return False

    # Load instance data
    try:
        instance_path = "output/output_data_star.trig"
        print(f"\n[2/2] Loading instance data from {instance_path}...")
        with open(instance_path, 'rb') as f:
            store.load(f, RdfFormat.TRIG)
        load_stats['instance_loaded'] = True
        print(f"      [OK] Instance data loaded successfully")
    except Exception as e:
        print(f"      [ERROR] Failed to load instance data: {e}")
        return False

    # Calculate statistics
    load_stats['total_quads'] = len(list(store))
    load_stats['load_time'] = time.time() - start_time

    # Count datasets and activities
    try:
        count_query = """
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX prov: <http://www.w3.org/ns/prov#>
        SELECT (COUNT(DISTINCT ?dataset) as ?datasetCount) (COUNT(DISTINCT ?activity) as ?activityCount)
        WHERE {
            OPTIONAL { ?dataset a dcat:Dataset }
            OPTIONAL { ?activity a prov:Activity }
        }
        """
        result = list(store.query(count_query))[0]
        # Extract counts properly
        datasets_raw = result[0]  # First variable
        activities_raw = result[1]  # Second variable
        load_stats['datasets_count'] = int(str(datasets_raw).strip('"'))
        load_stats['activities_count'] = int(str(activities_raw).strip('"'))
    except Exception as e:
        print(f"[WARNING] Could not count entities: {e}")
        load_stats['datasets_count'] = 0
        load_stats['activities_count'] = 0

    print("\n" + "="*80)
    print("Store Initialized Successfully")
    print("="*80)
    print(f"Total quads loaded: {load_stats['total_quads']:,}")
    print(f"Datasets: {load_stats['datasets_count']:,}")
    print(f"Activities: {load_stats['activities_count']:,}")
    print(f"Load time: {load_stats['load_time']:.2f} seconds")
    print("="*80)

    return True


@app.on_event("startup")
async def startup_event():
    """Initialize store on startup"""
    if not initialize_store():
        print("[ERROR] Failed to initialize store!")
        raise RuntimeError("Store initialization failed")


@app.get("/", response_class=HTMLResponse)
async def home():
    """Home page with API information"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI SPARQL Endpoint - RDF-star Data Products</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; }}
            .endpoint {{ background: #ecf0f1; padding: 15px; border-radius: 4px; margin: 20px 0; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
            .stat {{ background: #3498db; color: white; padding: 15px; border-radius: 4px; text-align: center; }}
            .stat-value {{ font-size: 24px; font-weight: bold; }}
            .stat-label {{ font-size: 12px; opacity: 0.9; }}
            code {{ background: #ecf0f1; padding: 2px 6px; border-radius: 3px; }}
            .example {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 10px 0; }}
            .success {{ color: #27ae60; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 FastAPI SPARQL Endpoint</h1>
            <p><strong>RDF-star Data Products with Governance Metadata</strong></p>
            
            <div class="endpoint">
                <strong>SPARQL Endpoint:</strong> 
                <code>http://localhost:7878/sparql</code>
                <br><br>
                <strong>Methods:</strong> GET (query parameter) or POST (body)
                <br>
                <strong>API Docs:</strong> <a href="/docs">/docs</a> (Swagger UI)
            </div>
            
            <h2>Store Statistics</h2>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{load_stats.get('total_quads', 0):,}</div>
                    <div class="stat-label">Total Quads</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{load_stats.get('datasets_count', 0):,}</div>
                    <div class="stat-label">Datasets</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{load_stats.get('activities_count', 0):,}</div>
                    <div class="stat-label">Activities</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{load_stats.get('load_time', 0):.2f}s</div>
                    <div class="stat-label">Load Time</div>
                </div>
            </div>
            
            <h2>Example SPARQL-star Query</h2>
            <div class="example">
                <pre>PREFIX ex: &lt;http://example.org/&gt;
PREFIX dcat: &lt;http://www.w3.org/ns/dcat#&gt;
PREFIX prov: &lt;http://www.w3.org/ns/prov#&gt;

SELECT ?dataset ?theme ?confidence ?source
WHERE {{
    ?dataset dcat:theme ?theme .
    
    # RDF-star: query metadata about the statement
    &lt;&lt;?dataset dcat:theme ?theme&gt;&gt; 
        ex:confidence ?confidence ;
        prov:wasDerivedFrom ?source .
    
    FILTER(?confidence > 0.90)
}}
LIMIT 10</pre>
            </div>
            
            <h2>Status</h2>
            <p class="success">Ontology: {'✓ Loaded' if load_stats.get('ontology_loaded') else '✗ Not loaded'}</p>
            <p class="success">Instance Data: {'✓ Loaded' if load_stats.get('instance_loaded') else '✗ Not loaded'}</p>
            
            <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d;">
                <strong>Server Started:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
    </body>
    </html>
    """
    return html


@app.get("/sparql")
async def sparql_get(query: str):
    """SPARQL endpoint - GET method"""
    return await execute_sparql(query)


@app.post("/sparql")
async def sparql_post(request: Request):
    """SPARQL endpoint - POST method"""
    content_type = request.headers.get('content-type', '')

    if 'application/sparql-query' in content_type:
        # Direct SPARQL query in body
        body = await request.body()
        query = body.decode('utf-8')
    else:
        # JSON body or form data
        try:
            json_body = await request.json()
            query = json_body.get('query', '')
        except:
            form = await request.form()
            query = form.get('query', '')

    if not query:
        raise HTTPException(status_code=400, detail="No query provided")

    return await execute_sparql(query)


async def execute_sparql(query: str) -> JSONResponse:
    """Execute SPARQL query and return results"""
    if store is None:
        raise HTTPException(status_code=500, detail="Store not initialized")

    try:
        start_time = time.time()

        print(f"\n[QUERY] Executing SPARQL query...")
        print(f"[QUERY] First 200 chars: {query[:200]}")

        # Execute query - DON'T convert to list yet!
        query_results = store.query(query)

        # Get variable names BEFORE converting to list
        vars = []
        if hasattr(query_results, 'variables'):
            var_objects = query_results.variables  # Property, not method!
            vars = [str(v).lstrip('?') for v in var_objects]  # Remove ? prefix
            print(f"[RESULT] Variables: {vars}")

        # NOW convert to list
        results = list(query_results)
        query_time = time.time() - start_time

        print(f"[RESULT] Got {len(results)} results in {query_time:.3f}s")

        # Convert results to bindings
        bindings = []
        for result in results:
            binding = {}
            for var in vars:
                try:
                    # Access by string key (without ?)
                    value = result[var]

                    if value is not None:
                        value_str = str(value)

                        # Determine type and format
                        if value_str.startswith('<') and value_str.endswith('>'):
                            # URI in angle brackets
                            binding[var] = {
                                'type': 'uri',
                                'value': value_str[1:-1]  # Remove < >
                            }
                        elif value_str.startswith('http://') or value_str.startswith('https://'):
                            # Plain URI
                            binding[var] = {
                                'type': 'uri',
                                'value': value_str
                            }
                        elif value_str.startswith('"'):
                            # Literal with quotes - might have datatype
                            if '^^' in value_str:
                                # "value"^^<datatype>
                                parts = value_str.split('^^')
                                literal_value = parts[0].strip('"')
                                datatype = parts[1].strip('<>')
                                binding[var] = {
                                    'type': 'literal',
                                    'value': literal_value,
                                    'datatype': datatype
                                }
                            else:
                                # Plain literal "value"
                                binding[var] = {
                                    'type': 'literal',
                                    'value': value_str.strip('"')
                                }
                        else:
                            # Unquoted value
                            binding[var] = {
                                'type': 'literal',
                                'value': value_str
                            }
                except (KeyError, IndexError) as e:
                    print(f"[WARNING] Could not extract {var}: {e}")
                    continue

            bindings.append(binding)

        print(f"[RESULT] Bindings created: {len(bindings)}")
        if bindings:
            print(f"[RESULT] First binding keys: {list(bindings[0].keys())}")
            print(f"[RESULT] First binding sample: {bindings[0]}")

        response_data = {
            'head': {'vars': vars},
            'results': {'bindings': bindings},
            'meta': {
                'query_time': f"{query_time:.3f}s",
                'result_count': len(results)
            }
        }

        return JSONResponse(content=response_data)

    except Exception as e:
        print(f"[ERROR] Query execution failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=400,
            detail={
                'error': 'Query execution failed',
                'message': str(e),
                'query': query[:500]
            }
        )


@app.get("/stats")
async def stats():
    """Return store statistics"""
    return load_stats


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        'status': 'healthy' if store is not None else 'unhealthy',
        'timestamp': datetime.now().isoformat(),
        'store_loaded': store is not None,
        'total_quads': load_stats.get('total_quads', 0)
    }


if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*80)
    print("FastAPI SPARQL Endpoint Server")
    print("RDF-star Data Products with Governance")
    print("="*80)
    print("\nStarting server...")
    print("SPARQL Endpoint: http://localhost:7878/sparql")
    print("API Docs:        http://localhost:7878/docs")
    print("Home Page:       http://localhost:7878/")
    print("="*80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=7878, log_level="info")

