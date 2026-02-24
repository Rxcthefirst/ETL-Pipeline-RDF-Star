"""
FastAPI SPARQL Endpoint Server for Batch Testing
=================================================

This server loads the batch simulation data and provides a SPARQL endpoint
for testing temporal queries, point-in-time queries, and batch comparisons.

Usage:
    python rdf-workbench.py

    # Or with custom data file:
    python rdf-workbench.py --data output/batch_simulation/two_batches.trig

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
from pyoxigraph import Store, RdfFormat, NamedNode
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


def uri_str(node):
    """Convert a pyoxigraph node to a clean URI string (strip angle brackets)."""
    if node is None:
        return None
    s = str(node)
    if s.startswith('<') and s.endswith('>'):
        return s[1:-1]
    return s


def label_from_uri(uri):
    """Extract a human-readable label from a URI."""
    return uri.split('#')[-1].split('/')[-1]


def _clean_literal(node):
    """Clean a pyoxigraph literal value to a plain string."""
    if node is None:
        return ''
    val = str(node)
    # Strip typed literal suffix: "value"^^<datatype>
    if '^^' in val:
        val = val.split('^^')[0]
    # Strip surrounding quotes
    val = val.strip('"')
    return val


def graph_uri_from_path(filepath: str, base_dir: str) -> str:
    """Derive a named graph URI from a file path relative to rdf-data-input."""
    rel = os.path.relpath(filepath, base_dir).replace("\\", "/")
    # Strip extension
    name = os.path.splitext(rel)[0]
    return f"http://example.org/graph/{name}"


def load_rdf_file(filepath: str, graph_uri: str, indent: str = "  "):
    """Load a single RDF file into a named graph."""
    global store
    entry = os.path.basename(filepath)
    graph = NamedNode(graph_uri)
    fmt = None

    if entry.endswith('.ttl') or entry.endswith('.turtle'):
        fmt = RdfFormat.TURTLE
    elif entry.endswith('.owl') or entry.endswith('.rdf') or entry.endswith('.xml'):
        fmt = RdfFormat.RDF_XML
    elif entry.endswith('.trig'):
        fmt = RdfFormat.TRIG
    elif entry.endswith('.nq') or entry.endswith('.nquads'):
        fmt = RdfFormat.N_QUADS
    elif entry.endswith('.nt') or entry.endswith('.ntriples'):
        fmt = RdfFormat.N_TRIPLES

    if fmt is None:
        return False

    try:
        print(f"{indent}Loading: {entry} -> <{graph_uri}>")
        with open(filepath, 'rb') as f:
            if fmt in (RdfFormat.TRIG, RdfFormat.N_QUADS):
                # These formats carry their own graph info
                store.load(f, fmt)
            else:
                store.load(f, fmt, to_graph=graph)
        print(f"{indent}  -> loaded successfully")
        return True
    except Exception as e:
        print(f"{indent}  -> Warning: Failed to load: {e}")
        return False


def load_rdf_directory_recursive(directory: str, base_dir: str = None, indent: str = "  "):
    """Recursively load all RDF files from a directory, each into its own named graph."""
    global store
    if base_dir is None:
        base_dir = directory

    for entry in sorted(os.listdir(directory)):
        filepath = os.path.join(directory, entry)

        if os.path.isdir(filepath):
            print(f"{indent}[DIR] {entry}/")
            load_rdf_directory_recursive(filepath, base_dir, indent + "  ")
        else:
            graph_uri = graph_uri_from_path(filepath, base_dir)
            load_rdf_file(filepath, graph_uri, indent)


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
            GRAPH ?g {
                { ?class a owl:Class } UNION { ?class a rdfs:Class }
                OPTIONAL { ?class rdfs:label ?label }
                OPTIONAL { ?class rdfs:comment ?comment }
                OPTIONAL { ?class rdfs:subClassOf ?parent }
                FILTER(!isBlank(?class))
            }
        }
        ORDER BY ?class
        """

        classes = []
        class_results = store.query(class_query)
        for row in class_results:
            class_uri = uri_str(row['class'])
            classes.append({
                'uri': class_uri,
                'label': str(row['label']).strip('"') if row['label'] else label_from_uri(class_uri),
                'comment': str(row['comment']).strip('"') if row['comment'] else None,
                'parent': uri_str(row['parent'])
            })

        # Query for object properties
        obj_prop_query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?prop ?label ?domain ?range
        WHERE {
            GRAPH ?g {
                ?prop a owl:ObjectProperty .
                OPTIONAL { ?prop rdfs:label ?label }
                OPTIONAL { ?prop rdfs:domain ?domain }
                OPTIONAL { ?prop rdfs:range ?range }
                FILTER(!isBlank(?prop))
            }
        }
        ORDER BY ?prop
        """

        object_properties = []
        obj_results = store.query(obj_prop_query)
        for row in obj_results:
            prop_uri = uri_str(row['prop'])
            object_properties.append({
                'uri': prop_uri,
                'label': str(row['label']).strip('"') if row['label'] else label_from_uri(prop_uri),
                'domain': uri_str(row['domain']),
                'range': uri_str(row['range'])
            })

        # Query for datatype properties
        data_prop_query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?prop ?label ?domain ?range
        WHERE {
            GRAPH ?g {
                ?prop a owl:DatatypeProperty .
                OPTIONAL { ?prop rdfs:label ?label }
                OPTIONAL { ?prop rdfs:domain ?domain }
                OPTIONAL { ?prop rdfs:range ?range }
                FILTER(!isBlank(?prop))
            }
        }
        ORDER BY ?prop
        """

        datatype_properties = []
        data_results = store.query(data_prop_query)
        for row in data_results:
            prop_uri = uri_str(row['prop'])
            datatype_properties.append({
                'uri': prop_uri,
                'label': str(row['label']).strip('"') if row['label'] else label_from_uri(prop_uri),
                'domain': uri_str(row['domain']),
                'range': uri_str(row['range'])
            })

        # Also get rdf:Property definitions
        rdf_prop_query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?prop ?label ?domain ?range
        WHERE {
            GRAPH ?g {
                ?prop a rdf:Property .
                OPTIONAL { ?prop rdfs:label ?label }
                OPTIONAL { ?prop rdfs:domain ?domain }
                OPTIONAL { ?prop rdfs:range ?range }
                FILTER(!isBlank(?prop))
            }
        }
        ORDER BY ?prop
        """

        rdf_results = store.query(rdf_prop_query)
        for row in rdf_results:
            prop_uri = uri_str(row['prop'])
            # Check if already in datatype or object properties
            if not any(p['uri'] == prop_uri for p in datatype_properties + object_properties):
                datatype_properties.append({
                    'uri': prop_uri,
                    'label': str(row['label']).strip('"') if row['label'] else label_from_uri(prop_uri),
                    'domain': uri_str(row['domain']),
                    'range': uri_str(row['range'])
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


# =========================================================================
# Named Graph Management API
# =========================================================================

@app.get("/api/graphs")
async def list_named_graphs():
    """List all named graphs in the store with triple counts."""
    if store is None:
        raise HTTPException(status_code=500, detail="Store not initialized")

    try:
        query = """
        SELECT ?graph (COUNT(*) AS ?count)
        WHERE { GRAPH ?graph { ?s ?p ?o } }
        GROUP BY ?graph
        ORDER BY ?graph
        """
        results = store.query(query)
        graphs = []
        for row in results:
            g = uri_str(row['graph'])
            c = str(row['count']).strip('"').split('^^')[0].strip('"')
            graphs.append({"uri": g, "tripleCount": int(c)})

        return JSONResponse({"graphs": graphs, "count": len(graphs)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graphs/load")
async def load_file_to_graph(
    file: str = Query(..., description="File path relative to rdf-data-input (e.g. ontologies/my_onto.ttl)"),
    graph: str = Query(None, description="Named graph URI (auto-derived from path if omitted)")
):
    """Load an RDF file from rdf-data-input into a specific named graph."""
    if store is None:
        raise HTTPException(status_code=500, detail="Store not initialized")

    input_dir = os.path.join(BASE_DIR, "rdf-data-input")
    filepath = os.path.join(input_dir, file.replace("/", os.sep))

    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"File not found: {file}")

    # Prevent path traversal
    if not os.path.abspath(filepath).startswith(os.path.abspath(input_dir)):
        raise HTTPException(status_code=400, detail="Invalid file path")

    graph_uri = graph if graph else graph_uri_from_path(filepath, input_dir)

    success = load_rdf_file(filepath, graph_uri, indent="  ")
    if not success:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {file}")

    # Recount
    count = len([q for q in store.quads_for_pattern(None, None, None, NamedNode(graph_uri))])

    return JSONResponse({
        "message": f"Loaded {file} into <{graph_uri}>",
        "graph": graph_uri,
        "tripleCount": count
    })


@app.post("/api/graphs/reload")
async def reload_all_graphs():
    """Reload all files from rdf-data-input, each into its own named graph."""
    global store
    store = Store()
    input_dir = os.path.join(BASE_DIR, "rdf-data-input")

    if os.path.exists(input_dir):
        load_rdf_directory_recursive(input_dir)

    # Recount
    graphs = set()
    total = 0
    for quad in store:
        total += 1
        if quad.graph_name:
            graphs.add(str(quad.graph_name))

    return JSONResponse({
        "message": "Reloaded all files",
        "totalQuads": total,
        "namedGraphs": len(graphs)
    })


# =========================================================================
# Class Explorer API Endpoints
# =========================================================================

@app.get("/api/class/neighbors")
async def get_class_neighbors(uri: str = Query(..., description="Class URI")):
    """Get neighboring classes connected via object properties, plus super/sub classes."""
    if store is None:
        raise HTTPException(status_code=500, detail="Store not initialized")
    try:
        import urllib.parse
        class_uri = urllib.parse.unquote(uri)

        query = f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?neighbor ?label ?property ?propertyLabel ?direction ?relType
        WHERE {{
          GRAPH ?g {{
            {{
                ?property a owl:ObjectProperty ;
                          rdfs:domain <{class_uri}> ;
                          rdfs:range ?neighbor .
                OPTIONAL {{ ?neighbor rdfs:label ?label }}
                OPTIONAL {{ ?property rdfs:label ?propertyLabel }}
                BIND("outgoing" AS ?direction)
                BIND("objectProperty" AS ?relType)
            }}
            UNION
            {{
                ?property a owl:ObjectProperty ;
                          rdfs:domain ?neighbor ;
                          rdfs:range <{class_uri}> .
                OPTIONAL {{ ?neighbor rdfs:label ?label }}
                OPTIONAL {{ ?property rdfs:label ?propertyLabel }}
                BIND("incoming" AS ?direction)
                BIND("objectProperty" AS ?relType)
            }}
            UNION
            {{
                <{class_uri}> rdfs:subClassOf ?neighbor .
                OPTIONAL {{ ?neighbor rdfs:label ?label }}
                BIND("superClass" AS ?direction)
                BIND("subClassOf" AS ?relType)
                BIND(rdfs:subClassOf AS ?property)
                BIND("subClassOf" AS ?propertyLabel)
                FILTER(!isBlank(?neighbor) && ?neighbor != <{class_uri}>)
            }}
            UNION
            {{
                ?neighbor rdfs:subClassOf <{class_uri}> .
                OPTIONAL {{ ?neighbor rdfs:label ?label }}
                BIND("subClass" AS ?direction)
                BIND("subClassOf" AS ?relType)
                BIND(rdfs:subClassOf AS ?property)
                BIND("subClassOf" AS ?propertyLabel)
                FILTER(!isBlank(?neighbor) && ?neighbor != <{class_uri}>)
            }}
            FILTER(!isBlank(?neighbor))
          }}
        }}
        ORDER BY ?direction ?label
        """

        neighbors = []
        seen = set()
        for row in store.query(query):
            n_uri = uri_str(row['neighbor'])
            prop = uri_str(row['property'])
            direction = str(row['direction']).strip('"') if row['direction'] else 'unknown'
            rel_type = str(row['relType']).strip('"') if row['relType'] else 'unknown'
            key = f"{n_uri}|{prop}|{direction}"
            if key in seen:
                continue
            seen.add(key)
            neighbors.append({
                'uri': n_uri,
                'label': str(row['label']).strip('"') if row['label'] else label_from_uri(n_uri),
                'property': prop,
                'propertyLabel': str(row['propertyLabel']).strip('"') if row['propertyLabel'] else (label_from_uri(prop) if prop else None),
                'direction': direction,
                'relType': rel_type
            })

        return JSONResponse({"classUri": class_uri, "neighbors": neighbors})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/class/properties")
async def get_class_properties(uri: str = Query(..., description="Class URI")):
    """Get datatype and object properties for a class."""
    if store is None:
        raise HTTPException(status_code=500, detail="Store not initialized")
    try:
        import urllib.parse
        class_uri = urllib.parse.unquote(uri)

        query = f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?prop ?label ?type ?range
        WHERE {{
          GRAPH ?g {{
            {{
                ?prop a owl:DatatypeProperty ; rdfs:domain <{class_uri}> .
                OPTIONAL {{ ?prop rdfs:label ?label }}
                OPTIONAL {{ ?prop rdfs:range ?range }}
                BIND("datatype" AS ?type)
            }}
            UNION
            {{
                ?prop a owl:ObjectProperty ; rdfs:domain <{class_uri}> .
                OPTIONAL {{ ?prop rdfs:label ?label }}
                OPTIONAL {{ ?prop rdfs:range ?range }}
                BIND("object" AS ?type)
            }}
          }}
        }}
        ORDER BY ?type ?label
        """

        datatype = []
        object_props = []
        for row in store.query(query):
            p = {
                'uri': uri_str(row['prop']),
                'label': str(row['label']).strip('"') if row['label'] else label_from_uri(uri_str(row['prop'])),
                'range': uri_str(row['range'])
            }
            if str(row['type']).strip('"') == 'datatype':
                datatype.append(p)
            else:
                object_props.append(p)

        return JSONResponse({
            "classUri": class_uri,
            "datatype": datatype,
            "object": object_props
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/class/restrictions")
async def get_class_restrictions(uri: str = Query(..., description="Class URI")):
    """Get OWL restrictions, cardinality constraints, property characteristics, and disjoint classes for a class."""
    if store is None:
        raise HTTPException(status_code=500, detail="Store not initialized")
    try:
        import urllib.parse
        class_uri = urllib.parse.unquote(uri)

        restrictions = []
        seen_keys = set()

        # Helper to query one cardinality predicate
        def _query_cardinality(card_pred, card_label):
            q = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?prop ?propLabel ?cardValue ?onClass ?onDataRange
            WHERE {{
              GRAPH ?g {{
                <{class_uri}> rdfs:subClassOf ?r .
                ?r a owl:Restriction ;
                   owl:onProperty ?prop ;
                   {card_pred} ?cardValue .
                OPTIONAL {{ ?prop rdfs:label ?propLabel }}
                OPTIONAL {{ ?r owl:onClass ?onClass }}
                OPTIONAL {{ ?r owl:onDataRange ?onDataRange }}
              }}
            }}
            """
            for row in store.query(q):
                prop_uri = uri_str(row['prop'])
                cv = _clean_literal(row['cardValue'])
                entry = {
                    'property': prop_uri,
                    'propertyLabel': str(row['propLabel']).strip('"') if row['propLabel'] else label_from_uri(prop_uri),
                    'cardinality': f"{card_label} {cv}",
                }
                if row['onClass']:
                    oc = uri_str(row['onClass'])
                    entry['onClass'] = oc
                    entry['onClassLabel'] = label_from_uri(oc)
                if row['onDataRange']:
                    dr = uri_str(row['onDataRange'])
                    entry['onDataRange'] = dr
                    entry['onDataRangeLabel'] = label_from_uri(dr) if dr else None
                dk = f"{prop_uri}|{entry['cardinality']}|{entry.get('onClass','')}|{entry.get('onDataRange','')}"
                if dk not in seen_keys:
                    seen_keys.add(dk)
                    restrictions.append(entry)

        _query_cardinality('owl:qualifiedCardinality', 'exactly')
        _query_cardinality('owl:minQualifiedCardinality', 'min')
        _query_cardinality('owl:maxQualifiedCardinality', 'max')
        _query_cardinality('owl:cardinality', 'exactly')
        _query_cardinality('owl:minCardinality', 'min')
        _query_cardinality('owl:maxCardinality', 'max')

        # Value constraints (min/max/pattern on datatype restrictions)
        for constraint_pred, constraint_label in [
            ('xsd:minInclusive', 'min'),
            ('xsd:maxInclusive', 'max'),
            ('xsd:pattern', 'pattern')
        ]:
            vc_q = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?prop ?constraintValue WHERE {{
              GRAPH ?g {{
                <{class_uri}> rdfs:subClassOf ?r .
                ?r a owl:Restriction ; owl:onProperty ?prop .
                {{ ?r owl:allValuesFrom ?dr }} UNION {{ ?r owl:onDataRange ?dr }}
                ?dr owl:withRestrictions ?resList .
                ?resList rdf:rest*/rdf:first ?restriction .
                ?restriction {constraint_pred} ?constraintValue .
              }}
            }}
            """
            try:
                for row in store.query(vc_q):
                    prop_uri = uri_str(row['prop'])
                    cv = _clean_literal(row['constraintValue'])
                    vc_str = f"{constraint_label}: {cv}"
                    # Attach to existing restriction entry
                    found = False
                    for entry in restrictions:
                        if entry['property'] == prop_uri:
                            if 'valueConstraints' not in entry:
                                entry['valueConstraints'] = []
                            if vc_str not in entry['valueConstraints']:
                                entry['valueConstraints'].append(vc_str)
                            found = True
                            break
                    if not found:
                        restrictions.append({
                            'property': prop_uri,
                            'propertyLabel': label_from_uri(prop_uri),
                            'valueConstraints': [vc_str]
                        })
            except Exception:
                pass  # Property path may not be supported; skip gracefully

        # Property characteristics
        characteristics = {}
        for char_type_uri, char_label in [
            ('owl:FunctionalProperty', 'Functional'),
            ('owl:AsymmetricProperty', 'Asymmetric'),
            ('owl:IrreflexiveProperty', 'Irreflexive'),
            ('owl:SymmetricProperty', 'Symmetric'),
            ('owl:TransitiveProperty', 'Transitive'),
            ('owl:InverseFunctionalProperty', 'InverseFunctional'),
            ('owl:ReflexiveProperty', 'Reflexive'),
        ]:
            cq = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT DISTINCT ?prop ?propLabel WHERE {{
              GRAPH ?g {{
                ?prop rdfs:domain <{class_uri}> .
                ?prop a {char_type_uri} .
                OPTIONAL {{ ?prop rdfs:label ?propLabel }}
              }}
            }}
            """
            try:
                for row in store.query(cq):
                    prop_uri = uri_str(row['prop'])
                    if prop_uri not in characteristics:
                        characteristics[prop_uri] = {
                            'property': prop_uri,
                            'propertyLabel': str(row['propLabel']).strip('"') if row['propLabel'] else label_from_uri(prop_uri),
                            'traits': [],
                            'inverseOf': None
                        }
                    if char_label not in characteristics[prop_uri]['traits']:
                        characteristics[prop_uri]['traits'].append(char_label)
            except Exception:
                pass

        # Inverse properties
        inv_q = f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?prop ?propLabel ?inverse WHERE {{
          GRAPH ?g {{
            ?prop rdfs:domain <{class_uri}> .
            ?prop owl:inverseOf ?inverse .
            OPTIONAL {{ ?prop rdfs:label ?propLabel }}
          }}
        }}
        """
        try:
            for row in store.query(inv_q):
                prop_uri = uri_str(row['prop'])
                if prop_uri not in characteristics:
                    characteristics[prop_uri] = {
                        'property': prop_uri,
                        'propertyLabel': str(row['propLabel']).strip('"') if row['propLabel'] else label_from_uri(prop_uri),
                        'traits': [],
                        'inverseOf': None
                    }
                characteristics[prop_uri]['inverseOf'] = uri_str(row['inverse'])
        except Exception:
            pass

        # Disjoint classes
        disjoint = []
        disjoint_q = f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT DISTINCT ?other ?otherLabel WHERE {{
          GRAPH ?g {{
            ?dc a owl:AllDisjointClasses ;
                owl:members ?list .
            ?list rdf:rest*/rdf:first <{class_uri}> .
            ?list rdf:rest*/rdf:first ?other .
            FILTER(?other != <{class_uri}>)
            OPTIONAL {{ ?other rdfs:label ?otherLabel }}
          }}
        }}
        """
        try:
            for row in store.query(disjoint_q):
                other_uri = uri_str(row['other'])
                disjoint.append({
                    'uri': other_uri,
                    'label': str(row['otherLabel']).strip('"') if row['otherLabel'] else label_from_uri(other_uri)
                })
        except Exception:
            pass

        # Class description
        desc_q = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?comment WHERE {{
          GRAPH ?g {{ <{class_uri}> rdfs:comment ?comment }}
        }} LIMIT 1
        """
        description = None
        try:
            for row in store.query(desc_q):
                if row['comment']:
                    description = _clean_literal(row['comment'])
        except Exception:
            pass

        return JSONResponse({
            "classUri": class_uri,
            "description": description,
            "restrictions": restrictions,
            "characteristics": list(characteristics.values()),
            "disjointWith": disjoint
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _collect_subclass_uris(class_uri: str) -> list:
    """Collect a class URI and all its subclass URIs (transitive) from the store."""
    all_classes = [class_uri]
    visited = {class_uri}
    frontier = [class_uri]

    while frontier:
        current = frontier.pop()
        sub_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?sub WHERE {{
            GRAPH ?g {{ ?sub rdfs:subClassOf <{current}> }}
            FILTER(!isBlank(?sub) && ?sub != <{current}>)
        }}
        """
        try:
            for row in store.query(sub_query):
                sub_uri = uri_str(row['sub'])
                if sub_uri not in visited:
                    visited.add(sub_uri)
                    all_classes.append(sub_uri)
                    frontier.append(sub_uri)
        except Exception:
            pass

    return all_classes


@app.get("/api/class/individuals")
async def get_class_individuals(uri: str = Query(..., description="Class URI"), limit: int = Query(20, ge=1, le=100)):
    """Get individuals/instances of a class (and its subclasses) with their data properties."""
    if store is None:
        raise HTTPException(status_code=500, detail="Store not initialized")
    try:
        import urllib.parse
        class_uri = urllib.parse.unquote(uri)

        # Collect the class and all transitive subclasses for inference
        target_classes = _collect_subclass_uris(class_uri)

        # Build a VALUES clause so we match instances of any subclass
        values_block = " ".join(f"<{c}>" for c in target_classes)

        query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?individual ?type ?label ?prop ?value
        WHERE {{
          VALUES ?type {{ {values_block} }}
          GRAPH ?g1 {{
            ?individual a ?type .
            FILTER(!isBlank(?individual))
          }}
          OPTIONAL {{
            GRAPH ?g2 {{ ?individual rdfs:label ?label }}
          }}
          OPTIONAL {{
            GRAPH ?g3 {{
              ?individual ?prop ?value .
              FILTER(isLiteral(?value))
              FILTER(?prop != rdf:type && ?prop != rdfs:label && ?prop != rdfs:comment)
            }}
          }}
        }}
        ORDER BY ?individual ?prop
        LIMIT {limit * 20}
        """

        individuals = {}
        for row in store.query(query):
            ind_uri = uri_str(row['individual'])
            if ind_uri not in individuals:
                ind_type = uri_str(row['type']) if row['type'] else class_uri
                individuals[ind_uri] = {
                    'uri': ind_uri,
                    'type': ind_type,
                    'typeLabel': label_from_uri(ind_type),
                    'label': str(row['label']).strip('"') if row['label'] else label_from_uri(ind_uri),
                    'properties': [],
                    '_seen_props': set()
                }
            if row['prop'] and row['value']:
                prop_uri = uri_str(row['prop'])
                val = _clean_literal(row['value'])
                prop_key = f"{prop_uri}|{val}"
                if prop_key not in individuals[ind_uri]['_seen_props']:
                    individuals[ind_uri]['_seen_props'].add(prop_key)
                    individuals[ind_uri]['properties'].append({
                        'uri': prop_uri,
                        'label': label_from_uri(prop_uri),
                        'value': val
                    })

        # Remove internal tracking key before returning
        result = []
        for ind in list(individuals.values())[:limit]:
            ind.pop('_seen_props', None)
            ind['objectProperties'] = []
            ind['incomingProperties'] = []
            result.append(ind)

        # Bulk-fetch object properties for all found individuals
        if result:
            ind_values = " ".join(f"<{ind['uri']}>" for ind in result)

            obj_query = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT DISTINCT ?individual ?prop ?target ?targetLabel
            WHERE {{
              VALUES ?individual {{ {ind_values} }}
              GRAPH ?g {{
                ?individual ?prop ?target .
                FILTER(isIRI(?target))
                FILTER(?prop != rdf:type)
              }}
              OPTIONAL {{ GRAPH ?g2 {{ ?target rdfs:label ?targetLabel }} }}
            }}
            ORDER BY ?individual ?prop
            """

            ind_lookup = {ind['uri']: ind for ind in result}
            for row in store.query(obj_query):
                i_uri = uri_str(row['individual'])
                if i_uri in ind_lookup:
                    prop_uri = uri_str(row['prop'])
                    target_uri = uri_str(row['target'])
                    ind_lookup[i_uri]['objectProperties'].append({
                        'uri': prop_uri,
                        'label': label_from_uri(prop_uri),
                        'target': target_uri,
                        'targetLabel': str(row['targetLabel']).strip('"') if row['targetLabel'] else label_from_uri(target_uri)
                    })

            inc_query = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT DISTINCT ?individual ?source ?sourceLabel ?prop
            WHERE {{
              VALUES ?individual {{ {ind_values} }}
              GRAPH ?g {{
                ?source ?prop ?individual .
                FILTER(isIRI(?source))
                FILTER(?prop != rdf:type)
              }}
              OPTIONAL {{ GRAPH ?g2 {{ ?source rdfs:label ?sourceLabel }} }}
            }}
            ORDER BY ?individual ?prop
            """

            for row in store.query(inc_query):
                i_uri = uri_str(row['individual'])
                if i_uri in ind_lookup:
                    src_uri = uri_str(row['source'])
                    prop_uri = uri_str(row['prop'])
                    ind_lookup[i_uri]['incomingProperties'].append({
                        'uri': prop_uri,
                        'label': label_from_uri(prop_uri),
                        'source': src_uri,
                        'sourceLabel': str(row['sourceLabel']).strip('"') if row['sourceLabel'] else label_from_uri(src_uri)
                    })

        return JSONResponse({
            "classUri": class_uri,
            "individuals": result,
            "count": len(result),
            "inferredClasses": [label_from_uri(c) for c in target_classes]
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/individual/details")
async def get_individual_details(uri: str = Query(..., description="Individual URI")):
    """Get full details of an individual: data properties and object property links."""
    if store is None:
        raise HTTPException(status_code=500, detail="Store not initialized")
    try:
        import urllib.parse
        ind_uri = urllib.parse.unquote(uri)

        # 1. Get label and type first (simple, separate queries)
        ind_label = label_from_uri(ind_uri)
        ind_type = None

        label_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?label WHERE {{ GRAPH ?g {{ <{ind_uri}> rdfs:label ?label }} }} LIMIT 1
        """
        for row in store.query(label_query):
            if row['label']:
                ind_label = str(row['label']).strip('"')

        type_query = f"""
        SELECT ?type WHERE {{ GRAPH ?g {{ <{ind_uri}> a ?type . FILTER(!isBlank(?type)) }} }} LIMIT 1
        """
        for row in store.query(type_query):
            if row['type']:
                ind_type = uri_str(row['type'])

        # 2. Data properties (literal values only)
        data_query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?prop ?value
        WHERE {{
          GRAPH ?g {{
            <{ind_uri}> ?prop ?value .
            FILTER(isLiteral(?value))
            FILTER(?prop != rdf:type && ?prop != rdfs:label && ?prop != rdfs:comment)
          }}
        }}
        ORDER BY ?prop
        """

        data_props = []
        for row in store.query(data_query):
            prop_uri = uri_str(row['prop'])
            val = _clean_literal(row['value'])
            data_props.append({
                'uri': prop_uri,
                'label': label_from_uri(prop_uri),
                'value': val
            })

        # 3. Object properties (outgoing links to other named resources)
        obj_query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?prop ?target ?targetLabel
        WHERE {{
          GRAPH ?g {{
            <{ind_uri}> ?prop ?target .
            FILTER(isIRI(?target))
            FILTER(?prop != rdf:type)
          }}
          OPTIONAL {{ GRAPH ?g2 {{ ?target rdfs:label ?targetLabel }} }}
        }}
        ORDER BY ?prop
        """

        obj_props = []
        for row in store.query(obj_query):
            prop_uri = uri_str(row['prop'])
            target_uri = uri_str(row['target'])
            obj_props.append({
                'uri': prop_uri,
                'label': label_from_uri(prop_uri),
                'target': target_uri,
                'targetLabel': str(row['targetLabel']).strip('"') if row['targetLabel'] else label_from_uri(target_uri)
            })

        # 4. Incoming links
        inc_query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?source ?sourceLabel ?prop
        WHERE {{
          GRAPH ?g {{
            ?source ?prop <{ind_uri}> .
            FILTER(isIRI(?source))
            FILTER(?prop != rdf:type)
          }}
          OPTIONAL {{ GRAPH ?g2 {{ ?source rdfs:label ?sourceLabel }} }}
        }}
        ORDER BY ?prop
        """

        inc_props = []
        for row in store.query(inc_query):
            src_uri = uri_str(row['source'])
            prop_uri = uri_str(row['prop'])
            inc_props.append({
                'uri': prop_uri,
                'label': label_from_uri(prop_uri),
                'source': src_uri,
                'sourceLabel': str(row['sourceLabel']).strip('"') if row['sourceLabel'] else label_from_uri(src_uri)
            })

        return JSONResponse({
            "uri": ind_uri,
            "label": ind_label,
            "type": ind_type,
            "typeLabel": label_from_uri(ind_type) if ind_type else None,
            "dataProperties": data_props,
            "objectProperties": obj_props,
            "incomingProperties": inc_props
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    python rdf-workbench.py
    python rdf-workbench.py --port 8080
    python rdf-workbench.py --rdf-input /path/to/custom/rdf-folder
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
