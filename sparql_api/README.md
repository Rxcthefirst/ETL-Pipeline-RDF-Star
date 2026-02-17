# RDF-star SPARQL API

FastAPI endpoint serving RDF-star data products with governance metadata.

## Quick Start

```bash
cd E:\MorphKGC-Test\sparql_api
uvicorn fastapi_sparql_endpoint:app --reload --port 8000
```

Server will start at: `http://localhost:8000`

## Data Loaded

- **Ontology:** `../ETL-RDF-STAR/ontology/data_products_ontology.ttl`
- **Instance Data:** `../ETL-RDF-STAR/output/output_data_star.trig`
- **Total:** 350,415 quads

## Endpoints

- `GET /` - Root
- `POST /sparql` - SPARQL query endpoint
- `GET /health` - Health check

## Example Query (PowerShell)

```powershell
$query = @{
    query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/sparql" `
    -Method POST `
    -Body $query `
    -ContentType "application/json"
```

## Postman Collection

Import: `../ETL-RDF-STAR/RDF_Star_Data_Products.postman_collection.json`

**Note:** Collection is configured for port 8000.

## Server is Running

The server is currently running in the background. Test with Postman!

