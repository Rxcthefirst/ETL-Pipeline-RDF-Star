# Batch Simulation Test Suite

## Overview

This test suite demonstrates the temporal knowledge graph batch management system with:
- Two ETL batches with customer data
- Point-in-time queries
- Batch comparisons (diff)
- RDF-star provenance tracking

## Quick Start

### 1. Generate Test Data

```bash
cd E:\MorphKGC-Test\ETL-RDF-STAR
python simulate_batch_flow.py
```

This creates `output/batch_simulation/two_batches.trig` with:
- **Batch 1** (Feb 15): 4 customers (C001-C004)
- **Batch 2** (Feb 17): 4 customers (C001-C003, C005)

### 2. Start the SPARQL Server

```bash
python batch_sparql_server.py --port 7878
```

Server runs at: http://localhost:7878

### 3. Import Postman Collection

Import: `sparql/Batch_Temporal_Queries.postman_collection.json`

### 4. Run Tests

Run the Postman collection to verify all temporal query patterns.

---

## Test Data Changes

| Customer | Batch 1 (Feb 15) | Batch 2 (Feb 17) | Change |
|----------|------------------|------------------|--------|
| C001 Alice | Score: 720 | Score: 735 | +15 (improved) |
| C002 Bob | Score: 680 | Score: 675 | -5 (decreased) |
| C003 Carol | Score: 750 | Score: 750 | No change |
| C004 David | Score: 695 | - | REMOVED |
| C005 Eve | - | Score: 710 | NEW |

---

## Postman Test Categories

### 1. Server Health (2 tests)
- Server stats
- List batches API

### 2. Batch Management (2 tests)
- List all batches (SPARQL)
- Get active batch

### 3. Point-in-Time Queries (6 tests)
- Alice score in Batch 1 (720)
- Alice score in Batch 2 (735)
- David in Batch 1 (exists)
- David in Batch 2 (removed)
- Eve in Batch 1 (not exists)
- Eve in Batch 2 (new customer)

### 4. Batch Comparison/Diff (3 tests)
- Added triples
- Removed triples
- Full diff with change type

### 5. Provenance Queries (2 tests)
- Alice provenance in Batch 1
- All customer provenance (active batch)

### 6. Value History (2 tests)
- Alice score history across batches
- All customer scores comparison

### 7. Regulatory Scenarios (2 tests)
- "What did we know on Feb 15?"
- "Why did we believe this score?"

---

## Key SPARQL Patterns

### Get Active Batch
```sparql
SELECT ?batch ?batchNumber
FROM <http://example.org/graph/metadata>
WHERE {
    ?batch a <http://example.org/Batch> ;
           <http://example.org/status> <http://example.org/BatchStatus/active> ;
           <http://example.org/batchNumber> ?batchNumber .
}
```

### Point-in-Time Query
```sparql
SELECT ?score
FROM <http://example.org/batch/2026-02-15T10:00:00Z>
WHERE {
    <http://example.org/customer/C001> <http://schema.org/creditScore> ?score .
}
```

### Batch Diff (Added)
```sparql
SELECT ?subject ?predicate ?object
WHERE {
    GRAPH <http://example.org/batch/2026-02-17T10:00:00Z> { ?subject ?predicate ?object }
    FILTER NOT EXISTS {
        GRAPH <http://example.org/batch/2026-02-15T10:00:00Z> { ?subject ?predicate ?object }
    }
}
```

### Provenance Query
```sparql
SELECT ?score ?source ?confidence
FROM <http://example.org/batch/2026-02-15T10:00:00Z>
WHERE {
    <http://example.org/customer/C001> <http://schema.org/creditScore> ?score .
    ?r <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> 
        << <http://example.org/customer/C001> <http://schema.org/creditScore> ?score >> .
    ?r <http://www.w3.org/ns/prov#wasDerivedFrom> ?source .
    OPTIONAL { ?r <http://example.org/confidence> ?confidence }
}
```

---

## Server Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page with API info |
| `/stats` | GET | Server statistics |
| `/batches` | GET | List all batches |
| `/sparql` | GET/POST | SPARQL endpoint |
| `/docs` | GET | Swagger UI |

---

## Files

| File | Description |
|------|-------------|
| `simulate_batch_flow.py` | Generates test data |
| `batch_sparql_server.py` | SPARQL server |
| `output/batch_simulation/two_batches.trig` | Test data |
| `sparql/Batch_Temporal_Queries.postman_collection.json` | Postman tests |
| `docs/KNOWLEDGE_ENGINEER_GUIDE.md` | Full documentation |
| `docs/NEPTUNE_TEMPORAL_QUERIES.md` | Neptune-specific guide |

