# Pyoxigraph SPARQL Endpoint Integration Guide

## Summary

**Yes, pyoxigraph supports SPARQL querying, but it does NOT include a built-in HTTP server.**

For SPARQL endpoint integration, you have three main options:

---

## Option 1: Oxigraph Server (Standalone) - ⭐ RECOMMENDED

The **Oxigraph Server** is a standalone application that provides a full-featured HTTP SPARQL endpoint.

### Features:
- ✅ Full SPARQL 1.1 Protocol support
- ✅ SPARQL Query & Update
- ✅ RDF-star support
- ✅ High performance
- ✅ REST API
- ✅ Web UI for queries

### Installation:

Download from: https://github.com/oxigraph/oxigraph/releases

Or using cargo:
```bash
cargo install oxigraph_server
```

### Usage:

```bash
# Start server with persistent storage
oxigraph_server --location ./data

# Server runs at http://localhost:7878
# SPARQL endpoint: http://localhost:7878/query
# Update endpoint: http://localhost:7878/update
```

### Querying:

```bash
# Using curl
curl -X POST http://localhost:7878/query \
  -H "Content-Type: application/sparql-query" \
  --data "SELECT * WHERE { ?s ?p ?o } LIMIT 10"

# Or use GET
curl "http://localhost:7878/query?query=SELECT%20*%20WHERE%20%7B%20%3Fs%20%3Fp%20%3Fo%20%7D%20LIMIT%2010"
```

---

## Option 2: Custom Python Web Service (Flask/FastAPI)

Wrap pyoxigraph Store with a web framework for custom SPARQL endpoints.

### Flask Example:

See `flask_sparql_endpoint.py` for full implementation.

```python
from flask import Flask, request, jsonify
from pyoxigraph import Store

app = Flask(__name__)
store = Store()

@app.route('/sparql', methods=['GET', 'POST'])
def sparql_endpoint():
    query = request.form.get('query') or request.args.get('query')
    results = store.query(query)
    output = [{var: str(row[var]) for var in row} for row in results]
    return jsonify({"results": output})

if __name__ == '__main__':
    app.run(port=5000)
```

**Install:** `pip install flask pyoxigraph`  
**Run:** `python flask_sparql_endpoint.py`  
**Query:** `POST http://localhost:5000/sparql` with `query` parameter

### FastAPI Example:

See `fastapi_sparql_endpoint.py` for full implementation.

```python
from fastapi import FastAPI
from pydantic import BaseModel
from pyoxigraph import Store

app = FastAPI()
store = Store()

class SPARQLQuery(BaseModel):
    query: str

@app.post("/sparql")
def sparql_endpoint(sparql_query: SPARQLQuery):
    results = store.query(sparql_query.query)
    output = [{var: str(row[var]) for var in row} for row in results]
    return {"results": output}
```

**Install:** `pip install fastapi uvicorn pyoxigraph`  
**Run:** `uvicorn fastapi_sparql_endpoint:app --reload`  
**Query:** `POST http://localhost:8000/sparql` with JSON body `{"query": "..."}`

### Advantages of Custom Wrappers:
- Full control over authentication, authorization
- Custom caching strategies
- Integration with existing Python services
- Custom endpoints and functionality
- Logging and monitoring hooks

---

## Option 3: Programmatic Integration (In-Process)

Use pyoxigraph directly in your Python application without HTTP overhead.

### Example:

```python
from pyoxigraph import Store

store = Store()

# Load data
store.load(data.encode('utf-8'), mime_type="text/turtle")

# Query directly
query = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT ?name WHERE {
    ?person a foaf:Person ;
            foaf:name ?name .
}
"""

results = store.query(query)
for row in results:
    print(row['name'])
```

### Advantages:
- ✅ Fastest performance (no HTTP overhead)
- ✅ Perfect for embedded use cases
- ✅ Simplest to set up
- ✅ Direct Python API access

### Best For:
- Single application using RDF data
- Batch processing scripts
- Data transformation pipelines
- Development and testing

---

## SPARQL Query Support

Pyoxigraph supports **all SPARQL 1.1 query types**:

### 1. SELECT Queries
```sparql
SELECT ?person ?name
WHERE {
    ?person foaf:name ?name .
}
```

### 2. ASK Queries
```sparql
ASK {
    ?person foaf:knows ?other .
}
```

### 3. CONSTRUCT Queries
```sparql
CONSTRUCT {
    ?person ex:hasName ?name .
}
WHERE {
    ?person foaf:name ?name .
}
```

### 4. DESCRIBE Queries
```sparql
DESCRIBE <http://example.org/Alice>
```

### 5. RDF-STAR Queries
```sparql
SELECT ?person1 ?person2 ?certainty
WHERE {
    ?person1 foaf:knows ?person2 .
    <<?person1 foaf:knows ?person2>> ex:certainty ?certainty .
}
```

---

## Comparison Table

| Feature | Oxigraph Server | Flask/FastAPI Wrapper | Programmatic |
|---------|----------------|----------------------|--------------|
| HTTP Endpoint | ✅ Built-in | ✅ Custom | ❌ No |
| Performance | ⭐⭐⭐ High | ⭐⭐ Medium | ⭐⭐⭐ Highest |
| Setup Complexity | ⭐ Easy | ⭐⭐ Medium | ⭐ Easy |
| Customization | ⭐ Limited | ⭐⭐⭐ Full | ⭐⭐⭐ Full |
| SPARQL 1.1 Protocol | ✅ Yes | 🔧 Manual | ❌ N/A |
| Authentication | 🔧 Proxy | ✅ Custom | ❌ N/A |
| Use Case | Production server | Custom integration | Embedded/scripts |

---

## Testing Files Created

1. **test_rdf_star.py** - Confirms RDF-star support
2. **test_sparql_endpoint.py** - Demonstrates all SPARQL capabilities
3. **flask_sparql_endpoint.py** - Ready-to-use Flask SPARQL endpoint
4. **fastapi_sparql_endpoint.py** - Ready-to-use FastAPI SPARQL endpoint
5. **test_endpoint_client.py** - Client to test Flask endpoint

---

## Quick Start Guide

### For Production Use:
1. Download and install **Oxigraph Server**
2. Load your RDF data
3. Use the HTTP SPARQL endpoint at port 7878

### For Custom Integration:
1. Choose Flask or FastAPI based on your needs
2. Customize the example endpoints
3. Add authentication, logging, caching as needed

### For Development:
1. Use pyoxigraph programmatically
2. Call `store.query()` directly in your Python code
3. No server needed!

---

## Conclusion

✅ **Pyoxigraph provides excellent SPARQL support**  
✅ **Multiple integration options available**  
✅ **RDF-star fully supported**  
✅ **Production-ready with Oxigraph Server**  
✅ **Flexible for custom integrations**

The choice depends on your use case:
- **Need a ready-made server?** → Use Oxigraph Server
- **Need custom logic?** → Use Flask/FastAPI wrapper
- **Embedding in Python app?** → Use programmatic API

