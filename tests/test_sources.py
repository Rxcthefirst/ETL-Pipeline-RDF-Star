"""
Comprehensive Tests for Data Source Connectors
===============================================

Tests for:
- CSV source
- JSON source with JSONPath
- XML source with XPath
- SQLite source
- HTTP source (mocked)
- Environment variable interpolation
"""

import sys
import os
import json
import tempfile
import shutil
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources import (
    SourceConfig, DataSource, FileSource,
    create_source, register_source, list_available_sources,
    interpolate_env_vars, interpolate_dict_env_vars
)
from sources.csv_source import CSVSource
from sources.json_source import JSONSource, extract_jsonpath, flatten_json
from sources.xml_source import XMLSource, element_to_dict
from sources.database.sqlite import SQLiteSource


class TestEnvironmentVariables(unittest.TestCase):
    """Test environment variable interpolation."""

    def setUp(self):
        os.environ['TEST_VAR'] = 'test_value'
        os.environ['TEST_PASSWORD'] = 'secret123'

    def tearDown(self):
        os.environ.pop('TEST_VAR', None)
        os.environ.pop('TEST_PASSWORD', None)

    def test_simple_interpolation(self):
        """Test basic ${VAR} interpolation."""
        result = interpolate_env_vars("${TEST_VAR}")
        self.assertEqual(result, "test_value")

    def test_interpolation_in_string(self):
        """Test interpolation within a larger string."""
        result = interpolate_env_vars("prefix_${TEST_VAR}_suffix")
        self.assertEqual(result, "prefix_test_value_suffix")

    def test_multiple_variables(self):
        """Test multiple variables in one string."""
        result = interpolate_env_vars("${TEST_VAR}:${TEST_PASSWORD}")
        self.assertEqual(result, "test_value:secret123")

    def test_missing_variable(self):
        """Test that missing variables raise an error."""
        with self.assertRaises(ValueError) as ctx:
            interpolate_env_vars("${NONEXISTENT_VAR}")
        self.assertIn("NONEXISTENT_VAR", str(ctx.exception))

    def test_dict_interpolation(self):
        """Test recursive dictionary interpolation."""
        d = {
            'username': '${TEST_VAR}',
            'password': '${TEST_PASSWORD}',
            'nested': {
                'key': '${TEST_VAR}'
            }
        }
        result = interpolate_dict_env_vars(d)
        self.assertEqual(result['username'], 'test_value')
        self.assertEqual(result['password'], 'secret123')
        self.assertEqual(result['nested']['key'], 'test_value')


class TestCSVSource(unittest.TestCase):
    """Test CSV data source."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Create test CSV
        self.csv_path = os.path.join(self.temp_dir, 'test.csv')
        with open(self.csv_path, 'w') as f:
            f.write("id,name,age\n")
            f.write("1,Alice,30\n")
            f.write("2,Bob,25\n")
            f.write("3,Charlie,35\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_load_csv(self):
        """Test basic CSV loading."""
        config = SourceConfig(
            name='test',
            source_type='csv',
            access=self.csv_path,
            reference_formulation='csv'
        )

        source = CSVSource(config, self.temp_dir)
        with source:
            df = source.fetch_data()

        self.assertEqual(len(df), 3)
        self.assertIn('id', df.columns)
        self.assertIn('name', df.columns)
        self.assertIn('age', df.columns)

    def test_custom_delimiter(self):
        """Test CSV with custom delimiter."""
        tsv_path = os.path.join(self.temp_dir, 'test.tsv')
        with open(tsv_path, 'w') as f:
            f.write("id\tname\tage\n")
            f.write("1\tAlice\t30\n")

        config = SourceConfig(
            name='test',
            source_type='csv',
            access=tsv_path,
            delimiter='\t'
        )

        source = CSVSource(config, self.temp_dir)
        with source:
            df = source.fetch_data()

        self.assertEqual(len(df), 1)
        self.assertEqual(df['name'][0], 'Alice')


class TestJSONSource(unittest.TestCase):
    """Test JSON data source with JSONPath."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_simple_json_array(self):
        """Test JSON file with simple array."""
        json_path = os.path.join(self.temp_dir, 'test.json')
        with open(json_path, 'w') as f:
            json.dump([
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"}
            ], f)

        config = SourceConfig(
            name='test',
            source_type='jsonpath',
            access=json_path,
            reference_formulation='jsonpath'
        )

        source = JSONSource(config, self.temp_dir)
        with source:
            df = source.fetch_data()

        self.assertEqual(len(df), 2)
        self.assertIn('id', df.columns)
        self.assertIn('name', df.columns)

    def test_nested_json_with_iterator(self):
        """Test JSON with nested structure and iterator."""
        json_path = os.path.join(self.temp_dir, 'test.json')
        with open(json_path, 'w') as f:
            json.dump({
                "status": "ok",
                "data": {
                    "users": [
                        {"id": 1, "name": "Alice"},
                        {"id": 2, "name": "Bob"}
                    ]
                }
            }, f)

        config = SourceConfig(
            name='test',
            source_type='jsonpath',
            access=json_path,
            reference_formulation='jsonpath',
            iterator='$.data.users[*]'
        )

        source = JSONSource(config, self.temp_dir)
        with source:
            df = source.fetch_data()

        self.assertEqual(len(df), 2)

    def test_flatten_nested_json(self):
        """Test flattening of nested JSON objects."""
        nested = {
            "user": {
                "name": "Alice",
                "address": {
                    "city": "NYC",
                    "zip": "10001"
                }
            }
        }

        flat = flatten_json(nested)

        self.assertEqual(flat['user_name'], 'Alice')
        self.assertEqual(flat['user_address_city'], 'NYC')
        self.assertEqual(flat['user_address_zip'], '10001')

    def test_jsonpath_extraction(self):
        """Test JSONPath extraction function."""
        data = {
            "items": [
                {"id": 1, "value": "a"},
                {"id": 2, "value": "b"}
            ]
        }

        results = extract_jsonpath(data, '$.items[*]')
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], 1)
        self.assertEqual(results[1]['id'], 2)


class TestXMLSource(unittest.TestCase):
    """Test XML data source with XPath."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_simple_xml(self):
        """Test simple XML file."""
        xml_path = os.path.join(self.temp_dir, 'test.xml')
        with open(xml_path, 'w') as f:
            f.write('''<?xml version="1.0"?>
<catalog>
  <product id="1">
    <name>Widget</name>
    <price>9.99</price>
  </product>
  <product id="2">
    <name>Gadget</name>
    <price>19.99</price>
  </product>
</catalog>
''')

        config = SourceConfig(
            name='test',
            source_type='xpath',
            access=xml_path,
            reference_formulation='xpath',
            iterator='.//product'
        )

        source = XMLSource(config, self.temp_dir)
        with source:
            df = source.fetch_data()

        self.assertEqual(len(df), 2)
        self.assertIn('name', df.columns)
        self.assertIn('price', df.columns)

    def test_xml_with_attributes(self):
        """Test XML with attributes."""
        xml_path = os.path.join(self.temp_dir, 'test.xml')
        with open(xml_path, 'w') as f:
            f.write('''<?xml version="1.0"?>
<items>
  <item id="1" category="A">First</item>
  <item id="2" category="B">Second</item>
</items>
''')

        config = SourceConfig(
            name='test',
            source_type='xpath',
            access=xml_path,
            iterator='.//item'
        )

        source = XMLSource(config, self.temp_dir)
        with source:
            df = source.fetch_data()

        self.assertEqual(len(df), 2)
        # Attributes should be extracted
        self.assertIn('id', df.columns)


class TestSQLiteSource(unittest.TestCase):
    """Test SQLite data source."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Create test SQLite database
        import sqlite3
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                email TEXT
            )
        ''')
        cursor.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@example.com')")
        cursor.execute("INSERT INTO users VALUES (2, 'Bob', 'bob@example.com')")
        conn.commit()
        conn.close()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_sqlite_query(self):
        """Test SQLite query execution."""
        config = SourceConfig(
            name='test',
            source_type='sqlite',
            access=self.db_path,
            query='SELECT * FROM users'
        )

        source = SQLiteSource(config, self.temp_dir)
        with source:
            df = source.fetch_data()

        self.assertEqual(len(df), 2)
        self.assertIn('id', df.columns)
        self.assertIn('name', df.columns)
        self.assertIn('email', df.columns)

    def test_sqlite_filtered_query(self):
        """Test SQLite query with WHERE clause."""
        config = SourceConfig(
            name='test',
            source_type='sqlite',
            access=self.db_path,
            query="SELECT * FROM users WHERE name = 'Alice'"
        )

        source = SQLiteSource(config, self.temp_dir)
        with source:
            df = source.fetch_data()

        self.assertEqual(len(df), 1)
        self.assertEqual(df['name'][0], 'Alice')


class TestSourceRegistry(unittest.TestCase):
    """Test source type registry."""

    def test_list_sources(self):
        """Test listing available source types."""
        sources = list_available_sources()

        self.assertIn('csv', sources)
        self.assertIn('json', sources)
        self.assertIn('jsonpath', sources)
        self.assertIn('xml', sources)
        self.assertIn('xpath', sources)
        self.assertIn('sqlite', sources)

    def test_create_csv_source(self):
        """Test factory function for CSV source."""
        config = SourceConfig(
            name='test',
            source_type='localfile',
            access='test.csv',
            reference_formulation='csv'
        )

        source = create_source(config)
        self.assertIsInstance(source, CSVSource)

    def test_create_json_source(self):
        """Test factory function for JSON source."""
        config = SourceConfig(
            name='test',
            source_type='localfile',
            access='test.json',
            reference_formulation='jsonpath'
        )

        source = create_source(config)
        self.assertIsInstance(source, JSONSource)


class TestSourceConfig(unittest.TestCase):
    """Test SourceConfig creation and parsing."""

    def test_from_yarrrml_simple(self):
        """Test creating config from simple YARRRML."""
        yarrrml = {
            'access': 'data/test.csv',
            'referenceFormulation': 'csv'
        }

        config = SourceConfig.from_yarrrml('test', yarrrml)

        self.assertEqual(config.name, 'test')
        self.assertEqual(config.access, 'data/test.csv')
        self.assertEqual(config.reference_formulation, 'csv')

    def test_from_yarrrml_with_credentials(self):
        """Test creating config with credentials."""
        os.environ['DB_USER'] = 'admin'
        os.environ['DB_PASS'] = 'secret'

        try:
            yarrrml = {
                'type': 'postgresql',
                'access': 'localhost:5432/mydb',
                'credentials': {
                    'username': '${DB_USER}',
                    'password': '${DB_PASS}'
                },
                'query': 'SELECT * FROM users'
            }

            config = SourceConfig.from_yarrrml('test', yarrrml)

            self.assertEqual(config.credentials['username'], 'admin')
            self.assertEqual(config.credentials['password'], 'secret')
        finally:
            os.environ.pop('DB_USER', None)
            os.environ.pop('DB_PASS', None)


def run_tests():
    """Run all source connector tests."""
    print("\n")
    print("=" * 80)
    print("DATA SOURCE CONNECTOR TESTS")
    print("=" * 80)
    print()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestEnvironmentVariables,
        TestCSVSource,
        TestJSONSource,
        TestXMLSource,
        TestSQLiteSource,
        TestSourceRegistry,
        TestSourceConfig,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print()

    if result.wasSuccessful():
        print("[PASS] ALL SOURCE CONNECTOR TESTS PASSED!")
    else:
        print("[FAIL] SOME TESTS FAILED")

    print("=" * 80)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(run_tests())

