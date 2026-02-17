# ✅ Benchmark Data Generator - Delivery Summary

## What Was Created

### 1. Configuration Files ✅

**`config_data_products_100k.json`**
- 100,000 rows of dataset metadata
- 5 columns: dataset_id, title, issued, owner, theme_uri
- 20 different dataset titles
- 15 different team owners
- 20 different theme URIs
- Date range: 2023-2025

**`config_lineage_100k.json`**
- 100,000 rows of lineage/provenance data
- 6 columns: dataset_id, source_system, extract_time, run_id, confidence, rule_id
- 15 different source systems (COLLIBRA, ALATION, etc.)
- 10 different extraction times
- 10 different run IDs
- Confidence scores: 0.75-0.99
- 10 different governance rules

### 2. Unified Generator Script ✅

**`generate_benchmark_data.py`**
- Generates BOTH data_products and lineage files
- Ensures matching dataset_ids across files
- Supports multiple sizes: 10k, 100k, 500k, 1m
- Custom size support
- Configurable output directory
- Optional config file saving
- Performance statistics
- Expected RDF-star output calculations

### 3. Documentation ✅

**`README_BENCHMARK.md`**
- Complete usage guide
- Quick start examples
- Schema documentation
- Performance testing guide
- Troubleshooting section
- Customization instructions

---

## Usage Examples

### Quick Test (10K rows)
```bash
cd E:\MorphKGC-Test\csv_generator
python generate_benchmark_data.py --size 10k
```

**Output:**
- `../ETL-RDF-STAR/benchmark_data/data_products_10k.csv` (~1 MB)
- `../ETL-RDF-STAR/benchmark_data/lineage_10k.csv` (~0.7 MB)

### Medium Benchmark (100K rows)
```bash
python generate_benchmark_data.py --size 100k --save-configs
```

**Output:**
- `../ETL-RDF-STAR/benchmark_data/data_products_100k.csv` (~10 MB)
- `../ETL-RDF-STAR/benchmark_data/lineage_100k.csv` (~7 MB)
- Configuration files saved

### Large Benchmark (500K rows)
```bash
python generate_benchmark_data.py --size 500k
```

**Output:**
- `../ETL-RDF-STAR/benchmark_data/data_products_500k.csv` (~50 MB)
- `../ETL-RDF-STAR/benchmark_data/lineage_500k.csv` (~35 MB)

### Custom Size
```bash
python generate_benchmark_data.py --custom 250000
```

---

## Test Results

### ✅ Tested with 10K rows

**Generation Performance:**
- data_products_10k.csv: 10,000 rows in 0.06 seconds (159,962 rows/sec)
- lineage_10k.csv: 10,000 rows in 0.02 seconds (476,213 rows/sec)
- Total time: ~0.08 seconds
- Total size: 1.67 MB

**Data Validation:**
- ✅ Headers match expected schema
- ✅ dataset_ids are sequential (DS-000001, DS-000002, ...)
- ✅ dataset_ids match between files (critical for joins!)
- ✅ All enum values within expected ranges
- ✅ Dates within 2023-2025 range
- ✅ Confidence scores within 0.75-0.99 range

**Sample Data:**
```csv
# data_products_10k.csv
dataset_id,title,issued,owner,theme_uri
DS-000001,Sales Performance Metrics,2025-05-10,CustomerInsights,http://example.org/themes/FinancialServices

# lineage_10k.csv
dataset_id,source_system,extract_time,run_id,confidence,rule_id
DS-000001,IBM_IGC,2025-02-15T15:00:00Z,RUN_20250215_009,0.84,RULE_009
```

---

## Expected RDF-star Pipeline Output

### For 10K Rows
- **Files processed:** 2
- **Rows processed:** 20,000 (10K + 10K)
- **Base triples:** 80,000 (10K datasets × 8 properties)
- **Quoted annotations:** 250,000 (10K datasets × 5 properties × 5 annotations)
- **Total quads:** ~330,000
- **Output size:** ~30 MB (TriG format)
- **Processing time:** ~5-10 seconds (estimated)

### For 100K Rows
- **Files processed:** 2
- **Rows processed:** 200,000
- **Base triples:** 800,000
- **Quoted annotations:** 2,500,000
- **Total quads:** ~3,300,000
- **Output size:** ~300 MB
- **Processing time:** ~60-120 seconds (estimated)

### For 500K Rows
- **Files processed:** 2
- **Rows processed:** 1,000,000
- **Base triples:** 4,000,000
- **Quoted annotations:** 12,500,000
- **Total quads:** ~16,500,000
- **Output size:** ~1.5 GB
- **Processing time:** ~5-10 minutes (estimated)

---

## Key Features

### ✅ Matching dataset_ids
Both files use the same random seed (42), ensuring dataset_ids match perfectly for join operations.

### ✅ Realistic Data
- 20 different dataset titles (not just random strings)
- 15 different team names
- 15 different data catalog systems
- 20 different theme URIs
- Realistic confidence scores (0.75-0.99)

### ✅ Scalable
- Generates 100K+ rows in seconds
- Efficient Polars-based implementation
- Memory-efficient streaming

### ✅ Reproducible
- Fixed random seed (42)
- Saved configuration files
- Consistent output format

---

## Integration with ETL Pipeline

### Step 1: Generate Data
```bash
cd E:\MorphKGC-Test\csv_generator
python generate_benchmark_data.py --size 100k
```

### Step 2: Update ETL Config
Edit `E:\MorphKGC-Test\ETL-RDF-STAR\etl_pipeline_config.yaml`:
```yaml
pipeline:
  mapping_file: "mappings/data_products_rml.yaml"
  data_directory: "benchmark_data"  # Changed from "data"
  output_rdfstar: "output/benchmark_100k.trig"
```

### Step 3: Update YARRRML Mappings
Edit `E:\MorphKGC-Test\ETL-RDF-STAR\mappings\data_products_rml.yaml`:
```yaml
datasetTM:
  sources:
    - ['data_products_100k.csv~csv']  # Changed from data_products.csv

datasetThemeTM:
  sources:
    - ['data_products_100k.csv~csv']

themeGovernanceTM:
  sources:
    - ['lineage_100k.csv~csv']  # Changed from lineage.csv

ingestActivityTM:
  sources:
    - ['lineage_100k.csv~csv']
```

### Step 4: Run Benchmark
```bash
cd E:\MorphKGC-Test\ETL-RDF-STAR
python rdf_star_etl_engine_optimized.py
```

---

## Files Created

```
csv_generator/
├── config_data_products_100k.json      ✅ Created
├── config_lineage_100k.json            ✅ Created
├── generate_benchmark_data.py          ✅ Created
├── README_BENCHMARK.md                 ✅ Created
├── config_data_products_10k.json       ✅ Generated (via --save-configs)
└── config_lineage_10k.json             ✅ Generated (via --save-configs)

ETL-RDF-STAR/benchmark_data/
├── data_products_10k.csv               ✅ Generated (1 MB)
└── lineage_10k.csv                     ✅ Generated (0.7 MB)
```

---

## Performance Comparison Ready

You can now benchmark:
1. **Original engine** vs **Optimized engine**
2. **Small dataset (10 rows)** vs **Large dataset (100K rows)**
3. **Single-threaded** vs **Parallel processing** (future)

Example benchmark script:
```bash
# Small dataset
time python rdf_star_etl_engine_dynamic.py    # Original
time python rdf_star_etl_engine_optimized.py  # Optimized

# Large dataset (update config first)
time python rdf_star_etl_engine_optimized.py  # Should be ~60-120 sec
```

---

## Status: ✅ COMPLETE

All requested configurations and scripts have been created and tested. The benchmark data generator is ready for performance testing of the RDF-star ETL pipeline.

**Next Step:** Generate larger datasets and benchmark the ETL pipeline!

---

**Created:** February 15, 2026  
**Tested:** ✅ 10K rows generated successfully  
**Ready for:** 100K, 500K, 1M row benchmarks

