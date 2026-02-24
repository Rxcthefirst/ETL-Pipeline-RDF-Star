"""
Test Script for Dynamic RDF-star ETL Pipeline
==============================================

This script validates that the ETL pipeline correctly:
1. Parses YARRRML-star mappings
2. Loads CSV data dynamically
3. Generates RDF triples
4. Creates RDF-star quoted triples
5. Outputs valid TriG format
"""

import os
import sys
from yarrrml_parser import YARRRMLParser
from rdf_star_etl_engine_dynamic import RDFStarETLEngine


def test_yarrrml_parser():
    """Test YARRRML parser functionality"""
    print("\n" + "="*80)
    print("TEST 1: YARRRML Parser")
    print("="*80)

    parser = YARRRMLParser("mappings/data_products_rml.yaml")
    triples_maps = parser.parse()

    # Validate prefixes
    assert 'ex' in parser.prefixes, "Missing 'ex' prefix"
    assert 'dcat' in parser.prefixes, "Missing 'dcat' prefix"
    print("✓ Prefixes loaded correctly")

    # Validate triples maps
    assert len(triples_maps) == 4, f"Expected 4 triples maps, got {len(triples_maps)}"
    print(f"✓ Found {len(triples_maps)} triples maps")

    # Validate specific triples map
    assert 'datasetTM' in triples_maps, "Missing datasetTM mapping"
    dataset_tm = triples_maps['datasetTM']
    assert dataset_tm.subject.template == "ex:dataset/$(dataset_id)", "Incorrect subject template"
    print("✓ Subject templates parsed correctly")

    # Validate quoted triple map
    assert 'themeGovernanceTM' in triples_maps, "Missing themeGovernanceTM mapping"
    governance_tm = triples_maps['themeGovernanceTM']
    assert governance_tm.subject.is_quoted == True, "Quoted triple not detected"
    assert governance_tm.subject.quoted_mapping_ref == "datasetThemeTM", "Incorrect quoted reference"
    print("✓ Quoted triple mappings parsed correctly")

    # Validate CSV requirements
    csv_files = parser.get_required_csv_files()
    assert 'data_products.csv' in csv_files, "Missing data_products.csv requirement"
    assert 'lineage.csv' in csv_files, "Missing lineage.csv requirement"
    print(f"✓ Required CSV files identified: {csv_files}")

    # Validate column requirements
    dp_columns = parser.get_required_columns_for_source('data_products.csv')
    expected_columns = ['dataset_id', 'issued', 'owner', 'theme_uri', 'title']
    for col in expected_columns:
        assert col in dp_columns, f"Missing required column: {col}"
    print(f"✓ Required columns for data_products.csv: {dp_columns}")

    print("\n✅ YARRRML Parser Test: PASSED")
    return True


def test_csv_data_files():
    """Test CSV data files exist and are readable"""
    print("\n" + "="*80)
    print("TEST 2: CSV Data Files")
    print("="*80)

    csv_files = [
        'data/data_products.csv',
        'data/lineage.csv'
    ]

    for csv_file in csv_files:
        assert os.path.exists(csv_file), f"Missing CSV file: {csv_file}"

        # Check file is not empty
        size = os.path.getsize(csv_file)
        assert size > 0, f"CSV file is empty: {csv_file}"

        print(f"✓ {csv_file} exists ({size} bytes)")

    print("\n✅ CSV Data Files Test: PASSED")
    return True


def test_etl_pipeline():
    """Test full ETL pipeline execution"""
    print("\n" + "="*80)
    print("TEST 3: ETL Pipeline Execution")
    print("="*80)

    # Run pipeline
    engine = RDFStarETLEngine("etl_pipeline_config.yaml")
    engine.run()

    # Validate statistics
    assert engine.stats['rows_processed'] > 0, "No rows were processed"
    assert engine.stats['triples_generated'] > 0, "No triples were generated"
    assert engine.stats['quoted_triples_generated'] > 0, "No quoted triples were generated"

    print(f"\n✓ Rows processed: {engine.stats['rows_processed']}")
    print(f"✓ Triples generated: {engine.stats['triples_generated']}")
    print(f"✓ Quoted triple annotations: {engine.stats['quoted_triples_generated']}")

    # Validate output file
    output_path = "../output/output_data_star.trig"
    assert os.path.exists(output_path), "Output file was not created"

    output_size = os.path.getsize(output_path)
    assert output_size > 0, "Output file is empty"
    print(f"✓ Output file created: {output_path} ({output_size} bytes)")

    print("\n✅ ETL Pipeline Test: PASSED")
    return True


def test_output_format():
    """Test output RDF-star format"""
    print("\n" + "="*80)
    print("TEST 4: RDF-star Output Format")
    print("="*80)

    output_path = "../output/output_data_star.trig"

    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for prefixes
    assert '@prefix ex:' in content, "Missing ex: prefix declaration"
    assert '@prefix dcat:' in content, "Missing dcat: prefix declaration"
    assert '@prefix prov:' in content, "Missing prov: prefix declaration"
    print("✓ Namespace prefixes present")

    # Check for RDF-star syntax (quoted triples)
    assert 'rdf:reifies' in content or '<rdf:reifies>' in content, "Missing rdf:reifies statements"
    assert '<<(' in content and ')>>' in content, "Missing RDF-star quoted triple syntax"
    print("✓ RDF-star quoted triple syntax present")

    # Check for expected URIs
    assert 'http://example.org/dataset/' in content, "Missing dataset URIs"
    assert 'http://www.w3.org/ns/dcat#' in content, "Missing DCAT namespace"
    assert 'http://www.w3.org/ns/prov#' in content, "Missing PROV namespace"
    print("✓ Expected URIs present")

    # Check for data values
    assert 'DS001' in content or 'DS002' in content, "Missing dataset IDs"
    assert 'COLLIBRA' in content or 'ALATION' in content, "Missing source systems"
    print("✓ Data values present")

    print("\n✅ Output Format Test: PASSED")
    return True


def run_all_tests():
    """Run all test suites"""
    print("\n" + "="*80)
    print("DYNAMIC RDF-STAR ETL PIPELINE - TEST SUITE")
    print("="*80)

    tests = [
        ("YARRRML Parser", test_yarrrml_parser),
        ("CSV Data Files", test_csv_data_files),
        ("ETL Pipeline", test_etl_pipeline),
        ("Output Format", test_output_format)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except AssertionError as e:
            print(f"\n❌ {test_name} Test: FAILED")
            print(f"   Error: {e}")
            results.append((test_name, False))
        except Exception as e:
            print(f"\n❌ {test_name} Test: ERROR")
            print(f"   {type(e).__name__}: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:30s} {status}")

    print("="*80)
    print(f"Results: {passed}/{total} tests passed")
    print("="*80)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

