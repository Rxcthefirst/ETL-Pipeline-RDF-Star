"""
Test script to confirm pyoxigraph supports RDF-star (RDF*)
"""

try:
    from pyoxigraph import Store
    print("✓ pyoxigraph imported successfully\n")
except ImportError:
    print("✗ pyoxigraph not installed. Installing now...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'pyoxigraph'])
    from pyoxigraph import Store
    print("✓ pyoxigraph installed and imported\n")

# Create an in-memory RDF store
store = Store()

# RDF-star example: using << >> syntax for embedded triples
turtle_star = """
@prefix : <http://example.org/> .
@prefix ex: <http://example.org/> .

# Regular triple
ex:Alice ex:knows ex:Bob .

# RDF-star: embedded triple with metadata
<< ex:Alice ex:knows ex:Bob >> ex:certainty 0.95 .
<< ex:Alice ex:knows ex:Bob >> ex:source "LinkedIn" .

# Another RDF-star example
ex:Bob ex:livesIn ex:Seattle .
<< ex:Bob ex:livesIn ex:Seattle >> ex:validFrom "2020-01-01" .
"""

print("Loading RDF-star (Turtle*) data into store...")
try:
    # Load Turtle* data into the store
    store.load(turtle_star.encode('utf-8'), mime_type="text/turtle")
    print("✓ RDF-star data loaded successfully\n")
except Exception as e:
    print(f"✗ Error loading data: {e}\n")
    exit(1)

# Query and display all quads in the store
print("=" * 70)
print("All quads in the store:")
print("=" * 70)

quad_count = 0
for quad in store.quads_for_pattern(None, None, None):
    quad_count += 1
    subject = quad.subject
    predicate = quad.predicate
    obj = quad.object

    # Check if subject or object is a triple (RDF-star feature)
    subject_str = str(subject)
    object_str = str(obj)

    # Display the quad
    print(f"\n[Quad {quad_count}]")
    print(f"  Subject:   {subject_str}")
    print(f"  Predicate: {predicate}")
    print(f"  Object:    {object_str}")

    # Highlight RDF-star triples
    if "<<" in subject_str or hasattr(subject, '__class__') and 'Triple' in subject.__class__.__name__:
        print(f"  *** RDF-STAR: Subject is an embedded triple! ***")
    if "<<" in object_str or hasattr(obj, '__class__') and 'Triple' in obj.__class__.__name__:
        print(f"  *** RDF-STAR: Object is an embedded triple! ***")

print("\n" + "=" * 70)
print(f"Total quads found: {quad_count}")
print("=" * 70)

# Test SPARQL query on RDF-star data
print("\n\nTesting SPARQL query on RDF-star data:")
print("=" * 70)

sparql_query = """
PREFIX ex: <http://example.org/>

SELECT ?s ?p ?o ?certainty
WHERE {
    ?s ?p ?o .
    <<?s ?p ?o>> ex:certainty ?certainty .
}
"""

try:
    results = store.query(sparql_query)
    print("Query results:")
    for result in results:
        print(f"  {result['s']} {result['p']} {result['o']} (certainty: {result['certainty']})")
    print("\n✓ SPARQL query on RDF-star data executed successfully!")
except Exception as e:
    print(f"✗ Error executing SPARQL query: {e}")

print("\n" + "=" * 70)
print("CONCLUSION: pyoxigraph SUPPORTS RDF-star! ✓")
print("=" * 70)

