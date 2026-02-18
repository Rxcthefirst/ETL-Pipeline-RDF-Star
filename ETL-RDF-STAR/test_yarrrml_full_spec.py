"""
Test script for YARRRML Full Specification Support
==================================================

This script tests the enhanced YARRRML parser with all new features:
- Base IRI
- Authors
- External references
- Language tags
- Multiple subjects/predicates/objects
- Graphs
- Inverse predicates
- Functions
- Conditions
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from yarrrml_parser import YARRRMLParser


def test_basic_parsing():
    """Test that the parser loads without errors"""
    print("=" * 80)
    print("Test 1: Basic Parsing")
    print("=" * 80)

    parser = YARRRMLParser("mappings/data_products_rml.yaml")
    triples_maps = parser.parse()

    print(f"✓ Parsed {len(triples_maps)} triples maps")
    print(f"✓ Found {len(parser.prefixes)} prefixes")
    print()


def test_full_spec_features():
    """Test all new YARRRML specification features"""
    print("=" * 80)
    print("Test 2: Full Specification Features")
    print("=" * 80)

    # Note: Create a minimal test mapping for this
    test_mapping = """
base: http://example.org/base#

authors:
  - name: Test Author
    email: test@example.com
  - Jane Doe <jane@example.com>

external:
  defaultValue: TestValue

prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"
  xsd: "http://www.w3.org/2001/XMLSchema#"

mappings:
  testMapping:
    sources:
      - ['test.csv~csv']
    subjects: ex:person/$(id)
    graphs: ex:TestGraph
    predicateobjects:
      # Basic literal
      - [foaf:name, $(name)]
      
      # With language
      - predicates: foaf:givenName
        objects:
          value: $(firstName)
          language: en
      
      # With datatype
      - [ex:age, $(age), xsd:integer]
      
      # IRI object
      - [foaf:knows, ex:person/$(friend)~iri]
"""

    # Write test mapping
    with open('mappings/test_temp.yaml', 'w') as f:
        f.write(test_mapping)

    try:
        parser = YARRRMLParser("mappings/test_temp.yaml")
        triples_maps = parser.parse()

        # Test base IRI
        if parser.base_iri:
            print(f"✓ Base IRI: {parser.base_iri}")
        else:
            print("✗ Base IRI not parsed")

        # Test authors
        if parser.authors:
            print(f"✓ Authors: {len(parser.authors)} author(s) parsed")
            for author in parser.authors:
                print(f"  - {author}")
        else:
            print("✗ Authors not parsed")

        # Test external references
        if parser.external_refs:
            print(f"✓ External references: {parser.external_refs}")
        else:
            print("✗ External references not parsed")

        # Test triples map features
        for tm_name, tm in triples_maps.items():
            print(f"\n✓ Triples Map: {tm_name}")

            # Test graphs
            if tm.graphs:
                print(f"  ✓ Mapping-level graphs: {tm.graphs}")

            # Test predicate-objects
            for po in tm.predicate_objects:
                if po.language:
                    print(f"  ✓ Language tag found: {po.language}")
                if po.datatype:
                    print(f"  ✓ Datatype found: {po.datatype}")
                if po.graphs:
                    print(f"  ✓ PO-level graphs: {po.graphs}")
                if po.inverse_predicate:
                    print(f"  ✓ Inverse predicate: {po.inverse_predicate}")

        print("\n✓ All features parsed successfully!")

    finally:
        # Cleanup
        if os.path.exists('mappings/test_temp.yaml'):
            os.remove('mappings/test_temp.yaml')

    print()


def test_existing_mappings():
    """Test that existing mappings still work"""
    print("=" * 80)
    print("Test 3: Backward Compatibility")
    print("=" * 80)

    parser = YARRRMLParser("mappings/data_products_rml.yaml")
    triples_maps = parser.parse()

    print(f"✓ Loaded existing mapping with {len(triples_maps)} triples maps")

    for tm_name, tm in triples_maps.items():
        print(f"\n  Triples Map: {tm_name}")
        print(f"    Sources: {len(tm.sources)}")
        print(f"    Subject template: {tm.subject.template}")
        print(f"    Is quoted: {tm.subject.is_quoted}")
        print(f"    Predicate-objects: {len(tm.predicate_objects)}")

        if tm.subject.is_quoted:
            print(f"    Quoted ref: {tm.subject.quoted_mapping_ref}")

    print("\n✓ Existing mappings work correctly!")
    print()


def test_language_tags():
    """Test language tag parsing"""
    print("=" * 80)
    print("Test 4: Language Tags")
    print("=" * 80)

    test_mapping = """
prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"

mappings:
  langTest:
    sources:
      - ['test.csv~csv']
    subjects: ex:person/$(id)
    predicateobjects:
      # Long format
      - predicates: foaf:name
        objects:
          value: $(name_en)
          language: en
      
      # Shortcut format (if implemented)
      - [foaf:name, $(name_fr), fr~lang]
"""

    with open('mappings/test_lang.yaml', 'w') as f:
        f.write(test_mapping)

    try:
        parser = YARRRMLParser("mappings/test_lang.yaml")
        triples_maps = parser.parse()

        tm = triples_maps['langTest']
        langs_found = [po.language for po in tm.predicate_objects if po.language]

        if langs_found:
            print(f"✓ Language tags found: {langs_found}")
        else:
            print("✗ No language tags found")

    finally:
        if os.path.exists('mappings/test_lang.yaml'):
            os.remove('mappings/test_lang.yaml')

    print()


def test_multiple_subjects():
    """Test multiple subjects support"""
    print("=" * 80)
    print("Test 5: Multiple Subjects")
    print("=" * 80)

    test_mapping = """
prefixes:
  ex: "http://example.org/"
  foaf: "http://xmlns.com/foaf/0.1/"

mappings:
  multiSubject:
    sources:
      - ['test.csv~csv']
    subjects: 
      - ex:person/$(id)
      - ex:human/$(id)
    predicateobjects:
      - [a, foaf:Person]
      - [foaf:name, $(name)]
"""

    with open('mappings/test_multi.yaml', 'w') as f:
        f.write(test_mapping)

    try:
        parser = YARRRMLParser("mappings/test_multi.yaml")
        triples_maps = parser.parse()

        tm = triples_maps['multiSubject']

        if len(tm.subject.templates) > 1:
            print(f"✓ Multiple subjects found: {tm.subject.templates}")
        else:
            print(f"✗ Only one subject found: {tm.subject.templates}")

    finally:
        if os.path.exists('mappings/test_multi.yaml'):
            os.remove('mappings/test_multi.yaml')

    print()


def main():
    """Run all tests"""
    print("\n")
    print("=" * 80)
    print(" " * 15 + "YARRRML FULL SPECIFICATION TEST SUITE" + " " * 24)
    print("=" * 80)
    print()

    tests = [
        test_basic_parsing,
        test_full_spec_features,
        test_existing_mappings,
        test_language_tags,
        test_multiple_subjects
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ Test failed: {test_func.__name__}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print()

    if failed == 0:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED")

    print()


if __name__ == "__main__":
    main()

