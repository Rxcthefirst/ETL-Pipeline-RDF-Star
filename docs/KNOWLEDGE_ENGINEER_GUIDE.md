# Knowledge Engineer's Guide to Temporal Knowledge Graphs

## Overview

This guide explains how to manage **temporal knowledge graphs** using **named graphs** and **SPARQL queries** for tracking changes in materialized RDF data over time. This approach is designed for deployment to **AWS Neptune** or any SPARQL 1.1 compliant triplestore.

### What This Enables

- "What did we know about customer X on January 15th?"
- "Why did we believe their credit score was 720 at that time?"
- "What changed between yesterday's batch and today's?"
- "Show me all facts that were corrected after we learned new information"

### Resources

| Resource | Description |
|----------|-------------|
| `docs/NEPTUNE_TEMPORAL_QUERIES.md` | Comprehensive Neptune/SPARQL guide |
| `sparql/batch_queries.rq` | Reusable SPARQL query library |
| `batch_manager.py` | Python helper for local development |
| `batch_cli.py` | Command-line interface for batch operations |

---

## Core Concepts

### Bi-Temporal Provenance

Every fact in our knowledge graph has two temporal dimensions:

| Dimension | Description | Example |
|-----------|-------------|---------|
| **Valid Time** | When the fact was true in the real world | "Credit score was 720 from Jan 1 to Feb 15" |
| **Transaction Time** | When we recorded the fact in our system | "We learned this on Jan 5 in batch #42" |

### Batches as Named Graphs

Each ETL run creates a **batch** stored as a **named graph**:

```turtle
# Batch graph with data and provenance
<http://example.org/batch/2026-02-17T10:00:00Z> {
    ex:customer/123 schema:creditScore "720"^^xsd:integer .
    ex:customer/123 foaf:name "John Doe" .
    
    # RDF-star provenance annotation
    << ex:customer/123 schema:creditScore "720"^^xsd:integer >>
        prov:wasDerivedFrom ex:source/Experian ;
        prov:generatedAtTime "2026-02-17T09:45:00Z"^^xsd:dateTime ;
        ex:confidence "0.95"^^xsd:decimal .
}
```

### Metadata Graph

A central metadata graph tracks all batches:

```turtle
<http://example.org/graph/metadata> {
    <http://example.org/batch/2026-02-17T10:00:00Z>
        a ex:Batch ;
        ex:batchNumber 17 ;
        ex:status ex:BatchStatus/active ;
        dct:created "2026-02-17T10:00:00Z"^^xsd:dateTime ;
        ex:loadedAt "2026-02-17T10:05:00Z"^^xsd:dateTime ;
        ex:quadCount 350264 .
}
```

### Batch Lifecycle

```
PENDING → ACTIVE → SUPERSEDED → ARCHIVED → DELETED
   │         │          │           │          │
   │         │          │           │          └── Permanently removed
   │         │          │           └── Kept for compliance/audit
   │         │          └── Replaced by newer batch
   │         └── Current "source of truth"
   └── Created but not yet loaded
```

---

## Essential SPARQL Patterns

### Standard Prefixes

```sparql
PREFIX ex:     <http://example.org/>
PREFIX batch:  <http://example.org/batch/>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
PREFIX prov:   <http://www.w3.org/ns/prov#>
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX schema: <http://schema.org/>
```

### 1. Get the Active Batch

```sparql
SELECT ?batch ?batchNumber ?created ?quadCount
FROM <http://example.org/graph/metadata>
WHERE {
    ?batch a ex:Batch ;
           ex:status ex:BatchStatus/active ;
           ex:batchNumber ?batchNumber ;
           dct:created ?created .
    OPTIONAL { ?batch ex:quadCount ?quadCount }
}
```

### 2. Query Current Data

```sparql
SELECT ?predicate ?object
WHERE {
    # Find active batch
    GRAPH <http://example.org/graph/metadata> {
        ?batch ex:status ex:BatchStatus/active .
    }
    # Query from that batch
    GRAPH ?batch {
        ex:customer/123 ?predicate ?object .
    }
}
```

### 3. Point-in-Time Query

"What did we know on February 15th?"

```sparql
SELECT ?predicate ?object ?batchDate
WHERE {
    GRAPH <http://example.org/graph/metadata> {
        ?batch a ex:Batch ;
               ex:loadedAt ?loadedAt ;
               dct:created ?batchDate .
        FILTER(?loadedAt <= "2026-02-15T12:00:00Z"^^xsd:dateTime)
        
        OPTIONAL { ?batch ex:supersededAt ?supersededAt }
        FILTER(!BOUND(?supersededAt) || 
               ?supersededAt > "2026-02-15T12:00:00Z"^^xsd:dateTime)
    }
    
    GRAPH ?batch {
        ex:customer/123 ?predicate ?object .
    }
}
```

### 4. Provenance Query (RDF-star)

"Why did we believe this credit score?"

```sparql
SELECT ?score ?source ?confidence ?timestamp
FROM <http://example.org/batch/2026-02-17T10:00:00Z>
WHERE {
    ex:customer/123 schema:creditScore ?score .
    
    << ex:customer/123 schema:creditScore ?score >>
        prov:wasDerivedFrom ?source ;
        ex:confidence ?confidence ;
        prov:generatedAtTime ?timestamp .
}
```

### 5. Batch Comparison (Diff)

"What changed between batches?"

```sparql
SELECT ?changeType ?subject ?predicate ?object
WHERE {
    {
        # Added triples
        GRAPH <http://example.org/batch/2026-02-17T10:00:00Z> {
            ?subject ?predicate ?object .
        }
        FILTER NOT EXISTS {
            GRAPH <http://example.org/batch/2026-02-16T10:00:00Z> {
                ?subject ?predicate ?object .
            }
        }
        BIND("ADDED" AS ?changeType)
    }
    UNION
    {
        # Removed triples
        GRAPH <http://example.org/batch/2026-02-16T10:00:00Z> {
            ?subject ?predicate ?object .
        }
        FILTER NOT EXISTS {
            GRAPH <http://example.org/batch/2026-02-17T10:00:00Z> {
                ?subject ?predicate ?object .
            }
        }
        BIND("REMOVED" AS ?changeType)
    }
}
ORDER BY ?changeType ?subject
LIMIT 100
```

### 6. Value History Over Time

"How did the credit score change?"

```sparql
SELECT ?batchDate ?creditScore ?source ?confidence
WHERE {
    GRAPH <http://example.org/graph/metadata> {
        ?batch a ex:Batch ;
               dct:created ?batchDate .
    }
    GRAPH ?batch {
        ex:customer/123 schema:creditScore ?creditScore .
        
        OPTIONAL {
            << ex:customer/123 schema:creditScore ?creditScore >>
                prov:wasDerivedFrom ?source ;
                ex:confidence ?confidence .
        }
    }
}
ORDER BY ?batchDate
```

---

## Use Cases

### Use Case 1: Credit Score Audit

**Query:** Show credit score history with provenance

```sparql
SELECT ?batchNumber ?batchDate ?score ?source ?confidence
WHERE {
    GRAPH <http://example.org/graph/metadata> {
        ?batch a ex:Batch ;
               ex:batchNumber ?batchNumber ;
               dct:created ?batchDate .
    }
    GRAPH ?batch {
        ex:customer/123 schema:creditScore ?score .
        OPTIONAL {
            << ex:customer/123 schema:creditScore ?score >>
                prov:wasDerivedFrom ?source ;
                ex:confidence ?confidence .
        }
    }
}
ORDER BY ?batchDate
```

**Result:**
| batchNumber | batchDate | score | source | confidence |
|-------------|-----------|-------|--------|------------|
| 12 | 2026-02-13 | 710 | ex:source/TransUnion | 0.90 |
| 13 | 2026-02-14 | 715 | ex:source/Equifax | 0.92 |
| 14 | 2026-02-15 | 715 | ex:source/Equifax | 0.92 |
| 15 | 2026-02-16 | 720 | ex:source/Experian | 0.95 |
| 16 | 2026-02-17 | 720 | ex:source/Experian | 0.98 |

### Use Case 2: Data Correction Audit

**Query:** What changed when a correction was applied?

```sparql
SELECT ?changeType ?predicate ?oldValue ?newValue
WHERE {
    {
        GRAPH <http://example.org/batch/2026-02-16T10:00:00Z> {
            ex:customer/123 ?predicate ?newValue .
        }
        FILTER NOT EXISTS {
            GRAPH <http://example.org/batch/2026-02-15T10:00:00Z> {
                ex:customer/123 ?predicate ?newValue .
            }
        }
        BIND("ADDED" AS ?changeType)
    }
    UNION
    {
        GRAPH <http://example.org/batch/2026-02-15T10:00:00Z> {
            ex:customer/123 ?predicate ?oldValue .
        }
        FILTER NOT EXISTS {
            GRAPH <http://example.org/batch/2026-02-16T10:00:00Z> {
                ex:customer/123 ?predicate ?oldValue .
            }
        }
        BIND("REMOVED" AS ?changeType)
    }
}
ORDER BY ?changeType ?predicate
```

### Use Case 3: Regulatory Inquiry

**Question:** "What data did you have when the loan decision was made on Feb 10th?"

```sparql
SELECT ?predicate ?value ?source ?confidence
WHERE {
    # Find batch active at decision time
    GRAPH <http://example.org/graph/metadata> {
        ?batch a ex:Batch ;
               ex:loadedAt ?loadedAt .
        FILTER(?loadedAt <= "2026-02-10T14:00:00Z"^^xsd:dateTime)
        OPTIONAL { ?batch ex:supersededAt ?supersededAt }
        FILTER(!BOUND(?supersededAt) || 
               ?supersededAt > "2026-02-10T14:00:00Z"^^xsd:dateTime)
    }
    
    # Get all data with provenance
    GRAPH ?batch {
        ex:customer/123 ?predicate ?value .
        OPTIONAL {
            << ex:customer/123 ?predicate ?value >>
                prov:wasDerivedFrom ?source ;
                ex:confidence ?confidence .
        }
    }
}
ORDER BY ?predicate
```

---

## Batch Management SPARQL

### Register New Batch

```sparql
INSERT DATA {
    GRAPH <http://example.org/graph/metadata> {
        <http://example.org/batch/2026-02-17T10:00:00Z>
            a ex:Batch ;
            ex:batchNumber 17 ;
            ex:status ex:BatchStatus/active ;
            dct:created "2026-02-17T10:00:00Z"^^xsd:dateTime ;
            dct:description "Daily ETL run" .
    }
}
```

### Supersede Previous Batch

```sparql
DELETE {
    GRAPH <http://example.org/graph/metadata> {
        ?oldBatch ex:status ex:BatchStatus/active .
    }
}
INSERT {
    GRAPH <http://example.org/graph/metadata> {
        ?oldBatch ex:status ex:BatchStatus/superseded ;
                  ex:supersededAt "2026-02-17T10:00:00Z"^^xsd:dateTime ;
                  ex:supersededBy <http://example.org/batch/2026-02-17T10:00:00Z> .
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

### Archive Old Batches (30+ days)

```sparql
DELETE {
    GRAPH <http://example.org/graph/metadata> {
        ?batch ex:status ex:BatchStatus/superseded .
    }
}
INSERT {
    GRAPH <http://example.org/graph/metadata> {
        ?batch ex:status ex:BatchStatus/archived ;
               ex:archivedAt ?now .
    }
}
WHERE {
    BIND(NOW() AS ?now)
    GRAPH <http://example.org/graph/metadata> {
        ?batch a ex:Batch ;
               ex:status ex:BatchStatus/superseded ;
               dct:created ?created .
        FILTER(?now - ?created > "P30D"^^xsd:duration)
    }
}
```

### Delete a Batch

```sparql
# Step 1: Drop the graph data
DROP GRAPH <http://example.org/batch/2026-02-10T10:00:00Z>
```

```sparql
# Step 2: Update metadata
DELETE {
    GRAPH <http://example.org/graph/metadata> {
        <http://example.org/batch/2026-02-10T10:00:00Z> ex:status ?s .
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
        <http://example.org/batch/2026-02-10T10:00:00Z> ex:status ?s .
    }
}
```

---

## YARRRML Provenance Configuration

To enable full provenance tracking in your ETL:

```yaml
prefixes:
  ex: "http://example.org/"
  prov: "http://www.w3.org/ns/prov#"
  xsd: "http://www.w3.org/2001/XMLSchema#"

mappings:
  # Main data mapping
  customerMapping:
    sources:
      - ['data/customers.csv~csv']
    subjects: ex:customer/$(customer_id)
    predicateobjects:
      - [schema:creditScore, $(credit_score), xsd:integer]
      - [foaf:name, $(name)]
  
  # RDF-star provenance annotations
  creditScoreProvenance:
    sources:
      - ['data/customers.csv~csv']
    subject:
      quoted: customerMapping
      condition:
        function: equal
        parameters:
          - [str1, $(customer_id)]
          - [str2, $(customer_id)]
    predicateobjects:
      - [prov:wasDerivedFrom, ex:source/$(source_system)~iri]
      - [prov:generatedAtTime, $(extract_timestamp), xsd:dateTime]
      - [ex:confidence, $(confidence_score), xsd:decimal]
```

---

## Best Practices

### 1. Batch Naming

Use ISO 8601 timestamps:
```
http://example.org/batch/2026-02-17T10:00:00Z
```

### 2. Always Include Provenance

Every fact should have:
- `prov:wasDerivedFrom` - Source system
- `prov:generatedAtTime` - When recorded
- `ex:confidence` - Confidence score

### 3. Retention Policy

| Age | Status | Action |
|-----|--------|--------|
| 0-7 days | active/superseded | Keep |
| 7-30 days | superseded | Archive |
| 30-90 days | archived | Keep for compliance |
| 90+ days | archived | Delete |

### 4. Query Performance

- Use `LIMIT` on large result sets
- Index metadata graph properties
- Consider pre-computing common diffs

---

## Next Steps

1. **Review:** `docs/NEPTUNE_TEMPORAL_QUERIES.md` for comprehensive guide
2. **Use:** `sparql/batch_queries.rq` for reusable query templates
3. **Test:** Use `batch_cli.py` for local development
4. **Deploy:** Load batches to Neptune with named graph URIs

---

## Quick Reference

| Task | Key Pattern |
|------|-------------|
| Active batch | `?batch ex:status ex:BatchStatus/active` |
| Point-in-time | `FILTER(?loadedAt <= $date)` |
| Provenance | `<< ?s ?p ?o >> prov:wasDerivedFrom ?source` |
| Diff (added) | `FILTER NOT EXISTS { GRAPH $old { ?s ?p ?o } }` |
| History | Query all batches, `ORDER BY ?batchDate` |
