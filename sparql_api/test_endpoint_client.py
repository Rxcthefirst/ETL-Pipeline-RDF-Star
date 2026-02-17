"""
Test client for the Flask SPARQL endpoint
This will test the Flask endpoint if it's running
"""

import requests
import json

ENDPOINT_URL = "http://localhost:5000/sparql"

def test_endpoint():
    print("=" * 80)
    print("Testing Flask SPARQL Endpoint")
    print("=" * 80)

    # Test query
    query = """
    PREFIX ex: <http://example.org/>
    SELECT ?s ?p ?o
    WHERE {
        ?s ?p ?o .
    }
    LIMIT 10
    """

    try:
        # Test POST request
        print("\nSending SPARQL query to endpoint...")
        response = requests.post(
            ENDPOINT_URL,
            data={'query': query},
            timeout=5
        )

        if response.status_code == 200:
            print("✓ Endpoint is responding!")
            print("\nResults:")
            results = response.json()
            print(json.dumps(results, indent=2))
        else:
            print(f"✗ Error: HTTP {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to endpoint at", ENDPOINT_URL)
        print("\nTo start the Flask endpoint, run:")
        print("  python flask_sparql_endpoint.py")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_endpoint()

