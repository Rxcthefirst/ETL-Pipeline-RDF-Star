"""
=============================================================================
RDF-star ETL Engine - YARRRML Direct Processing
=============================================================================

A streamlined ETL engine that processes YARRRML mapping files directly,
without requiring a separate configuration file. All configuration is
derived from the YARRRML specification:

- Sources: Defined in YARRRML mappings
- Targets: Defined in YARRRML targets section
- Prefixes: Defined in YARRRML prefixes section
- Output: Derived from targets or command line

Usage:
    python rdf_star_etl_yarrrml.py <mapping_file.yaml> [output_file.trig]

Example:
    python rdf_star_etl_yarrrml.py mappings/data_products_rml.yaml
    python rdf_star_etl_yarrrml.py mappings/my_mapping.yaml output/result.trig

=============================================================================
"""

import polars as pl
import os
import re
import argparse
from datetime import datetime, timezone
from io import BytesIO
from typing import Dict, List, Any, Optional, Tuple
from functools import lru_cache

from pyoxigraph import (
    Store, Quad, Triple, NamedNode, BlankNode, Literal, RdfFormat
)

from yarrrml_parser import YARRRMLParser, TriplesMap

# Pre-compile regex patterns for performance
TEMPLATE_VAR_PATTERN = re.compile(r'\$\(([^)]+)\)')
URI_SANITIZE_PATTERN = re.compile(r'[^\w\-.]')


@lru_cache(maxsize=10000)
def sanitize_uri_component_cached(value: str) -> str:
    """Cached version of URI sanitization"""
    if not value:
        return "unknown"
    sanitized = URI_SANITIZE_PATTERN.sub('_', value)
    return sanitized if sanitized else "unknown"


def sanitize_uri_component(value: Any) -> str:
    """Sanitize a value for use as a URI component"""
    if value is None or value == '':
        return "unknown"
    return sanitize_uri_component_cached(str(value))


@lru_cache(maxsize=1000)
def expand_uri_cached(uri_template: str, prefixes_tuple: Tuple) -> str:
    """Cached version of URI expansion"""
    prefixes = dict(prefixes_tuple)
    if ':' in uri_template and not uri_template.startswith('http'):
        prefix, local_name = uri_template.split(':', 1)
        if prefix in prefixes:
            return prefixes[prefix] + local_name
    return uri_template


def expand_uri(uri_template: str, prefixes: Dict[str, str]) -> str:
    """Expand prefixed URI to full URI"""
    return expand_uri_cached(uri_template, tuple(prefixes.items()))


def create_quad_with_graph(subject, predicate, obj, graph_uri: Optional[str], prefixes: Dict[str, str]) -> Quad:
    """Create a Quad with optional named graph"""
    if graph_uri:
        graph_full_uri = expand_uri(graph_uri, prefixes)
        return Quad(subject, predicate, obj, NamedNode(graph_full_uri))
    else:
        return Quad(subject, predicate, obj)


def instantiate_template_vectorized(template: str, df: pl.DataFrame, prefixes: Dict[str, str]) -> List[str]:
    """Batch template instantiation - processes DataFrame efficiently"""
    variables = TEMPLATE_VAR_PATTERN.findall(template)
    records = df.to_dicts()

    results = []
    for row in records:
        result = template
        for var in variables:
            value = row.get(var, '')
            sanitized = sanitize_uri_component(value)
            result = result.replace(f"$({var})", sanitized)

        result = result.replace('~iri', '')
        result = expand_uri(result, prefixes)
        results.append(result)

    return results


class RDFStarETLEngine:
    """
    RDF-star ETL Engine that processes YARRRML mappings directly.

    All configuration is derived from the YARRRML file:
    - prefixes: From YARRRML prefixes section
    - sources: From YARRRML sources section and mapping sources
    - targets: From YARRRML targets section
    - base_iri: From YARRRML base key
    - authors: From YARRRML authors section
    """

    def __init__(self, mapping_file: str, output_file: Optional[str] = None):
        """
        Initialize the ETL engine with a YARRRML mapping file.

        Args:
            mapping_file: Path to the YARRRML mapping file
            output_file: Optional output file path (overrides targets in YARRRML)
        """
        self.mapping_file = mapping_file
        self.mapping_dir = os.path.dirname(os.path.abspath(mapping_file))
        self.output_file = output_file

        self.parser = None
        self.store = Store()
        self.prefixes = {}
        self.base_iri = None
        self.dataframes = {}
        self.triples_cache = {}
        self.processed_files = set()

        # Pre-expanded URIs for common predicates
        self.rdf_type_uri = None

        # Statistics
        self.stats = {
            'triples_generated': 0,
            'quoted_triples_generated': 0,
            'rows_processed': 0,
            'files_processed': 0
        }

    def load_mapping(self):
        """Load and parse the YARRRML mapping file"""
        print(f"[{datetime.now()}] Loading YARRRML mapping: {self.mapping_file}")

        self.parser = YARRRMLParser(self.mapping_file)
        self.parser.parse()

        # Extract configuration from YARRRML
        self.prefixes = self.parser.prefixes
        self.base_iri = self.parser.base_iri

        # Ensure essential prefixes exist
        if 'rdf' not in self.prefixes:
            self.prefixes['rdf'] = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        if 'rdfs' not in self.prefixes:
            self.prefixes['rdfs'] = 'http://www.w3.org/2000/01/rdf-schema#'
        if 'xsd' not in self.prefixes:
            self.prefixes['xsd'] = 'http://www.w3.org/2001/XMLSchema#'

        # Pre-expand common URIs
        self.rdf_type_uri = expand_uri('rdf:type', self.prefixes)

        # Determine output file
        if not self.output_file:
            self.output_file = self._determine_output_file()

        print(f"[{datetime.now()}] Mapping loaded successfully")
        print(f"[{datetime.now()}] Prefixes: {list(self.prefixes.keys())}")
        print(f"[{datetime.now()}] Triples maps: {len(self.parser.triples_maps)}")
        if self.base_iri:
            print(f"[{datetime.now()}] Base IRI: {self.base_iri}")
        if self.parser.authors:
            print(f"[{datetime.now()}] Authors: {len(self.parser.authors)}")
        print(f"[{datetime.now()}] Output file: {self.output_file}")

    def _determine_output_file(self) -> str:
        """Determine output file from YARRRML targets or default"""
        # Check YARRRML targets
        if self.parser.targets:
            for target_name, target_spec in self.parser.targets.items():
                if isinstance(target_spec, dict) and 'access' in target_spec:
                    return target_spec['access']
                elif isinstance(target_spec, list) and len(target_spec) > 0:
                    # Shortcut format: [access~type, serialization, compression]
                    access = target_spec[0]
                    if '~' in access:
                        return access.split('~')[0]
                    return access

        # Default: same name as mapping file but with .trig extension
        base_name = os.path.splitext(os.path.basename(self.mapping_file))[0]
        return os.path.join(self.mapping_dir, 'output', f'{base_name}_output.trig')

    def _resolve_source_path(self, source_path: str) -> str:
        """Resolve source path relative to mapping file directory"""
        if os.path.isabs(source_path):
            if os.path.exists(source_path):
                return source_path

        # Get the workspace root (parent of mappings directory)
        workspace_root = os.path.dirname(self.mapping_dir)

        # List of directories to search
        search_dirs = [
            self.mapping_dir,                          # Same dir as mapping
            workspace_root,                            # Parent dir
            os.path.join(workspace_root, 'data'),      # data/
            os.path.join(workspace_root, 'benchmark_data'),  # benchmark_data/
            os.path.join(workspace_root, 'csv_data'),  # csv_data/
            os.path.join(self.mapping_dir, 'data'),    # mappings/data/
            os.path.join(self.mapping_dir, '..', 'data'),  # ../data/
            os.path.join(self.mapping_dir, '..', 'benchmark_data'),  # ../benchmark_data/
        ]

        for search_dir in search_dirs:
            candidate = os.path.join(search_dir, source_path)
            if os.path.exists(candidate):
                return os.path.abspath(candidate)

        # Return relative to mapping directory (let it fail with clear error)
        return os.path.join(self.mapping_dir, source_path)

    def load_csv_data(self, csv_path: str) -> pl.DataFrame:
        """Load CSV data with polars, with caching"""
        if csv_path in self.dataframes:
            return self.dataframes[csv_path]

        resolved_path = self._resolve_source_path(csv_path)

        print(f"[{datetime.now()}] Loading CSV: {resolved_path}")

        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"Source file not found: {resolved_path}")

        df = pl.read_csv(resolved_path, ignore_errors=True)
        self.dataframes[csv_path] = df
        print(f"[{datetime.now()}] Loaded {df.height} rows from {resolved_path}")

        return df

    def add_metadata(self):
        """Add metadata about the ETL source/process"""
        if 'dcat' not in self.prefixes:
            self.prefixes['dcat'] = 'http://www.w3.org/ns/dcat#'
        if 'dct' not in self.prefixes:
            self.prefixes['dct'] = 'http://purl.org/dc/terms/'

        # Create dataset URI
        base = self.base_iri or 'http://example.org/'
        dataset_uri = f"{base}dataset/etl_import"

        dataset = NamedNode(dataset_uri)

        # Add type
        self.store.add(Quad(
            dataset,
            NamedNode(expand_uri('rdf:type', self.prefixes)),
            NamedNode(expand_uri('dcat:Dataset', self.prefixes))
        ))

        # Add title
        self.store.add(Quad(
            dataset,
            NamedNode(expand_uri('dct:title', self.prefixes)),
            Literal("ETL Pipeline Generated Dataset")
        ))

        # Add description
        self.store.add(Quad(
            dataset,
            NamedNode(expand_uri('dct:description', self.prefixes)),
            Literal(f"Generated from YARRRML mapping: {os.path.basename(self.mapping_file)}")
        ))

        # Add created timestamp
        self.store.add(Quad(
            dataset,
            NamedNode(expand_uri('dct:created', self.prefixes)),
            Literal(datetime.now(timezone.utc).isoformat(),
                    datatype=NamedNode(expand_uri('xsd:dateTime', self.prefixes)))
        ))

        # Add authors if present
        for author in self.parser.authors:
            author_name = author.get('name', author.get('webid', 'Unknown'))
            self.store.add(Quad(
                dataset,
                NamedNode(expand_uri('dct:creator', self.prefixes)),
                Literal(author_name)
            ))

        print(f"[{datetime.now()}] Added ETL metadata")

    def process_triples_map_vectorized(self, tm_name: str, tm: TriplesMap):
        """Process triples map using vectorized operations"""
        print(f"\n[{datetime.now()}] Processing triples map: {tm_name}")

        if tm.subject.is_quoted:
            print(f"  -> Quoted triple map - will process after base triples")
            return

        if not tm.sources:
            print(f"  [WARNING] No sources defined, skipping")
            return

        source = tm.sources[0]
        df = self.load_csv_data(source.path)

        if df.height == 0:
            return

        # Vectorized subject URI generation
        if not tm.subject.template:
            return

        subject_uris = instantiate_template_vectorized(tm.subject.template, df, self.prefixes)

        # Batch create triples for type statements
        quads_batch = []
        triples_for_cache = []

        # Determine graph for mapping-level
        mapping_graph = tm.graphs[0] if tm.graphs else None
        subject_graph = tm.subject.graphs[0] if tm.subject.graphs else None
        default_graph = mapping_graph or subject_graph

        for type_uri in tm.type_statements:
            type_full_uri = expand_uri(type_uri, self.prefixes)
            type_node = NamedNode(type_full_uri)
            rdf_type_node = NamedNode(self.rdf_type_uri)

            for i in range(df.height):
                subject = NamedNode(subject_uris[i])
                triple = Triple(subject, rdf_type_node, type_node)

                quad = create_quad_with_graph(subject, rdf_type_node, type_node, default_graph, self.prefixes)
                quads_batch.append(quad)

                triples_for_cache.append({
                    'row_idx': i,
                    'triple': triple
                })

        # Batch create triples for predicate-objects
        for po in tm.predicate_objects:
            predicate_uri = expand_uri(po.predicate, self.prefixes)
            predicate = NamedNode(predicate_uri)

            # Determine graph for this predicate-object (PO graph > default graph)
            po_graph = po.graphs[0] if po.graphs else default_graph

            # Check if object is IRI with direct column reference
            if po.object_type == "iri" and po.value.strip().startswith('$(') and po.value.strip().endswith(')'):
                col_name = po.value.strip()[2:-1]
                if col_name in df.columns:
                    col_values = df[col_name].to_list()

                    for i in range(df.height):
                        value = col_values[i]
                        subject = NamedNode(subject_uris[i])

                        if value and (str(value).startswith('http://') or str(value).startswith('https://')):
                            obj = NamedNode(str(value))
                        else:
                            obj_uri = instantiate_template_vectorized(po.value, df[i:i+1], self.prefixes)[0]
                            obj = NamedNode(obj_uri)

                        triple = Triple(subject, predicate, obj)
                        quad = create_quad_with_graph(subject, predicate, obj, po_graph, self.prefixes)
                        quads_batch.append(quad)
                        triples_for_cache.append({
                            'row_idx': i,
                            'triple': triple
                        })
            else:
                # Handle literals with vectorized operations
                if po.object_type == "literal":
                    value_series = instantiate_template_vectorized(po.value, df, self.prefixes)

                    for i in range(df.height):
                        subject = NamedNode(subject_uris[i])
                        value = value_series[i]

                        if po.datatype:
                            datatype_uri = expand_uri(po.datatype, self.prefixes)
                            obj = Literal(value, datatype=NamedNode(datatype_uri))
                        elif po.language:
                            obj = Literal(value, language=po.language)
                        else:
                            obj = Literal(value)

                        triple = Triple(subject, predicate, obj)
                        quad = create_quad_with_graph(subject, predicate, obj, po_graph, self.prefixes)
                        quads_batch.append(quad)
                        triples_for_cache.append({
                            'row_idx': i,
                            'triple': triple
                        })
                else:
                    # IRI objects with templates
                    obj_uris = instantiate_template_vectorized(po.value, df, self.prefixes)

                    for i in range(df.height):
                        subject = NamedNode(subject_uris[i])
                        obj = NamedNode(obj_uris[i])

                        triple = Triple(subject, predicate, obj)
                        quad = create_quad_with_graph(subject, predicate, obj, po_graph, self.prefixes)
                        quads_batch.append(quad)
                        triples_for_cache.append({
                            'row_idx': i,
                            'triple': triple
                        })

        # Bulk insert into store
        for quad in quads_batch:
            self.store.add(quad)

        self.stats['triples_generated'] += len(quads_batch)

        # Only count rows from this file once
        if source.path not in self.processed_files:
            self.stats['rows_processed'] += df.height
            self.stats['files_processed'] += 1
            self.processed_files.add(source.path)

        # Cache triples with row data
        if tm_name not in self.triples_cache:
            self.triples_cache[tm_name] = []

        df_dicts = df.to_dicts()

        for item in triples_for_cache:
            row_idx = item['row_idx']
            row_dict = df_dicts[row_idx]
            self.triples_cache[tm_name].append({
                'row_data': row_dict,
                'triple': item['triple']
            })

        print(f"  [OK] Generated {len(triples_for_cache)} triples for {df.height} rows")

    def process_quoted_triples_map(self, tm_name: str, tm: TriplesMap):
        """Process quoted triples map (RDF-star annotations)"""
        print(f"\n[{datetime.now()}] Processing quoted triples map: {tm_name}")

        if not tm.subject.is_quoted or not tm.subject.quoted_mapping_ref:
            return

        # Build lookup for cached triples
        all_cached_triples = []
        for cache_name, cache_list in self.triples_cache.items():
            all_cached_triples.extend(cache_list)

        if not all_cached_triples:
            print(f"  [WARNING] No cached triples found")
            return

        if not tm.sources:
            return

        source = tm.sources[0]
        df = self.load_csv_data(source.path)

        # Extract join key
        join_key = self._extract_join_key(tm.subject.join_condition)

        if join_key:
            # Create index for cached triples
            cached_index = {}
            for cached in all_cached_triples:
                key_value = cached['row_data'].get(join_key)
                triple_subject_uri = str(cached['triple'].subject)
                if '/dataset/' in triple_subject_uri and key_value:
                    if key_value not in cached_index:
                        cached_index[key_value] = []
                    cached_index[key_value].append(cached)

            # Batch process quoted triples
            quads_batch = []

            for row_dict in df.iter_rows(named=True):
                join_value = row_dict.get(join_key)
                matching_triples = cached_index.get(join_value, [])

                for cached_triple_data in matching_triples:
                    base_triple = cached_triple_data['triple']
                    reifier = BlankNode()

                    # rdf:reifies link
                    quads_batch.append(Quad(
                        reifier,
                        NamedNode(expand_uri('rdf:reifies', self.prefixes)),
                        base_triple
                    ))

                    # Add annotation properties
                    for po in tm.predicate_objects:
                        predicate_uri = expand_uri(po.predicate, self.prefixes)
                        predicate = NamedNode(predicate_uri)

                        if po.object_type == "iri":
                            obj_uri = self._instantiate_template_single(po.value, row_dict)
                            obj = NamedNode(obj_uri)
                        else:
                            value = self._instantiate_template_single(po.value, row_dict)
                            if po.datatype:
                                datatype_uri = expand_uri(po.datatype, self.prefixes)
                                obj = Literal(value, datatype=NamedNode(datatype_uri))
                            elif po.language:
                                obj = Literal(value, language=po.language)
                            else:
                                obj = Literal(value)

                        quads_batch.append(Quad(reifier, predicate, obj))
                        self.stats['quoted_triples_generated'] += 1

            # Bulk insert
            for quad in quads_batch:
                self.store.add(quad)

        print(f"  [OK] Generated quoted triples annotations for {df.height} rows")

    def _extract_join_key(self, join_condition: Optional[Dict]) -> Optional[str]:
        """Extract join key from join condition"""
        if not join_condition:
            return None

        equal_params = join_condition.get('equal', '')
        str1_match = re.search(r'str1=\$\(([^)]+)\)', equal_params)

        if str1_match:
            return str1_match.group(1)

        return None

    def _instantiate_template_single(self, template: str, row_dict: Dict[str, Any]) -> str:
        """Instantiate template for a single row"""
        result = template

        variables = TEMPLATE_VAR_PATTERN.findall(template)
        for var in variables:
            value = row_dict.get(var, '')
            sanitized_value = sanitize_uri_component(value)
            result = result.replace(f"$({var})", sanitized_value)

        result = result.replace('~iri', '')
        result = expand_uri(result, self.prefixes)

        return result

    def run(self):
        """Execute the complete ETL pipeline"""
        start_time = datetime.now()
        print(f"\n{'='*80}")
        print(f"RDF-star ETL Pipeline - YARRRML Direct Processing")
        print(f"{'='*80}")
        print(f"Started at: {start_time}")
        print(f"Mapping file: {self.mapping_file}")

        self.load_mapping()

        # Add metadata
        self.add_metadata()

        # Pass 1: Regular triples
        print(f"\n{'='*80}")
        print(f"Pass 1: Processing regular triples maps")
        print(f"{'='*80}")

        for tm_name, tm in self.parser.triples_maps.items():
            if not tm.subject.is_quoted:
                self.process_triples_map_vectorized(tm_name, tm)

        # Pass 2: Quoted triples
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
        print(f"Output file: {self.output_file}")
        print(f"{'='*80}\n")

    def _write_output(self):
        """Write RDF output to file"""
        # Ensure output directory exists
        output_dir = os.path.dirname(self.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        print(f"\n[{datetime.now()}] Writing output to: {self.output_file}")

        # Build prefix block
        prefix_lines = []
        for prefix, uri in self.prefixes.items():
            prefix_lines.append(f"@prefix {prefix}: <{uri}> .")

        prefix_block = '\n'.join(prefix_lines) + '\n\n'

        # Serialize to TriG format
        buffer = BytesIO()
        self.store.dump(buffer, RdfFormat.TRIG)
        content = buffer.getvalue().decode('utf-8')
        buffer.close()

        # Remove auto-generated prefixes
        lines = content.split('\n')
        filtered_lines = [line for line in lines
                         if not (line.strip().startswith('@prefix') or line.strip().startswith('PREFIX'))]

        # Combine prefixes with content
        final_content = prefix_block + '\n'.join(filtered_lines)

        # Write to file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(final_content)
            f.flush()
            os.fsync(f.fileno())

        file_size = os.path.getsize(self.output_file)
        print(f"[{datetime.now()}] Output written successfully ({file_size:,} bytes)")


def main():
    """Main entry point with command line argument support"""
    parser = argparse.ArgumentParser(
        description='RDF-star ETL Engine - Process YARRRML mappings directly',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python rdf_star_etl_yarrrml.py mappings/data_products_rml.yaml
    python rdf_star_etl_yarrrml.py mappings/my_mapping.yaml output/result.trig
    python rdf_star_etl_yarrrml.py --help
        """
    )

    parser.add_argument(
        'mapping_file',
        help='Path to the YARRRML mapping file'
    )

    parser.add_argument(
        'output_file',
        nargs='?',
        default=None,
        help='Output file path (optional, derived from YARRRML targets or mapping name)'
    )

    args = parser.parse_args()

    if not os.path.exists(args.mapping_file):
        print(f"[ERROR] Mapping file not found: {args.mapping_file}")
        return 1

    try:
        engine = RDFStarETLEngine(args.mapping_file, args.output_file)
        engine.run()
        return 0
    except Exception as e:
        print(f"\n[ERROR] ETL Pipeline failed:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

