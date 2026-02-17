# Benchmark Data Generator for RDF-star ETL Pipeline

## Overview

This directory contains configuration files and scripts to generate large-scale benchmark datasets that align with the RDF-star ETL pipeline's expected schema for `data_products.csv` and `lineage.csv`.

## Quick Start

### Generate 10K rows (quick test)
```bash
python generate_benchmark_data.py --size 10k
```

### Generate 100K rows (medium benchmark)
```bash
python generate_benchmark_data.py --size 100k
```

### Generate 500K rows (large benchmark)
```bash
python generate_benchmark_data.py --size 500k
```

### Generate 1M rows (stress test)
```bash
python generate_benchmark_data.py --size 1m
```

## Configuration Files

### Pre-made Configurations

1. **`config_data_products_100k.json`** - Generates 100K data product records
   - Columns: dataset_id, title, issued, owner, theme_uri
   - Matches schema of `ETL-RDF-STAR/data/data_products.csv`

2. **`config_lineage_100k.json`** - Generates 100K lineage records
   - Columns: dataset_id, source_system, extract_time, run_id, confidence, rule_id
   - Matches schema of `ETL-RDF-STAR/data/lineage.csv`

3. **`config_mortgage_500k.json`** - Original mortgage loan example (500K rows)

## Using Individual Configs

### Generate data_products only
```bash
python generate_large_dataset.py \
  --config config_data_products_100k.json \
  --output ../ETL-RDF-STAR/benchmark_data/data_products_100k.csv
```

### Generate lineage only
```bash
python generate_large_dataset.py \
  --config config_lineage_100k.json \
  --output ../ETL-RDF-STAR/benchmark_data/lineage_100k.csv
```

## Using the Benchmark Script (Recommended)

The `generate_benchmark_data.py` script generates **both** files with **matching dataset_ids**, which is essential for the RDF-star join operations.

### Features
- ✅ Generates both data_products and lineage files
- ✅ Ensures matching dataset_ids across files
- ✅ Uses same random seed for consistency
- ✅ Calculates expected RDF-star output statistics
- ✅ Saves configuration files for reproducibility

### Command Examples

```bash
# Quick test (10K rows, ~1.6 MB)
python generate_benchmark_data.py --size 10k

# Medium benchmark (100K rows, ~16 MB)
python generate_benchmark_data.py --size 100k

# Large benchmark (500K rows, ~80 MB)
python generate_benchmark_data.py --size 500k

# Stress test (1M rows, ~160 MB)
python generate_benchmark_data.py --size 1m

# Custom size
python generate_benchmark_data.py --custom 250000

# Specify output directory
python generate_benchmark_data.py --size 100k --output ../ETL-RDF-STAR/data

# Save configuration files used
python generate_benchmark_data.py --size 100k --save-configs
```

## Output Files

Generated files are saved to `../ETL-RDF-STAR/benchmark_data/` by default:

- `data_products_{size}.csv` - Dataset metadata
- `lineage_{size}.csv` - Provenance/lineage data

## Schema Details

### data_products.csv
```
dataset_id,title,issued,owner,theme_uri
DS-000001,Customer Segmentation Dataset,2025-01-15,DataGovernanceTeam,http://example.org/themes/CustomerAnalytics
```

**Columns:**
- `dataset_id`: Unique identifier (DS-XXXXXX format)
- `title`: Dataset name (20 different realistic titles)
- `issued`: Issue date (2023-01-01 to 2025-12-31)
- `owner`: Owning team (15 different teams)
- `theme_uri`: Theme classification URI (20 different themes)

### lineage.csv
```
dataset_id,source_system,extract_time,run_id,confidence,rule_id
DS-000001,COLLIBRA,2025-02-15T10:30:00Z,RUN_20250215_001,0.95,RULE_001
```

**Columns:**
- `dataset_id`: Matches data_products dataset_id
- `source_system`: Data catalog system (15 different systems)
- `extract_time`: Extraction timestamp (10 different times)
- `run_id`: ETL run identifier (10 different runs)
- `confidence`: Confidence score (0.75-0.99)
- `rule_id`: Governance rule applied (10 different rules)

## Expected RDF-star Output

For each dataset size, the ETL pipeline should generate:

| Size | Rows | Base Triples | Quoted Annotations | Total Quads | Est. Output Size |
|------|------|--------------|-----------------------|-------------|------------------|
| 10K  | 10,000 | 80,000 | 250,000 | ~330,000 | ~30 MB |
| 100K | 100,000 | 800,000 | 2,500,000 | ~3,300,000 | ~300 MB |
| 500K | 500,000 | 4,000,000 | 12,500,000 | ~16,500,000 | ~1.5 GB |
| 1M   | 1,000,000 | 8,000,000 | 25,000,000 | ~33,000,000 | ~3 GB |

**Calculation:**
- Base triples: Each dataset generates 8 triples (type, title, issued, publisher, theme + 3 activity triples)
- Quoted annotations: Each dataset has 5 properties × 5 annotation properties = 25 annotations
- Total quads: Base + annotations + reifiers

## Performance Testing

### Test Pipeline Performance

1. **Generate benchmark data:**
```bash
python generate_benchmark_data.py --size 100k --output ../ETL-RDF-STAR/benchmark_data
```

2. **Update ETL config to use benchmark data:**
```yaml
# ETL-RDF-STAR/etl_pipeline_config.yaml
pipeline:
  mapping_file: "mappings/data_products_rml.yaml"
  data_directory: "benchmark_data"  # Change from "data"
  output_rdfstar: "output/benchmark_100k.trig"
```

3. **Update YARRRML to reference new files:**
```yaml
# ETL-RDF-STAR/mappings/data_products_rml.yaml
sources:
  - ['data_products_100k.csv~csv']  # Update filename
  
# And for lineage:
sources:
  - ['lineage_100k.csv~csv']  # Update filename
```

4. **Run the ETL pipeline:**
```bash
cd ../ETL-RDF-STAR
python rdf_star_etl_engine_optimized.py
```

5. **Compare performance:**
- Original (10 rows): ~0.01 seconds
- 10K rows: ~1-2 seconds (expected)
- 100K rows: ~10-20 seconds (expected)
- 500K rows: ~60-120 seconds (expected)

## Customization

### Add New Enum Values

Edit the configuration files to add more variety:

```json
{
  "name": "source_system",
  "type": "enum",
  "values": [
    "COLLIBRA",
    "ALATION",
    "YOUR_SYSTEM_HERE"
  ]
}
```

### Change Date Ranges

```json
{
  "name": "issued",
  "type": "date",
  "format": "2023-01-01:2025-12-31"
}
```

### Adjust Confidence Range

```json
{
  "name": "confidence",
  "type": "float",
  "min": 0.75,
  "max": 0.99,
  "decimals": 2
}
```

## Troubleshooting

### Issue: Out of Memory
**Solution:** Generate smaller batches or use streaming mode

### Issue: Different dataset_ids in files
**Solution:** Use `generate_benchmark_data.py` instead of individual configs - it uses the same seed

### Issue: Slow generation
**Solution:** Normal - generating 500K rows takes ~5-10 seconds

## Files in This Directory

```
csv_generator/
├── generate_large_dataset.py           # Core generator
├── generate_benchmark_data.py          # Benchmark data generator (use this!)
├── config_data_products_100k.json      # Data products config
├── config_lineage_100k.json            # Lineage config
├── config_mortgage_500k.json           # Original mortgage example
├── config_data_products_10k.json       # Generated 10K config
├── config_lineage_10k.json             # Generated 10K config
└── README_BENCHMARK.md                 # This file
```

## Next Steps

1. Generate benchmark data
2. Update ETL pipeline config to use benchmark files
3. Run performance tests
4. Compare optimized vs original engine
5. Profile with larger datasets

---

**Created:** February 15, 2026  
**Purpose:** Performance benchmarking for RDF-star ETL pipeline  
**Status:** ✅ Ready for use

