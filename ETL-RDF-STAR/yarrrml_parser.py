"""
YARRRML-star Parser for RDF-star ETL Pipeline
==============================================

This module parses YARRRML-star mapping files and extracts:
- Prefixes/namespaces
- Source definitions (CSV files)
- Subject mappings (including quoted triple subjects for RDF-star)
- Predicate-object mappings
- RDF-star annotations (quoted triples)

Supports YARRRML-star features:
- Standard triples
- Quoted triples (RDF-star subjects)
- Join functions for linking quoted triples
- Multiple object types (literal, iri, typed literals)
"""

import yaml
import re
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Source:
    """Represents a data source (e.g., CSV file)"""
    name: str
    path: str
    format: str = "csv"


@dataclass
class PredicateObject:
    """Represents a predicate-object pair in RML mapping"""
    predicate: str
    value: str
    object_type: str = "literal"  # literal, iri, or blank
    datatype: Optional[str] = None
    language: Optional[str] = None


@dataclass
class SubjectMapping:
    """Represents a subject mapping (can be URI or quoted triple)"""
    template: Optional[str] = None
    is_quoted: bool = False
    quoted_mapping_ref: Optional[str] = None
    join_condition: Optional[Dict[str, Any]] = None


@dataclass
class TriplesMap:
    """Represents a complete triples map from YARRRML"""
    name: str
    sources: List[Source] = field(default_factory=list)
    subject: SubjectMapping = field(default_factory=SubjectMapping)
    predicate_objects: List[PredicateObject] = field(default_factory=list)
    type_statements: List[str] = field(default_factory=list)


class YARRRMLParser:
    """Parser for YARRRML-star mapping files"""

    def __init__(self, mapping_file: str):
        self.mapping_file = mapping_file
        self.prefixes: Dict[str, str] = {}
        self.triples_maps: Dict[str, TriplesMap] = {}
        self.raw_data = None

    def parse(self) -> Dict[str, TriplesMap]:
        """Parse the YARRRML file and return triples maps"""
        with open(self.mapping_file, 'r', encoding='utf-8') as f:
            self.raw_data = yaml.safe_load(f)

        # Parse prefixes
        if 'prefixes' in self.raw_data:
            self.prefixes = self.raw_data['prefixes']

        # Parse mappings
        if 'mappings' in self.raw_data:
            for mapping_name, mapping_def in self.raw_data['mappings'].items():
                triples_map = self._parse_triples_map(mapping_name, mapping_def)
                self.triples_maps[mapping_name] = triples_map

        return self.triples_maps

    def _parse_triples_map(self, name: str, mapping_def: Dict) -> TriplesMap:
        """Parse a single triples map"""
        triples_map = TriplesMap(name=name)

        # Parse sources
        if 'sources' in mapping_def:
            triples_map.sources = self._parse_sources(mapping_def['sources'])

        # Parse subject
        if 'subject' in mapping_def:
            triples_map.subject = self._parse_subject(mapping_def['subject'])

        # Parse predicate-objects
        if 'predicateobjects' in mapping_def:
            triples_map.predicate_objects, triples_map.type_statements = \
                self._parse_predicate_objects(mapping_def['predicateobjects'])

        return triples_map

    def _parse_sources(self, sources_list: List) -> List[Source]:
        """Parse source definitions"""
        sources = []
        for source_def in sources_list:
            if isinstance(source_def, list) and len(source_def) > 0:
                source_str = source_def[0]
                # Parse format like 'data_products.csv~csv'
                if '~' in source_str:
                    path, fmt = source_str.split('~', 1)
                else:
                    path = source_str
                    fmt = 'csv'

                sources.append(Source(
                    name=path.replace('.csv', '').replace('.', '_'),
                    path=path,
                    format=fmt
                ))
        return sources

    def _parse_subject(self, subject_def) -> SubjectMapping:
        """Parse subject definition (can be template or quoted triple)"""
        subject_mapping = SubjectMapping()

        if isinstance(subject_def, str):
            # Simple template string
            subject_mapping.template = subject_def
        elif isinstance(subject_def, list):
            # Quoted triple subject (RDF-star)
            for item in subject_def:
                if isinstance(item, dict) and 'function' in item:
                    # Parse join function for quoted triples
                    func_str = item['function']
                    subject_mapping.is_quoted = True

                    # Extract quoted mapping reference
                    # e.g., "join(quoted=datasetThemeTM, equal(str1=$(dataset_id), str2=$(dataset_id)))"
                    quoted_match = re.search(r'quoted=(\w+)', func_str)
                    if quoted_match:
                        subject_mapping.quoted_mapping_ref = quoted_match.group(1)

                    # Extract join condition
                    # Handle nested parentheses: equal(str1=$(dataset_id), str2=$(dataset_id))
                    equal_match = re.search(r'equal\((.+)\)\)', func_str)
                    if equal_match:
                        equal_params = equal_match.group(1)
                        subject_mapping.join_condition = {'equal': equal_params}

        return subject_mapping

    def _parse_predicate_objects(self, po_list: List) -> Tuple[List[PredicateObject], List[str]]:
        """Parse predicate-object pairs"""
        predicate_objects = []
        type_statements = []

        for po_def in po_list:
            if isinstance(po_def, list) and len(po_def) >= 2:
                # Shorthand format: [predicate, object] or [predicate, object, datatype]
                predicate = po_def[0]
                obj_value = po_def[1]
                datatype = po_def[2] if len(po_def) > 2 else None

                # Check if this is a type statement
                if predicate == 'a' or predicate == 'rdf:type':
                    type_statements.append(obj_value)
                else:
                    # Determine object type
                    obj_type = "literal"
                    if datatype:
                        # Check if datatype indicates IRI
                        if datatype == "iri":
                            obj_type = "iri"

                    predicate_objects.append(PredicateObject(
                        predicate=predicate,
                        value=obj_value,
                        object_type=obj_type,
                        datatype=datatype
                    ))

            elif isinstance(po_def, dict):
                # Long format with 'predicates' and 'objects' keys
                predicates = po_def.get('predicates', po_def.get('predicate', []))
                if not isinstance(predicates, list):
                    predicates = [predicates]

                objects_def = po_def.get('objects', po_def.get('object', {}))
                if not isinstance(objects_def, list):
                    objects_def = [objects_def]

                for pred in predicates:
                    for obj in objects_def:
                        if isinstance(obj, dict):
                            obj_value = obj.get('value', '')
                            obj_type = obj.get('type', 'literal')
                            datatype = obj.get('datatype', None)
                            language = obj.get('language', None)

                            predicate_objects.append(PredicateObject(
                                predicate=pred,
                                value=obj_value,
                                object_type=obj_type,
                                datatype=datatype,
                                language=language
                            ))
                        else:
                            # Simple value
                            predicate_objects.append(PredicateObject(
                                predicate=pred,
                                value=str(obj),
                                object_type="literal"
                            ))

        return predicate_objects, type_statements

    def expand_prefix(self, prefixed_uri: str) -> str:
        """Expand a prefixed URI to full URI"""
        if ':' in prefixed_uri and not prefixed_uri.startswith('http'):
            prefix, local_name = prefixed_uri.split(':', 1)
            if prefix in self.prefixes:
                return self.prefixes[prefix] + local_name
        return prefixed_uri

    def extract_template_variables(self, template: str) -> List[str]:
        """Extract variable names from a template string like 'ex:dataset/$(dataset_id)'"""
        # Match $(variable_name) pattern
        variables = re.findall(r'\$\(([^)]+)\)', template)
        return variables

    def instantiate_template(self, template: str, row_data: Dict[str, Any]) -> str:
        """Instantiate a template with actual data from a row"""
        result = template

        # Replace $(variable) with actual values
        for var_name in self.extract_template_variables(template):
            placeholder = f"$({var_name})"
            value = row_data.get(var_name, '')
            # Sanitize value for URI
            if value:
                value = str(value).replace(' ', '_').replace('/', '_')
            result = result.replace(placeholder, str(value))

        return result

    def get_required_csv_files(self) -> List[str]:
        """Get list of all CSV files referenced in the mappings"""
        csv_files = set()
        for tm in self.triples_maps.values():
            for source in tm.sources:
                if source.format == 'csv':
                    csv_files.add(source.path)
        return sorted(list(csv_files))

    def get_required_columns_for_source(self, source_path: str) -> List[str]:
        """Get all columns needed from a specific CSV source"""
        columns = set()

        for tm in self.triples_maps.values():
            # Check if this triples map uses this source
            uses_source = any(s.path == source_path for s in tm.sources)
            if not uses_source:
                continue

            # Extract variables from subject template
            if tm.subject.template:
                columns.update(self.extract_template_variables(tm.subject.template))

            # Extract variables from predicate-objects
            for po in tm.predicate_objects:
                columns.update(self.extract_template_variables(po.value))
                if po.predicate:
                    columns.update(self.extract_template_variables(po.predicate))

        return sorted(list(columns))


def test_parser():
    """Test the YARRRML parser with the data_products_rml.yaml file"""
    parser = YARRRMLParser("mappings/data_products_rml.yaml")
    triples_maps = parser.parse()

    print("=== YARRRML Parser Test ===\n")
    print(f"Prefixes: {parser.prefixes}\n")
    print(f"Number of triples maps: {len(triples_maps)}\n")

    for name, tm in triples_maps.items():
        print(f"\n--- Triples Map: {name} ---")
        print(f"Sources: {[s.path for s in tm.sources]}")
        print(f"Subject template: {tm.subject.template}")
        print(f"Is quoted triple: {tm.subject.is_quoted}")
        if tm.subject.quoted_mapping_ref:
            print(f"Quoted mapping ref: {tm.subject.quoted_mapping_ref}")
        print(f"Type statements: {tm.type_statements}")
        print(f"Predicate-objects ({len(tm.predicate_objects)}):")
        for po in tm.predicate_objects[:3]:  # Show first 3
            print(f"  - {po.predicate}: {po.value} (type: {po.object_type}, datatype: {po.datatype})")

    print("\n\n=== Required CSV Files ===")
    csv_files = parser.get_required_csv_files()
    for csv_file in csv_files:
        print(f"\n{csv_file}:")
        columns = parser.get_required_columns_for_source(csv_file)
        print(f"  Required columns: {columns}")


if __name__ == "__main__":
    test_parser()

