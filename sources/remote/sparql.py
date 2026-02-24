"""
SPARQL Endpoint Data Source Connector
======================================

Queries SPARQL endpoints and returns results as tabular data.

Dependencies:
    pip install SPARQLWrapper

YARRRML Example:
```yaml
sources:
  sparql-source:
    type: sparql
    access: https://dbpedia.org/sparql
    queryFormulation: sparql11
    query: |
      SELECT ?person ?name ?birthDate WHERE {
        ?person a dbo:Person ;
                rdfs:label ?name ;
                dbo:birthDate ?birthDate .
        FILTER(LANG(?name) = 'en')
      } LIMIT 100
    referenceFormulation: csv
```
"""

import polars as pl
from typing import List

from .. import RemoteSource, SourceConfig, register_source


@register_source('sparql')
class SPARQLSource(RemoteSource):
    """
    SPARQL endpoint data source.

    Executes SPARQL SELECT queries against endpoints and returns
    the results as a DataFrame.
    """

    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.sparql = None

    def validate_config(self) -> List[str]:
        errors = super().validate_config()
        if not self.config.query:
            errors.append("'query' is required for SPARQL sources")
        return errors

    def connect(self) -> None:
        """Initialize SPARQL endpoint connection."""
        try:
            from SPARQLWrapper import SPARQLWrapper, JSON, CSV
            self._sparql_wrapper = SPARQLWrapper
            self._json_format = JSON
            self._csv_format = CSV
        except ImportError:
            raise ImportError(
                "SPARQLWrapper required for SPARQL sources. "
                "Install with: pip install SPARQLWrapper"
            )

        self.sparql = self._sparql_wrapper(self.config.access)
        self.sparql.setTimeout(self.config.timeout)

        # Set return format
        self.sparql.setReturnFormat(self._json_format)

        self._connected = True

    def close(self) -> None:
        """Clean up SPARQL wrapper."""
        self.sparql = None
        self._connected = False

    def fetch_data(self) -> pl.DataFrame:
        """Execute SPARQL query and return results as DataFrame."""
        if not self._connected:
            self.connect()

        query = self.config.query
        if not query:
            raise ValueError("No query specified for SPARQL source")

        self.sparql.setQuery(query)

        try:
            results = self.sparql.query().convert()
        except Exception as e:
            raise RuntimeError(f"SPARQL query failed: {e}")

        # Parse JSON results
        if 'results' in results and 'bindings' in results['results']:
            bindings = results['results']['bindings']
            variables = results['head']['vars']

            if not bindings:
                return pl.DataFrame({var: [] for var in variables})

            # Convert bindings to DataFrame
            data = {var: [] for var in variables}
            for binding in bindings:
                for var in variables:
                    if var in binding:
                        value = binding[var].get('value', '')
                        data[var].append(value)
                    else:
                        data[var].append(None)

            return pl.DataFrame(data)

        return pl.DataFrame()

