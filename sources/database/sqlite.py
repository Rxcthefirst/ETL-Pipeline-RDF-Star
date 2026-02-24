"""
SQLite Data Source Connector
=============================

Connects to SQLite databases (local file-based).

No additional dependencies required (uses Python's built-in sqlite3).

YARRRML Example:
```yaml
sources:
  sqlite-source:
    type: sqlite
    access: data/local.db
    query: SELECT * FROM products WHERE category = 'electronics'
```
"""

import sqlite3
import polars as pl
from typing import List

from .. import FileSource, SourceConfig, register_source


@register_source('sqlite')
@register_source('sqlite3')
class SQLiteSource(FileSource):
    """
    SQLite database data source.

    This is a file-based database, so it uses FileSource as base.
    """

    def __init__(self, config: SourceConfig, base_path: str = None):
        super().__init__(config, base_path)
        self.connection = None

    def validate_config(self) -> List[str]:
        errors = []
        if not self.config.access:
            errors.append("'access' (database file path) is required")
        if not self.config.query:
            errors.append("'query' is required for SQLite sources")
        return errors

    def connect(self) -> None:
        """Open SQLite database connection."""
        # First resolve the file path
        super().connect()

        # Then open database connection
        self.connection = sqlite3.connect(
            self.resolved_path,
            timeout=self.config.timeout
        )
        # Enable read-only mode via PRAGMA
        self.connection.execute("PRAGMA query_only = ON")

    def close(self) -> None:
        """Close SQLite connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
        super().close()

    def fetch_data(self) -> pl.DataFrame:
        """Execute query and return results as DataFrame."""
        if not self._connected:
            self.connect()

        query = self.config.query
        if not query:
            raise ValueError("No query specified for SQLite source")

        cursor = self.connection.cursor()
        cursor.execute(query)

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        cursor.close()

        if not rows:
            return pl.DataFrame({col: [] for col in columns})

        data = {col: [] for col in columns}
        for row in rows:
            for col, val in zip(columns, row):
                data[col].append(val)

        return pl.DataFrame(data)

