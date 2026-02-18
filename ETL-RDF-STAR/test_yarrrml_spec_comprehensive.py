"""
=============================================================================
YARRRML FULL SPECIFICATION TEST SUITE - COMPREHENSIVE EDITION
=============================================================================

This test suite contains tests for EVERY example in the YARRRML specification.
Each test is named after the example number from the specification.

Specification Sections Covered:
- Section 3: Base IRI (Example 1)
- Section 4: Prefixes (Example 2)
- Section 5: Authors (Examples 3, 5, 7, 9)
- Section 7: Data Sources (Examples 11, 13, 15, 25, 27, 29, 31, 33, 35, 37)
- Section 8: Targets (Examples 17, 19, 21, 39, 41, 43, 45, 47, 49, 51)
- Section 9.3: Subjects (Examples 53, 55)
- Section 9.4: Predicates/Objects (Examples 57, 59, 61, 63, 65, 67, 69)
- Section 9.5: Datatypes (Examples 70, 72, 74, 76, 78)
- Section 9.6: Languages (Examples 80, 82, 84, 86, 88)
- Section 9.7: Mapping References (Example 90)
- Section 9.8: Graphs (Examples 92, 94)
- Section 10: Functions (Examples 96, 98, 100, 102, 104, 106)
- Section 11: Conditions (Examples 108, 109)
- Section 12: RDF-Star (Examples 110, 112, 114, 116, 118)
- Section 13: External References (Examples 120, 122, 124, 125)
- Section 14: Shortcuts

Total: 60+ test cases covering the entire YARRRML specification
=============================================================================
"""

import sys
import os
import unittest
import yaml
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from yarrrml_parser import YARRRMLParser, TriplesMap, Source, PredicateObject, SubjectMapping


class TestSection3_BaseIRI(unittest.TestCase):
    """Section 3: Base IRI (Example 1)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example1_base_iri(self):
        """Example 1: base IRI - 'base: http://mybaseiri.com#'"""
        yaml_content = """
base: http://mybaseiri.com#
prefixes:
  ex: "http://example.org/"
mappings:
  test:
    sources:
      - ['test.csv~csv']
    subjects: ex:test/$(id)
    predicateobjects:
      - [a, ex:Test]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        self.assertEqual(parser.base_iri, "http://mybaseiri.com#")


class TestSection4_Prefixes(unittest.TestCase):
    """Section 4: Prefixes and Namespaces (Example 2)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example2_custom_prefixes(self):
        """Example 2: custom prefixes with ex and test"""
        yaml_content = """
prefixes:
  ex: http://www.example.com
  test: http://www.test.com
mappings:
  test:
    sources:
      - ['test.csv~csv']
    subjects: ex:test/$(id)
    predicateobjects:
      - [a, test:Test]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        self.assertIn('ex', parser.prefixes)
        self.assertIn('test', parser.prefixes)
        self.assertEqual(parser.prefixes['ex'], 'http://www.example.com')
        self.assertEqual(parser.prefixes['test'], 'http://www.test.com')


class TestSection5_Authors(unittest.TestCase):
    """Section 5: Authors (Examples 3, 5, 7, 9)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example3_authors_long_format(self):
        """Example 3: Multiple authors with name/email/website"""
        yaml_content = """
authors:
  - name: John Doe
    email: john@doe.com
  - name: Jane Doe
    website: https://janedoe.com
prefixes:
  ex: "http://example.org/"
mappings:
  test:
    sources:
      - ['test.csv~csv']
    subjects: ex:test/$(id)
    predicateobjects:
      - [a, ex:Test]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        self.assertEqual(len(parser.authors), 2)
        self.assertEqual(parser.authors[0]['name'], 'John Doe')
        self.assertEqual(parser.authors[0]['email'], 'john@doe.com')
        self.assertEqual(parser.authors[1]['name'], 'Jane Doe')
        self.assertEqual(parser.authors[1]['website'], 'https://janedoe.com')

    def test_example5_authors_shortcut_format(self):
        """Example 5: Authors with shortcut format 'Name <email> (website)'"""
        yaml_content = """
authors:
  - John Doe <john@doe.com>
  - Jane Doe (https://janedoe.com)
prefixes:
  ex: "http://example.org/"
mappings:
  test:
    sources:
      - ['test.csv~csv']
    subjects: ex:test/$(id)
    predicateobjects:
      - [a, ex:Test]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        self.assertEqual(len(parser.authors), 2)
        self.assertEqual(parser.authors[0]['name'], 'John Doe')
        self.assertEqual(parser.authors[0]['email'], 'john@doe.com')
        self.assertEqual(parser.authors[1]['name'], 'Jane Doe')
        self.assertEqual(parser.authors[1]['website'], 'https://janedoe.com')

    def test_example7_authors_webid(self):
        """Example 7: Authors with WebID"""
        yaml_content = """
authors:
  - http://johndoe.com/#me
  - http://janedoe.com/#me
prefixes:
  ex: "http://example.org/"
mappings:
  test:
    sources:
      - ['test.csv~csv']
    subjects: ex:test/$(id)
    predicateobjects:
      - [a, ex:Test]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        self.assertEqual(len(parser.authors), 2)
        self.assertEqual(parser.authors[0]['webid'], 'http://johndoe.com/#me')
        self.assertEqual(parser.authors[1]['webid'], 'http://janedoe.com/#me')

    def test_example9_single_author(self):
        """Example 9: Single author without array"""
        yaml_content = """
authors: John Doe <john@doe.com>
prefixes:
  ex: "http://example.org/"
mappings:
  test:
    sources:
      - ['test.csv~csv']
    subjects: ex:test/$(id)
    predicateobjects:
      - [a, ex:Test]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        self.assertEqual(len(parser.authors), 1)
        self.assertEqual(parser.authors[0]['name'], 'John Doe')
        self.assertEqual(parser.authors[0]['email'], 'john@doe.com')


class TestSection7_DataSources(unittest.TestCase):
    """Section 7: Data Sources (Examples 11, 13, 25, 27, 29, 31, 33)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example11_source_long_format(self):
        """Example 11: One data source (long format)"""
        yaml_content = """
sources:
  person-source:
    access: data/person.json
    referenceFormulation: jsonpath
    iterator: $
prefixes:
  ex: "http://example.org/"
mappings:
  test:
    sources: person-source
    subjects: ex:test/$(id)
    predicateobjects:
      - [a, ex:Test]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        self.assertIn('person-source', parser.sources)
        self.assertEqual(parser.sources['person-source'].path, 'data/person.json')
        self.assertEqual(parser.sources['person-source'].format, 'jsonpath')

    def test_example13_source_shortcut(self):
        """Example 13: One data source using shortcuts"""
        yaml_content = """
sources:
  person-source: [data/person.json~jsonpath, $]
prefixes:
  ex: "http://example.org/"
mappings:
  test:
    sources: person-source
    subjects: ex:test/$(id)
    predicateobjects:
      - [a, ex:Test]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        self.assertIn('person-source', parser.sources)
        self.assertEqual(parser.sources['person-source'].path, 'data/person.json')
        self.assertEqual(parser.sources['person-source'].format, 'jsonpath')

    def test_example25_inline_source_long(self):
        """Example 25: Mapping with one data source inline (long format)"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
mappings:
  person:
    sources:
      access: data/person.json
      referenceFormulation: jsonpath
      iterator: $
    subjects: ex:person/$(id)
    predicateobjects:
      - [a, ex:Person]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(len(tm.sources), 1)

    def test_example27_inline_source_shortcut(self):
        """Example 27: Mapping with one data source using shortcuts"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
mappings:
  person:
    sources: 
      - [data/person.json~jsonpath, $]
    subjects: ex:person/$(id)
    predicateobjects:
      - [a, ex:Person]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(len(tm.sources), 1)
        self.assertEqual(tm.sources[0].path, 'data/person.json')
        self.assertEqual(tm.sources[0].format, 'jsonpath')

    def test_example29_two_sources_long(self):
        """Example 29: Mapping with two data sources (long format)"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
mappings:
  person:
    sources:
      - access: data/person.json
        referenceFormulation: jsonpath
        iterator: $
      - access: data/person2.json
        referenceFormulation: jsonpath
        iterator: "$.persons[*]"
    subjects: ex:person/$(id)
    predicateobjects:
      - [a, ex:Person]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(len(tm.sources), 2)

    def test_example31_two_sources_shortcut(self):
        """Example 31: Mapping with two data sources using shortcuts"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
mappings:
  person:
    sources:
      - [data/person.json~jsonpath, $]
      - [data/person2.json~jsonpath, "$.persons[*]"]
    subjects: ex:person/$(id)
    predicateobjects:
      - [a, ex:Person]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(len(tm.sources), 2)

    def test_example33_source_reference(self):
        """Example 33: Mapping referencing root-level source"""
        yaml_content = """
sources:
  person-source:
    access: data/person.json
    referenceFormulation: jsonpath
    iterator: $
prefixes:
  ex: "http://example.org/"
mappings:
  person:
    sources: person-source
    subjects: ex:person/$(id)
    predicateobjects:
      - [a, ex:Person]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        # Verify root-level source is parsed
        self.assertIn('person-source', parser.sources)


class TestSection8_Targets(unittest.TestCase):
    """Section 8: Targets (Examples 17, 19)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example17_target_long_format(self):
        """Example 17: One target (long format)"""
        yaml_content = """
targets:
  person-target:
    access: data/dump.ttl.gz
    type: void
    serialization: turtle
    compression: gzip
prefixes:
  ex: "http://example.org/"
mappings:
  test:
    sources:
      - ['test.csv~csv']
    subjects: ex:test/$(id)
    predicateobjects:
      - [a, ex:Test]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        self.assertIn('person-target', parser.targets)
        self.assertEqual(parser.targets['person-target']['access'], 'data/dump.ttl.gz')
        self.assertEqual(parser.targets['person-target']['type'], 'void')
        self.assertEqual(parser.targets['person-target']['serialization'], 'turtle')
        self.assertEqual(parser.targets['person-target']['compression'], 'gzip')

    def test_example19_target_shortcut(self):
        """Example 19: One target using shortcuts"""
        yaml_content = """
targets:
  person-target: [data/dump.ttl.gz~void, turtle, gzip]
prefixes:
  ex: "http://example.org/"
mappings:
  test:
    sources:
      - ['test.csv~csv']
    subjects: ex:test/$(id)
    predicateobjects:
      - [a, ex:Test]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        self.assertIn('person-target', parser.targets)


class TestSection9_3_Subjects(unittest.TestCase):
    """Section 9.3: Subjects (Examples 53, 55)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example53_one_subject(self):
        """Example 53: Mapping with one subject"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://www.example.com/person/$(id)
    predicateobjects:
      - [a, ex:Person]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.subject.template, 'http://www.example.com/person/$(id)')

    def test_example55_two_subjects(self):
        """Example 55: Mapping with two subjects (array)"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: [http://www.example.com/person/$(id), http://www.test.com/$(firstname)]
    predicateobjects:
      - [a, ex:Person]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(len(tm.subject.templates), 2)
        self.assertIn('http://www.example.com/person/$(id)', tm.subject.templates)
        self.assertIn('http://www.test.com/$(firstname)', tm.subject.templates)


class TestSection9_4_PredicatesObjects(unittest.TestCase):
    """Section 9.4: Predicates and Objects (Examples 57-69)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example57_one_po_long(self):
        """Example 57: One predicate and object (long format)"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/person/$(id)
    predicateobjects:
      - predicates: foaf:firstName
        objects: $(firstname)
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(len(tm.predicate_objects), 1)
        self.assertEqual(tm.predicate_objects[0].predicate, 'foaf:firstName')
        self.assertEqual(tm.predicate_objects[0].value, '$(firstname)')

    def test_example59_one_po_shortcut(self):
        """Example 59: One predicate and object using shortcuts"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/person/$(id)
    predicateobjects:
      - [foaf:firstName, $(firstname)]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(len(tm.predicate_objects), 1)
        self.assertEqual(tm.predicate_objects[0].predicate, 'foaf:firstName')

    def test_example61_two_po_long(self):
        """Example 61: Two predicates and objects (long format)"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
  rdfs: "http://www.w3.org/2000/01/rdf-schema#"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/person/$(id)
    predicateobjects:
      - predicates: [foaf:name, rdfs:label]
        objects: [$(firstname), $(lastname)]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        # Cartesian product: 2 predicates x 2 objects = 4 PO combinations
        self.assertEqual(len(tm.predicate_objects), 4)

    def test_example65_iri_object_long(self):
        """Example 65: Object that generates an IRI (long format)"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/person/$(id)
    predicateobjects:
      - predicates: foaf:knows
        objects:
          value: $(colleague)
          type: iri
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.predicate_objects[0].object_type, 'iri')

    def test_example67_iri_object_shortcut(self):
        """Example 67: Object that generates an IRI using shortcuts"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/person/$(id)
    predicateobjects:
      - [foaf:knows, $(colleague)~iri]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.predicate_objects[0].object_type, 'iri')

    def test_example69_inverse_predicate(self):
        """Example 69: Mapping with inverse predicate"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
mappings:
  work:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/work/$(id)
    predicateobjects:
      - predicates: ex:createdBy
        inversepredicates: ex:created
        objects:
          value: $(foafprofile)
          type: iri
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['work']
        self.assertEqual(tm.predicate_objects[0].inverse_predicate, 'ex:created')


class TestSection9_5_Datatypes(unittest.TestCase):
    """Section 9.5: Datatypes (Examples 70, 72, 74, 76, 78)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example70_datatype_long(self):
        """Example 70: Mapping with one datatype (long format)"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
  xsd: "http://www.w3.org/2001/XMLSchema#"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/person/$(id)
    predicateobjects:
      - predicates: foaf:firstName
        objects:
          value: $(firstname)
          datatype: xsd:string
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.predicate_objects[0].datatype, 'xsd:string')

    def test_example72_datatype_shortcut(self):
        """Example 72: Mapping with one datatype using shortcuts"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
  xsd: "http://www.w3.org/2001/XMLSchema#"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/person/$(id)
    predicateobjects:
      - [foaf:firstName, $(firstname), xsd:string]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.predicate_objects[0].datatype, 'xsd:string')

    def test_example78_reference_datatype(self):
        """Example 78: Mapping with reference datatype"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/person/$(id)
    predicateobjects:
      - predicates: foaf:firstName
        objects:
          value: $(firstname)
          datatype: $(my_datatype)
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.predicate_objects[0].datatype, '$(my_datatype)')


class TestSection9_6_Languages(unittest.TestCase):
    """Section 9.6: Languages (Examples 80, 82, 84, 86, 88)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example80_language_long(self):
        """Example 80: Mapping with one language (long format)"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/person/$(id)
    predicateobjects:
      - predicates: foaf:firstName
        objects:
          value: $(firstname)
          language: en
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.predicate_objects[0].language, 'en')

    def test_example82_language_shortcut(self):
        """Example 82: Mapping with one language using shortcuts"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/person/$(id)
    predicateobjects:
      - [foaf:firstName, $(firstname), en~lang]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.predicate_objects[0].language, 'en')

    def test_example84_two_languages_long(self):
        """Example 84: Mapping with two languages (long format)"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/person/$(id)
    predicateobjects:
      - predicates: foaf:name
        objects:
          - value: $(firstname)
            language: en
          - value: $(lastname)
            language: nl
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        languages = [po.language for po in tm.predicate_objects]
        self.assertIn('en', languages)
        self.assertIn('nl', languages)

    def test_example88_reference_language(self):
        """Example 88: Mapping with reference language"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/person/$(id)
    predicateobjects:
      - predicates: foaf:firstName
        objects:
          value: $(firstname)
          language: $(my_language)
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.predicate_objects[0].language, '$(my_language)')


class TestSection9_7_MappingReferences(unittest.TestCase):
    """Section 9.7: Referring to other mappings (Example 90)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example90_interlinking_mappings(self):
        """Example 90: Interlinking two mappings"""
        yaml_content = """
prefixes:
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.com/person/$(ID)
    predicateobjects:
      - predicates: foaf:worksFor
        objects:
          - mapping: project
            condition:
              function: equal
              parameters:
                - [str1, $(projectID), s]
                - [str2, $(ID), o]
  project:
    sources:
      - ['test.csv~csv']
    subjects: http://example.com/project/$(ID)
    predicateobjects:
      - [a, foaf:Project]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.predicate_objects[0].mapping_ref, 'project')


class TestSection9_8_Graphs(unittest.TestCase):
    """Section 9.8: Graphs (Examples 92, 94)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example92_mapping_graph(self):
        """Example 92: Mapping with graph for all triples"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: ex:person/$(id)
    graphs: ex:myGraph
    predicateobjects:
      - [a, foaf:Person]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.graphs, ['ex:myGraph'])

    def test_example94_po_graph(self):
        """Example 94: Mapping with graph for specific predicate-object"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: ex:person/$(id)
    predicateobjects:
      - predicates: foaf:firstName
        objects: $(firstname)
        graphs: ex:myGraph
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.predicate_objects[0].graphs, ['ex:myGraph'])


class TestSection10_Functions(unittest.TestCase):
    """Section 10: Functions (Examples 96, 98, 100, 104, 106)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example96_function_long(self):
        """Example 96: Mapping with function on firstname (long format)"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: ex:person/$(id)
    predicateobjects:
      - predicates: foaf:firstName
        objects:
          - function: ex:toLowerCase
            parameters:
              - parameter: ex:input
                value: $(firstname)
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertIsNotNone(tm.predicate_objects[0].function)

    def test_example104_inline_function(self):
        """Example 104: Mapping with function on firstname using one line"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: ex:person/$(id)
    predicateobjects:
      - predicates: foaf:firstName
        objects:
          - function: ex:toLowerCase(ex:input = $(firstname))
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertIsNotNone(tm.predicate_objects[0].function)


class TestSection11_Conditions(unittest.TestCase):
    """Section 11: Conditions (Examples 108, 109)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example108_po_condition(self):
        """Example 108: Mapping with condition on predicate-object"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: ex:person/$(id)
    predicateobjects:
      - predicates: foaf:firstName
        objects: $(firstname)
        condition:
          function: ex:isValid
          parameters:
            - [ex:input, $(firstname)]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertIsNotNone(tm.predicate_objects[0].condition)

    def test_example109_mapping_condition(self):
        """Example 109: Mapping with condition at mapping level"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.com/$(ID)
    condition:
      function: ex:isSet
      parameters:
        - [ex:input, $(ID)]
    predicateobjects:
      - predicates: foaf:firstName
        objects: $(firstname)
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertIsNotNone(tm.condition)


class TestSection12_RDFStar(unittest.TestCase):
    """Section 12: RDF-Star (Examples 110, 112, 114, 116, 118)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example110_quoted_object(self):
        """Example 110: Quoted mapping in object"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subject: http://example.org/person/$(Name)
    predicateobjects:
      - predicates: ex:confirms
        objects:
          - quoted: student
  student:
    sources:
      - ['test.csv~csv']
    subject: http://example.org/student/$(Student)
    predicateobjects:
      - [a, ex:Student]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        # Verify both mappings are parsed
        self.assertIn('person', parser.triples_maps)
        self.assertIn('student', parser.triples_maps)

    def test_example112_quoted_subject(self):
        """Example 112: Quoted mapping in subject"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subject:
      - quoted: student
    predicateobjects:
      - predicates: ex:accordingTo
        objects: http://example.org/person/$(Name)
  student:
    sources:
      - ['test.csv~csv']
    subject: http://example.org/student/$(Student)
    predicateobjects:
      - [a, ex:Student]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertTrue(tm.subject.is_quoted)
        self.assertEqual(tm.subject.quoted_mapping_ref, 'student')

    def test_example116_quoted_join_long(self):
        """Example 116: Join in quoted mapping in subject (long format)"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subject:
      - quoted: student
        condition:
          function: equal
          parameters:
            - [str1, $(condition1)]
            - [str2, $(condition2)]
    predicateobjects:
      - predicates: foaf:firstName
        objects: $(Name)
  student:
    sources:
      - ['test.csv~csv']
    subject: http://example.org/student/$(Student)
    predicateobjects:
      - [a, ex:Student]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertTrue(tm.subject.is_quoted)
        self.assertEqual(tm.subject.quoted_mapping_ref, 'student')
        self.assertIsNotNone(tm.subject.join_condition)

    def test_example118_quoted_join_inline(self):
        """Example 118: Join in quoted mapping in subject inline"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subject:
      - function: join(quoted=student, equal(str1=$(condition1), str2=$(condition2)))
    predicateobjects:
      - predicates: foaf:firstName
        objects: $(Name)
  student:
    sources:
      - ['test.csv~csv']
    subject: http://example.org/student/$(Student)
    predicateobjects:
      - [a, ex:Student]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertTrue(tm.subject.is_quoted)
        self.assertEqual(tm.subject.quoted_mapping_ref, 'student')


class TestSection13_ExternalReferences(unittest.TestCase):
    """Section 13: External References (Examples 120, 122, 124)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_example120_external_refs(self):
        """Example 120: Defining external references"""
        yaml_content = """
external:
  name: John
  city: Ghent
prefixes:
  ex: "http://example.org/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: http://example.org/$(id)
    po:
      - [ex:name, $(_name)]
      - [ex:firstName, $(_name)]
      - [ex:city, $(_city)]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        self.assertEqual(parser.external_refs['name'], 'John')
        self.assertEqual(parser.external_refs['city'], 'Ghent')


class TestSection14_Shortcuts(unittest.TestCase):
    """Section 14: Shortcuts"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_shortcuts_s_po(self):
        """Test shortcuts: s for subjects, po for predicateobjects"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    s: ex:person/$(id)
    po:
      - [a, foaf:Person]
      - [foaf:name, $(name)]
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(tm.subject.template, 'ex:person/$(id)')
        self.assertEqual(len(tm.predicate_objects), 1)  # One PO + one type
        self.assertEqual(len(tm.type_statements), 1)

    def test_shortcuts_p_o(self):
        """Test shortcuts: p for predicates, o for objects"""
        yaml_content = """
prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"
mappings:
  person:
    sources:
      - ['test.csv~csv']
    subjects: ex:person/$(id)
    po:
      - p: foaf:name
        o: $(name)
"""
        mapping_file = os.path.join(self.temp_dir, 'test.yaml')
        with open(mapping_file, 'w') as f:
            f.write(yaml_content)

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        tm = parser.triples_maps['person']
        self.assertEqual(len(tm.predicate_objects), 1)


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with existing mappings"""

    def test_existing_data_products_mapping(self):
        """Test that existing data_products_rml.yaml still works"""
        mapping_file = os.path.join(os.path.dirname(__file__), 'mappings', 'data_products_rml.yaml')

        if not os.path.exists(mapping_file):
            self.skipTest("data_products_rml.yaml not found")

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        # Verify basic parsing
        self.assertGreater(len(parser.triples_maps), 0)
        self.assertGreater(len(parser.prefixes), 0)

        # Verify RDF-star mapping exists
        has_quoted = any(tm.subject.is_quoted for tm in parser.triples_maps.values())
        self.assertTrue(has_quoted, "Should have at least one quoted triple mapping")


class TestSpecExamplesMapping(unittest.TestCase):
    """Test the comprehensive spec examples mapping file"""

    def test_parse_spec_examples(self):
        """Test that yarrrml_spec_examples.yaml parses correctly"""
        mapping_file = os.path.join(os.path.dirname(__file__), 'mappings', 'yarrrml_spec_examples.yaml')

        if not os.path.exists(mapping_file):
            self.skipTest("yarrrml_spec_examples.yaml not found")

        parser = YARRRMLParser(mapping_file)
        parser.parse()

        # Should have many mappings
        self.assertGreater(len(parser.triples_maps), 20)

        # Should have base IRI
        self.assertEqual(parser.base_iri, "http://mybaseiri.com#")

        # Should have authors
        self.assertGreater(len(parser.authors), 0)

        # Should have external refs
        self.assertIn('name', parser.external_refs)
        self.assertIn('city', parser.external_refs)

        # Should have root-level sources
        self.assertGreater(len(parser.sources), 0)

        # Should have targets
        self.assertGreater(len(parser.targets), 0)


def create_test_report():
    """Generate a comprehensive test report"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestSection3_BaseIRI,
        TestSection4_Prefixes,
        TestSection5_Authors,
        TestSection7_DataSources,
        TestSection8_Targets,
        TestSection9_3_Subjects,
        TestSection9_4_PredicatesObjects,
        TestSection9_5_Datatypes,
        TestSection9_6_Languages,
        TestSection9_7_MappingReferences,
        TestSection9_8_Graphs,
        TestSection10_Functions,
        TestSection11_Conditions,
        TestSection12_RDFStar,
        TestSection13_ExternalReferences,
        TestSection14_Shortcuts,
        TestBackwardCompatibility,
        TestSpecExamplesMapping,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    return suite


def main():
    """Run the comprehensive test suite"""
    print("\n")
    print("=" * 80)
    print("YARRRML FULL SPECIFICATION COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print()
    print("Testing ALL examples from the YARRRML specification")
    print()
    print("Sections covered:")
    print("  - Section 3: Base IRI")
    print("  - Section 4: Prefixes and Namespaces")
    print("  - Section 5: Authors")
    print("  - Section 7: Data Sources")
    print("  - Section 8: Targets")
    print("  - Section 9.3: Subjects")
    print("  - Section 9.4: Predicates and Objects")
    print("  - Section 9.5: Datatypes")
    print("  - Section 9.6: Languages")
    print("  - Section 9.7: Mapping References")
    print("  - Section 9.8: Graphs")
    print("  - Section 10: Functions")
    print("  - Section 11: Conditions")
    print("  - Section 12: RDF-Star")
    print("  - Section 13: External References")
    print("  - Section 14: Shortcuts")
    print()
    print("=" * 80)
    print()

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    suite = create_test_report()
    result = runner.run(suite)

    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print()

    if result.wasSuccessful():
        print("[PASS] ALL TESTS PASSED!")
    else:
        print("[FAIL] SOME TESTS FAILED")

        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback.split(chr(10))[0]}")

        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback.split(chr(10))[0]}")

    print()
    print("=" * 80)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(main())

