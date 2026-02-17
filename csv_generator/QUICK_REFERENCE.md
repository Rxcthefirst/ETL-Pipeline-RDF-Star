
# Quick Reference - Benchmark Data Generator

## Generate Benchmark Data

```bash
cd E:\MorphKGC-Test\csv_generator

# Quick test (10K rows, ~2 MB, <1 second)
python generate_benchmark_data.py --size 10k

# Medium benchmark (100K rows, ~17 MB, ~2 seconds)
python generate_benchmark_data.py --size 100k

# Large benchmark (500K rows, ~85 MB, ~10 seconds)
python generate_benchmark_data.py --size 500k

# Stress test (1M rows, ~170 MB, ~20 seconds)
python generate_benchmark_data.py --size 1m
```

## Run ETL Pipeline on Benchmark Data

### 1. Update config (one-time setup)
Edit `E:\MorphKGC-Test\ETL-RDF-STAR\etl_pipeline_config.yaml`:
```yaml
data_directory: "benchmark_data"  # Change from "data"
```

### 2. Update YARRRML (one-time setup)
Edit `E:\MorphKGC-Test\ETL-RDF-STAR\mappings\data_products_rml.yaml`:
- Change `data_products.csv` → `data_products_100k.csv`
- Change `lineage.csv` → `lineage_100k.csv`

### 3. Run benchmark
```bash
cd E:\MorphKGC-Test\ETL-RDF-STAR
python rdf_star_etl_engine_optimized.py
```

## Expected Performance

| Size | Generation | ETL Processing | Output Size |
|------|-----------|----------------|-------------|
| 10K  | <1 sec    | ~5-10 sec      | ~30 MB      |
| 100K | ~2 sec    | ~60-120 sec    | ~300 MB     |
| 500K | ~10 sec   | ~5-10 min      | ~1.5 GB     |
| 1M   | ~20 sec   | ~10-20 min     | ~3 GB       |

## Files Generated

```
ETL-RDF-STAR/benchmark_data/
├── data_products_10k.csv
├── lineage_10k.csv
├── data_products_100k.csv
├── lineage_100k.csv
├── data_products_500k.csv
└── lineage_500k.csv
```

## Configurations

**Pre-made configs:**
- `config_data_products_100k.json` - Data products schema
- `config_lineage_100k.json` - Lineage schema
- `config_mortgage_500k.json` - Original mortgage example

**Generated configs (with --save-configs):**
- `config_data_products_{size}.json`
- `config_lineage_{size}.json`

## Troubleshooting

**Q: Files don't match (different dataset_ids)?**  
A: Use `generate_benchmark_data.py` (not individual configs) - it ensures matching IDs

**Q: Out of memory?**  
A: Use smaller size or process in batches

**Q: ETL pipeline not finding files?**  
A: Check `data_directory` in config and file names in YARRRML

## Quick Commands

```bash
# Generate + save configs
python generate_benchmark_data.py --size 100k --save-configs

# Custom size
python generate_benchmark_data.py --custom 250000

# Custom output dir
python generate_benchmark_data.py --size 100k --output ./my_data

# View first 10 rows
head -10 ../ETL-RDF-STAR/benchmark_data/data_products_10k.csv
```

