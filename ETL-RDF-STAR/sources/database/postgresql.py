"""
PostgreSQL Data Source Connector
=================================

Connects to PostgreSQL databases and executes SQL queries.

Dependencies:
    pip install psycopg2-binary
    # or for async: pip install asyncpg

YARRRML Example:
```yaml
sources:
  pg-source:
    type: postgresql
    access: localhost:5432/mydb
    credentials:
      username: ${PG_USER}
      password: ${PG_PASSWORD}
    query: SELECT id, name, email FROM customers WHERE active = true
    referenceFormulation: csv
    ssl: true
```

Security Notes:
- Always use environment variables for credentials
- Enable SSL in production
- Use read-only database users when possible
- Queries are executed as-is; ensure proper access controls
"""

import polars as pl
from typing import Optional, List
from urllib.parse import urlparse

from .. import DatabaseSource, SourceConfig, register_source


@register_source('postgresql')
@register_source('postgres')
@register_source('pg')
class PostgreSQLSource(DatabaseSource):
    """
    PostgreSQL database data source.

    Connection string format:
        host:port/database

    Example access values:
        - localhost:5432/mydb
        - db.example.com:5432/production
        - /var/run/postgresql/mydb (Unix socket)
    """

    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self._parse_access()

    def _parse_access(self):
        """Parse access string into connection parameters."""
        access = self.config.access

        # Handle full URI format
        if access.startswith('postgresql://') or access.startswith('postgres://'):
            parsed = urlparse(access)
            self.host = parsed.hostname or 'localhost'
            self.port = parsed.port or 5432
            self.database = parsed.path.lstrip('/') if parsed.path else 'postgres'
            # URI might include credentials
            if parsed.username and not self.config.credentials:
                self.config.credentials = {
                    'username': parsed.username,
                    'password': parsed.password or ''
                }
        else:
            # Simple format: host:port/database
            if '/' in access:
                host_port, self.database = access.rsplit('/', 1)
            else:
                host_port = access
                self.database = 'postgres'

            if ':' in host_port:
                self.host, port_str = host_port.rsplit(':', 1)
                self.port = int(port_str)
            else:
                self.host = host_port
                self.port = 5432

    def validate_config(self) -> List[str]:
        errors = super().validate_config()
        if not self.config.credentials:
            errors.append("'credentials' with 'username' and 'password' required")
        elif not self.config.credentials.get('username'):
            errors.append("'credentials.username' is required")
        return errors

    def get_connection_string(self) -> str:
        """Build psycopg2 connection string."""
        creds = self.config.credentials or {}
        return (
            f"host={self.host} "
            f"port={self.port} "
            f"dbname={self.database} "
            f"user={creds.get('username', '')} "
            f"password={creds.get('password', '')} "
            f"sslmode={'require' if self.config.ssl else 'prefer'}"
        )

    def connect(self) -> None:
        """Establish PostgreSQL connection."""
        try:
            import psycopg2
        except ImportError:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. "
                "Install with: pip install psycopg2-binary"
            )

        creds = self.config.credentials or {}

        self.connection = psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=creds.get('username'),
            password=creds.get('password'),
            sslmode='require' if self.config.ssl else 'prefer',
            connect_timeout=self.config.timeout
        )

        # Set to read-only mode for safety
        self.connection.set_session(readonly=True)
        self._connected = True

    def fetch_data(self) -> pl.DataFrame:
        """Execute query and return results as DataFrame."""
        if not self._connected:
            self.connect()

        query = self.config.query
        if not query:
            raise ValueError("No query specified for PostgreSQL source")

        try:
            # Use Polars direct PostgreSQL support if available
            conn_str = (
                f"postgresql://{self.config.credentials.get('username', '')}:"
                f"{self.config.credentials.get('password', '')}@"
                f"{self.host}:{self.port}/{self.database}"
            )
            return pl.read_database(query, conn_str)
        except Exception:
            # Fallback to psycopg2 cursor
            cursor = self.connection.cursor()
            cursor.execute(query)

            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()

            if not rows:
                return pl.DataFrame({col: [] for col in columns})

            # Convert to dict of lists
            data = {col: [] for col in columns}
            for row in rows:
                for col, val in zip(columns, row):
                    data[col].append(val)

            return pl.DataFrame(data)

