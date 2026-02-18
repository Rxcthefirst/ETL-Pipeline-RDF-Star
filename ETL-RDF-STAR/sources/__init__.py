"""
Data Source Base Classes and Registry
======================================

This module provides the abstract base class for all data source connectors
and a registry for discovering and instantiating source types.

Supported source types:
- CSV files (csv)
- JSON files with JSONPath (jsonpath)
- XML files with XPath (xpath)
- PostgreSQL (postgresql)
- MySQL (mysql)
- SQL Server (mssqlserver)
- SQLite (sqlite)
- Oracle (oracle)
- HTTP/REST APIs (remotefile)
- SPARQL endpoints (sparql)
"""

import os
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Iterator
from dataclasses import dataclass
import polars as pl


# Environment variable pattern for credential interpolation
ENV_VAR_PATTERN = re.compile(r'\$\{([^}]+)\}')


def interpolate_env_vars(value: str) -> str:
    """
    Interpolate environment variables in a string.

    Supports ${VAR_NAME} syntax.

    Example:
        interpolate_env_vars("${DB_PASSWORD}") -> "actual_password"
    """
    if not isinstance(value, str):
        return value

    def replace_var(match):
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            raise ValueError(f"Environment variable not set: {var_name}")
        return env_value

    return ENV_VAR_PATTERN.sub(replace_var, value)


def interpolate_dict_env_vars(d: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively interpolate environment variables in a dictionary."""
    result = {}
    for key, value in d.items():
        if isinstance(value, str):
            result[key] = interpolate_env_vars(value)
        elif isinstance(value, dict):
            result[key] = interpolate_dict_env_vars(value)
        else:
            result[key] = value
    return result


@dataclass
class SourceConfig:
    """Configuration for a data source."""
    name: str
    source_type: str  # csv, jsonpath, xpath, postgresql, mysql, etc.
    access: str  # File path, URL, or connection string
    reference_formulation: str = "csv"
    iterator: Optional[str] = None  # JSONPath or XPath expression
    query: Optional[str] = None  # SQL or SPARQL query
    credentials: Optional[Dict[str, str]] = None
    encoding: str = "utf-8"
    delimiter: str = ","
    headers: Optional[Dict[str, str]] = None  # HTTP headers
    ssl: bool = True
    timeout: int = 30

    @classmethod
    def from_yarrrml(cls, name: str, source_spec: Dict[str, Any]) -> 'SourceConfig':
        """Create SourceConfig from YARRRML source specification."""
        # Interpolate environment variables in credentials
        credentials = source_spec.get('credentials')
        if credentials:
            credentials = interpolate_dict_env_vars(credentials)

        return cls(
            name=name,
            source_type=source_spec.get('type', 'localfile'),
            access=source_spec.get('access', ''),
            reference_formulation=source_spec.get('referenceFormulation', 'csv'),
            iterator=source_spec.get('iterator'),
            query=source_spec.get('query'),
            credentials=credentials,
            encoding=source_spec.get('encoding', 'utf-8'),
            delimiter=source_spec.get('delimiter', ','),
            headers=source_spec.get('headers'),
            ssl=source_spec.get('ssl', True),
            timeout=source_spec.get('timeout', 30)
        )


class DataSource(ABC):
    """
    Abstract base class for all data source connectors.

    Subclasses must implement:
    - connect(): Establish connection to the data source
    - fetch_data(): Retrieve data as a Polars DataFrame
    - close(): Clean up resources
    """

    def __init__(self, config: SourceConfig):
        self.config = config
        self._connected = False

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the data source."""
        pass

    @abstractmethod
    def fetch_data(self) -> pl.DataFrame:
        """Fetch data and return as a Polars DataFrame."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connection and clean up resources."""
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        if not self.config.access:
            errors.append("'access' is required")
        return errors


class FileSource(DataSource):
    """Base class for file-based data sources (CSV, JSON, XML)."""

    def __init__(self, config: SourceConfig, base_path: Optional[str] = None):
        super().__init__(config)
        self.base_path = base_path or os.getcwd()
        self.resolved_path: Optional[str] = None

    def connect(self) -> None:
        """Resolve and validate file path."""
        self.resolved_path = self._resolve_path(self.config.access)
        if not os.path.exists(self.resolved_path):
            raise FileNotFoundError(f"Source file not found: {self.resolved_path}")
        self._connected = True

    def close(self) -> None:
        """No-op for file sources."""
        self._connected = False

    def _resolve_path(self, path: str) -> str:
        """Resolve file path relative to base path."""
        if os.path.isabs(path):
            return path

        # Search directories
        search_dirs = [
            self.base_path,
            os.path.dirname(self.base_path),
            os.path.join(self.base_path, 'data'),
            os.path.join(self.base_path, 'benchmark_data'),
            os.path.join(os.path.dirname(self.base_path), 'data'),
            os.path.join(os.path.dirname(self.base_path), 'benchmark_data'),
        ]

        for search_dir in search_dirs:
            candidate = os.path.join(search_dir, path)
            if os.path.exists(candidate):
                return os.path.abspath(candidate)

        return os.path.join(self.base_path, path)


class DatabaseSource(DataSource):
    """Base class for database data sources."""

    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.connection = None

    def validate_config(self) -> List[str]:
        errors = super().validate_config()
        if not self.config.query:
            errors.append("'query' is required for database sources")
        return errors

    @abstractmethod
    def get_connection_string(self) -> str:
        """Build connection string for this database type."""
        pass

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
        self._connected = False


class RemoteSource(DataSource):
    """Base class for remote data sources (HTTP, SPARQL, GraphQL)."""

    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.session = None

    def validate_config(self) -> List[str]:
        errors = super().validate_config()
        if not self.config.access.startswith(('http://', 'https://')):
            errors.append("'access' must be a valid HTTP(S) URL")
        return errors


# Source Registry
_SOURCE_REGISTRY: Dict[str, type] = {}


def register_source(source_type: str):
    """Decorator to register a source class."""
    def decorator(cls):
        _SOURCE_REGISTRY[source_type.lower()] = cls
        return cls
    return decorator


def get_source_class(source_type: str) -> Optional[type]:
    """Get the source class for a given type."""
    return _SOURCE_REGISTRY.get(source_type.lower())


def create_source(config: SourceConfig, base_path: Optional[str] = None) -> DataSource:
    """Factory function to create a data source instance."""
    # Determine source type
    source_type = config.source_type.lower()

    # Map reference formulation to source type if needed
    if source_type in ('localfile', 'remotefile'):
        source_type = config.reference_formulation.lower()

    source_class = get_source_class(source_type)
    if source_class is None:
        raise ValueError(f"Unknown source type: {source_type}")

    # File sources need base_path
    if issubclass(source_class, FileSource):
        return source_class(config, base_path)

    return source_class(config)


def list_available_sources() -> List[str]:
    """List all registered source types."""
    return list(_SOURCE_REGISTRY.keys())


# Auto-import source modules to register them
# These imports trigger the @register_source decorators
try:
    from . import csv_source
except ImportError:
    pass

try:
    from . import json_source
except ImportError:
    pass

try:
    from . import xml_source
except ImportError:
    pass

try:
    from .database import sqlite
except ImportError:
    pass

try:
    from .database import postgresql
except ImportError:
    pass

try:
    from .database import mysql
except ImportError:
    pass

try:
    from .remote import http
except ImportError:
    pass

try:
    from .remote import sparql
except ImportError:
    pass

