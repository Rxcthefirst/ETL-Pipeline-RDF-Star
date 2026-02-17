# Dynamic RDF-star ETL Pipeline - User Guide

## Overview

This ETL pipeline transforms unstructured data (CSV files) into RDF-star knowledge graphs using YARRRML-star mapping specifications. The pipeline is **fully dynamic** - it parses YARRRML mapping files to understand data transformation rules, eliminating hardcoded mappings.

## Features

✅ **YARRRML-star Parser**: Automatically parses mapping files to extract transformation rules  
✅ **Dynamic Mapping**: No hardcoded properties - everything driven by YARRRML  
✅ **RDF-star Support**: Generates quoted triples for provenance and metadata annotations  
✅ **Multiple Sources**: Supports multiple CSV files with join capabilities  
✅ **Flexible Output**: TriG format with proper namespace prefixes  
✅ **Provenance Tracking**: Uses `rdf:reifies` pattern for rich metadata on triples  

## Architecture

```
┌─────────────────────┐
│  Configuration      │
│  (YAML)             │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐      ┌──────────────────┐
│  YARRRML-star       │◄─────┤  CSV Data Files  │
│  Mapping File       │      │  (data/*.csv)    │
└──────────┬──────────┘      └──────────────────┘
           │
           ▼
┌─────────────────────┐
│  YARRRML Parser     │
│  (yarrrml_parser.py)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────┐
│  RDF-star ETL Engine    │
│  (dynamic processing)   │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  RDF-star Output        │
│  (TriG format)          │
└─────────────────────────┘
```

## File Structure

```
ETL-RDF-STAR/
├── etl_pipeline_config.yaml          # Main configuration file
├── rdf_star_etl_engine_dynamic.py    # Dynamic ETL engine
├── yarrrml_parser.py                 # YARRRML-star parser
├── data/                             # Input CSV data
│   ├── data_products.csv
│   └── lineage.csv
├── mappings/                         # YARRRML-star mappings
│   └── data_products_rml.yaml
├── output/                           # Generated RDF-star output
│   └── output_data_star.trig
└── logs/                             # Pipeline logs
```

## Quick Start

### 1. Configure the Pipeline

Edit `etl_pipeline_config.yaml`:

```yaml
pipeline:
  mapping_file: "mappings/data_products_rml.yaml"
  data_directory: "data"
  output_rdfstar: "output/output_data_star.trig"
  rdf_format: "TRIG"
```

### 2. Prepare Your Data

Place CSV files in the `data/` directory that align with your YARRRML mappings.

Example - `data/data_products.csv`:
```csv
dataset_id,title,issued,owner,theme_uri
DS001,Customer Segmentation Dataset,2025-01-15,DataGovernanceTeam,http://example.org/themes/CustomerAnalytics
DS002,Mortgage Risk Analysis,2025-02-10,RiskManagement,http://example.org/themes/fibo/MortgageRisk
```

### 3. Create YARRRML Mapping

Define your transformation rules in `mappings/data_products_rml.yaml`:

```yaml
prefixes:
  ex:   "http://example.org/"
  dcat: "http://www.w3.org/ns/dcat#"
  dct:  "http://purl.org/dc/terms/"
  prov: "http://www.w3.org/ns/prov#"
  xsd:  "http://www.w3.org/2001/XMLSchema#"

mappings:
  # Base dataset mapping
  datasetTM:
    sources:
      - ['data_products.csv~csv']
    subject: ex:dataset/$(dataset_id)
    predicateobjects:
      - [a, dcat:Dataset]
      - [dct:title, $(title), xsd:string]
      - [dct:issued, $(issued), xsd:date]
```

### 4. Run the Pipeline

```bash
python rdf_star_etl_engine_dynamic.py
```

### 5. Inspect Output

The RDF-star output will be in `output/output_data_star.trig`:

```turtle
@prefix ex: <http://example.org/> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .

<http://example.org/dataset/DS001> a dcat:Dataset ;
    dct:title "Customer Segmentation Dataset"^^xsd:string ;
    dct:issued "2025-01-15"^^xsd:date .
```

## YARRRML-star Features Supported

### 1. Standard Triples

```yaml
datasetTM:
  sources:
    - ['data_products.csv~csv']
  subject: ex:dataset/$(dataset_id)
  predicateobjects:
    - [a, dcat:Dataset]
    - [dct:title, $(title), xsd:string]
```

### 2. IRI Objects

```yaml
predicateobjects:
  - predicates: dcat:theme
    objects:
      value: $(theme_uri)
      type: iri
```

### 3. Typed Literals

```yaml
predicateobjects:
  - [dct:issued, $(issued), xsd:date]
  - [ex:confidence, $(confidence), xsd:decimal]
```

### 4. Quoted Triples (RDF-star)

Link metadata to specific triples:

```yaml
# Base triple
datasetThemeTM:
  sources:
    - ['data_products.csv~csv']
  subject: ex:dataset/$(dataset_id)
  predicateobjects:
    - predicates: dcat:theme
      objects:
        value: $(theme_uri)
        type: iri

# Metadata about the triple above
themeGovernanceTM:
  sources:
    - ['lineage.csv~csv']
  subject:
    - function: join(quoted=datasetThemeTM, equal(str1=$(dataset_id), str2=$(dataset_id)))
  predicateobjects:
    - predicates: prov:wasDerivedFrom
      objects:
        value: ex:system/$(source_system)
        type: iri
    - [ex:confidence, $(confidence), xsd:decimal]
```

This generates:

```turtle
_:reifier1 rdf:reifies <<( ex:dataset/DS001 dcat:theme ex:themes/CustomerAnalytics )>> ;
    prov:wasDerivedFrom ex:system/COLLIBRA ;
    ex:confidence 0.95 .
```

## Advanced Usage

### Multiple CSV Sources

The parser automatically detects all CSV files referenced in mappings:

```python
from yarrrml_parser import YARRRMLParser

parser = YARRRMLParser("mappings/data_products_rml.yaml")
parser.parse()

csv_files = parser.get_required_csv_files()
# Returns: ['data_products.csv', 'lineage.csv']

for csv_file in csv_files:
    columns = parser.get_required_columns_for_source(csv_file)
    print(f"{csv_file}: {columns}")
```

### Custom Namespace Prefixes

Add custom prefixes in your YARRRML file:

```yaml
prefixes:
  ex:   "http://example.org/"
  myns: "http://mycompany.com/ontology/"
  fibo: "https://spec.edmcouncil.org/fibo/ontology/"
```

### Join Conditions

Link data from multiple CSV files:

```yaml
subject:
  - function: join(quoted=datasetThemeTM, equal(str1=$(dataset_id), str2=$(dataset_id)))
```

## Testing the Parser

Test YARRRML parsing independently:

```bash
python yarrrml_parser.py
```

Output:
```
=== YARRRML Parser Test ===

Prefixes: {'ex': 'http://example.org/', ...}
Number of triples maps: 4

--- Triples Map: datasetTM ---
Sources: ['data_products.csv']
Subject template: ex:dataset/$(dataset_id)
Type statements: ['dcat:Dataset']
...
```

## CSV Data Requirements

The pipeline determines required CSV columns from the YARRRML mappings. 

For the example mapping:
- **data_products.csv** requires: `dataset_id`, `title`, `issued`, `owner`, `theme_uri`
- **lineage.csv** requires: `dataset_id`, `source_system`, `extract_time`, `run_id`, `confidence`, `rule_id`

## Performance Statistics

After execution, the pipeline reports:

```
================================================================================
ETL Pipeline Complete
================================================================================
Duration: 0.02 seconds
Rows processed: 15
Triples generated: 40
Quoted triple annotations: 125
Total quads in store: 184
================================================================================
```

## Troubleshooting

### Error: "empty CSV"
- Ensure CSV files have data and proper headers
- Check file encoding (use UTF-8)

### Error: "No scheme found in an absolute IRI"
- Verify IRI values in CSV are complete URLs (e.g., `http://example.org/...`)
- Check YARRRML object type is set to `iri` for URI fields

### Missing Triples
- Run parser test: `python yarrrml_parser.py`
- Verify CSV column names match YARRRML template variables
- Check data directory path in config

## Extending the Pipeline

### Add New Data Sources

1. Create CSV file in `data/` directory
2. Add mapping in YARRRML file
3. Reference in `sources` section

### Custom Provenance

Modify `process_quoted_triples_map()` in `rdf_star_etl_engine_dynamic.py` to add custom metadata patterns.

### Alternative Output Formats

Change `rdf_format` in config:
- `TRIG` - TriG format (default)
- `NQUADS` - N-Quads
- `TURTLE` - Turtle (for single graph)

## Benefits of Dynamic Approach

### Before (Hardcoded)
❌ Properties hardcoded in Python  
❌ Schema changes require code updates  
❌ Difficult to maintain  
❌ Not reusable across projects  

### After (Dynamic)
✅ Properties defined in YARRRML  
✅ Schema changes only update YAML  
✅ Easy to maintain  
✅ Fully reusable - just swap YARRRML files  

## Next Steps

1. **Custom Ontologies**: Extend YARRRML with your domain ontologies
2. **SPARQL Endpoint**: Load output into a triplestore for querying
3. **Validation**: Add SHACL shapes for data quality validation
4. **Incremental Updates**: Implement change detection for large datasets

## Support

For issues or questions:
- Check YARRRML parser output for mapping validation
- Enable debug logging in config
- Review sample data files for format reference

