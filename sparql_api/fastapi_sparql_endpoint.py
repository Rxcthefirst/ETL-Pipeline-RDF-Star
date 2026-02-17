
"""
Example: FastAPI SPARQL endpoint using pyoxigraph
Install: pip install fastapi uvicorn pyoxigraph
Run: uvicorn fastapi_sparql_endpoint:app --reload
Query: POST http://localhost:8000/sparql with {"query": "SELECT * WHERE {?s ?p ?o}"}
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pyoxigraph import Store, RdfFormat
import json
from pathlib import Path

app = FastAPI(title="RDF-star Data Products SPARQL Endpoint")
store = Store()

# Load ontology and RDF-star instance data
print("Loading data into PyOxigraph store...")

# Load ontology
ontology_path = Path("../ETL-RDF-STAR/ontology/data_products_ontology.ttl")
if ontology_path.exists():
    with open(ontology_path, 'rb') as f:
        store.load(f, RdfFormat.TURTLE)
    print(f"✓ Loaded ontology from {ontology_path}")
else:
    print(f"✗ Ontology not found: {ontology_path}")

# Load RDF-star instance data
instance_path = Path("../ETL-RDF-STAR/output/output_data_star.trig")
if instance_path.exists():
    with open(instance_path, 'rb') as f:
        store.load(f, RdfFormat.TRIG)
    print(f"✓ Loaded instance data from {instance_path}")
else:
    print(f"✗ Instance data not found: {instance_path}")

total_quads = len(list(store))
print(f"✓ Total quads loaded: {total_quads:,}")
print("="*80)

class SPARQLQuery(BaseModel):
    query: str

@app.get("/")
def read_root():
    return {"message": "SPARQL Endpoint", "endpoint": "/sparql"}

@app.post("/sparql")
def sparql_endpoint(sparql_query: SPARQLQuery):
    try:
        query_results = store.query(sparql_query.query)

        # Handle different query types
        if isinstance(query_results, bool):
            # ASK query
            return {"type": "ask", "result": query_results}

        # SELECT query - get variable names BEFORE converting to list
        vars = []
        if hasattr(query_results, 'variables'):
            var_objects = query_results.variables
            vars = [str(v).lstrip('?') for v in var_objects]

        # Convert to list and build results
        output = []
        for row in query_results:
            row_dict = {}
            for var in vars:
                try:
                    value = row[var]
                    row_dict[var] = str(value)
                except (KeyError, IndexError):
                    row_dict[var] = None
            output.append(row_dict)

        return {
            "type": "select",
            "variables": vars,
            "results": output,
            "count": len(output)
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}
