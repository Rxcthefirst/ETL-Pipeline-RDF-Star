"""
Dynamic RDF-star ETL Engine using YARRRML-star Parser
======================================================

This ETL engine:
1. Parses YARRRML-star mapping files to understand the data transformation rules
2. Loads CSV data sources dynamically based on the mappings
3. Generates RDF triples according to the mapping specifications
4. Produces RDF-star (quoted triples) for provenance and metadata annotations
5. Outputs TriG format with proper prefixes and reification patterns

Key Features:
- No hardcoded mappings - everything is driven by YARRRML
- Supports standard triples and RDF-star quoted triples
- Handles multiple CSV sources and joins
- Flexible provenance annotations using rdf:reifies pattern
"""

import yaml
import polars as pl
import os
import re
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Any, Optional

from pyoxigraph import (
    Store, Quad, Triple, NamedNode, BlankNode, Literal, RdfFormat
)

from yarrrml_parser import YARRRMLParser, TriplesMap


def add_dataset_metadata(store, config, prefixes):
    """Add DCAT metadata about the ETL source/process itself"""
    # Ensure we have the RDF prefix
    if 'rdf' not in prefixes:
        prefixes['rdf'] = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'

    # Create URIs for the ETL source dataset
    source_uri = expand_uri('ex:dataset/etl_import', prefixes)
    publisher_uri = expand_uri('ex:organization/etl_team', prefixes)

    dataset = NamedNode(source_uri)

    # Add type
    store.add(Quad(
        dataset,
        NamedNode(expand_uri('rdf:type', prefixes)),
        NamedNode(expand_uri('dcat:Dataset', prefixes))
    ))

    # Add title
    store.add(Quad(
        dataset,
        NamedNode(expand_uri('dct:title', prefixes)),
        Literal("ETL Pipeline Source Dataset")
    ))

    # Add description
    store.add(Quad(
        dataset,
        NamedNode(expand_uri('dct:description', prefixes)),
        Literal("Dataset metadata imported via dynamic YARRRML-star ETL pipeline")
    ))

    # Add publisher
    store.add(Quad(
        dataset,
        NamedNode(expand_uri('dct:publisher', prefixes)),
        NamedNode(publisher_uri)
    ))

    # Add created timestamp
    from datetime import datetime, timezone
    store.add(Quad(
        dataset,
        NamedNode(expand_uri('dct:created', prefixes)),
        Literal(datetime.now(timezone.utc).isoformat(),
                datatype=NamedNode(expand_uri('xsd:dateTime', prefixes)))
    ))

    print(f"[{datetime.now()}] Added ETL source dataset metadata (5 triples)")


def sanitize_uri_component(value: Any) -> str:
    """Sanitize a value for use as a URI component"""
    if value is None or value == '':
        return "unknown"
    # Convert to string and sanitize
    sanitized = re.sub(r'[^\w\-\.]', '_', str(value))
    return sanitized if sanitized else "unknown"


def expand_uri(uri_template: str, prefixes: Dict[str, str]) -> str:
    """Expand prefixed URI to full URI"""
    if ':' in uri_template and not uri_template.startswith('http'):
        prefix, local_name = uri_template.split(':', 1)
        if prefix in prefixes:
            return prefixes[prefix] + local_name
    return uri_template


def instantiate_template(template: str, row: Dict[str, Any], prefixes: Dict[str, str]) -> str:
    """
    Instantiate a URI template with row data
    Example: 'ex:dataset/$(dataset_id)' + {'dataset_id': 'DS001'} -> 'http://example.org/dataset/DS001'
    """
    result = template

    # Replace $(variable) placeholders
    variables = re.findall(r'\$\(([^)]+)\)', template)
    for var in variables:
        value = row.get(var, '')
        # Sanitize for URI
        sanitized_value = sanitize_uri_component(value)
        result = result.replace(f"$({var})", sanitized_value)

    # Handle ~iri suffix (strip it)
    result = result.replace('~iri', '')

    # Expand prefix
    result = expand_uri(result, prefixes)

    return result


def create_rdf_node(value_template: str, row: Dict[str, Any], prefixes: Dict[str, str],
                    object_type: str = "literal", datatype: Optional[str] = None):
    """Create appropriate RDF node (NamedNode or Literal) based on object type"""

    # Check if this is a direct reference to a column value (for IRIs from CSV)
    # Pattern: $(column_name) without any additional text
    if object_type == "iri" and value_template.strip().startswith('$(') and value_template.strip().endswith(')'):
        # Extract column name
        col_name = value_template.strip()[2:-1]
        value = row.get(col_name, '')

        # Use the value directly if it's already a full URI
        if value and (str(value).startswith('http://') or str(value).startswith('https://')):
            return NamedNode(str(value))

    # Otherwise, instantiate template
    value = instantiate_template(value_template, row, prefixes)

    if object_type == "iri":
        return NamedNode(value)
    else:
        # Literal
        if datatype:
            datatype_uri = expand_uri(datatype, prefixes)
            return Literal(value, datatype=NamedNode(datatype_uri))
        else:
            return Literal(value)


class RDFStarETLEngine:
    """Dynamic RDF-star ETL Engine driven by YARRRML-star mappings"""

    def __init__(self, config_path: str):
        """Initialize the ETL engine with configuration"""
        self.config_path = config_path
        self.config = None
        self.parser = None
        self.store = Store()
        self.prefixes = {}
        self.dataframes = {}  # Cache for loaded CSV dataframes
        self.triples_cache = {}  # Cache triples for quoted triple references
        self.processed_files = set()  # Track which files we've counted

        # Statistics
        self.stats = {
            'triples_generated': 0,
            'quoted_triples_generated': 0,
            'rows_processed': 0,
            'files_processed': 0
        }

    def load_config(self):
        """Load pipeline configuration"""
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Get mapping file path
        mapping_file = self.config['pipeline']['mapping_file']

        # Initialize parser
        self.parser = YARRRMLParser(mapping_file)
        self.parser.parse()
        self.prefixes = self.parser.prefixes

        print(f"[{datetime.now()}] Configuration loaded")
        print(f"[{datetime.now()}] Mapping file: {mapping_file}")
        print(f"[{datetime.now()}] Prefixes: {list(self.prefixes.keys())}")

    def load_csv_data(self, csv_path: str) -> pl.DataFrame:
        """Load CSV data with polars, with caching"""
        if csv_path in self.dataframes:
            return self.dataframes[csv_path]

        # Resolve path relative to data directory if needed
        if not os.path.isabs(csv_path):
            base_dir = os.path.dirname(self.config_path)
            # Check if data_directory is specified in config
            data_dir = self.config['pipeline'].get('data_directory', '')
            if data_dir:
                csv_path = os.path.join(base_dir, data_dir, csv_path)
            else:
                csv_path = os.path.join(base_dir, csv_path)

        print(f"[{datetime.now()}] Loading CSV: {csv_path}")
        df = pl.read_csv(csv_path, ignore_errors=True)
        self.dataframes[csv_path] = df
        print(f"[{datetime.now()}] Loaded {df.height} rows from {csv_path}")

        return df

    def process_triples_map(self, tm_name: str, tm: TriplesMap):
        """Process a single triples map and generate RDF triples"""

        print(f"\n[{datetime.now()}] Processing triples map: {tm_name}")

        # Skip quoted triple maps for now (process them separately)
        if tm.subject.is_quoted:
            print(f"  → Quoted triple map - will process after base triples")
            return

        # Load source data
        if not tm.sources:
            print(f"  ⚠ No sources defined, skipping")
            return

        source = tm.sources[0]  # Use first source
        df = self.load_csv_data(source.path)

        # Track row count only once per file
        if source.path not in self.processed_files:
            self.stats['rows_processed'] += df.height
            self.stats['files_processed'] += 1
            self.processed_files.add(source.path)

        # Process each row
        for row_dict in df.iter_rows(named=True):

            # Generate subject URI
            if not tm.subject.template:
                continue

            subject_uri = instantiate_template(tm.subject.template, row_dict, self.prefixes)
            subject = NamedNode(subject_uri)

            # Generate type triples
            for type_uri in tm.type_statements:
                type_full_uri = expand_uri(type_uri, self.prefixes)
                type_triple = Triple(
                    subject,
                    NamedNode(expand_uri('rdf:type', self.prefixes)),
                    NamedNode(type_full_uri)
                )
                self.store.add(Quad(
                    subject,
                    NamedNode(expand_uri('rdf:type', self.prefixes)),
                    NamedNode(type_full_uri)
                ))
                self.stats['triples_generated'] += 1

                # Cache this triple for potential quoted triple references
                self._cache_triple(tm_name, row_dict, type_triple)

            # Generate predicate-object triples
            for po in tm.predicate_objects:
                # Expand predicate URI
                predicate_uri = expand_uri(po.predicate, self.prefixes)
                predicate = NamedNode(predicate_uri)

                # Create object node
                obj = create_rdf_node(
                    po.value,
                    row_dict,
                    self.prefixes,
                    po.object_type,
                    po.datatype
                )

                # Create and store triple
                triple = Triple(subject, predicate, obj)
                self.store.add(Quad(subject, predicate, obj))
                self.stats['triples_generated'] += 1

                # Cache this triple for potential quoted triple references
                self._cache_triple(tm_name, row_dict, triple)

        print(f"  ✓ Generated triples for {df.height} rows")

    def _cache_triple(self, tm_name: str, row_data: Dict, triple: Triple):
        """Cache a triple for potential use as a quoted triple subject"""
        # Create a cache key based on the triples map name and key columns
        if tm_name not in self.triples_cache:
            self.triples_cache[tm_name] = []

        self.triples_cache[tm_name].append({
            'row_data': row_data,
            'triple': triple
        })

    def process_quoted_triples_map(self, tm_name: str, tm: TriplesMap):
        """Process a triples map that creates quoted triples (RDF-star)"""

        print(f"\n[{datetime.now()}] Processing quoted triples map: {tm_name}")

        if not tm.subject.is_quoted or not tm.subject.quoted_mapping_ref:
            return

        # Get the referenced triples map
        ref_tm_name = tm.subject.quoted_mapping_ref
        if ref_tm_name not in self.triples_cache:
            print(f"  ⚠ Referenced triples map '{ref_tm_name}' not found in cache")
            return

        # Load source data for this annotation map
        if not tm.sources:
            return

        source = tm.sources[0]
        df = self.load_csv_data(source.path)

        # Process each row and match with cached triples
        for row_dict in df.iter_rows(named=True):
            # Find matching triples from the referenced map
            # Match based on join condition (e.g., dataset_id)
            matching_triples = self._find_matching_triples(
                ref_tm_name,
                row_dict,
                tm.subject.join_condition
            )

            for cached_triple_data in matching_triples:
                base_triple = cached_triple_data['triple']

                # Create a blank node reifier for the quoted triple
                reifier = BlankNode()

                # Link reifier to the base triple using rdf:reifies
                self.store.add(Quad(
                    reifier,
                    NamedNode(expand_uri('rdf:reifies', self.prefixes)),
                    base_triple
                ))

                # Add annotation properties to the reifier
                for po in tm.predicate_objects:
                    predicate_uri = expand_uri(po.predicate, self.prefixes)
                    predicate = NamedNode(predicate_uri)

                    obj = create_rdf_node(
                        po.value,
                        row_dict,
                        self.prefixes,
                        po.object_type,
                        po.datatype
                    )

                    self.store.add(Quad(reifier, predicate, obj))
                    self.stats['quoted_triples_generated'] += 1

        print(f"  ✓ Generated quoted triples annotations for {df.height} rows")

    def _find_matching_triples(self, ref_tm_name: str, row_dict: Dict,
                               join_condition: Optional[Dict]) -> List[Dict]:
        """Find triples from cache that match the join condition"""
        if ref_tm_name not in self.triples_cache:
            return []

        cached_triples = self.triples_cache[ref_tm_name]

        if not join_condition:
            # No join condition - return all
            return cached_triples

        # Parse join condition (e.g., equal(str1=$(dataset_id), str2=$(dataset_id)))
        equal_params = join_condition.get('equal', '')

        # Extract variable names from str1 and str2
        # Handle nested parentheses properly
        str1_match = re.search(r'str1=\$\(([^)]+)\)', equal_params)
        str2_match = re.search(r'str2=\$\(([^)]+)\)', equal_params)

        if not str1_match or not str2_match:
            return cached_triples

        join_key = str1_match.group(1)  # Usually the same as str2
        join_value = row_dict.get(join_key)

        # Filter cached triples by join key
        matching = []
        for cached in cached_triples:
            cached_row = cached['row_data']
            if cached_row.get(join_key) == join_value:
                matching.append(cached)

        return matching

    def run(self):
        """Execute the complete ETL pipeline"""
        start_time = datetime.now()
        print(f"\n{'='*80}")
        print(f"RDF-star ETL Pipeline - Dynamic YARRRML-star Engine")
        print(f"{'='*80}")
        print(f"Started at: {start_time}")

        # Load configuration and parse mappings
        self.load_config()

        # Add metadata about the ETL source dataset
        add_dataset_metadata(self.store, self.config, self.prefixes)

        # Process all triples maps in two passes
        # Pass 1: Regular triples (non-quoted)
        print(f"\n{'='*80}")
        print(f"Pass 1: Processing regular triples maps")
        print(f"{'='*80}")

        for tm_name, tm in self.parser.triples_maps.items():
            if not tm.subject.is_quoted:
                self.process_triples_map(tm_name, tm)

        # Pass 2: Quoted triples (RDF-star annotations)
        print(f"\n{'='*80}")
        print(f"Pass 2: Processing quoted triples (RDF-star annotations)")
        print(f"{'='*80}")

        for tm_name, tm in self.parser.triples_maps.items():
            if tm.subject.is_quoted:
                self.process_quoted_triples_map(tm_name, tm)

        # Write output
        self._write_output()

        # Print statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\n{'='*80}")
        print(f"ETL Pipeline Complete")
        print(f"{'='*80}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Rows processed: {self.stats['rows_processed']}")
        print(f"Triples generated: {self.stats['triples_generated']}")
        print(f"Quoted triple annotations: {self.stats['quoted_triples_generated']}")
        print(f"Total quads in store: {len(list(self.store))}")
        print(f"{'='*80}\n")

    def _write_output(self):
        """Write RDF output to file with proper prefixes"""
        output_path = self.config['pipeline']['output_rdfstar']
        rdf_format = self.config['pipeline'].get('rdf_format', 'TRIG')

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        print(f"\n[{datetime.now()}] Writing output to: {output_path}")
        print(f"[{datetime.now()}] Format: {rdf_format}")

        # Build prefix declarations
        prefix_lines = []
        for prefix, uri in self.prefixes.items():
            prefix_lines.append(f"@prefix {prefix}: <{uri}> .")

        # Add standard prefixes if not present
        if 'rdf' not in self.prefixes:
            prefix_lines.append("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
        if 'rdfs' not in self.prefixes:
            prefix_lines.append("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")

        prefix_block = '\n'.join(prefix_lines) + '\n\n'

        # Serialize store to TriG
        buffer = BytesIO()
        self.store.dump(buffer, RdfFormat.TRIG)
        content = buffer.getvalue().decode('utf-8')
        buffer.close()  # Explicitly close buffer

        # Remove auto-generated prefixes from pyoxigraph
        lines = content.split('\n')
        filtered_lines = [line for line in lines
                         if not (line.strip().startswith('@prefix') or line.strip().startswith('PREFIX'))]

        # Combine custom prefixes with content
        final_content = prefix_block + '\n'.join(filtered_lines)

        # Write to file with explicit flush
        try:
            with open(output_path, 'w', encoding='utf-8', buffering=1) as f:
                f.write(final_content)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f"[ERROR] Failed to write output: {e}")
            raise

        # Verify write
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"[{datetime.now()}] ✓ Output written successfully ({file_size:,} bytes)")
        else:
            print(f"[{datetime.now()}] [ERROR] Output file not found")


def main():
    """Main entry point"""
    config_file = "etl_pipeline_config.yaml"

    if not os.path.exists(config_file):
        print(f"❌ Configuration file not found: {config_file}")
        return 1

    try:
        engine = RDFStarETLEngine(config_file)
        engine.run()
        return 0
    except Exception as e:
        print(f"\n❌ ETL Pipeline failed with error:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

