"""
RDF-star Demonstration: Data Products with Governance Metadata
==============================================================

This script demonstrates the power of RDF-star by:
1. Loading an OWL ontology for data products
2. Loading instance data with RDF-star annotations (provenance & quality)
3. Running advanced queries that leverage RDF-star features

Key RDF-star Features Demonstrated:
- Statement-level metadata (who said what, when, with what confidence)
- Provenance tracking at the triple level
- Quality metrics on specific assertions
- Complex queries across ontology and instance data
"""

from pyoxigraph import Store, NamedNode, RdfFormat
import time

print("="*80)
print("RDF-STAR DEMONSTRATION: Data Products with Governance")
print("="*80)
print()

# Create store
store = Store()

# ============================================================================
# 1. Load OWL Ontology
# ============================================================================
print("Step 1: Loading OWL Ontology...")
print("-" * 80)

ontology_path = "ontology/data_products_ontology.ttl"
try:
    with open(ontology_path, 'rb') as f:
        store.load(f, RdfFormat.TURTLE)
    print(f"[OK] Loaded ontology from {ontology_path}")
except FileNotFoundError:
    print(f"[X] Ontology file not found: {ontology_path}")
    print("  Please ensure the ontology file exists.")
    exit(1)
except SyntaxError as e:
    print(f"[X] Syntax error in ontology: {e}")
    print("  There may be an issue with the Turtle syntax.")
    exit(1)

print()

# ============================================================================
# 2. Load Instance Data with RDF-star
# ============================================================================
print("Step 2: Loading Instance Data (with RDF-star annotations)...")
print("-" * 80)

instance_path = "output/output_data_star.trig"
try:
    with open(instance_path, 'rb') as f:
        store.load(f, RdfFormat.TRIG)

    # Count quads
    quad_count = len(list(store))
    print(f"✓ Loaded instance data from {instance_path}")
    print(f"  Total quads in store: {quad_count:,}")
except FileNotFoundError:
    print(f"✗ Instance data file not found: {instance_path}")
    print("  Run the ETL pipeline first: python rdf_star_etl_engine_optimized.py")
    exit(1)

print()

# ============================================================================
# 3. RDF-star Query Demonstrations
# ============================================================================
print("="*80)
print("RDF-STAR QUERY DEMONSTRATIONS")
print("="*80)
print()

# ----------------------------------------------------------------------------
# Query 1: Find datasets with high-confidence theme assignments
# ----------------------------------------------------------------------------
print("Query 1: Datasets with high-confidence theme assignments (>0.90)")
print("-" * 80)

query1 = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?theme ?confidence ?source
WHERE {
    # The base triple
    ?dataset dcat:theme ?theme .
    ?dataset dct:title ?title .
    
    # RDF-star: metadata about the theme assignment
    <<?dataset dcat:theme ?theme>> ex:confidence ?confidence ;
                                    prov:wasDerivedFrom ?source .
    
    FILTER(?confidence > 0.90)
}
ORDER BY DESC(?confidence)
LIMIT 10
"""

try:
    results = list(store.query(query1))
    print(f"Found {len(results)} datasets with confidence > 0.90:")
    print()
    for i, result in enumerate(results[:5], 1):
        dataset = str(result['dataset']).split('/')[-1]
        title = str(result['title'])
        theme = str(result['theme']).split('/')[-1]
        conf = float(str(result['confidence']))
        source = str(result['source']).split('/')[-1]
        print(f"  {i}. Dataset: {dataset}")
        print(f"     Title: {title}")
        print(f"     Theme: {theme}")
        print(f"     Confidence: {conf:.2f} (from {source})")
        print()
except Exception as e:
    print(f"✗ Error executing query: {e}")
    print()

# ----------------------------------------------------------------------------
# Query 2: Track provenance - which system provided which data?
# ----------------------------------------------------------------------------
print()
print("Query 2: Provenance tracking - Data by source system")
print("-" * 80)

query2 = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?source (COUNT(DISTINCT ?dataset) as ?datasetCount) (AVG(?confidence) as ?avgConfidence)
WHERE {
    ?dataset dcat:theme ?theme .
    
    # RDF-star: get source and confidence from statement annotation
    <<?dataset dcat:theme ?theme>> prov:wasDerivedFrom ?source ;
                                    ex:confidence ?confidence .
}
GROUP BY ?source
ORDER BY DESC(?datasetCount)
"""

try:
    results = list(store.query(query2))
    print(f"Data provenance by source system:")
    print()
    for result in results:
        source = str(result['source']).split('/')[-1]
        count = int(str(result['datasetCount']))
        avg_conf = float(str(result['avgConfidence']))
        print(f"  • {source:20s} {count:6,} datasets   Avg confidence: {avg_conf:.3f}")
    print()
except Exception as e:
    print(f"✗ Error executing query: {e}")
    print()

# ----------------------------------------------------------------------------
# Query 3: Find datasets with conflicting metadata from different sources
# ----------------------------------------------------------------------------
print()
print("Query 3: Datasets with multiple theme assignments (potential conflicts)")
print("-" * 80)

query3 = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title (COUNT(DISTINCT ?theme) as ?themeCount) 
       (GROUP_CONCAT(DISTINCT ?theme; separator=", ") as ?themes)
WHERE {
    ?dataset dcat:theme ?theme .
    ?dataset dct:title ?title .
}
GROUP BY ?dataset ?title
HAVING (COUNT(DISTINCT ?theme) > 1)
ORDER BY DESC(?themeCount)
LIMIT 5
"""

try:
    results = list(store.query(query3))
    if results:
        print(f"Found {len(results)} datasets with multiple themes:")
        print()
        for result in results:
            dataset = str(result['dataset']).split('/')[-1]
            title = str(result['title'])
            count = int(str(result['themeCount']))
            print(f"  • {dataset}: {title}")
            print(f"    Has {count} different theme assignments")
            print()
    else:
        print("  No conflicts found - each dataset has a single theme assignment.")
        print()
except Exception as e:
    print(f"✗ Error executing query: {e}")
    print()

# ----------------------------------------------------------------------------
# Query 4: Quality metrics - Find low confidence assertions
# ----------------------------------------------------------------------------
print()
print("Query 4: Low confidence data quality alerts (<0.85)")
print("-" * 80)

query4 = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?predicate ?object ?confidence ?source ?rule
WHERE {
    # Find any triple about a dataset
    ?dataset ?predicate ?object .
    ?dataset dct:title ?title .
    FILTER(?predicate != dct:title && ?predicate != rdf:type)
    
    # Get confidence from RDF-star annotation
    <<?dataset ?predicate ?object>> ex:confidence ?confidence ;
                                     prov:wasDerivedFrom ?source ;
                                     ex:rule ?rule .
    
    FILTER(?confidence < 0.85)
}
ORDER BY ?confidence
LIMIT 10
"""

try:
    results = list(store.query(query4))
    if results:
        print(f"Found {len(results)} assertions with low confidence:")
        print()
        for result in results:
            dataset = str(result['dataset']).split('/')[-1]
            title = str(result['title'])
            conf = float(str(result['confidence']))
            source = str(result['source']).split('/')[-1]
            rule = str(result['rule']).split('/')[-1]
            print(f"  ⚠ {dataset}: {title}")
            print(f"     Confidence: {conf:.2f} (from {source}, rule {rule})")
            print()
    else:
        print("  No low confidence assertions found.")
        print()
except Exception as e:
    print(f"✗ Error executing query: {e}")
    print()

# ----------------------------------------------------------------------------
# Query 5: Temporal analysis - Data freshness by generation time
# ----------------------------------------------------------------------------
print()
print("Query 5: Data freshness - Most recently updated datasets")
print("-" * 80)

query5 = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?theme ?lastUpdated ?source
WHERE {
    ?dataset dcat:theme ?theme .
    ?dataset dct:title ?title .
    
    # Get generation time from RDF-star annotation
    <<?dataset dcat:theme ?theme>> prov:generatedAtTime ?lastUpdated ;
                                    prov:wasDerivedFrom ?source .
}
ORDER BY DESC(?lastUpdated)
LIMIT 10
"""

try:
    results = list(store.query(query5))
    print(f"Most recently updated datasets:")
    print()
    for i, result in enumerate(results[:5], 1):
        dataset = str(result['dataset']).split('/')[-1]
        title = str(result['title'])
        theme = str(result['theme']).split('/')[-1]
        updated = str(result['lastUpdated'])
        source = str(result['source']).split('/')[-1]
        print(f"  {i}. {dataset}: {title}")
        print(f"     Theme: {theme}, Updated: {updated} (via {source})")
        print()
except Exception as e:
    print(f"✗ Error executing query: {e}")
    print()

# ----------------------------------------------------------------------------
# Query 6: Complex RDF-star query - Governance audit trail
# ----------------------------------------------------------------------------
print()
print("Query 6: Complete governance audit trail for a specific dataset")
print("-" * 80)

query6 = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?predicate ?value ?confidence ?source ?rule ?timestamp ?activity
WHERE {
    # Get first dataset as example
    {
        SELECT ?dataset (MIN(?d) as ?minDataset)
        WHERE { ?d a dcat:Dataset }
        GROUP BY ?dataset
        LIMIT 1
    }
    
    ?dataset ?predicate ?value .
    ?dataset dct:title ?title .
    FILTER(?predicate != rdf:type)
    
    # RDF-star: get all governance metadata
    <<?dataset ?predicate ?value>> ex:confidence ?confidence ;
                                    prov:wasDerivedFrom ?source ;
                                    ex:rule ?rule ;
                                    prov:generatedAtTime ?timestamp ;
                                    prov:wasGeneratedBy ?activity .
}
ORDER BY ?predicate ?timestamp
"""

try:
    results = list(store.query(query6))
    if results:
        dataset_name = None
        print(f"Complete audit trail for sample dataset:")
        print()

        for result in results[:10]:
            if dataset_name is None:
                dataset_name = str(result['dataset']).split('/')[-1]
                title = str(result['title'])
                print(f"Dataset: {dataset_name} - {title}")
                print("-" * 80)

            pred = str(result['predicate']).split('/')[-1].split('#')[-1]
            val = str(result['value'])
            if '/' in val:
                val = val.split('/')[-1]
            conf = float(str(result['confidence']))
            source = str(result['source']).split('/')[-1]
            rule = str(result['rule']).split('/')[-1]
            timestamp = str(result['timestamp'])
            activity = str(result['activity']).split('/')[-1]

            print(f"\n  Property: {pred}")
            print(f"  Value: {val}")
            print(f"  Confidence: {conf:.2f}")
            print(f"  Source: {source}")
            print(f"  Rule: {rule}")
            print(f"  Timestamp: {timestamp}")
            print(f"  Activity: {activity}")
        print()
    else:
        print("  No audit trail data found.")
        print()
except Exception as e:
    print(f"✗ Error executing query: {e}")
    print()

# ----------------------------------------------------------------------------
# Query 7: Ontology reasoning - Find all subclasses of prov:Agent
# ----------------------------------------------------------------------------
print()
print("Query 7: Ontology reasoning - System types in the governance framework")
print("-" * 80)

query7 = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX ex: <http://example.org/>

SELECT DISTINCT ?class ?label ?comment
WHERE {
    ?class rdfs:subClassOf* prov:Agent .
    OPTIONAL { ?class rdfs:label ?label }
    OPTIONAL { ?class rdfs:comment ?comment }
    FILTER(?class != prov:Agent)
}
"""

try:
    results = list(store.query(query7))
    print(f"Agent types in the ontology:")
    print()
    for result in results:
        cls = str(result['class']).split('/')[-1].split('#')[-1]
        label = str(result.get('label', 'N/A'))
        print(f"  • {cls}: {label}")
    print()
except Exception as e:
    print(f"✗ Error executing query: {e}")
    print()

# ============================================================================
# Summary Statistics
# ============================================================================
print("="*80)
print("SUMMARY STATISTICS")
print("="*80)

# Count different entity types
summary_query = """
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX ex: <http://example.org/>

SELECT 
    (COUNT(DISTINCT ?dataset) as ?datasetCount)
    (COUNT(DISTINCT ?activity) as ?activityCount)
    (COUNT(DISTINCT ?theme) as ?themeCount)
WHERE {
    ?dataset a dcat:Dataset .
    OPTIONAL { ?activity a prov:Activity }
    OPTIONAL { ?dataset dcat:theme ?theme }
}
"""

try:
    result = list(store.query(summary_query))[0]
    datasets = int(str(result['datasetCount']))
    activities = int(str(result['activityCount']))
    themes = int(str(result['themeCount']))

    print(f"\nEntity counts:")
    print(f"  Datasets:   {datasets:,}")
    print(f"  Activities: {activities:,}")
    print(f"  Themes:     {themes:,}")
    print(f"  Total quads: {len(list(store)):,}")
    print()
except Exception as e:
    print(f"✗ Error getting summary: {e}")

print("="*80)
print("RDF-STAR DEMONSTRATION COMPLETE")
print("="*80)
print()
print("Key Takeaways:")
print("  ✓ RDF-star allows statement-level metadata (provenance, quality)")
print("  ✓ Can track WHO said WHAT, WHEN, with WHAT confidence")
print("  ✓ Enables complex governance queries across ontology + instances")
print("  ✓ Perfect for data quality, audit trails, and lineage tracking")
print("="*80)

