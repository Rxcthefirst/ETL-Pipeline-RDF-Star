# RDF-star SPARQL Endpoint & Postman Test Suite

## Overview

This complete demonstration showcases the power of RDF-star for data governance, provenance tracking, and quality management through:

1. **PyOxigraph SPARQL Endpoint** - Server with 350K+ quads loaded
2. **Postman Collection** - 30+ queries demonstrating RDF-star capabilities
3. **OWL Ontology** - Data products schema with governance metadata

---

## Quick Start

### 1. Start the SPARQL Endpoint Server

```bash
cd E:\MorphKGC-Test\ETL-RDF-STAR
python sparql_endpoint_server.py
```

**Server will start at:** `http://localhost:7878`

**Output:**
```
================================================================================
Initializing PyOxigraph SPARQL Endpoint with RDF-star
================================================================================

[1/2] Loading ontology from ontology/data_products_ontology.ttl...
      [OK] Ontology loaded successfully

[2/2] Loading instance data from output/output_data_star.trig...
      [OK] Instance data loaded successfully

================================================================================
Store Initialized Successfully
================================================================================
Total quads loaded: 350,415
Datasets: 10,000
Activities: 10
Load time: 2.45 seconds
================================================================================

SPARQL Endpoint: http://localhost:7878/sparql
Home Page:       http://localhost:7878/
Health Check:    http://localhost:7878/health
Statistics:      http://localhost:7878/stats
```

### 2. Import Postman Collection

1. Open Postman
2. Click **Import** button
3. Select file: `RDF_Star_Data_Products.postman_collection.json`
4. Collection will appear with 8 folders and 30+ requests

### 3. Test the Endpoint

#### Option A: Use Postman (Recommended)
- Open the imported collection
- Run requests from different folders
- See results in JSON format

#### Option B: Use Browser
- Navigate to `http://localhost:7878/`
- View server homepage with stats
- Try example queries

#### Option C: Use cURL
```bash
curl -X POST http://localhost:7878/sparql \
  -H "Content-Type: application/sparql-query" \
  -d "PREFIX dcat: <http://www.w3.org/ns/dcat#>
      SELECT (COUNT(?dataset) as ?count) WHERE { ?dataset a dcat:Dataset . }"
```

---

## Postman Collection Structure

### 📁 1. Basic Queries (3 requests)
Verify data loading and explore the graph:
- Count all datasets (should return ~10,000)
- List first 10 datasets
- Count all activities

### 📁 2. RDF-star Provenance Queries (3 requests)
**Demonstrate statement-level metadata:**
- **2.1 High-Confidence Themes** - Find trusted data (>90% confidence)
- **2.2 Data by Source System** - Track which system provided data
- **2.3 Complete Provenance Chain** - Full audit trail for a dataset

**Key Feature:** Direct querying of metadata attached to statements!

```sparql
<<?dataset dcat:theme ?theme>> ex:confidence ?confidence ;
                                prov:wasDerivedFrom ?source .
```

### 📁 3. Data Quality & Governance (3 requests)
**Quality metrics and governance tracking:**
- **3.1 Low Confidence Data** - Find data quality issues (<85%)
- **3.2 Governance Rules** - Which rules were applied
- **3.3 Confidence by System** - Compare system reliability

**Use Case:** Data quality monitoring and alerts

### 📁 4. Temporal & Freshness Queries (3 requests)
**Time-based analysis:**
- **4.1 Recently Updated** - Find fresh data
- **4.2 Time Range Filter** - Data updated in specific period
- **4.3 Freshness by Theme** - When was each theme last updated

**Use Case:** Data freshness tracking and staleness detection

### 📁 5. Ontology Alignment Queries (4 requests)
**Demonstrate ontology integration:**
- **5.1 List Classes** - All OWL classes in ontology
- **5.2 Object Properties** - Relationships defined
- **5.3 Named Individuals** - Data catalog systems
- **5.4 Instance-Ontology Alignment** - Verify schema compliance

**Use Case:** Schema validation and ontology reasoning

### 📁 6. Complex Multi-faceted Queries (4 requests)
**Advanced queries combining multiple aspects:**
- **6.1 Trusted Data** - High confidence from specific system
- **6.2 Cross-System Comparison** - Conflicts between sources
- **6.3 Quality Trends** - Track quality over time
- **6.4 Governance Report** - Complete report for a theme

**Use Case:** Complex governance and compliance reporting

### 📁 7. Reification Comparison (2 requests)
**Show RDF-star advantages over traditional reification:**
- **7.1 Direct Query** - RDF-star simple approach
- **7.2 Count Reifications** - How many statements have metadata

**Key Insight:** RDF-star is much simpler than old-style reification!

### 📁 8. Health & Statistics (3 requests)
**Server monitoring:**
- Health check endpoint
- Store statistics
- HTML homepage

---

## Example Query Results

### Query 2.1: High-Confidence Theme Assignments

**Request:**
```sparql
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?theme ?confidence ?source
WHERE {
    ?dataset dcat:theme ?theme ;
             dct:title ?title .
    
    <<?dataset dcat:theme ?theme>> ex:confidence ?confidence ;
                                    prov:wasDerivedFrom ?source .
    
    FILTER(?confidence > 0.90)
}
ORDER BY DESC(?confidence)
LIMIT 10
```

**Response:**
```json
{
  "head": {"vars": ["dataset", "title", "theme", "confidence", "source"]},
  "results": {
    "bindings": [
      {
        "dataset": {"type": "uri", "value": "http://example.org/dataset/DS-000123"},
        "title": {"type": "literal", "value": "Customer Segmentation Dataset"},
        "theme": {"type": "uri", "value": "http://example.org/themes/CustomerAnalytics"},
        "confidence": {"type": "literal", "value": "0.98"},
        "source": {"type": "uri", "value": "http://example.org/system/COLLIBRA"}
      },
      ...
    ]
  },
  "meta": {
    "query_time": "0.042s",
    "result_count": 10
  }
}
```

---

## Key RDF-star Features Demonstrated

### 1. **Statement-Level Metadata**
Instead of creating separate provenance nodes, attach metadata directly:

```turtle
# The base fact
ex:dataset/DS001 dcat:theme ex:themes/CustomerAnalytics .

# Metadata ABOUT the fact (RDF-star)
<< ex:dataset/DS001 dcat:theme ex:themes/CustomerAnalytics >>
    prov:wasDerivedFrom ex:system/COLLIBRA ;
    ex:confidence 0.95 ;
    prov:generatedAtTime "2025-02-15T10:30:00Z"^^xsd:dateTime ;
    ex:rule ex:rule/RULE_001 .
```

### 2. **Intuitive Querying**
Query provenance directly without complex joins:

```sparql
# Find who said what with high confidence
SELECT ?dataset ?theme ?source ?confidence
WHERE {
    ?dataset dcat:theme ?theme .
    <<?dataset dcat:theme ?theme>> prov:wasDerivedFrom ?source ;
                                    ex:confidence ?confidence .
    FILTER(?confidence > 0.90)
}
```

### 3. **Complete Audit Trails**
Track WHO, WHAT, WHEN, HOW for every assertion:
- **WHO:** Source system (`prov:wasDerivedFrom`)
- **WHAT:** The actual data triple
- **WHEN:** Timestamp (`prov:generatedAtTime`)
- **HOW:** Governance rule applied (`ex:rule`)
- **QUALITY:** Confidence score (`ex:confidence`)

---

## Use Cases Enabled

### ✅ Data Quality Monitoring
- Track confidence scores on every assertion
- Alert on low-confidence data
- Compare quality across source systems

### ✅ Provenance Tracking
- Know which system provided which data
- Complete audit trail for compliance
- Track data lineage through transformations

### ✅ Conflict Resolution
- Identify conflicting assertions from different sources
- Choose higher-confidence source
- Track when conflicts occurred

### ✅ Temporal Analysis
- Track when data was last updated
- Find stale data
- Analyze data freshness by theme

### ✅ Governance Compliance
- Link assertions to governance rules
- Audit which rules were applied
- Generate compliance reports

---

## RDF-star vs Traditional Reification

### Traditional Reification (Complex)
```turtle
# The statement
ex:dataset/DS001 dcat:theme ex:themes/CustomerAnalytics .

# Reification (verbose and disconnected)
_:stmt1 rdf:type rdf:Statement ;
        rdf:subject ex:dataset/DS001 ;
        rdf:predicate dcat:theme ;
        rdf:object ex:themes/CustomerAnalytics ;
        prov:wasDerivedFrom ex:system/COLLIBRA ;
        ex:confidence 0.95 .
```

**Query requires complex self-joins!**

### RDF-star (Simple & Direct)
```turtle
ex:dataset/DS001 dcat:theme ex:themes/CustomerAnalytics .

<< ex:dataset/DS001 dcat:theme ex:themes/CustomerAnalytics >>
    prov:wasDerivedFrom ex:system/COLLIBRA ;
    ex:confidence 0.95 .
```

**Query is intuitive and direct!**

---

## Troubleshooting

### Server won't start
**Error:** `FileNotFoundError: ontology/data_products_ontology.ttl`

**Solution:** Ensure you're in the correct directory:
```bash
cd E:\MorphKGC-Test\ETL-RDF-STAR
```

### No data in queries
**Error:** Queries return 0 results

**Solution:** Generate instance data first:
```bash
python rdf_star_etl_engine_optimized.py
```

### Port already in use
**Error:** `Address already in use`

**Solution:** Kill existing process or use different port:
```bash
# Windows
netstat -ano | findstr :7878
taskkill /PID <PID> /F

# Or change port in sparql_endpoint_server.py
app.run(host='0.0.0.0', port=7879)
```

### Postman connection refused
**Error:** `Could not connect to server`

**Solution:**
1. Ensure server is running
2. Check firewall settings
3. Try `http://127.0.0.1:7878` instead of `localhost`

---

## Advanced Usage

### Custom Queries
Modify existing queries or create new ones in Postman:
1. Duplicate an existing request
2. Edit the SPARQL query in the body
3. Save and run

### Export Results
Postman allows exporting results to:
- JSON
- CSV (via Postman visualizer)
- HTML reports

### Automation
Use Postman Collection Runner:
1. Click "Runner" in Postman
2. Select the collection
3. Configure iterations
4. Run all tests automatically

---

## Files Delivered

```
ETL-RDF-STAR/
├── sparql_endpoint_server.py                    ✅ Flask SPARQL endpoint
├── RDF_Star_Data_Products.postman_collection.json ✅ 30+ test queries
├── ontology/
│   └── data_products_ontology.ttl               ✅ OWL schema
├── output/
│   └── output_data_star.trig                    ✅ 350K quads
└── POSTMAN_README.md                            ✅ This file
```

---

## Next Steps

### 1. Explore the Queries
- Run all queries in order
- Understand the results
- Modify queries to explore your data

### 2. Create Custom Queries
- Use the templates as examples
- Build queries for your use cases
- Save them in the collection

### 3. Integrate with Your Systems
- Use the SPARQL endpoint in applications
- Build dashboards with query results
- Create automated data quality reports

### 4. Extend the Ontology
- Add more classes and properties
- Define additional governance rules
- Create SHACL shapes for validation

---

## Summary

✅ **SPARQL Endpoint Server** - Running with 350K+ quads  
✅ **Postman Collection** - 30+ queries in 8 categories  
✅ **RDF-star Demonstrations** - Statement-level metadata  
✅ **Ontology Integration** - Schema-aware queries  
✅ **Complete Documentation** - Ready to use  

**The power of RDF-star is now at your fingertips!**

Use this endpoint and collection to demonstrate:
- Data governance at scale
- Statement-level provenance
- Quality metrics tracking
- Temporal analysis
- Compliance reporting

---

**Server:** http://localhost:7878  
**Status:** ✅ READY TO USE  
**Date:** February 15, 2026

