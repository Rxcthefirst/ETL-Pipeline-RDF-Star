# Knowledge Engineer's Guide to Temporal Knowledge Graphs in Neptune

## Overview

This guide explains how to manage **temporal knowledge graphs** using **pure SPARQL** on AWS Neptune (or any SPARQL 1.1 compliant triplestore). No Python code required for queries - everything is handled at the query level.

### Key Principles

1. **Batches are Named Graphs** - Each ETL run loads data into a distinct named graph
2. **Metadata Graph** - A special graph stores batch metadata
3. **RDF-star for Provenance** - Each triple has annotations for source, confidence, timestamp
4. **SPARQL for Everything** - Point-in-time queries, diffs, provenance - all in SPARQL

---

## Graph Architecture

### Named Graph Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NEPTUNE CLUSTER                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ <http://example.org/graph/metadata>                         │   │
│  │   - Batch registry                                          │   │
│  │   - Batch status (active, superseded, archived)             │   │
│  │   - Batch timestamps                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ <http://example.org/batch/2026-02-15T10:00:00Z>             │   │
│  │   - Data snapshot from Feb 15                               │   │
│  │   - Status: superseded                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ <http://example.org/batch/2026-02-16T10:00:00Z>             │   │
│  │   - Data snapshot from Feb 16                               │   │
│  │   - Status: superseded                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ <http://example.org/batch/2026-02-17T10:00:00Z>             │   │
│  │   - Data snapshot from Feb 17 (CURRENT)                     │   │
│  │   - Status: active                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Prefix Definitions

```sparql
PREFIX batch: <http://example.org/batch/>
PREFIX meta:  <http://example.org/graph/metadata/>
PREFIX ex:    <http://example.org/>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>
PREFIX prov:  <http://www.w3.org/ns/prov#>
PREFIX dct:   <http://purl.org/dc/terms/>
PREFIX schema: <http://schema.org/>
```

---

## Batch Metadata Schema

### Metadata Graph Structure

Every batch has metadata stored in a central metadata graph:

```sparql
# Metadata graph: <http://example.org/graph/metadata>

<http://example.org/batch/2026-02-17T10:00:00Z>
    a                       ex:Batch ;
    ex:batchNumber          17 ;
    ex:status               ex:BatchStatus/active ;
    dct:created             "2026-02-17T10:00:00Z"^^xsd:dateTime ;
    ex:loadedAt             "2026-02-17T10:05:23Z"^^xsd:dateTime ;
    ex:quadCount            350264 ;
    ex:sourceMapping        "mappings/data_products_rml.yaml" ;
    dct:description         "Daily ETL run - Production" ;
    ex:supersedes           <http://example.org/batch/2026-02-16T10:00:00Z> ;
    prov:wasGeneratedBy     <http://example.org/etl/run/2026-02-17> .
```

### Batch Status Values

```sparql
ex:BatchStatus/pending      # Created, not yet loaded
ex:BatchStatus/active       # Current production batch
ex:BatchStatus/superseded   # Replaced by newer batch
ex:BatchStatus/archived     # Kept for compliance
ex:BatchStatus/deleted      # Marked for removal
```

---

## Core SPARQL Patterns

### 1. Register a New Batch

When the ETL completes, insert metadata:

```sparql
PREFIX ex: <http://example.org/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX prov: <http://www.w3.org/ns/prov#>

INSERT DATA {
    GRAPH <http://example.org/graph/metadata> {
        <http://example.org/batch/2026-02-17T10:00:00Z>
            a                   ex:Batch ;
            ex:batchNumber      17 ;
            ex:status           ex:BatchStatus/active ;
            dct:created         "2026-02-17T10:00:00Z"^^xsd:dateTime ;
            ex:loadedAt         "2026-02-17T10:05:23Z"^^xsd:dateTime ;
            dct:description     "Daily ETL run" ;
            ex:sourceMapping    "mappings/data_products_rml.yaml" .
    }
}
```

### 2. Supersede Previous Batch

When loading a new batch, mark the old one as superseded:

```sparql
PREFIX ex: <http://example.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

# First, find and update the current active batch
DELETE {
    GRAPH <http://example.org/graph/metadata> {
        ?oldBatch ex:status ex:BatchStatus/active .
    }
}
INSERT {
    GRAPH <http://example.org/graph/metadata> {
        ?oldBatch ex:status ex:BatchStatus/superseded .
        ?oldBatch ex:supersededAt "2026-02-17T10:00:00Z"^^xsd:dateTime .
        ?oldBatch ex:supersededBy <http://example.org/batch/2026-02-17T10:00:00Z> .
    }
}
WHERE {
    GRAPH <http://example.org/graph/metadata> {
        ?oldBatch a ex:Batch ;
                  ex:status ex:BatchStatus/active .
        FILTER(?oldBatch != <http://example.org/batch/2026-02-17T10:00:00Z>)
    }
}
```

### 3. Get Active Batch

```sparql
PREFIX ex: <http://example.org/>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?batch ?created ?description ?quadCount
FROM <http://example.org/graph/metadata>
WHERE {
    ?batch a ex:Batch ;
           ex:status ex:BatchStatus/active ;
           dct:created ?created .
    OPTIONAL { ?batch dct:description ?description }
    OPTIONAL { ?batch ex:quadCount ?quadCount }
}
```

### 4. List All Batches

```sparql
PREFIX ex: <http://example.org/>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?batch ?batchNumber ?status ?created ?quadCount
FROM <http://example.org/graph/metadata>
WHERE {
    ?batch a ex:Batch ;
           ex:batchNumber ?batchNumber ;
           ex:status ?status ;
           dct:created ?created .
    OPTIONAL { ?batch ex:quadCount ?quadCount }
}
ORDER BY DESC(?batchNumber)
LIMIT 20
```

---

## Point-in-Time Queries

### "What Did We Know On Date X?"

Find the batch that was active at a specific point in time:

```sparql
PREFIX ex: <http://example.org/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

# Step 1: Find the batch active at the target date
SELECT ?batch
FROM <http://example.org/graph/metadata>
WHERE {
    ?batch a ex:Batch ;
           ex:loadedAt ?loadedAt .
    
    # Batch was loaded before our target date
    FILTER(?loadedAt <= "2026-02-15T12:00:00Z"^^xsd:dateTime)
    
    # And either still active OR superseded after our target date
    OPTIONAL {
        ?batch ex:supersededAt ?supersededAt .
    }
    FILTER(!BOUND(?supersededAt) || ?supersededAt > "2026-02-15T12:00:00Z"^^xsd:dateTime)
}
ORDER BY DESC(?loadedAt)
LIMIT 1
```

### Query Data at That Point in Time

Once you have the batch graph URI, query directly from it:

```sparql
PREFIX schema: <http://schema.org/>
PREFIX ex: <http://example.org/>

# Query customer data as of Feb 15, 2026
SELECT ?predicate ?object
FROM <http://example.org/batch/2026-02-15T10:00:00Z>
WHERE {
    ex:customer/123 ?predicate ?object .
}
```

### Combined Query: Data at Point in Time

```sparql
PREFIX ex: <http://example.org/>
PREFIX schema: <http://schema.org/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?predicate ?object ?batchDate
WHERE {
    # Find the relevant batch
    GRAPH <http://example.org/graph/metadata> {
        ?batch a ex:Batch ;
               ex:loadedAt ?loadedAt ;
               dct:created ?batchDate .
        FILTER(?loadedAt <= "2026-02-15T12:00:00Z"^^xsd:dateTime)
        OPTIONAL { ?batch ex:supersededAt ?supersededAt }
        FILTER(!BOUND(?supersededAt) || ?supersededAt > "2026-02-15T12:00:00Z"^^xsd:dateTime)
    }
    
    # Query data from that batch
    GRAPH ?batch {
        ex:customer/123 ?predicate ?object .
    }
}
ORDER BY ?predicate
```

---

## Provenance Queries (RDF-star)

### Data Model with Provenance

Each fact has RDF-star annotations:

```turtle
# In batch graph: <http://example.org/batch/2026-02-17T10:00:00Z>

ex:customer/123 schema:creditScore "720"^^xsd:integer .

# RDF-star annotation (provenance)
<< ex:customer/123 schema:creditScore "720"^^xsd:integer >>
    prov:wasDerivedFrom     ex:source/Experian ;
    prov:generatedAtTime    "2026-02-17T09:45:00Z"^^xsd:dateTime ;
    ex:confidence           "0.95"^^xsd:decimal ;
    prov:wasGeneratedBy     ex:etl/run/2026-02-17 .
```

### "Why Did We Believe This?"

Query provenance for a specific fact:

```sparql
PREFIX ex: <http://example.org/>
PREFIX schema: <http://schema.org/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?score ?source ?confidence ?timestamp ?etlRun
FROM <http://example.org/batch/2026-02-17T10:00:00Z>
WHERE {
    # The fact
    ex:customer/123 schema:creditScore ?score .
    
    # RDF-star provenance (Neptune syntax)
    BIND(<< ex:customer/123 schema:creditScore ?score >> AS ?triple)
    
    OPTIONAL { ?triple prov:wasDerivedFrom ?source }
    OPTIONAL { ?triple ex:confidence ?confidence }
    OPTIONAL { ?triple prov:generatedAtTime ?timestamp }
    OPTIONAL { ?triple prov:wasGeneratedBy ?etlRun }
}
```

### Get Full Provenance for a Subject

```sparql
PREFIX ex: <http://example.org/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?predicate ?object ?source ?confidence ?timestamp
FROM <http://example.org/batch/2026-02-17T10:00:00Z>
WHERE {
    ex:customer/123 ?predicate ?object .
    
    OPTIONAL {
        BIND(<< ex:customer/123 ?predicate ?object >> AS ?triple)
        ?triple prov:wasDerivedFrom ?source .
        OPTIONAL { ?triple ex:confidence ?confidence }
        OPTIONAL { ?triple prov:generatedAtTime ?timestamp }
    }
}
ORDER BY ?predicate
```

---

## Batch Comparison Queries

### Find Changes Between Batches

```sparql
PREFIX ex: <http://example.org/>

# Triples in batch2 but NOT in batch1 (ADDED)
SELECT ?subject ?predicate ?object
WHERE {
    GRAPH <http://example.org/batch/2026-02-17T10:00:00Z> {
        ?subject ?predicate ?object .
    }
    FILTER NOT EXISTS {
        GRAPH <http://example.org/batch/2026-02-16T10:00:00Z> {
            ?subject ?predicate ?object .
        }
    }
}
LIMIT 100
```

### Find Removed Triples

```sparql
PREFIX ex: <http://example.org/>

# Triples in batch1 but NOT in batch2 (REMOVED)
SELECT ?subject ?predicate ?object
WHERE {
    GRAPH <http://example.org/batch/2026-02-16T10:00:00Z> {
        ?subject ?predicate ?object .
    }
    FILTER NOT EXISTS {
        GRAPH <http://example.org/batch/2026-02-17T10:00:00Z> {
            ?subject ?predicate ?object .
        }
    }
}
LIMIT 100
```

### Find Modified Subjects

Subjects that exist in both batches but have different triples:

```sparql
PREFIX ex: <http://example.org/>

SELECT DISTINCT ?subject (COUNT(?p1) AS ?triplesInOld) (COUNT(?p2) AS ?triplesInNew)
WHERE {
    # Subject exists in both batches
    GRAPH <http://example.org/batch/2026-02-16T10:00:00Z> {
        ?subject ?p1 ?o1 .
    }
    GRAPH <http://example.org/batch/2026-02-17T10:00:00Z> {
        ?subject ?p2 ?o2 .
    }
    
    # But has at least one changed triple
    FILTER EXISTS {
        GRAPH <http://example.org/batch/2026-02-16T10:00:00Z> {
            ?subject ?px ?ox .
        }
        FILTER NOT EXISTS {
            GRAPH <http://example.org/batch/2026-02-17T10:00:00Z> {
                ?subject ?px ?ox .
            }
        }
    }
}
GROUP BY ?subject
LIMIT 100
```

### Diff Summary

```sparql
PREFIX ex: <http://example.org/>

SELECT 
    (COUNT(DISTINCT ?added) AS ?addedCount)
    (COUNT(DISTINCT ?removed) AS ?removedCount)
WHERE {
    {
        # Count added
        SELECT (CONCAT(STR(?s), STR(?p), STR(?o)) AS ?added)
        WHERE {
            GRAPH <http://example.org/batch/2026-02-17T10:00:00Z> { ?s ?p ?o }
            FILTER NOT EXISTS {
                GRAPH <http://example.org/batch/2026-02-16T10:00:00Z> { ?s ?p ?o }
            }
        }
    }
    UNION
    {
        # Count removed
        SELECT (CONCAT(STR(?s), STR(?p), STR(?o)) AS ?removed)
        WHERE {
            GRAPH <http://example.org/batch/2026-02-16T10:00:00Z> { ?s ?p ?o }
            FILTER NOT EXISTS {
                GRAPH <http://example.org/batch/2026-02-17T10:00:00Z> { ?s ?p ?o }
            }
        }
    }
}
```

---

## Credit Score History Example

### Track Credit Score Over Time

```sparql
PREFIX ex: <http://example.org/>
PREFIX schema: <http://schema.org/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?batchDate ?creditScore ?source ?confidence
WHERE {
    # Get all batches with their dates
    GRAPH <http://example.org/graph/metadata> {
        ?batch a ex:Batch ;
               dct:created ?batchDate .
    }
    
    # Get credit score from each batch
    GRAPH ?batch {
        ex:customer/123 schema:creditScore ?creditScore .
        
        # Get provenance if available
        OPTIONAL {
            << ex:customer/123 schema:creditScore ?creditScore >>
                prov:wasDerivedFrom ?source ;
                ex:confidence ?confidence .
        }
    }
}
ORDER BY ?batchDate
```

**Result:**
| batchDate | creditScore | source | confidence |
|-----------|-------------|--------|------------|
| 2026-02-13 | 710 | ex:source/TransUnion | 0.90 |
| 2026-02-14 | 715 | ex:source/Equifax | 0.92 |
| 2026-02-15 | 715 | ex:source/Equifax | 0.92 |
| 2026-02-16 | 720 | ex:source/Experian | 0.95 |
| 2026-02-17 | 720 | ex:source/Experian | 0.98 |

### When Did a Value Change?

```sparql
PREFIX ex: <http://example.org/>
PREFIX schema: <http://schema.org/>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?batch1Date ?oldScore ?batch2Date ?newScore
WHERE {
    # Get consecutive batches
    GRAPH <http://example.org/graph/metadata> {
        ?batch1 a ex:Batch ;
                ex:batchNumber ?num1 ;
                dct:created ?batch1Date .
        ?batch2 a ex:Batch ;
                ex:batchNumber ?num2 ;
                dct:created ?batch2Date .
        FILTER(?num2 = ?num1 + 1)
    }
    
    # Get scores from each batch
    GRAPH ?batch1 {
        ex:customer/123 schema:creditScore ?oldScore .
    }
    GRAPH ?batch2 {
        ex:customer/123 schema:creditScore ?newScore .
    }
    
    # Only show where it changed
    FILTER(?oldScore != ?newScore)
}
ORDER BY ?batch1Date
```

---

## Regulatory Audit Queries

### "What Data Did We Have When Decision Was Made?"

```sparql
PREFIX ex: <http://example.org/>
PREFIX schema: <http://schema.org/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

# Decision was made on Feb 15, 2026 at 2pm
# What data did we have at that moment?

SELECT ?predicate ?value ?source ?confidence ?recordedAt
WHERE {
    # Find the batch that was active at decision time
    GRAPH <http://example.org/graph/metadata> {
        ?batch a ex:Batch ;
               ex:loadedAt ?loadedAt .
        FILTER(?loadedAt <= "2026-02-15T14:00:00Z"^^xsd:dateTime)
        OPTIONAL { ?batch ex:supersededAt ?supersededAt }
        FILTER(!BOUND(?supersededAt) || ?supersededAt > "2026-02-15T14:00:00Z"^^xsd:dateTime)
    }
    
    # Get all data about the customer
    GRAPH ?batch {
        ex:customer/123 ?predicate ?value .
        
        # Get provenance
        OPTIONAL {
            << ex:customer/123 ?predicate ?value >>
                prov:wasDerivedFrom ?source ;
                ex:confidence ?confidence ;
                prov:generatedAtTime ?recordedAt .
        }
    }
}
ORDER BY ?predicate
```

### Complete Audit Trail for a Subject

```sparql
PREFIX ex: <http://example.org/>
PREFIX schema: <http://schema.org/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?batchNumber ?batchDate ?predicate ?value ?source ?confidence ?action
WHERE {
    # Get all batches
    GRAPH <http://example.org/graph/metadata> {
        ?batch a ex:Batch ;
               ex:batchNumber ?batchNumber ;
               dct:created ?batchDate .
    }
    
    # Check if subject exists in this batch
    {
        GRAPH ?batch {
            ex:customer/123 ?predicate ?value .
            OPTIONAL {
                << ex:customer/123 ?predicate ?value >>
                    prov:wasDerivedFrom ?source ;
                    ex:confidence ?confidence .
            }
        }
        BIND("present" AS ?action)
    }
}
ORDER BY ?batchNumber ?predicate
```

---

## Batch Lifecycle Management

### Archive Old Batches

```sparql
PREFIX ex: <http://example.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

# Archive batches older than 30 days that are superseded
DELETE {
    GRAPH <http://example.org/graph/metadata> {
        ?batch ex:status ex:BatchStatus/superseded .
    }
}
INSERT {
    GRAPH <http://example.org/graph/metadata> {
        ?batch ex:status ex:BatchStatus/archived .
        ?batch ex:archivedAt ?now .
    }
}
WHERE {
    BIND(NOW() AS ?now)
    GRAPH <http://example.org/graph/metadata> {
        ?batch a ex:Batch ;
               ex:status ex:BatchStatus/superseded ;
               dct:created ?created .
        FILTER(?created < ?now - "P30D"^^xsd:duration)
    }
}
```

### Delete Batch Data (Keep Metadata)

```sparql
PREFIX ex: <http://example.org/>

# Delete all triples in a batch graph (but keep metadata)
DROP GRAPH <http://example.org/batch/2026-02-10T10:00:00Z>
```

### Update Batch Metadata After Deletion

```sparql
PREFIX ex: <http://example.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

DELETE {
    GRAPH <http://example.org/graph/metadata> {
        <http://example.org/batch/2026-02-10T10:00:00Z> ex:status ?oldStatus .
    }
}
INSERT {
    GRAPH <http://example.org/graph/metadata> {
        <http://example.org/batch/2026-02-10T10:00:00Z> 
            ex:status ex:BatchStatus/deleted ;
            ex:deletedAt "2026-02-17T15:00:00Z"^^xsd:dateTime .
    }
}
WHERE {
    GRAPH <http://example.org/graph/metadata> {
        <http://example.org/batch/2026-02-10T10:00:00Z> ex:status ?oldStatus .
    }
}
```

---

## Neptune-Specific Considerations

### Loading Data via Bulk Loader

When using Neptune's bulk loader, specify the named graph:

```json
{
  "source": "s3://my-bucket/batch-2026-02-17/",
  "format": "nquads",
  "namedGraphUri": "http://example.org/batch/2026-02-17T10:00:00Z",
  "parserConfiguration": {
    "baseUri": "http://example.org/"
  }
}
```

### RDF-star in Neptune

Neptune supports RDF-star with SPARQL-star syntax:

```sparql
# Neptune RDF-star query
SELECT ?score ?source
WHERE {
    ex:customer/123 schema:creditScore ?score .
    << ex:customer/123 schema:creditScore ?score >> prov:wasDerivedFrom ?source .
}
```

### Graph Statistics

```sparql
# Count quads per batch
SELECT ?batch (COUNT(*) AS ?quadCount)
WHERE {
    GRAPH ?batch { ?s ?p ?o }
    FILTER(STRSTARTS(STR(?batch), "http://example.org/batch/"))
}
GROUP BY ?batch
ORDER BY DESC(?quadCount)
```

---

## Query Templates

### Template: Point-in-Time Subject Query

```sparql
# Parameters: $SUBJECT, $TARGET_DATE
PREFIX ex: <http://example.org/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?predicate ?object
WHERE {
    GRAPH <http://example.org/graph/metadata> {
        ?batch a ex:Batch ;
               ex:loadedAt ?loadedAt .
        FILTER(?loadedAt <= "$TARGET_DATE"^^xsd:dateTime)
        OPTIONAL { ?batch ex:supersededAt ?supersededAt }
        FILTER(!BOUND(?supersededAt) || ?supersededAt > "$TARGET_DATE"^^xsd:dateTime)
    }
    GRAPH ?batch {
        <$SUBJECT> ?predicate ?object .
    }
}
```

### Template: Batch Diff

```sparql
# Parameters: $OLD_BATCH, $NEW_BATCH
PREFIX ex: <http://example.org/>

SELECT ?changeType ?subject ?predicate ?object
WHERE {
    {
        SELECT ("added" AS ?changeType) ?subject ?predicate ?object
        WHERE {
            GRAPH <$NEW_BATCH> { ?subject ?predicate ?object }
            FILTER NOT EXISTS {
                GRAPH <$OLD_BATCH> { ?subject ?predicate ?object }
            }
        }
    }
    UNION
    {
        SELECT ("removed" AS ?changeType) ?subject ?predicate ?object
        WHERE {
            GRAPH <$OLD_BATCH> { ?subject ?predicate ?object }
            FILTER NOT EXISTS {
                GRAPH <$NEW_BATCH> { ?subject ?predicate ?object }
            }
        }
    }
}
ORDER BY ?changeType ?subject ?predicate
LIMIT 1000
```

### Template: Subject History

```sparql
# Parameters: $SUBJECT, $PREDICATE
PREFIX ex: <http://example.org/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?batchDate ?value ?source ?confidence
WHERE {
    GRAPH <http://example.org/graph/metadata> {
        ?batch a ex:Batch ;
               dct:created ?batchDate .
    }
    GRAPH ?batch {
        <$SUBJECT> <$PREDICATE> ?value .
        OPTIONAL {
            << <$SUBJECT> <$PREDICATE> ?value >>
                prov:wasDerivedFrom ?source ;
                ex:confidence ?confidence .
        }
    }
}
ORDER BY ?batchDate
```

---

## Best Practices

### 1. Batch Naming Convention

Use ISO 8601 timestamps in batch URIs:
```
http://example.org/batch/2026-02-17T10:00:00Z
```

### 2. Always Include Provenance

Every fact should have:
- `prov:wasDerivedFrom` - Source system
- `prov:generatedAtTime` - When recorded
- `ex:confidence` - Confidence score
- `prov:wasGeneratedBy` - ETL run identifier

### 3. Metadata Consistency

Always update metadata when:
- Creating a new batch
- Superseding old batches
- Archiving or deleting batches

### 4. Query Performance

- Use `LIMIT` on diff queries
- Create indexes on batch metadata properties
- Consider materialized views for frequent queries

### 5. Retention Policy

Implement via scheduled SPARQL UPDATE:
- Archive batches older than 30 days
- Delete archived batches older than 90 days

---

## Summary

| Task | SPARQL Pattern |
|------|----------------|
| Get active batch | `?batch ex:status ex:BatchStatus/active` |
| Point-in-time query | `FILTER(?loadedAt <= $date)` + `GRAPH ?batch { ... }` |
| Provenance | `<< ?s ?p ?o >> prov:wasDerivedFrom ?source` |
| Batch diff | `FILTER NOT EXISTS { GRAPH $other { ?s ?p ?o } }` |
| Value history | Query all batches, ORDER BY `?batchDate` |
| Supersede batch | DELETE/INSERT to update `ex:status` |

This approach gives you full temporal knowledge graph capabilities using only SPARQL queries - perfect for Neptune deployment!

