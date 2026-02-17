"""
Test script to run Morph-KGC on the mortgage loan dataset
Transforms CSV data into RDF triples using RML mappings
"""

import morph_kgc
import time
import os

def main():
    print("=" * 70)
    print("Morph-KGC Test - Mortgage Loan Dataset to RDF Transformation")
    print("=" * 70)
    print()

    # Configuration
    mapping_file = "../ETL-RDF-STAR/mappings/rml/mapping_final.rml.ttl"
    output_file = "../rdf-data/output_mortgage_loans.ttl"

    # Check if files exist
    if not os.path.exists(mapping_file):
        print(f"ERROR: Mapping file '{mapping_file}' not found!")
        return

    if not os.path.exists("../csv_data/loans_500k.csv"):
        print("ERROR: CSV file 'loans_500k.csv' not found!")
        return

    print(f"✓ Mapping file: {mapping_file}")
    print(f"✓ CSV file: loans_500k.csv")
    print(f"✓ Output file: {output_file}")
    print()

    # Configure Morph-KGC
    config = f"""
[CONFIGURATION]
output_format=N-TRIPLES

[DataSource1]
mappings={mapping_file}
"""

    # Write config to temporary file
    config_file = "morph_config.ini"
    with open(config_file, "w") as f:
        f.write(config)

    print(f"Starting RDF transformation...")
    print(f"Processing 500,000 mortgage loan records...")
    print()

    start_time = time.time()

    try:
        # Run Morph-KGC
        graph = morph_kgc.materialize(config_file)

        elapsed_time = time.time() - start_time

        # Get statistics
        num_triples = len(graph)

        print("=" * 70)
        print("✓ RDF Transformation Completed Successfully!")
        print("=" * 70)
        print(f"Total triples generated: {num_triples:,}")
        print(f"Processing time: {elapsed_time:.2f} seconds")
        print(f"Throughput: {num_triples/elapsed_time:.0f} triples/second")
        print()

        # Save to file in Turtle format for better readability
        print(f"Saving RDF triples to {output_file}...")
        graph.serialize(destination=output_file, format="turtle")

        # Get file size
        file_size = os.path.getsize(output_file)
        file_size_mb = file_size / (1024 * 1024)

        print(f"✓ Output file size: {file_size_mb:.2f} MB")
        print()

        # Show sample triples
        print("Sample RDF Triples (first 20 lines):")
        print("-" * 70)
        with open(output_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 20:
                    break
                print(line.rstrip())
        print("-" * 70)
        print()

        # Count entities by type
        print("Entity Statistics:")
        print("-" * 70)

        # Query for different entity types
        from rdflib import Namespace
        ex = Namespace("https://example.com/mortgage#")

        mortgage_loans = len(list(graph.subjects(predicate=None, object=ex.MortgageLoan)))
        borrowers = len(list(graph.subjects(predicate=None, object=ex.Borrower)))
        properties = len(list(graph.subjects(predicate=None, object=ex.Property)))

        print(f"Mortgage Loans: {mortgage_loans:,}")
        print(f"Borrowers: {borrowers:,}")
        print(f"Properties: {properties:,}")
        print()

        print("=" * 70)
        print("Test completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"ERROR during transformation: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup config file
        if os.path.exists(config_file):
            os.remove(config_file)

if __name__ == "__main__":
    import sys

    # Check for command-line format argument
    output_format = "turtle"  # default
    if len(sys.argv) > 1:
        output_format = sys.argv[1].lower()

    main(output_format)

