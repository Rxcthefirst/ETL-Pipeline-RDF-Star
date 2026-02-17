"""
Comprehensive Pytest Suite for ALL Postman Collection SPARQL Queries
=====================================================================

This test suite validates EVERY query from the RDF_Star_Data_Products.postman_collection.json
against the running SPARQL endpoint on port 7878.

Usage:
    pytest test_postman_queries.py -v
    pytest test_postman_queries.py -v -s  # With detailed output
    pytest test_postman_queries.py -v -k "Basic"  # Run only Basic queries
    pytest test_postman_queries.py --tb=short  # Shorter tracebacks
"""

import pytest
import requests
import json
from typing import Dict, Optional

# Configuration
BASE_URL = "http://localhost:7878"
SPARQL_ENDPOINT = f"{BASE_URL}/sparql"
QUERY_TIMEOUT = 30


@pytest.fixture(scope="module")
def check_server():
    """Verify server is running before tests"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200, "Server health check failed"
        data = response.json()
        print(f"\n[OK] Server is running on {BASE_URL}")
        print(f"  Status: {data}")
        return data
    except requests.exceptions.RequestException as e:
        pytest.fail(f"[ERROR] Server not accessible at {BASE_URL}: {e}\nMake sure the SPARQL server is running on port 7878!")


def execute_sparql(query: str, expect_results: bool = True, verbose: bool = True) -> Optional[Dict]:
    """
    Execute a SPARQL query and return results

    Args:
        query: SPARQL query string
        expect_results: Whether we expect results (for validation)
        verbose: Print detailed information

    Returns:
        Query result dict or None if failed
    """
    headers = {"Content-Type": "application/sparql-query"}

    try:
        response = requests.post(
            SPARQL_ENDPOINT,
            data=query.encode('utf-8'),
            headers=headers,
            timeout=QUERY_TIMEOUT
        )

        if verbose:
            print(f"\n  Status: {response.status_code}")

        if response.status_code != 200:
            print(f"\nâŒ Query failed with status {response.status_code}")
            print(f"  Response: {response.text[:500]}")
            return None

        result = response.json()
        bindings = result.get('results', {}).get('bindings', [])

        if verbose:
            vars_list = result.get('head', {}).get('vars', [])
            print(f"  Variables: {vars_list}")
            print(f"  Result count: {len(bindings)}")

            if bindings:
                print(f"  First result: {json.dumps(bindings[0], indent=4)}")
            elif expect_results:
                print(f"  âš ï¸  WARNING: No results returned (expected results)")

        return result

    except requests.exceptions.Timeout:
        print(f"\nâŒ Query timed out after {QUERY_TIMEOUT}s")
        return None
    except Exception as e:
        print(f"\nâŒ Exception: {type(e).__name__}: {e}")
        return None


# ============================================================================
# 1. BASIC QUERIES
# ============================================================================

class TestBasicQueries:
    """Test Category 1: Basic Queries"""

    def test_1_1_count_all_datasets(self, check_server):
        """1.1 Count All Datasets"""
        query = """
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT (COUNT(?dataset) as ?count)
WHERE {
    ?dataset a dcat:Dataset .
}
"""
        result = execute_sparql(query, expect_results=True)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        assert len(bindings) > 0, "No results returned"

        count_val = bindings[0].get('count', {}).get('value')
        print(f"\n  âœ“ Found {count_val} datasets")
        assert count_val is not None, "Count is None"

    def test_1_2_list_first_10_datasets(self, check_server):
        """1.2 List First 10 Datasets"""
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
        result = execute_sparql(query, expect_results=True)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Listed {len(bindings)} datasets")

        if bindings:
            for i, b in enumerate(bindings[:3], 1):
                title = b.get('title', {}).get('value', 'N/A')
                print(f"    {i}. {title}")

    def test_1_3_count_all_activities(self, check_server):
        """1.3 Count All Activities"""
        query = """
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT (COUNT(DISTINCT ?activity) as ?count)
WHERE {
    ?activity a prov:Activity .
}
"""
        result = execute_sparql(query, expect_results=True)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        if bindings:
            count_val = bindings[0].get('count', {}).get('value')
            print(f"\n  âœ“ Found {count_val} activities")


# ============================================================================
# 2. RDF-STAR PROVENANCE QUERIES
# ============================================================================

class TestRDFStarProvenanceQueries:
    """Test Category 2: RDF-star Provenance Queries"""

    def test_2_1_find_high_confidence_theme_assignments(self, check_server):
        """2.1 Find High-Confidence Theme Assignments"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?theme ?confidence ?source
WHERE {
    # Base triple
    ?dataset dcat:theme ?theme ;
             dct:title ?title .
    
    # RDF-star: Get metadata about the theme assignment
    <<?dataset dcat:theme ?theme>> ex:confidence ?confidence ;
                                    prov:wasDerivedFrom ?source .
    
    FILTER(?confidence > 0.90)
}
ORDER BY DESC(?confidence)
LIMIT 20
"""
        result = execute_sparql(query, expect_results=False)  # May not have data
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} high-confidence assignments")

        if bindings:
            for i, b in enumerate(bindings[:3], 1):
                conf = b.get('confidence', {}).get('value', 'N/A')
                title = b.get('title', {}).get('value', 'N/A')[:50]
                print(f"    {i}. {title}... (confidence: {conf})")

    def test_2_2_track_data_by_source_system(self, check_server):
        """2.2 Track Data by Source System"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?source (COUNT(DISTINCT ?dataset) as ?datasetCount)
WHERE {
    ?dataset dcat:theme ?theme .
    
    # RDF-star: Get source from statement annotation
    <<?dataset dcat:theme ?theme>> prov:wasDerivedFrom ?source .
}
GROUP BY ?source
ORDER BY DESC(?datasetCount)
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} source systems")

        for i, b in enumerate(bindings[:5], 1):
            source = b.get('source', {}).get('value', 'N/A')
            count = b.get('datasetCount', {}).get('value', '0')
            print(f"    {i}. {source}: {count} datasets")

    def test_2_3_complete_provenance_chain_for_dataset(self, check_server):
        """2.3 Complete Provenance Chain for Dataset"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?predicate ?value ?source ?timestamp ?activity ?rule
WHERE {
    # Specific dataset (change ID as needed)
    BIND(<http://example.org/dataset/DS-000001> as ?dataset)
    
    ?dataset ?predicate ?value .
    FILTER(?predicate != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
    
    # RDF-star: Get all provenance metadata
    <<?dataset ?predicate ?value>> prov:wasDerivedFrom ?source ;
                                    prov:generatedAtTime ?timestamp ;
                                    prov:wasGeneratedBy ?activity ;
                                    ex:rule ?rule .
}
ORDER BY ?predicate
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} provenance entries for DS-000001")


# ============================================================================
# 3. DATA QUALITY & GOVERNANCE
# ============================================================================

class TestDataQualityGovernance:
    """Test Category 3: Data Quality & Governance"""

    def test_3_1_find_low_confidence_data(self, check_server):
        """3.1 Find Low Confidence Data"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?theme ?confidence ?source
WHERE {
    ?dataset dcat:theme ?theme ;
             dct:title ?title .
    
    # RDF-star: Get confidence score
    <<?dataset dcat:theme ?theme>> ex:confidence ?confidence ;
                                    prov:wasDerivedFrom ?source .
    
    FILTER(?confidence < 0.85)
}
ORDER BY ?confidence
LIMIT 20
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} low-confidence items")

    def test_3_2_governance_rules_applied(self, check_server):
        """3.2 Governance Rules Applied"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>

SELECT ?rule (COUNT(?dataset) as ?applicationsCount)
WHERE {
    ?dataset dcat:theme ?theme .
    
    # RDF-star: Get governance rule
    <<?dataset dcat:theme ?theme>> ex:rule ?rule .
}
GROUP BY ?rule
ORDER BY DESC(?applicationsCount)
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} governance rules")

        for i, b in enumerate(bindings[:5], 1):
            rule = b.get('rule', {}).get('value', 'N/A')
            count = b.get('applicationsCount', {}).get('value', '0')
            print(f"    {i}. {rule}: {count} applications")

    def test_3_3_average_confidence_by_source_system(self, check_server):
        """3.3 Average Confidence by Source System"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?source (COUNT(?dataset) as ?count) (AVG(?confidence) as ?avgConf) (MIN(?confidence) as ?minConf) (MAX(?confidence) as ?maxConf)
WHERE {
    ?dataset dcat:theme ?theme .
    
    <<?dataset dcat:theme ?theme>> prov:wasDerivedFrom ?source ;
                                    ex:confidence ?confidence .
}
GROUP BY ?source
ORDER BY DESC(?avgConf)
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Analyzed {len(bindings)} source systems")


# ============================================================================
# 4. TEMPORAL & FRESHNESS QUERIES
# ============================================================================

class TestTemporalFreshnessQueries:
    """Test Category 4: Temporal & Freshness Queries"""

    def test_4_1_most_recently_updated_datasets(self, check_server):
        """4.1 Most Recently Updated Datasets"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?theme ?lastUpdated ?source
WHERE {
    ?dataset dcat:theme ?theme ;
             dct:title ?title .
    
    # RDF-star: Get generation time
    <<?dataset dcat:theme ?theme>> prov:generatedAtTime ?lastUpdated ;
                                    prov:wasDerivedFrom ?source .
}
ORDER BY DESC(?lastUpdated)
LIMIT 20
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} recently updated datasets")

    def test_4_2_datasets_updated_in_time_range(self, check_server):
        """4.2 Datasets Updated in Time Range"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?dataset ?title ?lastUpdated
WHERE {
    ?dataset dcat:theme ?theme ;
             dct:title ?title .
    
    <<?dataset dcat:theme ?theme>> prov:generatedAtTime ?lastUpdated .
    
    # Filter by time range (adjust as needed)
    FILTER(?lastUpdated >= "2025-02-15T14:00:00Z"^^xsd:dateTime)
}
ORDER BY DESC(?lastUpdated)
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} datasets in time range")

    def test_4_3_data_freshness_by_theme(self, check_server):
        """4.3 Data Freshness by Theme"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?theme (COUNT(?dataset) as ?datasetCount) (MAX(?updated) as ?mostRecent)
WHERE {
    ?dataset dcat:theme ?theme .
    
    <<?dataset dcat:theme ?theme>> prov:generatedAtTime ?updated .
}
GROUP BY ?theme
ORDER BY DESC(?mostRecent)
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Analyzed {len(bindings)} themes for freshness")


# ============================================================================
# 5. ONTOLOGY ALIGNMENT QUERIES
# ============================================================================

class TestOntologyAlignmentQueries:
    """Test Category 5: Ontology Alignment Queries"""

    def test_5_1_list_all_classes_in_ontology(self, check_server):
        """5.1 List All Classes in Ontology"""
        query = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?class ?label ?comment
WHERE {
    ?class a owl:Class .
    OPTIONAL { ?class rdfs:label ?label }
    OPTIONAL { ?class rdfs:comment ?comment }
}
ORDER BY ?class
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} ontology classes")

        for i, b in enumerate(bindings[:5], 1):
            cls = b.get('class', {}).get('value', 'N/A')
            label = b.get('label', {}).get('value', 'N/A')
            print(f"    {i}. {label} ({cls})")

    def test_5_2_list_all_object_properties(self, check_server):
        """5.2 List All Object Properties"""
        query = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?property ?label ?domain ?range
WHERE {
    ?property a owl:ObjectProperty .
    OPTIONAL { ?property rdfs:label ?label }
    OPTIONAL { ?property rdfs:domain ?domain }
    OPTIONAL { ?property rdfs:range ?range }
}
ORDER BY ?property
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} object properties")

    def test_5_3_find_all_data_catalog_systems(self, check_server):
        """5.3 Find All Data Catalog Systems (Named Individuals)"""
        query = """
PREFIX ex: <http://example.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?label ?comment
WHERE {
    ?system a ex:DataCatalogSystem .
    OPTIONAL { ?system rdfs:label ?label }
    OPTIONAL { ?system rdfs:comment ?comment }
}
ORDER BY ?label
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} data catalog systems")

    def test_5_4_verify_instance_ontology_alignment(self, check_server):
        """5.4 Verify Instance-Ontology Alignment"""
        query = """
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX ex: <http://example.org/ontology#>

SELECT ?type (COUNT(?instance) as ?instanceCount)
WHERE {
    ?instance a ?type .
    # Only count types from our ontologies
    FILTER(STRSTARTS(STR(?type), "http://www.w3.org/ns/dcat#") || 
           STRSTARTS(STR(?type), "http://www.w3.org/ns/prov#") ||
           STRSTARTS(STR(?type), "http://example.org/ontology#"))
}
GROUP BY ?type
ORDER BY DESC(?instanceCount)
"""
        result = execute_sparql(query, expect_results=True)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} ontology types with instances")

        for i, b in enumerate(bindings[:10], 1):
            typ = b.get('type', {}).get('value', 'N/A')
            count = b.get('instanceCount', {}).get('value', '0')
            print(f"    {i}. {typ}: {count} instances")


# ============================================================================
# 6. COMPLEX MULTI-FACETED QUERIES
# ============================================================================

class TestComplexMultiFacetedQueries:
    """Test Category 6: Complex Multi-faceted Queries"""

    def test_6_1_trusted_data_from_specific_system(self, check_server):
        """6.1 Trusted Data from Specific System"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?theme ?confidence ?timestamp
WHERE {
    ?dataset dcat:theme ?theme ;
             dct:title ?title .
    
    # RDF-star: Complex filter on metadata
    <<?dataset dcat:theme ?theme>> 
        prov:wasDerivedFrom <http://example.org/system/COLLIBRA> ;
        ex:confidence ?confidence ;
        prov:generatedAtTime ?timestamp .
    
    FILTER(?confidence > 0.92)
}
ORDER BY DESC(?confidence) DESC(?timestamp)
LIMIT 20
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} trusted datasets from COLLIBRA")

    def test_6_2_cross_system_comparison(self, check_server):
        """6.2 Cross-System Comparison"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?source1 ?source2 (COUNT(?dataset) as ?sharedDatasets) 
WHERE {
    # Same dataset has data from two different sources
    ?dataset dcat:theme ?theme1 ;
             dcat:theme ?theme2 .
    
    <<?dataset dcat:theme ?theme1>> prov:wasDerivedFrom ?source1 .
    <<?dataset dcat:theme ?theme2>> prov:wasDerivedFrom ?source2 .
    
    FILTER(?source1 != ?source2)
    FILTER(STR(?source1) < STR(?source2))  # Avoid duplicates
}
GROUP BY ?source1 ?source2
ORDER BY DESC(?sharedDatasets)
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Found {len(bindings)} cross-system comparisons")

    def test_6_3_quality_trend_analysis(self, check_server):
        """6.3 Quality Trend Analysis"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?activity (COUNT(?dataset) as ?datasetCount) (AVG(?confidence) as ?avgQuality)
WHERE {
    ?dataset dcat:theme ?theme .
    
    <<?dataset dcat:theme ?theme>> ex:confidence ?confidence ;
                                    prov:wasGeneratedBy ?activity .
}
GROUP BY ?activity
ORDER BY ?activity
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Analyzed {len(bindings)} activities for quality trends")

    def test_6_4_complete_governance_report_for_theme(self, check_server):
        """6.4 Complete Governance Report for Theme"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?dataset ?title ?source ?confidence ?rule ?timestamp
WHERE {
    # Focus on specific theme (change URI as needed)
    BIND(<http://example.org/themes/CustomerAnalytics> as ?targetTheme)
    
    ?dataset dcat:theme ?targetTheme ;
             dct:title ?title .
    
    # RDF-star: Get all governance metadata
    <<?dataset dcat:theme ?targetTheme>> 
        prov:wasDerivedFrom ?source ;
        ex:confidence ?confidence ;
        ex:rule ?rule ;
        prov:generatedAtTime ?timestamp .
}
ORDER BY DESC(?confidence) DESC(?timestamp)
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ Generated governance report with {len(bindings)} entries")


# ============================================================================
# 7. REIFICATION COMPARISON
# ============================================================================

class TestReificationComparison:
    """Test Category 7: Reification Comparison"""

    def test_7_1_rdf_star_direct_query(self, check_server):
        """7.1 RDF-star Direct Query (Simple)"""
        query = """
PREFIX ex: <http://example.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX prov: <http://www.w3.org/ns/prov#>

# RDF-star approach: Direct and intuitive
SELECT ?dataset ?theme ?source ?confidence
WHERE {
    ?dataset dcat:theme ?theme .
    
    # Simple: Query metadata directly on the statement
    <<?dataset dcat:theme ?theme>> prov:wasDerivedFrom ?source ;
                                    ex:confidence ?confidence .
}
LIMIT 10
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        print(f"\n  âœ“ RDF-star query returned {len(bindings)} results")

    def test_7_2_count_reified_statements(self, check_server):
        """7.2 Count Reified Statements"""
        query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

# Count how many statements have RDF-star annotations
SELECT (COUNT(?reifier) as ?reifiedStatements)
WHERE {
    ?reifier rdf:reifies ?triple .
}
"""
        result = execute_sparql(query, expect_results=False)
        assert result is not None, "Query execution failed"

        bindings = result['results']['bindings']
        if bindings:
            count = bindings[0].get('reifiedStatements', {}).get('value', '0')
            print(f"\n  âœ“ Found {count} reified statements")


# ============================================================================
# 8. HEALTH & STATISTICS
# ============================================================================

class TestHealthStatistics:
    """Test Category 8: Health & Statistics"""

    def test_8_1_health_check(self, check_server):
        """8.1 Health Check"""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            assert response.status_code == 200, "Health check failed"

            data = response.json()
            print(f"\n  âœ“ Health: {data}")
            assert 'status' in data or 'message' in data, "Invalid health response"

        except Exception as e:
            pytest.fail(f"Health check failed: {e}")

    def test_8_2_store_statistics(self, check_server):
        """8.2 Store Statistics"""
        try:
            response = requests.get(f"{BASE_URL}/stats", timeout=5)
            assert response.status_code == 200, "Stats request failed"

            data = response.json()
            print(f"\n  âœ“ Statistics: {json.dumps(data, indent=2)}")

        except Exception as e:
            pytest.fail(f"Stats request failed: {e}")

    def test_8_3_home_page_html(self, check_server):
        """8.3 Home Page (HTML)"""
        try:
            response = requests.get(f"{BASE_URL}/", timeout=5)
            assert response.status_code == 200, "Home page request failed"

            content_type = response.headers.get('Content-Type', '')
            print(f"\n  âœ“ Home page accessible")
            print(f"    Content-Type: {content_type}")
            print(f"    Length: {len(response.text)} bytes")

            assert len(response.text) > 0, "Empty response"

        except Exception as e:
            pytest.fail(f"Home page request failed: {e}")


# ============================================================================
# SUMMARY TEST
# ============================================================================

def test_final_summary(check_server):
    """Generate a summary of all test results"""
    print("\n" + "="*70)
    print("TEST SUITE SUMMARY")
    print("="*70)
    print(f"Server: {BASE_URL}")
    print(f"All queries from Postman collection have been tested.")
    print(f"\nNote: Some queries may return 0 results if RDF-star data is not loaded.")
    print(f"Check individual test output for details on which queries returned data.")
    print("="*70)


