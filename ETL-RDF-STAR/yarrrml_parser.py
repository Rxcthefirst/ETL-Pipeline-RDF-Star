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
    inverse_predicate: Optional[str] = None
    graphs: List[str] = field(default_factory=list)
    condition: Optional[Dict[str, Any]] = None
    function: Optional[Dict[str, Any]] = None
    mapping_ref: Optional[str] = None  # For object references to other mappings


@dataclass
class SubjectMapping:
    """Represents a subject mapping (can be URI or quoted triple)"""
    template: Optional[str] = None
    templates: List[str] = field(default_factory=list)  # Multiple subjects
    is_quoted: bool = False
    quoted_mapping_ref: Optional[str] = None
    quoted_non_asserted: bool = False  # For quotedNonAsserted
    join_condition: Optional[Dict[str, Any]] = None
    graphs: List[str] = field(default_factory=list)
    condition: Optional[Dict[str, Any]] = None
    function: Optional[Dict[str, Any]] = None


@dataclass
class TriplesMap:
    """Represents a complete triples map from YARRRML"""
    name: str
    sources: List[Source] = field(default_factory=list)
    subject: SubjectMapping = field(default_factory=SubjectMapping)
    predicate_objects: List[PredicateObject] = field(default_factory=list)
    type_statements: List[str] = field(default_factory=list)
    graphs: List[str] = field(default_factory=list)  # Graphs for all triples
    condition: Optional[Dict[str, Any]] = None  # Condition for entire mapping


class YARRRMLParser:
    """Parser for YARRRML-star mapping files"""

    def __init__(self, mapping_file: str):
        self.mapping_file = mapping_file
        self.prefixes: Dict[str, str] = {}
        self.triples_maps: Dict[str, TriplesMap] = {}
        self.raw_data = None
        self.base_iri: Optional[str] = None
        self.authors: List[Dict[str, str]] = []
        self.external_refs: Dict[str, str] = {}
        self.targets: Dict[str, Dict[str, Any]] = {}
        self.sources: Dict[str, Source] = {}  # Named sources at root level

    def parse(self) -> Dict[str, TriplesMap]:
        """Parse the YARRRML file and return triples maps"""
        with open(self.mapping_file, 'r', encoding='utf-8') as f:
            self.raw_data = yaml.safe_load(f)

        # Parse base IRI
        if 'base' in self.raw_data:
            self.base_iri = self.raw_data['base']

        # Parse authors
        if 'authors' in self.raw_data or 'author' in self.raw_data:
            self.authors = self._parse_authors(self.raw_data.get('authors', self.raw_data.get('author')))

        # Parse external references
        if 'external' in self.raw_data:
            self.external_refs = self.raw_data['external']

        # Parse prefixes
        if 'prefixes' in self.raw_data:
            self.prefixes = self.raw_data['prefixes']

        # Parse root-level sources
        if 'sources' in self.raw_data:
            sources_def = self.raw_data['sources']
            if isinstance(sources_def, dict):
                for source_name, source_spec in sources_def.items():
                    self.sources[source_name] = self._parse_source_definition(source_spec, source_name)

        # Parse root-level targets
        if 'targets' in self.raw_data:
            targets_def = self.raw_data['targets']
            if isinstance(targets_def, dict):
                self.targets = targets_def

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

        # Parse subject (or shortcut 's' or 'subject')
        subject_key = None
        for key in ['subjects', 'subject', 's']:
            if key in mapping_def:
                subject_key = key
                break

        if subject_key:
            triples_map.subject = self._parse_subject(mapping_def[subject_key])

        # Parse predicate-objects (or shortcut 'po')
        po_key = None
        for key in ['predicateobjects', 'po']:
            if key in mapping_def:
                po_key = key
                break

        if po_key:
            triples_map.predicate_objects, triples_map.type_statements = \
                self._parse_predicate_objects(mapping_def[po_key])

        # Parse graphs at mapping level
        if 'graphs' in mapping_def:
            graphs_val = mapping_def['graphs']
            if isinstance(graphs_val, str):
                triples_map.graphs = [graphs_val]
            elif isinstance(graphs_val, list):
                triples_map.graphs = graphs_val

        # Parse condition at mapping level
        if 'condition' in mapping_def:
            triples_map.condition = self._parse_condition(mapping_def['condition'])

        return triples_map

    def _parse_sources(self, sources_def) -> List[Source]:
        """Parse source definitions - handles various formats"""
        sources = []

        # Handle string reference to root-level source
        if isinstance(sources_def, str):
            # Reference to a named source - return placeholder
            sources.append(Source(
                name=sources_def,
                path=sources_def,  # Will be resolved later
                format='csv'
            ))
            return sources

        # Handle single dict (inline long format)
        if isinstance(sources_def, dict):
            source = self._parse_single_source_dict(sources_def)
            if source:
                sources.append(source)
            return sources

        # Handle list of sources
        if isinstance(sources_def, list):
            for source_def in sources_def:
                if isinstance(source_def, list) and len(source_def) > 0:
                    # Shortcut format: ['data.csv~csv', '$']
                    source_str = source_def[0]
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
                elif isinstance(source_def, dict):
                    # Long format dict
                    source = self._parse_single_source_dict(source_def)
                    if source:
                        sources.append(source)
                elif isinstance(source_def, str):
                    # Reference to named source
                    sources.append(Source(
                        name=source_def,
                        path=source_def,
                        format='csv'
                    ))

        return sources

    def _parse_single_source_dict(self, source_dict: Dict) -> Optional[Source]:
        """Parse a single source from dict format"""
        access = source_dict.get('access', '')
        ref_formulation = source_dict.get('referenceFormulation', 'csv')

        if not access:
            return None

        return Source(
            name=access.replace('/', '_').replace('.', '_'),
            path=access,
            format=ref_formulation
        )

    def _parse_subject(self, subject_def) -> SubjectMapping:
        """Parse subject definition (can be template, array, or quoted triple)"""
        subject_mapping = SubjectMapping()

        if isinstance(subject_def, str):
            # Simple template string
            subject_mapping.template = subject_def
            subject_mapping.templates = [subject_def]
        elif isinstance(subject_def, list):
            # Could be multiple subjects OR quoted triple
            has_quoted = False
            for item in subject_def:
                if isinstance(item, dict):
                    # Check for function (quoted triple) or regular dict
                    if 'function' in item:
                        # Quoted triple subject (RDF-star)
                        func_str = item['function']
                        subject_mapping.is_quoted = True

                        # Extract quoted mapping reference
                        quoted_match = re.search(r'quoted=(\w+)', func_str)
                        if quoted_match:
                            subject_mapping.quoted_mapping_ref = quoted_match.group(1)
                            has_quoted = True

                        # Extract quotedNonAsserted
                        if 'quotedNonAsserted=' in func_str:
                            subject_mapping.quoted_non_asserted = True

                        # Extract join condition
                        equal_match = re.search(r'equal\((.+)\)\)', func_str)
                        if equal_match:
                            equal_params = equal_match.group(1)
                            subject_mapping.join_condition = {'equal': equal_params}

                    elif 'quoted' in item:
                        # Long format: quoted: mappingName
                        subject_mapping.is_quoted = True
                        subject_mapping.quoted_mapping_ref = item['quoted']
                        has_quoted = True

                        if 'condition' in item:
                            subject_mapping.join_condition = self._parse_condition(item['condition'])

                    elif 'quotedNonAsserted' in item:
                        # Long format: quotedNonAsserted: mappingName
                        subject_mapping.is_quoted = True
                        subject_mapping.quoted_non_asserted = True
                        subject_mapping.quoted_mapping_ref = item['quotedNonAsserted']
                        has_quoted = True

                        if 'condition' in item:
                            subject_mapping.join_condition = self._parse_condition(item['condition'])

                    elif 'value' in item:
                        # Object with value key
                        subject_mapping.templates.append(item['value'])
                elif isinstance(item, str):
                    # Multiple subject templates
                    subject_mapping.templates.append(item)

            if not has_quoted and subject_mapping.templates:
                # Multiple regular subjects
                subject_mapping.template = subject_mapping.templates[0] if subject_mapping.templates else None

        elif isinstance(subject_def, dict):
            # Dictionary format
            if 'value' in subject_def:
                subject_mapping.template = subject_def['value']
                subject_mapping.templates = [subject_def['value']]

            if 'graphs' in subject_def:
                graphs_val = subject_def['graphs']
                if isinstance(graphs_val, str):
                    subject_mapping.graphs = [graphs_val]
                elif isinstance(graphs_val, list):
                    subject_mapping.graphs = graphs_val

            if 'condition' in subject_def:
                subject_mapping.condition = self._parse_condition(subject_def['condition'])

            if 'function' in subject_def:
                subject_mapping.function = self._parse_function(subject_def['function'])

        return subject_mapping

    def _parse_predicate_objects(self, po_list: List) -> Tuple[List[PredicateObject], List[str]]:
        """Parse predicate-object pairs"""
        predicate_objects = []
        type_statements = []

        for po_def in po_list:
            if isinstance(po_def, list) and len(po_def) >= 2:
                # Shorthand format: [predicate, object] or [predicate, object, datatype/language]
                predicates = po_def[0] if isinstance(po_def[0], list) else [po_def[0]]
                objects = po_def[1] if isinstance(po_def[1], list) else [po_def[1]]

                for predicate in predicates:
                    for obj_value in objects:
                        datatype = None
                        language = None
                        obj_type = "literal"

                        # Parse object value and modifiers
                        if isinstance(obj_value, str):
                            # Check for ~iri suffix
                            if obj_value.endswith('~iri'):
                                obj_type = "iri"
                                obj_value = obj_value[:-4]
                            # Check for language tag ~lang
                            elif '~lang' in obj_value:
                                parts = obj_value.split(',')
                                if len(parts) >= 2:
                                    # Format: [predicate, [value, lang~lang]]
                                    obj_value = parts[0].strip()
                                    language = parts[1].strip().replace('~lang', '').strip()

                        # Check third element for datatype or language
                        if len(po_def) > 2:
                            modifier = po_def[2]
                            if isinstance(modifier, str):
                                if modifier == "iri":
                                    obj_type = "iri"
                                elif modifier.endswith('~lang'):
                                    language = modifier.replace('~lang', '')
                                elif ':' in modifier:
                                    # Looks like a datatype
                                    datatype = modifier
                                else:
                                    datatype = modifier

                        # Check if this is a type statement
                        if predicate == 'a' or predicate == 'rdf:type':
                            type_statements.append(obj_value)
                        else:
                            predicate_objects.append(PredicateObject(
                                predicate=predicate,
                                value=obj_value,
                                object_type=obj_type,
                                datatype=datatype,
                                language=language
                            ))

            elif isinstance(po_def, dict):
                # Long format with 'predicates' and 'objects' keys (or shortcuts 'p', 'o')
                predicates = po_def.get('predicates', po_def.get('predicate', po_def.get('p', [])))
                if not isinstance(predicates, list):
                    predicates = [predicates]

                objects_def = po_def.get('objects', po_def.get('object', po_def.get('o', {})))
                if not isinstance(objects_def, list):
                    objects_def = [objects_def]

                # Parse inverse predicates
                inverse_preds = po_def.get('inversepredicates', po_def.get('inversepredicate', po_def.get('i', [])))
                if not isinstance(inverse_preds, list):
                    inverse_preds = [inverse_preds] if inverse_preds else []

                # Parse graphs for this predicate-object
                graphs = []
                if 'graphs' in po_def:
                    graphs_val = po_def['graphs']
                    if isinstance(graphs_val, str):
                        graphs = [graphs_val]
                    elif isinstance(graphs_val, list):
                        graphs = graphs_val

                # Parse condition for this predicate-object
                condition = None
                if 'condition' in po_def:
                    condition = self._parse_condition(po_def['condition'])

                for pred in predicates:
                    for obj in objects_def:
                        obj_value = None
                        obj_type = "literal"
                        datatype = None
                        language = None
                        function = None
                        mapping_ref = None
                        inverse_predicate = inverse_preds[0] if inverse_preds else None

                        if isinstance(obj, dict):
                            obj_value = obj.get('value', obj.get('v', ''))
                            obj_type = obj.get('type', 'literal')
                            datatype = obj.get('datatype', None)
                            language = obj.get('language', None)

                            # Function on object
                            if 'function' in obj or 'fn' in obj or 'f' in obj:
                                function = self._parse_function(obj.get('function', obj.get('fn', obj.get('f'))))

                            # Reference to another mapping
                            if 'mapping' in obj:
                                mapping_ref = obj['mapping']
                                obj_type = 'iri'
                                if 'condition' in obj:
                                    condition = self._parse_condition(obj['condition'])

                            # Quoted triple in object position
                            if 'quoted' in obj:
                                # TODO: Implement quoted triple in object position
                                pass

                            if 'quotedNonAsserted' in obj:
                                # TODO: Implement quotedNonAsserted in object position
                                pass

                            # Graphs specific to this object
                            if 'graphs' in obj and not graphs:
                                obj_graphs = obj['graphs']
                                if isinstance(obj_graphs, str):
                                    graphs = [obj_graphs]
                                elif isinstance(obj_graphs, list):
                                    graphs = obj_graphs
                        else:
                            # Simple value
                            obj_value = str(obj)

                        predicate_objects.append(PredicateObject(
                            predicate=pred,
                            value=obj_value if obj_value is not None else str(obj),
                            object_type=obj_type,
                            datatype=datatype,
                            language=language,
                            inverse_predicate=inverse_predicate,
                            graphs=graphs,
                            condition=condition,
                            function=function,
                            mapping_ref=mapping_ref
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

    def _parse_authors(self, authors_def) -> List[Dict[str, str]]:
        """Parse authors from various formats"""
        authors = []

        if isinstance(authors_def, str):
            # Single author as string
            authors.append(self._parse_single_author(authors_def))
        elif isinstance(authors_def, list):
            for author in authors_def:
                authors.append(self._parse_single_author(author))

        return authors

    def _parse_single_author(self, author_def) -> Dict[str, str]:
        """Parse a single author from string or dict"""
        if isinstance(author_def, dict):
            return author_def
        elif isinstance(author_def, str):
            # Parse shortcut format: "Name <email> (website)" or WebID
            if author_def.startswith('http://') or author_def.startswith('https://'):
                return {'webid': author_def}

            author = {}
            # Extract email
            email_match = re.search(r'<([^>]+)>', author_def)
            if email_match:
                author['email'] = email_match.group(1)
                author_def = author_def.replace(email_match.group(0), '').strip()

            # Extract website
            website_match = re.search(r'\(([^)]+)\)', author_def)
            if website_match:
                author['website'] = website_match.group(1)
                author_def = author_def.replace(website_match.group(0), '').strip()

            # Remaining is name
            if author_def:
                author['name'] = author_def

            return author

        return {}

    def _parse_function(self, func_def) -> Dict[str, Any]:
        """Parse function definition"""
        if isinstance(func_def, str):
            # Inline format: ex:toLowerCase(input=$(firstname))
            func_name_match = re.match(r'([^(]+)', func_def)
            if func_name_match:
                func_name = func_name_match.group(1).strip()
                params = []

                # Extract parameters
                params_match = re.search(r'\((.+)\)', func_def)
                if params_match:
                    params_str = params_match.group(1)
                    # Split by comma (outside of nested parentheses)
                    param_pairs = self._split_params(params_str)

                    for pair in param_pairs:
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            params.append({'parameter': key.strip(), 'value': value.strip()})

                return {
                    'function': func_name,
                    'parameters': params
                }
        elif isinstance(func_def, dict):
            # Long format already
            return func_def

        return {}

    def _parse_condition(self, condition_def) -> Dict[str, Any]:
        """Parse condition definition"""
        if isinstance(condition_def, dict):
            return condition_def
        return {}

    def _parse_source_definition(self, source_spec, source_name: str) -> Source:
        """Parse a single source definition"""
        if isinstance(source_spec, list):
            # Shortcut format: [path~format, iterator]
            if len(source_spec) > 0:
                path_part = source_spec[0]
                if '~' in path_part:
                    path, fmt = path_part.split('~', 1)
                else:
                    path = path_part
                    fmt = 'csv'

                return Source(name=source_name, path=path, format=fmt)
        elif isinstance(source_spec, dict):
            # Long format
            access = source_spec.get('access', '')
            ref_formulation = source_spec.get('referenceFormulation', 'csv')

            return Source(
                name=source_name,
                path=access,
                format=ref_formulation
            )

        return Source(name=source_name, path=str(source_spec), format='csv')

    def _split_params(self, params_str: str) -> List[str]:
        """Split function parameters by comma, respecting nested parentheses"""
        params = []
        current = ""
        depth = 0

        for char in params_str:
            if char == '(':
                depth += 1
                current += char
            elif char == ')':
                depth -= 1
                current += char
            elif char == ',' and depth == 0:
                params.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            params.append(current.strip())

        return params


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

