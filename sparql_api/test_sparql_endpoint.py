"""
Test script to demonstrate pyoxigraph SPARQL endpoint capabilities
Shows how to create and query a SPARQL endpoint with pyoxigraph
"""

import sys

# Test 1: Check if pyoxigraph has server capabilities
print("=" * 80)
print("TESTING PYOXIGRAPH SPARQL ENDPOINT CAPABILITIES")
print("=" * 80)

try:
    from pyoxigraph import Store
    print("\n✓ pyoxigraph Store imported successfully")
except ImportError:
    print("✗ pyoxigraph not installed. Installing now...")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyoxigraph'])
    from pyoxigraph import Store
    print("✓ pyoxigraph installed and imported")

# Check for server module
print("\n" + "=" * 80)
print("Checking for built-in HTTP server capabilities...")
print("=" * 80)

try:
    # Try importing server-related functionality
    import pyoxigraph
    available_modules = dir(pyoxigraph)

    print("\nAvailable pyoxigraph modules:")
    for module in sorted(available_modules):
        if not module.startswith('_'):
            print(f"  - {module}")

    # Check specifically for server-related components
    has_server = 'Server' in available_modules or 'serve' in available_modules

    if has_server:
        print("\n✓ Server module found in pyoxigraph!")
    else:
        print("\n⚠ No built-in Server module found in pyoxigraph")
        print("  Note: pyoxigraph focuses on the storage layer.")
        print("  For HTTP SPARQL endpoint, you can use external servers like:")
        print("    - Oxigraph server (standalone binary)")
        print("    - Custom Flask/FastAPI wrapper around pyoxigraph Store")

except Exception as e:
    print(f"Error checking modules: {e}")

# Test 2: Demonstrate programmatic SPARQL querying
print("\n" + "=" * 80)
print("PROGRAMMATIC SPARQL QUERY INTERFACE (Always Available)")
print("=" * 80)

# Create store and load sample data
store = Store()

sample_data = """
@prefix ex: <http://example.org/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:Alice a foaf:Person ;
    foaf:name "Alice Smith" ;
    foaf:age 30 ;
    foaf:knows ex:Bob .

ex:Bob a foaf:Person ;
    foaf:name "Bob Johnson" ;
    foaf:age 25 ;
    foaf:knows ex:Charlie .

ex:Charlie a foaf:Person ;
    foaf:name "Charlie Brown" ;
    foaf:age 35 .

# RDF-star metadata
<< ex:Alice foaf:knows ex:Bob >> ex:since "2020-01-01"^^xsd:date ;
    ex:confidence 0.95 .
"""

store.load(sample_data.encode('utf-8'), mime_type="text/turtle")
print("\n✓ Sample data loaded into store")

# Test various SPARQL query types
print("\n" + "-" * 80)
print("1. SELECT Query - Finding all persons")
print("-" * 80)

select_query = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>

SELECT ?person ?name ?age
WHERE {
    ?person a foaf:Person ;
            foaf:name ?name ;
            foaf:age ?age .
}
ORDER BY ?age
"""

results = store.query(select_query)
for row in results:
    print(f"  {row['name']} (age {row['age']})")

# Test ASK query
print("\n" + "-" * 80)
print("2. ASK Query - Does Alice know someone?")
print("-" * 80)

ask_query = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX ex: <http://example.org/>

ASK {
    ex:Alice foaf:knows ?someone .
}
"""

result = store.query(ask_query)
print(f"  Result: {result}")

# Test CONSTRUCT query
print("\n" + "-" * 80)
print("3. CONSTRUCT Query - Build new graph")
print("-" * 80)

construct_query = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX ex: <http://example.org/>

CONSTRUCT {
    ?person ex:hasConnection ?friend .
}
WHERE {
    ?person foaf:knows ?friend .
}
"""

result_graph = store.query(construct_query)
print("  Constructed triples:")
for triple in result_graph:
    print(f"    {triple.subject} -> {triple.object}")

# Test RDF-star SPARQL query
print("\n" + "-" * 80)
print("4. RDF-STAR SPARQL Query - Querying metadata on triples")
print("-" * 80)

rdf_star_query = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX ex: <http://example.org/>

SELECT ?person1 ?person2 ?since ?confidence
WHERE {
    ?person1 foaf:knows ?person2 .
    <<?person1 foaf:knows ?person2>> ex:since ?since ;
                                      ex:confidence ?confidence .
}
"""

results = store.query(rdf_star_query)
for row in results:
    print(f"  {row['person1']} knows {row['person2']} since {row['since']} (confidence: {row['confidence']})")

# Test 3: Integration options
print("\n" + "=" * 80)
print("SPARQL ENDPOINT INTEGRATION OPTIONS")
print("=" * 80)

print("""
pyoxigraph provides powerful SPARQL querying capabilities through its Store API.
For HTTP SPARQL endpoint access, you have these options:

1. **Oxigraph Server (Recommended)**
   - Standalone server application
   - Full SPARQL 1.1 Protocol support
   - Install: Download from https://github.com/oxigraph/oxigraph/releases
   - Usage: oxigraph_server --location ./data
   - Provides HTTP SPARQL endpoint at http://localhost:7878/query

2. **Custom Python Web Service** (Using Flask/FastAPI)
   - Wrap pyoxigraph Store with a web framework
   - Implement SPARQL protocol endpoints
   - Full control over authentication, caching, etc.

3. **Programmatic Integration** (Current approach)
   - Import pyoxigraph in your Python application
   - Call store.query() directly
   - No HTTP overhead, fastest performance
   - Best for embedded use cases

""")

print("=" * 80)
print("DEMONSTRATION: Creating a simple Flask SPARQL endpoint wrapper")
print("=" * 80)

# Create a simple Flask endpoint example
flask_example = '''
"""
Example: Simple Flask SPARQL endpoint using pyoxigraph
Install: pip install flask pyoxigraph
Run: python flask_sparql_endpoint.py
Query: POST http://localhost:5000/sparql with query parameter
"""

from flask import Flask, request, jsonify
from pyoxigraph import Store
import io

app = Flask(__name__)
store = Store()

# Load your data
data = """
@prefix ex: <http://example.org/> .
ex:Alice ex:knows ex:Bob .
"""
store.load(data.encode('utf-8'), mime_type="text/turtle")

@app.route('/sparql', methods=['GET', 'POST'])
def sparql_endpoint():
    # Get query from request
    if request.method == 'POST':
        query = request.form.get('query') or request.json.get('query')
    else:
        query = request.args.get('query')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        # Execute query
        results = store.query(query)
        
        # Format results
        output = []
        for row in results:
            output.append({var: str(row[var]) for var in row})
        
        return jsonify({"results": output})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
'''

print("\nSaving Flask SPARQL endpoint example...")

with open('flask_sparql_endpoint.py', 'w') as f:
    f.write(flask_example)

print("✓ Example saved to: flask_sparql_endpoint.py")

# FastAPI example
fastapi_example = '''
"""
Example: FastAPI SPARQL endpoint using pyoxigraph
Install: pip install fastapi uvicorn pyoxigraph
Run: uvicorn fastapi_sparql_endpoint:app --reload
Query: POST http://localhost:8000/sparql with {"query": "SELECT * WHERE {?s ?p ?o}"}
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pyoxigraph import Store
import json

app = FastAPI(title="Pyoxigraph SPARQL Endpoint")
store = Store()

# Load your data
data = """
@prefix ex: <http://example.org/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

ex:Alice a foaf:Person ; foaf:name "Alice Smith" .
ex:Bob a foaf:Person ; foaf:name "Bob Johnson" .
ex:Alice foaf:knows ex:Bob .
"""
store.load(data.encode('utf-8'), mime_type="text/turtle")

class SPARQLQuery(BaseModel):
    query: str

@app.get("/")
def read_root():
    return {"message": "SPARQL Endpoint", "endpoint": "/sparql"}

@app.post("/sparql")
def sparql_endpoint(sparql_query: SPARQLQuery):
    try:
        results = store.query(sparql_query.query)
        
        # Handle different query types
        if isinstance(results, bool):
            # ASK query
            return {"type": "ask", "result": results}
        
        # SELECT query - convert to list of dicts
        output = []
        for row in results:
            output.append({var: str(row[var]) for var in row})
        
        return {"type": "select", "results": output}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}
'''

with open('fastapi_sparql_endpoint.py', 'w') as f:
    f.write(fastapi_example)

print("✓ Example saved to: fastapi_sparql_endpoint.py")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
✓ pyoxigraph provides programmatic SPARQL querying (no HTTP server built-in)
✓ Supports all SPARQL 1.1 query types: SELECT, ASK, CONSTRUCT, DESCRIBE
✓ Supports RDF-star queries
✓ For HTTP SPARQL endpoint, use:
  - Oxigraph Server (standalone binary) - RECOMMENDED
  - Custom wrapper with Flask/FastAPI (examples created)
  
Example files created:
  - flask_sparql_endpoint.py (Flask-based SPARQL endpoint)
  - fastapi_sparql_endpoint.py (FastAPI-based SPARQL endpoint)
""")

print("=" * 80)

