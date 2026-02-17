
"""
Complete Integration Demo: Morph-KGC + Pyoxigraph + SPARQL Endpoint

This script demonstrates the full workflow:
1. Generate RDF data with Morph-KGC (simulated here)
2. Load into pyoxigraph Store
3. Query via programmatic SPARQL
4. Optional: Serve via Flask endpoint

Run: python complete_integration_demo.py
"""

from pyoxigraph import Store
import os

print("=" * 80)
print("COMPLETE INTEGRATION DEMO: Morph-KGC → Pyoxigraph → SPARQL")
print("=" * 80)

# Step 1: Simulate Morph-KGC output (or load from your output_mortgage_loans.ttl)
print("\n[Step 1] Loading RDF data into pyoxigraph Store")
print("-" * 80)

store = Store()

# Option A: Load from file if it exists (skip for large files)
output_file = "../rdf-data/output_mortgage_loans.ttl"
file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0

if os.path.exists(output_file) and file_size < 10_000_000:  # Only load files < 10MB
    print(f"Loading data from {output_file}...")
    with open(output_file, 'rb') as f:
        store.load(f, mime_type="text/turtle")
    print(f"✓ Loaded data from {output_file}")
else:
    if os.path.exists(output_file):
        print(f"File {output_file} is too large ({file_size:,} bytes). Using sample data for demo...")
    else:
        print(f"File {output_file} not found. Using sample data...")
    # Option B: Use sample mortgage data
    sample_mortgage_data = """
    @prefix ex: <http://example.org/mortgage/> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix schema: <http://schema.org/> .
    
    ex:Loan_001 a ex:MortgageLoan ;
        ex:loanId "LOAN-001" ;
        ex:borrowerName "John Smith" ;
        ex:loanAmount "350000.00"^^xsd:decimal ;
        ex:interestRate "3.25"^^xsd:decimal ;
        ex:loanTerm "30"^^xsd:integer ;
        ex:propertyAddress "123 Main St, Seattle, WA" ;
        ex:loanStatus "Active" .
    
    ex:Loan_002 a ex:MortgageLoan ;
        ex:loanId "LOAN-002" ;
        ex:borrowerName "Jane Doe" ;
        ex:loanAmount "475000.00"^^xsd:decimal ;
        ex:interestRate "3.50"^^xsd:decimal ;
        ex:loanTerm "30"^^xsd:integer ;
        ex:propertyAddress "456 Oak Ave, Portland, OR" ;
        ex:loanStatus "Active" .
    
    ex:Loan_003 a ex:MortgageLoan ;
        ex:loanId "LOAN-003" ;
        ex:borrowerName "Bob Johnson" ;
        ex:loanAmount "625000.00"^^xsd:decimal ;
        ex:interestRate "3.75"^^xsd:decimal ;
        ex:loanTerm "15"^^xsd:integer ;
        ex:propertyAddress "789 Pine Rd, San Francisco, CA" ;
        ex:loanStatus "Approved" .
    
    # RDF-star metadata - track data provenance
    << ex:Loan_001 ex:loanAmount "350000.00"^^xsd:decimal >> 
        ex:verifiedBy "System" ;
        ex:verifiedDate "2024-01-15"^^xsd:date ;
        ex:confidence 1.0 .
    
    << ex:Loan_002 ex:interestRate "3.50"^^xsd:decimal >>
        ex:source "BankingSystem" ;
        ex:lastUpdated "2024-02-01"^^xsd:date .
    """

    store.load(sample_mortgage_data.encode('utf-8'), mime_type="text/turtle")
    print("✓ Loaded sample mortgage loan data")

# Step 2: Query the data
print("\n[Step 2] Querying RDF data with SPARQL")
print("-" * 80)

# Query 1: Get all loans
print("\nQuery 1: List all mortgage loans")
query1 = """
PREFIX ex: <http://example.org/mortgage/>

SELECT ?loan ?loanId ?borrower ?amount ?rate ?term
WHERE {
    ?loan a ex:MortgageLoan ;
          ex:loanId ?loanId ;
          ex:borrowerName ?borrower ;
          ex:loanAmount ?amount ;
          ex:interestRate ?rate ;
          ex:loanTerm ?term .
}
ORDER BY DESC(?amount)
"""

results = store.query(query1)
print(f"\n{'Loan ID':<12} {'Borrower':<20} {'Amount':<15} {'Rate':<8} {'Term'}")
print("-" * 75)
for row in results:
    print(f"{str(row['loanId']):<12} {str(row['borrower']):<20} ${str(row['amount']):<14} {str(row['rate']):<8} {str(row['term'])} years")

# Query 2: Statistical analysis
print("\n\nQuery 2: Loan statistics")
query2 = """
PREFIX ex: <http://example.org/mortgage/>

SELECT (COUNT(?loan) AS ?totalLoans) 
       (AVG(?amount) AS ?avgAmount) 
       (MIN(?amount) AS ?minAmount)
       (MAX(?amount) AS ?maxAmount)
WHERE {
    ?loan a ex:MortgageLoan ;
          ex:loanAmount ?amount .
}
"""

results = store.query(query2)
for row in results:
    # Extract values from literals properly
    total = str(row['totalLoans']).split('"')[1] if '"' in str(row['totalLoans']) else str(row['totalLoans'])
    avg_val = str(row['avgAmount']).split('"')[1] if '"' in str(row['avgAmount']) else str(row['avgAmount'])
    min_val = str(row['minAmount']).split('"')[1] if '"' in str(row['minAmount']) else str(row['minAmount'])
    max_val = str(row['maxAmount']).split('"')[1] if '"' in str(row['maxAmount']) else str(row['maxAmount'])

    print(f"  Total Loans: {total}")
    print(f"  Average Amount: ${float(avg_val):,.2f}")
    print(f"  Min Amount: ${min_val}")
    print(f"  Max Amount: ${max_val}")

# Query 3: Filter by loan amount
print("\n\nQuery 3: High-value loans (> $400,000)")
query3 = """
PREFIX ex: <http://example.org/mortgage/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?loanId ?borrower ?amount ?address
WHERE {
    ?loan a ex:MortgageLoan ;
          ex:loanId ?loanId ;
          ex:borrowerName ?borrower ;
          ex:loanAmount ?amount ;
          ex:propertyAddress ?address .
    FILTER(?amount > "400000.00"^^xsd:decimal)
}
"""

results = store.query(query3)
for row in results:
    print(f"  {str(row['loanId'])}: {str(row['borrower'])} - ${str(row['amount'])}")
    print(f"    Property: {str(row['address'])}")

# Query 4: RDF-star query - get metadata
print("\n\nQuery 4: Data provenance (RDF-star)")
query4 = """
PREFIX ex: <http://example.org/mortgage/>

SELECT ?loan ?property ?value ?verifiedBy ?verifiedDate ?confidence
WHERE {
    ?loan ?property ?value .
    <<?loan ?property ?value>> ex:verifiedBy ?verifiedBy ;
                                ex:verifiedDate ?verifiedDate ;
                                ex:confidence ?confidence .
}
"""

results = store.query(query4)
has_results = False
for row in results:
    has_results = True
    print(f"  Loan: {str(row['loan'])}")
    print(f"    Property: {str(row['property'])}")
    print(f"    Value: {str(row['value'])}")
    print(f"    Verified by: {str(row['verifiedBy'])} on {str(row['verifiedDate'])}")
    print(f"    Confidence: {str(row['confidence'])}\n")

if not has_results:
    print("  (No provenance metadata found)")

# Query 5: ASK query
print("\nQuery 5: Are there any loans with interest rate < 3.5%?")
query5 = """
PREFIX ex: <http://example.org/mortgage/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

ASK {
    ?loan ex:interestRate ?rate .
    FILTER(?rate < "3.50"^^xsd:decimal)
}
"""

result = store.query(query5)
print(f"  Answer: {'Yes' if result else 'No'}")

# Step 3: Export/serialize data
print("\n[Step 3] Exporting data to different formats")
print("-" * 80)

# Export to N-Triples
from io import BytesIO
ntriples_buffer = BytesIO()
store.dump(ntriples_buffer, mime_type="application/n-triples")
ntriples_output = ntriples_buffer.getvalue()
print(f"\nN-Triples format (first 500 chars):")
print(ntriples_output.decode('utf-8')[:500])

# Export to Turtle
turtle_buffer = BytesIO()
store.dump(turtle_buffer, mime_type="text/turtle")
turtle_output = turtle_buffer.getvalue()
print(f"\n\nTurtle format (first 500 chars):")
print(turtle_output.decode('utf-8')[:500])

# Save to file
with open('../rdf-data/exported_loans.ttl', 'wb') as f:
    f.write(turtle_output)
print("\n✓ Data exported to: exported_loans.ttl")

# Step 4: Performance info
print("\n[Step 4] Store Information")
print("-" * 80)

total_triples = len(list(store))
print(f"Total triples in store: {total_triples}")

# Step 5: Integration options
print("\n[Step 5] Integration Options")
print("-" * 80)

print("""
Your pyoxigraph store is now loaded with RDF data. You can:

1. **Use programmatically** (current approach):
   - Call store.query() directly in Python
   - Fastest performance, no HTTP overhead
   
2. **Serve via Flask endpoint**:
   - Run: python flask_sparql_endpoint.py
   - Query at: http://localhost:5000/sparql
   
3. **Serve via FastAPI endpoint**:
   - Run: uvicorn fastapi_sparql_endpoint:app --reload
   - Query at: http://localhost:8000/sparql
   - API docs: http://localhost:8000/docs
   
4. **Use Oxigraph Server**:
   - Save data: store.dump() to file
   - Load into Oxigraph Server
   - Full SPARQL 1.1 Protocol endpoint

For more details, see: SPARQL_ENDPOINT_GUIDE.md
""")

print("=" * 80)
print("DEMO COMPLETE!")
print("=" * 80)

print("""
Next steps:
1. Review the queries above
2. Modify queries for your use case
3. Choose an integration method (programmatic, Flask, FastAPI, or Oxigraph Server)
4. Scale up with your actual data

Files created:
- exported_loans.ttl (sample data export)
- test_rdf_star.py (RDF-star confirmation)
- test_sparql_endpoint.py (full SPARQL demo)
- flask_sparql_endpoint.py (Flask SPARQL endpoint)
- fastapi_sparql_endpoint.py (FastAPI SPARQL endpoint)
- SPARQL_ENDPOINT_GUIDE.md (complete documentation)
""")

