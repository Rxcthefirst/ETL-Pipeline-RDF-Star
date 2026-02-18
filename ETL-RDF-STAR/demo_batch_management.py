#!/usr/bin/env python
"""
=============================================================================
Batch Management Demo - "What Did We Know When?"
=============================================================================

This demo shows how to:
1. Create multiple batches representing daily ETL runs
2. Track changes over time
3. Query point-in-time state ("What did we know on date X?")
4. Get full provenance ("Why did we believe this?")

Scenario:
    A customer's credit score changes over several days.
    We need to track what we knew and when we knew it.

=============================================================================
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pyoxigraph import Store, Quad, Triple, NamedNode, BlankNode, Literal, RdfFormat
from batch_manager import BatchManager, BatchStatus


# Prefixes
EX = "http://example.org/"
SCHEMA = "http://schema.org/"
PROV = "http://www.w3.org/ns/prov#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XSD = "http://www.w3.org/2001/XMLSchema#"


def create_customer_data(store: Store, customer_id: str, credit_score: int,
                         source_system: str, confidence: float, timestamp: str):
    """
    Create RDF-star triples for a customer with provenance annotations.

    This demonstrates the bi-temporal model:
    - The fact: customer has credit score X
    - The provenance: we learned this from system Y at time Z with confidence C
    """
    customer = NamedNode(f"{EX}customer/{customer_id}")

    # Main fact: credit score
    store.add(Quad(
        customer,
        NamedNode(f"{SCHEMA}creditScore"),
        Literal(str(credit_score), datatype=NamedNode(f"{XSD}integer"))
    ))

    # Customer name (for context)
    store.add(Quad(
        customer,
        NamedNode(f"{SCHEMA}name"),
        Literal("John Doe")
    ))

    # RDF-star provenance using reification
    # We create a reifier node that annotates the credit score triple
    reifier = BlankNode()

    # Link reifier to the triple it annotates (using rdf:reifies)
    base_triple = Triple(
        customer,
        NamedNode(f"{SCHEMA}creditScore"),
        Literal(str(credit_score), datatype=NamedNode(f"{XSD}integer"))
    )
    store.add(Quad(
        reifier,
        NamedNode(f"{RDF}reifies"),
        base_triple
    ))

    # Source system
    store.add(Quad(
        reifier,
        NamedNode(f"{PROV}wasDerivedFrom"),
        NamedNode(f"{EX}source/{source_system}")
    ))

    # Confidence
    store.add(Quad(
        reifier,
        NamedNode(f"{EX}confidence"),
        Literal(str(confidence), datatype=NamedNode(f"{XSD}decimal"))
    ))

    # Timestamp when we recorded this
    store.add(Quad(
        reifier,
        NamedNode(f"{PROV}generatedAtTime"),
        Literal(timestamp, datatype=NamedNode(f"{XSD}dateTime"))
    ))


def demo_batch_timeline():
    """
    Demonstrate a timeline of batches with changing data.
    """
    print("\n" + "=" * 70)
    print("DEMO: Batch Management - What Did We Know When?")
    print("=" * 70)

    # Use in-memory store and temp metadata
    store = Store()
    manager = BatchManager(store, metadata_dir="demo_batch_metadata")

    # Simulate 5 days of data
    base_date = datetime(2026, 2, 10, tzinfo=timezone.utc)

    timeline = [
        # Day 1: Initial score from TransUnion
        {
            "day": 0,
            "credit_score": 710,
            "source": "TransUnion",
            "confidence": 0.90,
            "note": "Initial data load"
        },
        # Day 2: Same score, higher confidence
        {
            "day": 1,
            "credit_score": 710,
            "source": "TransUnion",
            "confidence": 0.92,
            "note": "Confidence improved"
        },
        # Day 3: Score updated from Equifax
        {
            "day": 2,
            "credit_score": 715,
            "source": "Equifax",
            "confidence": 0.95,
            "note": "Score improved"
        },
        # Day 4: Score updated from Experian
        {
            "day": 3,
            "credit_score": 720,
            "source": "Experian",
            "confidence": 0.98,
            "note": "Latest update"
        },
        # Day 5: Correction - score was actually lower
        {
            "day": 4,
            "credit_score": 718,
            "source": "Experian",
            "confidence": 0.99,
            "note": "Corrected value"
        },
    ]

    batches = []

    print("\n--- Creating Batches ---\n")

    for data in timeline:
        day = data["day"]
        batch_date = base_date + timedelta(days=day)
        timestamp = batch_date.isoformat()

        print(f"Day {day + 1} ({batch_date.date()}): {data['note']}")
        print(f"  Credit Score: {data['credit_score']} (Source: {data['source']}, Confidence: {data['confidence']})")

        # Create batch
        batch = manager.create_batch(
            source_mapping="demo_mapping.yaml",
            source_files=["demo_data.csv"],
            description=f"Day {day + 1}: {data['note']}",
            tags=["demo", f"day{day + 1}"]
        )

        # Create data store for this batch
        batch_store = Store()
        create_customer_data(
            batch_store,
            customer_id="123",
            credit_score=data["credit_score"],
            source_system=data["source"],
            confidence=data["confidence"],
            timestamp=timestamp
        )

        # Load into batch
        manager.load_batch_from_store(batch.batch_id, batch_store)
        batches.append(batch.batch_id)
        print(f"  Batch: {batch.batch_id}\n")

    # Show batch status
    print("\n--- Batch Status ---\n")
    manager.print_status()

    # Demonstrate "What did we know when?"
    print("\n--- Point-in-Time Queries ---\n")

    for i, batch_id in enumerate(batches):
        batch = manager.get_batch(batch_id)
        print(f"Batch {i + 1} ({batch.created_at.date()}): {batch.description}")

        # Get state at this batch
        state = manager.get_state_at_batch(batch_id)

        # Find credit score in this state
        for quad in state:
            if "creditScore" in str(quad.predicate):
                print(f"  -> Credit Score: {quad.object}")
                break

    # Demonstrate batch comparison
    if len(batches) >= 2:
        print("\n--- Batch Comparisons ---\n")

        # Compare first and last batch
        first_batch = batches[0]
        last_batch = batches[-1]

        print(f"Comparing {first_batch} vs {last_batch}:")
        diff = manager.compare_batches(first_batch, last_batch)
        print(f"  Added: {len(diff.added_triples)}")
        print(f"  Removed: {len(diff.removed_triples)}")
        print(f"  Unchanged: {diff.unchanged_count}")

        # Compare consecutive batches
        print("\nDay-over-day changes:")
        for i in range(len(batches) - 1):
            diff = manager.compare_batches(batches[i], batches[i + 1])
            changes = len(diff.added_triples) + len(diff.removed_triples)
            print(f"  Day {i + 1} -> Day {i + 2}: {changes} changes")

    # Demonstrate provenance query
    print("\n--- Provenance Query ---\n")
    print("Why did we believe customer 123 had their credit score?")

    active_batch = manager.get_active_batch()
    if active_batch:
        # Query for provenance
        print(f"\nIn active batch ({active_batch.batch_id}):")

        # Get all quads about customer 123
        customer_uri = f"{EX}customer/123"
        state = manager.get_state_at_batch(active_batch.batch_id)

        print(f"\nAll facts about <{customer_uri}>:")
        for quad in state:
            subj = str(quad.subject)
            if "customer/123" in subj or "reifies" in str(quad.predicate):
                print(f"  {quad.subject}")
                print(f"    {quad.predicate}")
                print(f"    {quad.object}")
                print()

    # Cleanup demo metadata
    print("\n--- Demo Complete ---\n")
    print("To clean up demo data, delete the 'demo_batch_metadata' directory.")

    return 0


def demo_regulatory_audit():
    """
    Demonstrate regulatory audit scenario:
    "Show me what we knew about customer X when decision Y was made."
    """
    print("\n" + "=" * 70)
    print("DEMO: Regulatory Audit Scenario")
    print("=" * 70)

    print("""
Scenario:
    On February 12, 2026, a loan decision was made for Customer 123.
    A regulator asks: "What data did you have about this customer at the time
    of the decision, and why did you believe it?"

Solution:
    1. Find the batch that was active on Feb 12
    2. Query that batch for all facts about Customer 123
    3. For each fact, retrieve the provenance (source, confidence, timestamp)
    """)

    # This would use the manager to query historical state
    print("""
Code example:

    from batch_manager import BatchManager
    from datetime import datetime, timezone
    
    manager = BatchManager(store)
    decision_date = datetime(2026, 2, 12, 12, 0, tzinfo=timezone.utc)
    
    # Find batch active at decision time
    for batch in manager.list_batches():
        if batch.loaded_at and batch.loaded_at <= decision_date:
            if not batch.superseded_at or batch.superseded_at > decision_date:
                relevant_batch = batch
                break
    
    # Query that batch
    results = manager.query_at_batch(
        relevant_batch.batch_id,
        '''
        SELECT ?predicate ?object ?source ?confidence ?timestamp
        WHERE {
            <http://example.org/customer/123> ?predicate ?object .
            OPTIONAL {
                ?r rdf:reifies << <http://example.org/customer/123> ?predicate ?object >> .
                ?r prov:wasDerivedFrom ?source .
                ?r ex:confidence ?confidence .
                ?r prov:generatedAtTime ?timestamp .
            }
        }
        '''
    )
    
    print("Data we had at decision time:")
    for row in results:
        print(f"  {row['predicate']}: {row['object']}")
        print(f"    Source: {row['source']}, Confidence: {row['confidence']}")
        print(f"    Recorded: {row['timestamp']}")
    """)

    return 0


if __name__ == "__main__":
    demo_batch_timeline()
    demo_regulatory_audit()

