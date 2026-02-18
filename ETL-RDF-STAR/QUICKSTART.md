# RDF-star ETL Engine - Quick Start Guide

## Overview

The RDF-star ETL Engine processes YARRRML mapping files directly to generate RDF-star output. **No separate configuration file is required** - all configuration is derived from the YARRRML specification.

### Supported Data Formats

| Format | Status | Dependencies |
|--------|--------|--------------|
| **CSV** | ✅ Built-in | None |
| **JSON** (JSONPath) | ✅ Built-in | `jsonpath-ng` (optional) |
| **XML** (XPath) | ✅ Built-in | `lxml` (optional) |
| **PostgreSQL** | ✅ Supported | `psycopg2-binary` |
| **MySQL/MariaDB** | ✅ Supported | `mysql-connector-python` |
| **SQLite** | ✅ Built-in | None |
| **HTTP/REST API** | ✅ Supported | `requests` |
| **SPARQL Endpoint** | ✅ Supported | `SPARQLWrapper` |

---

## Quick Start

### Basic Usage

```bash
# Process a YARRRML mapping file
python rdf_star_etl_yarrrml.py mappings/your_mapping.yaml

# Specify custom output file
python rdf_star_etl_yarrrml.py mappings/your_mapping.yaml output/result.trig
```

### Example

```bash
# Process the sample data products mapping
cd E:\MorphKGC-Test\ETL-RDF-STAR
python rdf_star_etl_yarrrml.py mappings/data_products_rml.yaml
```

Output:
```
================================================================================
RDF-star ETL Pipeline - YARRRML Direct Processing
================================================================================
Duration: 4.02 seconds
Files processed: 2
Rows processed: 20000
Triples generated: 80000
Quoted triple annotations: 250000
================================================================================
```

---

## Data Format Examples

### CSV Files
```yaml
sources:
  csv-source:
    access: data/people.csv
    referenceFormulation: csv
    delimiter: ","
    encoding: utf-8

# Or shortcut format:
sources:
  - ['data/people.csv~csv']
```

### JSON with JSONPath
```yaml
sources:
  json-source:
    access: data/api_response.json
    referenceFormulation: jsonpath
    iterator: $.data.users[*]    # JSONPath to iterate over
```

### XML with XPath
```yaml
sources:
  xml-source:
    access: data/catalog.xml
    referenceFormulation: xpath
    iterator: //product          # XPath to select elements
```

### PostgreSQL Database
```yaml
sources:
  pg-source:
    type: postgresql
    access: localhost:5432/mydb
    credentials:
      username: ${PG_USER}       # From environment variable
      password: ${PG_PASSWORD}
    query: SELECT * FROM customers WHERE active = true
    ssl: true
```

### MySQL Database
```yaml
sources:
  mysql-source:
    type: mysql
    access: localhost:3306/ecommerce
    credentials:
      username: ${MYSQL_USER}
      password: ${MYSQL_PASSWORD}
    query: SELECT id, name, email FROM users
```

### SQLite (Local File)
```yaml
sources:
  sqlite-source:
    type: sqlite
    access: data/local.db
    query: SELECT * FROM products
```

### HTTP/REST API
```yaml
sources:
  api-source:
    type: remotefile
    access: https://api.example.com/v1/users
    referenceFormulation: jsonpath
    iterator: $.results[*]
    headers:
      Authorization: Bearer ${API_TOKEN}
```

### SPARQL Endpoint
```yaml
sources:
  sparql-source:
    type: sparql
    access: https://dbpedia.org/sparql
    query: |
      SELECT ?person ?name WHERE {
        ?person a dbo:Person ;
                rdfs:label ?name .
      } LIMIT 100
```

---

## Security: Environment Variables

**Never hardcode credentials in mapping files!**

Use `${VAR_NAME}` syntax to read from environment:

```yaml
credentials:
  username: ${DB_USER}
  password: ${DB_PASSWORD}
```

Set environment variables before running:

```bash
# Windows PowerShell
$env:DB_USER = "myuser"
$env:DB_PASSWORD = "secret123"

# Linux/macOS
export DB_USER=myuser
export DB_PASSWORD=secret123

# Then run the ETL
python rdf_star_etl_yarrrml.py mappings/database_mapping.yaml
```

---

## How It Works

The engine extracts all configuration from your YARRRML file:

| YARRRML Section | Purpose |
|-----------------|---------|
| `prefixes:` | RDF namespace prefixes |
| `sources:` | Data source definitions |
| `targets:` | Output file specification |
| `mappings:` | Triple generation rules |
| `base:` | Base IRI for relative URIs |
| `authors:` | Metadata about mapping authors |

### Example YARRRML Mapping

```yaml
# All configuration in one file!
base: http://example.org/

prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"
  xsd: "http://www.w3.org/2001/XMLSchema#"

# Optional: Define output target
targets:
  main-output:
    access: output/result.trig
    serialization: trig

# Your data sources
mappings:
  personMapping:
    sources:
      - ['data/persons.csv~csv']
    subjects: ex:person/$(id)
    predicateobjects:
      - [a, foaf:Person]
      - [foaf:name, $(name)]
      - [foaf:age, $(age), xsd:integer]
```

---

## Command Line Options

```bash
python rdf_star_etl_yarrrml.py [-h] mapping_file [output_file]

Arguments:
  mapping_file    Path to the YARRRML mapping file (required)
  output_file     Output file path (optional)

Options:
  -h, --help      Show help message
```

### Output File Resolution

If no output file is specified, the engine will:
1. Check YARRRML `targets:` section for output path
2. If no targets, create `output/<mapping_name>_output.trig`

---

## Source File Resolution

The engine automatically searches for source files in:
1. Same directory as the mapping file
2. Parent directory
3. `data/` subdirectory
4. `benchmark_data/` subdirectory
5. `csv_data/` subdirectory

You can use relative paths in your YARRRML:
```yaml
sources:
  - ['persons.csv~csv']           # Will find in any search directory
  - ['data/projects.csv~csv']     # Will find data/projects.csv
```

---

## Features Supported

### Core YARRRML
- ✅ Prefixes and namespaces
- ✅ Multiple data sources
- ✅ Subject templates
- ✅ Multiple subjects
- ✅ Predicate-object mappings
- ✅ Type statements
- ✅ Datatypes (static and reference)
- ✅ Language tags
- ✅ IRI objects
- ✅ Named graphs

### RDF-star
- ✅ Quoted triples in subjects
- ✅ Join conditions
- ✅ Annotations on quoted triples
- ✅ Inline join syntax

### Metadata
- ✅ Base IRI
- ✅ Authors
- ✅ ETL provenance metadata

---

## Migration from Config File

### Old Approach (Deprecated)
```bash
# Required separate config file
python rdf_star_etl_engine_optimized.py
# Uses etl_pipeline_config.yaml
```

### New Approach (Recommended)
```bash
# Direct YARRRML processing
python rdf_star_etl_yarrrml.py mappings/your_mapping.yaml
# No config file needed!
```

### Migration Steps

1. **Move configuration to YARRRML:**
   - Output path → `targets:` section
   - Data directory → Use relative paths in `sources:`
   
2. **Update your command:**
   ```bash
   # Old
   python rdf_star_etl_engine_optimized.py
   
   # New
   python rdf_star_etl_yarrrml.py mappings/your_mapping.yaml
   ```

3. **Delete config file** (optional - kept for backward compatibility)

---

## Troubleshooting

### "Source file not found"

The engine couldn't find your CSV file. Check:
1. File path is correct in YARRRML `sources:`
2. File exists in one of the search directories
3. Use absolute path if needed

### "No sources defined"

Your mapping is missing the `sources:` key:
```yaml
mappings:
  myMapping:
    sources:                    # Add this!
      - ['data/mydata.csv~csv']
    subjects: ...
```

### "Mapping file not found"

Check the path to your YARRRML file:
```bash
# Use correct path
python rdf_star_etl_yarrrml.py mappings/data_products_rml.yaml
```

---

## Performance

The engine uses optimized processing:
- **Polars** for fast CSV loading
- **Vectorized operations** for batch triple generation
- **Caching** for repeated data access
- **Bulk insertion** into RDF store

Typical performance:
- 10,000 rows → ~4 seconds
- 100,000 rows → ~30 seconds
- 1,000,000 rows → ~5 minutes

---

## Files

| File | Purpose |
|------|---------|
| `rdf_star_etl_yarrrml.py` | **Main ETL engine** (use this!) |
| `yarrrml_parser.py` | YARRRML parser |
| `rdf_star_etl_engine_optimized.py` | Legacy engine (backward compat) |
| `etl_pipeline_config.yaml` | Legacy config (deprecated) |

---

## Examples

### Simple Mapping
```bash
python rdf_star_etl_yarrrml.py mappings/simple.yaml
```

### Custom Output
```bash
python rdf_star_etl_yarrrml.py mappings/complex.yaml output/my_graph.trig
```

### Full Pipeline
```bash
# Process mapping
python rdf_star_etl_yarrrml.py mappings/data_products_rml.yaml output/data.trig

# Start SPARQL endpoint
python fastapi_sparql_server.py

# Query your data
curl http://localhost:8000/sparql -d "query=SELECT * WHERE { ?s ?p ?o } LIMIT 10"
```

---

## Next Steps

1. **Create your YARRRML mapping** - See `YARRRML_QUICK_REFERENCE.md`
2. **Prepare your data** - CSV files with your data
3. **Run the engine** - `python rdf_star_etl_yarrrml.py your_mapping.yaml`
4. **Query your RDF** - Use the SPARQL endpoint

---

## Support

- **Documentation:** `YARRRML_QUICK_REFERENCE.md`
- **Specification:** `YARRRML-SPECIFICATION.md`
- **Tests:** `python test_yarrrml_spec_comprehensive.py`
- **Examples:** `mappings/` directory

---

**Version:** 2.0 (YARRRML Direct)  
**Date:** February 2026

