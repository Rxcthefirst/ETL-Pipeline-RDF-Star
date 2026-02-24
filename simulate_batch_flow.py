"""
=============================================================================
Batch Simulation: Two-Run ETL with Changes
=============================================================================

This script simulates:
1. Initial ETL run (Batch 1) - Customer data
2. Data changes (credit score updates, new customers)
3. Second ETL run (Batch 2) - Updated data
4. Loads both batches into the SPARQL server for testing

Usage:
    python simulate_batch_flow.py

After running, use the Postman collection to test temporal queries.
=============================================================================
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from io import BytesIO

from pyoxigraph import Store, Quad, Triple, NamedNode, BlankNode, Literal, RdfFormat

# Namespaces
EX = "http://example.org/"
BATCH = "http://example.org/batch/"
META = "http://example.org/graph/metadata"
SCHEMA = "http://schema.org/"
FOAF = "http://xmlns.com/foaf/0.1/"
PROV = "http://www.w3.org/ns/prov#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XSD = "http://www.w3.org/2001/XMLSchema#"
DCT = "http://purl.org/dc/terms/"


def create_customer_triple(store: Store, graph: NamedNode, customer_id: str,
                           name: str, credit_score: int, email: str,
                           source: str, confidence: float, timestamp: str):
    """Create customer triples with RDF-star provenance annotations."""
    customer = NamedNode(f"{EX}customer/{customer_id}")

    # Basic customer data
    store.add(Quad(customer, NamedNode(f"{RDF}type"), NamedNode(f"{SCHEMA}Person"), graph))
    store.add(Quad(customer, NamedNode(f"{FOAF}name"), Literal(name), graph))
    store.add(Quad(customer, NamedNode(f"{SCHEMA}email"), Literal(email), graph))

    # Credit score
    score_literal = Literal(str(credit_score), datatype=NamedNode(f"{XSD}integer"))
    store.add(Quad(customer, NamedNode(f"{SCHEMA}creditScore"), score_literal, graph))

    # RDF-star provenance for credit score
    credit_triple = Triple(customer, NamedNode(f"{SCHEMA}creditScore"), score_literal)
    reifier = BlankNode()

    store.add(Quad(reifier, NamedNode(f"{RDF}reifies"), credit_triple, graph))
    store.add(Quad(reifier, NamedNode(f"{PROV}wasDerivedFrom"),
                   NamedNode(f"{EX}source/{source}"), graph))
    store.add(Quad(reifier, NamedNode(f"{EX}confidence"),
                   Literal(str(confidence), datatype=NamedNode(f"{XSD}decimal")), graph))
    store.add(Quad(reifier, NamedNode(f"{PROV}generatedAtTime"),
                   Literal(timestamp, datatype=NamedNode(f"{XSD}dateTime")), graph))


def create_batch_metadata(store: Store, batch_uri: str, batch_number: int,
                          created: str, loaded: str, description: str,
                          status: str, quad_count: int,
                          supersedes: str = None, superseded_at: str = None):
    """Create batch metadata in the metadata graph."""
    meta_graph = NamedNode(META)
    batch = NamedNode(batch_uri)

    store.add(Quad(batch, NamedNode(f"{RDF}type"), NamedNode(f"{EX}Batch"), meta_graph))
    store.add(Quad(batch, NamedNode(f"{EX}batchNumber"),
                   Literal(str(batch_number), datatype=NamedNode(f"{XSD}integer")), meta_graph))
    store.add(Quad(batch, NamedNode(f"{EX}status"),
                   NamedNode(f"{EX}BatchStatus/{status}"), meta_graph))
    store.add(Quad(batch, NamedNode(f"{DCT}created"),
                   Literal(created, datatype=NamedNode(f"{XSD}dateTime")), meta_graph))
    store.add(Quad(batch, NamedNode(f"{EX}loadedAt"),
                   Literal(loaded, datatype=NamedNode(f"{XSD}dateTime")), meta_graph))
    store.add(Quad(batch, NamedNode(f"{DCT}description"), Literal(description), meta_graph))
    store.add(Quad(batch, NamedNode(f"{EX}quadCount"),
                   Literal(str(quad_count), datatype=NamedNode(f"{XSD}integer")), meta_graph))

    if supersedes:
        store.add(Quad(batch, NamedNode(f"{EX}supersedes"),
                       NamedNode(supersedes), meta_graph))

    if superseded_at:
        store.add(Quad(batch, NamedNode(f"{EX}supersededAt"),
                       Literal(superseded_at, datatype=NamedNode(f"{XSD}dateTime")), meta_graph))


def simulate_batch_flow():
    """Simulate two ETL runs with changes between them."""

    print("\n" + "=" * 70)
    print("BATCH SIMULATION: Two ETL Runs with Changes")
    print("=" * 70)

    store = Store()

    # Timestamps
    batch1_time = "2026-02-15T10:00:00Z"
    batch1_loaded = "2026-02-15T10:05:00Z"
    batch2_time = "2026-02-17T10:00:00Z"
    batch2_loaded = "2026-02-17T10:05:00Z"

    batch1_uri = f"{BATCH}2026-02-15T10:00:00Z"
    batch2_uri = f"{BATCH}2026-02-17T10:00:00Z"

    # =========================================================================
    # BATCH 1: Initial Data (Feb 15)
    # =========================================================================
    print("\n--- Creating Batch 1 (Feb 15) ---")

    batch1_graph = NamedNode(batch1_uri)

    # Customer data for Batch 1
    batch1_customers = [
        {"id": "C001", "name": "Alice Johnson", "score": 720, "email": "alice@example.com",
         "source": "Experian", "confidence": 0.95},
        {"id": "C002", "name": "Bob Smith", "score": 680, "email": "bob@example.com",
         "source": "TransUnion", "confidence": 0.92},
        {"id": "C003", "name": "Carol Williams", "score": 750, "email": "carol@example.com",
         "source": "Equifax", "confidence": 0.98},
        {"id": "C004", "name": "David Brown", "score": 695, "email": "david@example.com",
         "source": "Experian", "confidence": 0.90},
    ]

    for c in batch1_customers:
        create_customer_triple(store, batch1_graph, c["id"], c["name"], c["score"],
                               c["email"], c["source"], c["confidence"], batch1_time)
        print(f"  Added: {c['name']} (Score: {c['score']}, Source: {c['source']})")

    batch1_quad_count = len([q for q in store.quads_for_pattern(None, None, None, batch1_graph)])
    print(f"  Total quads in Batch 1: {batch1_quad_count}")

    # =========================================================================
    # BATCH 2: Updated Data (Feb 17)
    # =========================================================================
    print("\n--- Creating Batch 2 (Feb 17) ---")
    print("  Changes from Batch 1:")
    print("    - C001 (Alice): Score 720 -> 735 (improved)")
    print("    - C002 (Bob): Score 680 -> 675 (decreased)")
    print("    - C003 (Carol): No change")
    print("    - C004 (David): REMOVED (account closed)")
    print("    - C005 (Eve): NEW customer added")

    batch2_graph = NamedNode(batch2_uri)

    # Customer data for Batch 2 (with changes)
    batch2_customers = [
        {"id": "C001", "name": "Alice Johnson", "score": 735, "email": "alice@example.com",  # CHANGED
         "source": "Experian", "confidence": 0.97},
        {"id": "C002", "name": "Bob Smith", "score": 675, "email": "bob@example.com",  # CHANGED
         "source": "TransUnion", "confidence": 0.94},
        {"id": "C003", "name": "Carol Williams", "score": 750, "email": "carol@example.com",  # SAME
         "source": "Equifax", "confidence": 0.98},
        # C004 (David) is REMOVED
        {"id": "C005", "name": "Eve Davis", "score": 710, "email": "eve@example.com",  # NEW
         "source": "Experian", "confidence": 0.91},
    ]

    for c in batch2_customers:
        create_customer_triple(store, batch2_graph, c["id"], c["name"], c["score"],
                               c["email"], c["source"], c["confidence"], batch2_time)
        print(f"  Added: {c['name']} (Score: {c['score']}, Source: {c['source']})")

    batch2_quad_count = len([q for q in store.quads_for_pattern(None, None, None, batch2_graph)])
    print(f"  Total quads in Batch 2: {batch2_quad_count}")

    # =========================================================================
    # METADATA
    # =========================================================================
    print("\n--- Creating Batch Metadata ---")

    # Batch 1 metadata (superseded)
    create_batch_metadata(
        store, batch1_uri, 1, batch1_time, batch1_loaded,
        "Initial customer data load - Feb 15",
        "superseded", batch1_quad_count,
        superseded_at=batch2_time
    )
    print(f"  Batch 1: {batch1_uri} (superseded)")

    # Batch 2 metadata (active)
    create_batch_metadata(
        store, batch2_uri, 2, batch2_time, batch2_loaded,
        "Daily update - Feb 17 with credit score changes",
        "active", batch2_quad_count,
        supersedes=batch1_uri
    )
    print(f"  Batch 2: {batch2_uri} (active)")

    # =========================================================================
    # SAVE OUTPUT
    # =========================================================================
    print("\n--- Saving Output ---")

    # Create output directory
    os.makedirs("output/batch_simulation", exist_ok=True)

    # Save as TriG
    output_file = "output/batch_simulation/two_batches.trig"

    # Build prefix block
    prefixes = f"""@prefix ex: <{EX}> .
@prefix batch: <{BATCH}> .
@prefix schema: <{SCHEMA}> .
@prefix foaf: <{FOAF}> .
@prefix prov: <{PROV}> .
@prefix rdf: <{RDF}> .
@prefix xsd: <{XSD}> .
@prefix dct: <{DCT}> .

"""

    buffer = BytesIO()
    store.dump(buffer, RdfFormat.TRIG)
    content = buffer.getvalue().decode('utf-8')

    # Remove auto-generated prefixes
    lines = content.split('\n')
    filtered_lines = [line for line in lines
                      if not (line.strip().startswith('@prefix') or line.strip().startswith('PREFIX'))]

    final_content = prefixes + '\n'.join(filtered_lines)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"  Saved to: {output_file}")
    print(f"  Total quads: {len(list(store))}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("SIMULATION COMPLETE")
    print("=" * 70)
    print(f"""
Batches Created:
  1. {batch1_uri}
     - Status: superseded
     - Customers: C001, C002, C003, C004
     - Quads: {batch1_quad_count}

  2. {batch2_uri}
     - Status: active
     - Customers: C001, C002, C003, C005 (C004 removed, C005 added)
     - Quads: {batch2_quad_count}

Changes:
  - C001 Alice: Score 720 -> 735 (IMPROVED)
  - C002 Bob: Score 680 -> 675 (DECREASED)
  - C003 Carol: No change
  - C004 David: REMOVED
  - C005 Eve: NEW (Score 710)

Next Steps:
  1. Start the SPARQL server:
     python fastapi_sparql_server.py --data output/batch_simulation/two_batches.trig
  
  2. Import the Postman collection:
     sparql/Batch_Temporal_Queries.postman_collection.json
  
  3. Run the Postman tests to verify temporal queries
""")
    print("=" * 70)

    return store


if __name__ == "__main__":
    simulate_batch_flow()

