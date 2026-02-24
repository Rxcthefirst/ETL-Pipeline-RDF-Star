#!/usr/bin/env python
"""
=============================================================================
Batch Management CLI
=============================================================================

Command-line interface for managing RDF-star batches.

Usage:
    python batch_cli.py run <mapping_file> [options]
    python batch_cli.py list [--status <status>]
    python batch_cli.py diff <batch1> <batch2>
    python batch_cli.py query <batch_id> "<sparql_query>"
    python batch_cli.py export <batch_id> <output_file>
    python batch_cli.py archive <batch_id>
    python batch_cli.py delete <batch_id> [--permanent]
    python batch_cli.py status
    python batch_cli.py provenance <subject_uri> [--batch <batch_id>]

=============================================================================
"""

import argparse
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pyoxigraph import Store, RdfFormat
from batch_manager import BatchManager, BatchStatus
from rdf_star_etl_yarrrml import RDFStarETLEngine


def cmd_run(args):
    """Run ETL and create a new batch."""
    print(f"\n{'='*70}")
    print("BATCH ETL RUN")
    print(f"{'='*70}")

    # Initialize batch manager with persistent store
    store = Store()
    manager = BatchManager(store, metadata_dir=args.metadata_dir)

    # Parse tags
    tags = args.tags.split(',') if args.tags else []

    # Create the batch
    batch = manager.create_batch(
        source_mapping=args.mapping_file,
        source_files=[],  # Will be populated by ETL
        description=args.description or f"ETL run from {os.path.basename(args.mapping_file)}",
        tags=tags
    )

    print(f"\nCreated batch: {batch.batch_id}")

    # Run ETL engine
    output_file = args.output or f"output/batch_{batch.batch_number:04d}.trig"

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)

    print(f"\nRunning ETL...")
    engine = RDFStarETLEngine(args.mapping_file, output_file)
    engine.run()

    # Update batch with source files from ETL
    batch.source_files = list(engine.dataframes.keys())

    # Load the output into the batch
    batch = manager.load_batch_from_file(
        batch_id=batch.batch_id,
        rdf_file=output_file
    )

    print(f"\n{'='*70}")
    print("BATCH COMPLETE")
    print(f"{'='*70}")
    print(f"Batch ID: {batch.batch_id}")
    print(f"Graph URI: {batch.graph_uri}")
    print(f"Quads loaded: {batch.quad_count}")
    print(f"Status: {batch.status.value}")
    print(f"{'='*70}\n")

    return 0


def cmd_list(args):
    """List batches."""
    store = Store()
    manager = BatchManager(store, metadata_dir=args.metadata_dir)

    # Parse status filter
    status_filter = None
    if args.status:
        try:
            status_filter = BatchStatus(args.status.lower())
        except ValueError:
            print(f"Invalid status: {args.status}")
            print(f"Valid values: {', '.join(s.value for s in BatchStatus)}")
            return 1

    batches = manager.list_batches(status=status_filter, limit=args.limit)

    print(f"\n{'='*70}")
    print("BATCHES")
    print(f"{'='*70}")

    if not batches:
        print("No batches found.")
    else:
        print(f"{'ID':<40} {'Status':<12} {'Quads':<10} {'Created'}")
        print("-" * 70)
        for batch in batches:
            created = batch.created_at.strftime("%Y-%m-%d %H:%M")
            print(f"{batch.batch_id:<40} {batch.status.value:<12} {batch.quad_count:<10} {created}")

    print(f"{'='*70}\n")
    return 0


def cmd_diff(args):
    """Compare two batches."""
    store = Store()
    manager = BatchManager(store, metadata_dir=args.metadata_dir)

    # Need to load the batch data files to compare
    batch1 = manager.get_batch(args.batch1)
    batch2 = manager.get_batch(args.batch2)

    if not batch1:
        print(f"Batch not found: {args.batch1}")
        return 1
    if not batch2:
        print(f"Batch not found: {args.batch2}")
        return 1

    # Load batch data from their export files if available
    print(f"\nNote: For full diff, batch data must be loaded in the store.")
    print(f"Run with a persistent store or export/import batches.\n")

    try:
        diff = manager.compare_batches(args.batch1, args.batch2, sample_limit=args.limit)

        print(f"\n{'='*70}")
        print(f"BATCH DIFF: {args.batch1} -> {args.batch2}")
        print(f"{'='*70}")
        print(f"Added triples: {len(diff.added_triples)}")
        print(f"Removed triples: {len(diff.removed_triples)}")
        print(f"Modified subjects: {len(diff.modified_subjects)}")
        print(f"Unchanged: {diff.unchanged_count}")

        if args.verbose and diff.added_triples:
            print(f"\nAdded (sample):")
            for t in diff.added_triples[:10]:
                print(f"  + {t}")

        if args.verbose and diff.removed_triples:
            print(f"\nRemoved (sample):")
            for t in diff.removed_triples[:10]:
                print(f"  - {t}")

        if args.verbose and diff.modified_subjects:
            print(f"\nModified subjects (sample):")
            for s in diff.modified_subjects[:10]:
                print(f"  ~ {s}")

        print(f"{'='*70}\n")

    except Exception as e:
        print(f"Error comparing batches: {e}")
        return 1

    return 0


def cmd_query(args):
    """Query a specific batch."""
    store = Store()
    manager = BatchManager(store, metadata_dir=args.metadata_dir)

    batch = manager.get_batch(args.batch_id)
    if not batch:
        print(f"Batch not found: {args.batch_id}")
        return 1

    print(f"\n{'='*70}")
    print(f"QUERY BATCH: {args.batch_id}")
    print(f"{'='*70}")
    print(f"Query: {args.query[:100]}...")
    print()

    try:
        results = manager.query_at_batch(args.batch_id, args.query)

        row_count = 0
        for row in results:
            row_count += 1
            print(row)
            if row_count >= args.limit:
                print(f"... (limited to {args.limit} rows)")
                break

        print(f"\nRows returned: {row_count}")

    except Exception as e:
        print(f"Query error: {e}")
        return 1

    print(f"{'='*70}\n")
    return 0


def cmd_export(args):
    """Export a batch to a file."""
    store = Store()
    manager = BatchManager(store, metadata_dir=args.metadata_dir)

    batch = manager.get_batch(args.batch_id)
    if not batch:
        print(f"Batch not found: {args.batch_id}")
        return 1

    # Determine format
    rdf_format = RdfFormat.TRIG
    if args.output_file.endswith('.ttl'):
        rdf_format = RdfFormat.TURTLE
    elif args.output_file.endswith('.nt'):
        rdf_format = RdfFormat.N_TRIPLES
    elif args.output_file.endswith('.nq'):
        rdf_format = RdfFormat.N_QUADS

    try:
        manager.export_batch(args.batch_id, args.output_file, rdf_format)
        print(f"Exported batch {args.batch_id} to {args.output_file}")
    except Exception as e:
        print(f"Export error: {e}")
        return 1

    return 0


def cmd_archive(args):
    """Archive a batch."""
    store = Store()
    manager = BatchManager(store, metadata_dir=args.metadata_dir)

    try:
        manager.archive_batch(args.batch_id)
        print(f"Archived batch: {args.batch_id}")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


def cmd_delete(args):
    """Delete a batch."""
    store = Store()
    manager = BatchManager(store, metadata_dir=args.metadata_dir)

    if args.permanent:
        confirm = input(f"Permanently delete batch {args.batch_id}? This cannot be undone. [y/N]: ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return 0

    try:
        manager.delete_batch(args.batch_id, permanent=args.permanent)
        action = "Permanently deleted" if args.permanent else "Marked as deleted"
        print(f"{action} batch: {args.batch_id}")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


def cmd_status(args):
    """Show batch management status."""
    store = Store()
    manager = BatchManager(store, metadata_dir=args.metadata_dir)
    manager.print_status()
    return 0


def cmd_provenance(args):
    """Get provenance for a subject."""
    store = Store()
    manager = BatchManager(store, metadata_dir=args.metadata_dir)

    batch_id = args.batch
    if not batch_id:
        active = manager.get_active_batch()
        if active:
            batch_id = active.batch_id
        else:
            print("No active batch. Specify --batch <batch_id>")
            return 1

    print(f"\n{'='*70}")
    print(f"PROVENANCE FOR: {args.subject_uri}")
    print(f"Batch: {batch_id}")
    print(f"{'='*70}")

    provenance = manager.get_provenance_for_subject(args.subject_uri, batch_id)

    if not provenance:
        print("No provenance information found.")
    else:
        for p in provenance:
            print(f"\nFact: {p['predicate']}")
            print(f"  Value: {p['object']}")
            if p['confidence']:
                print(f"  Confidence: {p['confidence']}")
            if p['source']:
                print(f"  Source: {p['source']}")
            if p['timestamp']:
                print(f"  Timestamp: {p['timestamp']}")

    print(f"{'='*70}\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Batch Management CLI for RDF-star ETL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run ETL and create a new batch
    python batch_cli.py run mappings/data_products_rml.yaml --description "Daily run"
    
    # List all batches
    python batch_cli.py list
    
    # List only active batches
    python batch_cli.py list --status active
    
    # Compare two batches
    python batch_cli.py diff batch_0001 batch_0002 --verbose
    
    # Show status
    python batch_cli.py status
    
    # Get provenance for a subject
    python batch_cli.py provenance http://example.org/customer/123
        """
    )

    parser.add_argument(
        '--metadata-dir',
        default='batch_metadata',
        help='Directory for batch metadata (default: batch_metadata)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # run command
    run_parser = subparsers.add_parser('run', help='Run ETL and create a batch')
    run_parser.add_argument('mapping_file', help='YARRRML mapping file')
    run_parser.add_argument('--output', '-o', help='Output file path')
    run_parser.add_argument('--description', '-d', help='Batch description')
    run_parser.add_argument('--tags', '-t', help='Comma-separated tags')

    # list command
    list_parser = subparsers.add_parser('list', help='List batches')
    list_parser.add_argument('--status', '-s', help='Filter by status')
    list_parser.add_argument('--limit', '-l', type=int, default=20, help='Max results')

    # diff command
    diff_parser = subparsers.add_parser('diff', help='Compare two batches')
    diff_parser.add_argument('batch1', help='First batch ID')
    diff_parser.add_argument('batch2', help='Second batch ID')
    diff_parser.add_argument('--verbose', '-v', action='store_true', help='Show sample changes')
    diff_parser.add_argument('--limit', '-l', type=int, default=100, help='Max samples')

    # query command
    query_parser = subparsers.add_parser('query', help='Query a batch')
    query_parser.add_argument('batch_id', help='Batch ID')
    query_parser.add_argument('query', help='SPARQL query')
    query_parser.add_argument('--limit', '-l', type=int, default=100, help='Max rows')

    # export command
    export_parser = subparsers.add_parser('export', help='Export a batch')
    export_parser.add_argument('batch_id', help='Batch ID')
    export_parser.add_argument('output_file', help='Output file')

    # archive command
    archive_parser = subparsers.add_parser('archive', help='Archive a batch')
    archive_parser.add_argument('batch_id', help='Batch ID')

    # delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a batch')
    delete_parser.add_argument('batch_id', help='Batch ID')
    delete_parser.add_argument('--permanent', action='store_true', help='Permanently delete')

    # status command
    status_parser = subparsers.add_parser('status', help='Show batch status')

    # provenance command
    prov_parser = subparsers.add_parser('provenance', help='Get provenance for a subject')
    prov_parser.add_argument('subject_uri', help='Subject URI')
    prov_parser.add_argument('--batch', '-b', help='Batch ID (default: active)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to command handler
    commands = {
        'run': cmd_run,
        'list': cmd_list,
        'diff': cmd_diff,
        'query': cmd_query,
        'export': cmd_export,
        'archive': cmd_archive,
        'delete': cmd_delete,
        'status': cmd_status,
        'provenance': cmd_provenance,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

