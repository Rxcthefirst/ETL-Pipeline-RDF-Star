# Quick Start Guide - Dynamic RDF-star ETL Pipeline

## 5-Minute Quick Start

### Step 1: Verify Installation
```bash
cd E:\MorphKGC-Test\ETL-RDF-STAR
python --version  # Should be Python 3.8+
```

### Step 2: Run the Test Suite
```bash
python test_dynamic_etl.py
```

Expected output:
```
================================================================================
Results: 4/4 tests passed
================================================================================
```

### Step 3: Run the Pipeline
```bash
python rdf_star_etl_engine_dynamic.py
```

Expected output:
```
================================================================================
ETL Pipeline Complete
================================================================================
Duration: 0.02 seconds
Rows processed: 15
Triples generated: 40
Quoted triple annotations: 125
Total quads in store: 184
```

### Step 4: Check the Output
```bash
# View the generated RDF-star file
notepad output/output_data_star.trig
```

You should see RDF-star quoted triples like:
```turtle
_:reifier rdf:reifies <<( ex:dataset/DS001 dcat:theme ex:themes/CustomerAnalytics )>> ;
    prov:wasDerivedFrom ex:system/COLLIBRA ;
    ex:confidence 0.95 .
```

---

## Creating Your Own Pipeline

### 1. Create Your CSV Data

**File: `data/my_data.csv`**
```csv
product_id,product_name,category,price
P001,Laptop,Electronics,999.99
P002,Desk Chair,Furniture,249.99
P003,Coffee Maker,Appliances,79.99
```

### 2. Create YARRRML Mapping

**File: `mappings/my_products.yaml`**
```yaml
prefixes:
  ex: "http://example.org/"
  schema: "http://schema.org/"
  xsd: "http://www.w3.org/2001/XMLSchema#"

mappings:
  productTM:
    sources:
      - ['my_data.csv~csv']
    subject: ex:product/$(product_id)
    predicateobjects:
      - [a, schema:Product]
      - [schema:name, $(product_name), xsd:string]
      - [schema:category, $(category), xsd:string]
      - [schema:price, $(price), xsd:decimal]
```

### 3. Update Configuration

**File: `etl_pipeline_config.yaml`**
```yaml
pipeline:
  mapping_file: "mappings/my_products.yaml"
  data_directory: "data"
  output_rdfstar: "output/my_products.trig"
  rdf_format: "TRIG"
```

### 4. Run Your Pipeline
```bash
python rdf_star_etl_engine_dynamic.py
```

### 5. Query the Results

Load `output/my_products.trig` into a SPARQL endpoint and query:

```sparql
PREFIX schema: <http://schema.org/>
PREFIX ex: <http://example.org/>

SELECT ?product ?name ?price
WHERE {
  ?product a schema:Product ;
           schema:name ?name ;
           schema:price ?price .
}
ORDER BY ?price
```

---

## Common Use Cases

### Use Case 1: Adding Provenance with RDF-star

**Data: `data/products.csv`**
```csv
product_id,product_name,price
P001,Laptop,999.99
```

**Data: `data/product_sources.csv`**
```csv
product_id,source_system,last_updated,quality_score
P001,ERP_SYSTEM,2025-02-15T10:00:00Z,0.98
```

**Mapping: `mappings/products_with_provenance.yaml`**
```yaml
prefixes:
  ex: "http://example.org/"
  prov: "http://www.w3.org/ns/prov#"
  xsd: "http://www.w3.org/2001/XMLSchema#"

mappings:
  # Base product data
  productTM:
    sources:
      - ['products.csv~csv']
    subject: ex:product/$(product_id)
    predicateobjects:
      - [ex:name, $(product_name), xsd:string]
  
  # Price fact
  productPriceTM:
    sources:
      - ['products.csv~csv']
    subject: ex:product/$(product_id)
    predicateobjects:
      - predicates: ex:price
        objects:
          value: $(price)
          datatype: xsd:decimal
  
  # Provenance annotations on the price triple
  priceProvenanceTM:
    sources:
      - ['product_sources.csv~csv']
    subject:
      - function: join(quoted=productPriceTM, equal(str1=$(product_id), str2=$(product_id)))
    predicateobjects:
      - predicates: prov:wasDerivedFrom
        objects:
          value: ex:system/$(source_system)
          type: iri
      - [prov:generatedAtTime, $(last_updated), xsd:dateTime]
      - [ex:qualityScore, $(quality_score), xsd:decimal]
```

**Result:**
```turtle
ex:product/P001 ex:name "Laptop" ;
                ex:price 999.99 .

_:reifier rdf:reifies <<( ex:product/P001 ex:price 999.99 )>> ;
    prov:wasDerivedFrom ex:system/ERP_SYSTEM ;
    prov:generatedAtTime "2025-02-15T10:00:00Z"^^xsd:dateTime ;
    ex:qualityScore 0.98 .
```

---

## Testing Your Mappings

### Test 1: Validate YARRRML Syntax
```python
from yarrrml_parser import YARRRMLParser

parser = YARRRMLParser("mappings/my_mapping.yaml")
try:
    triples_maps = parser.parse()
    print(f"✓ Valid YARRRML with {len(triples_maps)} triples maps")
except Exception as e:
    print(f"✗ Invalid YARRRML: {e}")
```

### Test 2: Check Required Columns
```python
parser = YARRRMLParser("mappings/my_mapping.yaml")
parser.parse()

for csv_file in parser.get_required_csv_files():
    columns = parser.get_required_columns_for_source(csv_file)
    print(f"{csv_file} needs: {columns}")
```

### Test 3: Dry Run
Modify `rdf_star_etl_engine_dynamic.py` temporarily:
```python
# In process_triples_map method, add:
print(f"Would process: {subject_uri}")
print(f"  Type: {tm.type_statements}")
print(f"  Properties: {[po.predicate for po in tm.predicate_objects]}")
# return  # Exit before actually writing
```

---

## Troubleshooting

### Problem: "FileNotFoundError: data_products.csv"
**Solution:** Check `data_directory` in config points to correct location

### Problem: "NoDataError: empty CSV"
**Solution:** Verify CSV has header row and data rows
```bash
# Check first few lines
head data/your_file.csv
```

### Problem: "ValueError: No scheme found in absolute IRI"
**Solution:** For IRI objects, ensure CSV contains full URIs or use templates
```yaml
# Bad - CSV has partial URI
predicates: ex:relatedTo
objects:
  value: $(related_id)  # CSV has: "item123" (not a full URI)
  type: iri

# Good - Use template
predicates: ex:relatedTo
objects:
  value: ex:item/$(related_id)  # Creates: ex:item/item123
  type: iri
```

### Problem: No quoted triples generated
**Solution:** Verify join conditions match between CSVs
```python
# Debug by adding print statements in _find_matching_triples()
print(f"Looking for {join_key}={join_value}")
print(f"Found {len(matching)} matches")
```

---

## Performance Tips

### Tip 1: CSV Optimization
- Remove unnecessary columns
- Use appropriate data types
- Pre-sort by join keys

### Tip 2: Batch Processing
For large files (>100K rows), split into smaller batches:
```bash
# Split CSV into 50K row chunks
split -l 50000 large_file.csv batch_
```

### Tip 3: Monitor Memory
```python
import psutil
print(f"Memory usage: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB")
```

---

## Next Steps

1. **Load into Triplestore:** Import output into Apache Jena Fuseki or Oxigraph
2. **Query with SPARQL:** Run queries on your knowledge graph
3. **Validate with SHACL:** Add data quality constraints
4. **Automate:** Schedule pipeline runs with cron/Task Scheduler
5. **Scale Up:** Process production datasets

---

## Resources

- **YARRRML Spec:** https://rml.io/yarrrml/spec/
- **RDF-star:** https://w3c.github.io/rdf-star/
- **SPARQL-star:** https://w3c.github.io/rdf-star/cg-spec/editors_draft.html
- **Polars Docs:** https://pola-rs.github.io/polars/
- **PyOxigraph:** https://pyoxigraph.readthedocs.io/

---

## Support & Examples

See `README_DYNAMIC_ETL.md` for comprehensive documentation and `IMPLEMENTATION_SUMMARY.md` for technical details.

**Test files included:**
- `data/data_products.csv` - Sample dataset metadata
- `data/lineage.csv` - Sample provenance data
- `mappings/data_products_rml.yaml` - Complete YARRRML-star example

