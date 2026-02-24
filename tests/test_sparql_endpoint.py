"""
Pytest Suite for RDF-star SPARQL Endpoint
==========================================

Tests all queries from the Postman collection to verify functionality
and diagnose why bindings might be empty.

Usage:
    pytest test_sparql_endpoint.py -v
    pytest test_sparql_endpoint.py -v -s  # With print output
"""

import pytest
import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:7878"
SPARQL_ENDPOINT = f"{BASE_URL}/sparql"

# Timeout for queries
QUERY_TIMEOUT = 30


@pytest.fixture(scope="module")
def check_server():
    """Verify server is running before tests"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200, "Server health check failed"
        data = response.json()
        print(f"\n[Server Status] {data}")
        return data
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Server not accessible: {e}")


def execute_sparql_query(query: str, verbose=True):
    """Execute a SPARQL query and return results"""
    headers = {"Content-Type": "application/sparql-query"}

    try:
        response = requests.post(
            SPARQL_ENDPOINT,
            data=query.encode('utf-8'),
            headers=headers,
            timeout=QUERY_TIMEOUT
        )

        if verbose:
            print(f"\n[Query Status] {response.status_code}")
            print(f"[Response Length] {len(response.text)} bytes")

        if response.status_code != 200:
            print(f"[Error Response] {response.text[:500]}")
            return None

        result = response.json()

        if verbose:
            print(f"[Variables] {result.get('head', {}).get('vars', [])}")
            bindings = result.get('results', {}).get('bindings', [])
            print(f"[Result Count] {len(bindings)} rows")

            # Print first result if available
            if bindings:
                print(f"[First Result] {json.dumps(bindings[0], indent=2)}")
            else:
                print("[WARNING] No bindings returned!")

        return result

    except Exception as e:
        print(f"[Exception] {type(e).__name__}: {e}")
        return None


# ============================================================================
# 1. BASIC QUERIES
# ============================================================================

class TestBasicQueries:
    """Test basic graph exploration queries"""

    def test_01_count_datasets(self, check_server):
        """Test counting all datasets"""
        query = """
PREFIX dcat: <http://www.w3.org/ns/dcat#>

SELECT (COUNT(?dataset) as ?count)
WHERE {
    ?dataset a dcat:Dataset .
}
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        assert len(bindings) > 0, "No results returned"

        count_value = bindings[0].get('count', {}).get('value')
        print(f"\n[Dataset Count] {count_value}")
        assert count_value is not None, "Count value is None"

    def test_02_list_datasets(self, check_server):
        """Test listing first 10 datasets"""
        query = """
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?dataset ?title ?issued
WHERE {
    ?dataset a dcat:Dataset ;
             dct:title ?title ;
             dct:issued ?issued .
}
ORDER BY ?dataset
LIMIT 10
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[Listed] {len(bindings)} datasets")

        if bindings:
            for i, binding in enumerate(bindings[:3]):
                print(f"  {i+1}. {binding.get('title', {}).get('value', 'N/A')}")

    def test_03_count_activities(self, check_server):
        """Test counting activities"""
        query = """
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT (COUNT(DISTINCT ?activity) as ?count)
WHERE {
    ?activity a prov:Activity .
}
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        if bindings:
            count = bindings[0].get('count', {}).get('value')
            print(f"\n[Activity Count] {count}")


# ============================================================================
# 2. RDF-STAR PROVENANCE QUERIES
# ============================================================================

class TestRDFStarProvenance:
    """Test RDF-star statement-level provenance queries"""

    def test_01_high_confidence_themes(self, check_server):
        """Test finding high-confidence theme assignments using RDF-star"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?theme ?confidence ?source
WHERE {
    ?dataset dcat:theme ?theme ;
             dct:title ?title .
    
    <<?dataset dcat:theme ?theme>> ex:confidence ?confidence ;
                                    prov:wasDerivedFrom ?source .
}
LIMIT 10
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[High Confidence Results] {len(bindings)} found")

        if bindings:
            for binding in bindings[:3]:
                conf = binding.get('confidence', {}).get('value', 'N/A')
                title = binding.get('title', {}).get('value', 'N/A')
                print(f"  - {title}: confidence={conf}")

    def test_02_data_by_source_system(self, check_server):
        """Test tracking data by source system"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?source (COUNT(DISTINCT ?dataset) as ?datasetCount)
WHERE {
    ?dataset dcat:theme ?theme .
    
    <<?dataset dcat:theme ?theme>> prov:wasDerivedFrom ?source .
}
GROUP BY ?source
ORDER BY DESC(?datasetCount)
LIMIT 10
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[Source Systems] {len(bindings)} found")

        if bindings:
            for binding in bindings:
                source = binding.get('source', {}).get('value', 'N/A')
                count = binding.get('datasetCount', {}).get('value', 'N/A')
                print(f"  - {source.split('/')[-1]}: {count} datasets")

    def test_03_simple_rdf_star_query(self, check_server):
        """Test simplest possible RDF-star query"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?theme ?source
WHERE {
    ?dataset dcat:theme ?theme .
    <<?dataset dcat:theme ?theme>> prov:wasDerivedFrom ?source .
}
LIMIT 5
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[Simple RDF-star] {len(bindings)} results")

        if bindings:
            print(f"[First binding] {json.dumps(bindings[0], indent=2)}")
        else:
            print("[WARNING] RDF-star syntax may not be supported or data not loaded correctly")


# ============================================================================
# 3. DATA QUALITY & GOVERNANCE
# ============================================================================

class TestDataQuality:
    """Test data quality and governance queries"""

    def test_01_find_any_confidence_scores(self, check_server):
        """Test if we can find ANY confidence scores"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>

SELECT ?dataset ?theme ?confidence
WHERE {
    ?dataset dcat:theme ?theme .
    <<?dataset dcat:theme ?theme>> ex:confidence ?confidence .
}
LIMIT 10
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[Confidence Scores Found] {len(bindings)}")

        if bindings:
            for binding in bindings[:5]:
                conf = binding.get('confidence', {}).get('value', 'N/A')
                print(f"  - Confidence: {conf}")
        else:
            print("[WARNING] No confidence scores found - RDF-star annotations may not be loaded")

    def test_02_governance_rules(self, check_server):
        """Test finding governance rules"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>

SELECT ?rule (COUNT(?dataset) as ?count)
WHERE {
    ?dataset dcat:theme ?theme .
    <<?dataset dcat:theme ?theme>> ex:rule ?rule .
}
GROUP BY ?rule
LIMIT 10
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[Governance Rules] {len(bindings)} found")


# ============================================================================
# 4. TEMPORAL QUERIES
# ============================================================================

class TestTemporalQueries:
    """Test temporal and freshness queries"""

    def test_01_find_timestamps(self, check_server):
        """Test if we can find any timestamps"""
        query = """
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX dcat: <http://www.w3.org/ns/dcat#>

SELECT ?dataset ?theme ?timestamp
WHERE {
    ?dataset dcat:theme ?theme .
    <<?dataset dcat:theme ?theme>> prov:generatedAtTime ?timestamp .
}
LIMIT 10
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[Timestamps Found] {len(bindings)}")

        if bindings:
            for binding in bindings[:3]:
                ts = binding.get('timestamp', {}).get('value', 'N/A')
                print(f"  - Generated at: {ts}")


# ============================================================================
# 5. ONTOLOGY QUERIES
# ============================================================================

class TestOntologyQueries:
    """Test ontologies alignment queries"""

    def test_01_list_classes(self, check_server):
        """Test listing OWL classes"""
        query = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?class ?label
WHERE {
    ?class a owl:Class .
    OPTIONAL { ?class rdfs:label ?label }
}
ORDER BY ?class
LIMIT 20
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[OWL Classes] {len(bindings)} found")

        if bindings:
            for binding in bindings[:5]:
                cls = binding.get('class', {}).get('value', 'N/A')
                label = binding.get('label', {}).get('value', '')
                print(f"  - {cls.split('/')[-1].split('#')[-1]}: {label}")

    def test_02_list_properties(self, check_server):
        """Test listing object properties"""
        query = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?property ?label
WHERE {
    ?property a owl:ObjectProperty .
    OPTIONAL { ?property rdfs:label ?label }
}
ORDER BY ?property
LIMIT 20
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[Object Properties] {len(bindings)} found")


# ============================================================================
# 6. DIAGNOSTIC QUERIES
# ============================================================================

class TestDiagnostics:
    """Diagnostic queries to understand the data"""

    def test_01_count_all_triples(self, check_server):
        """Count total triples in the store"""
        query = """
SELECT (COUNT(*) as ?tripleCount)
WHERE {
    ?s ?p ?o .
}
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        if bindings:
            count = bindings[0].get('tripleCount', {}).get('value', 'N/A')
            print(f"\n[Total Triples] {count}")

    def test_02_list_predicates(self, check_server):
        """List all predicates used"""
        query = """
SELECT DISTINCT ?predicate (COUNT(?s) as ?usage)
WHERE {
    ?s ?predicate ?o .
}
GROUP BY ?predicate
ORDER BY DESC(?usage)
LIMIT 20
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[Predicates Used] {len(bindings)} distinct")

        if bindings:
            for binding in bindings[:10]:
                pred = binding.get('predicate', {}).get('value', 'N/A')
                usage = binding.get('usage', {}).get('value', 'N/A')
                print(f"  - {pred.split('/')[-1].split('#')[-1]}: {usage} uses")

    def test_03_check_rdf_star_syntax(self, check_server):
        """Check if RDF-star reifies predicate exists"""
        query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?reifier ?triple
WHERE {
    ?reifier rdf:reifies ?triple .
}
LIMIT 10
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[RDF-star Reifiers] {len(bindings)} found")

        if bindings:
            print("[SUCCESS] RDF-star data is present!")
            for binding in bindings[:3]:
                print(f"  - Reifier: {binding.get('reifier', {}).get('value', 'N/A')}")
        else:
            print("[WARNING] No rdf:reifies found - RDF-star may not be loaded correctly")

    def test_04_sample_any_data(self, check_server):
        """Get a sample of any data"""
        query = """
SELECT ?s ?p ?o
WHERE {
    ?s ?p ?o .
}
LIMIT 20
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[Sample Data] {len(bindings)} triples")

        if bindings:
            for i, binding in enumerate(bindings[:5]):
                s = str(binding.get('s', {}).get('value', 'N/A'))[-30:]
                p = str(binding.get('p', {}).get('value', 'N/A'))[-30:]
                o = str(binding.get('o', {}).get('value', 'N/A'))[-30:]
                print(f"  {i+1}. ...{s} ...{p} ...{o}")

    def test_05_check_dataset_themes_directly(self, check_server):
        """Check if dataset-theme relationships exist (without RDF-star)"""
        query = """
PREFIX dcat: <http://www.w3.org/ns/dcat#>

SELECT ?dataset ?theme
WHERE {
    ?dataset dcat:theme ?theme .
}
LIMIT 10
"""
        result = execute_sparql_query(query)
        assert result is not None, "Query failed"

        bindings = result['results']['bindings']
        print(f"\n[Dataset-Theme Relations] {len(bindings)} found")

        if bindings:
            for binding in bindings[:5]:
                dataset = binding.get('dataset', {}).get('value', 'N/A')
                theme = binding.get('theme', {}).get('value', 'N/A')
                print(f"  - {dataset.split('/')[-1]} -> {theme.split('/')[-1]}")


# ============================================================================
# SUMMARY TEST
# ============================================================================

def test_final_summary(check_server):
    """Print a summary of findings"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    # Check server stats
    try:
        stats_response = requests.get(f"{BASE_URL}/stats", timeout=5)
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"\nServer Statistics:")
            print(f"  Total Quads: {stats.get('total_quads', 'N/A'):,}")
            print(f"  Datasets: {stats.get('datasets_count', 'N/A')}")
            print(f"  Activities: {stats.get('activities_count', 'N/A')}")
            print(f"  Ontology Loaded: {stats.get('ontology_loaded', False)}")
            print(f"  Instance Loaded: {stats.get('instance_loaded', False)}")
    except:
        print("\n[WARNING] Could not fetch server statistics")

    print("\n" + "="*80)
    print("If many tests show empty bindings:")
    print("  1. Check if server loaded data correctly")
    print("  2. Verify RDF-star syntax is supported")
    print("  3. Check if ontologies/instance files exist")
    print("  4. Try simpler queries first (test_04_sample_any_data)")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("Run with: pytest test_sparql_endpoint.py -v -s")

