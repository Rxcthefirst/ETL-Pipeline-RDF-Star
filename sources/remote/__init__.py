"""
Remote Data Source Connectors Package
======================================

Provides connectors for remote data sources:
- HTTP/REST APIs
- SPARQL endpoints
- GraphQL endpoints
"""

from .http import HTTPSource
from .sparql import SPARQLSource

__all__ = [
    'HTTPSource',
    'SPARQLSource',
]

