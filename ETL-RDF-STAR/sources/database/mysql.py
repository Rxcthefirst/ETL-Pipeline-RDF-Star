"""
MySQL/MariaDB Data Source Connector
====================================

Connects to MySQL and MariaDB databases.

Dependencies:
    pip install mysql-connector-python
    # or: pip install pymysql

YARRRML Example:
```yaml
sources:
  mysql-source:
    type: mysql
    access: localhost:3306/mydb
    credentials:
      username: ${MYSQL_USER}
      password: ${MYSQL_PASSWORD}
    query: SELECT id, name, created_at FROM users
    ssl: true
```
"""

import polars as pl
from typing import Optional, List
from urllib.parse import urlparse

from .. import DatabaseSource, SourceConfig, register_source


@register_source('mysql')
@register_source('mariadb')
class MySQLSource(DatabaseSource):
    """
    MySQL/MariaDB database data source.

    Connection string format:
        host:port/database
    """

    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self._parse_access()

    def _parse_access(self):
        """Parse access string into connection parameters."""
        access = self.config.access

        if access.startswith('mysql://'):
            parsed = urlparse(access)
            self.host = parsed.hostname or 'localhost'
            self.port = parsed.port or 3306
            self.database = parsed.path.lstrip('/') if parsed.path else ''
            if parsed.username and not self.config.credentials:
                self.config.credentials = {
                    'username': parsed.username,
                    'password': parsed.password or ''
                }
        else:
            if '/' in access:
                host_port, self.database = access.rsplit('/', 1)
            else:
                host_port = access
                self.database = ''

            if ':' in host_port:
                self.host, port_str = host_port.rsplit(':', 1)
                self.port = int(port_str)
            else:
                self.host = host_port
                self.port = 3306

    def validate_config(self) -> List[str]:
        errors = super().validate_config()
        if not self.config.credentials:
            errors.append("'credentials' with 'username' required")
        return errors

    def get_connection_string(self) -> str:
        """Build MySQL connection string."""
        creds = self.config.credentials or {}
        return (
            f"mysql://{creds.get('username', '')}:{creds.get('password', '')}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    def connect(self) -> None:
        """Establish MySQL connection."""
        try:
            import mysql.connector
            connector = mysql.connector
        except ImportError:
            try:
                import pymysql
                connector = pymysql
            except ImportError:
                raise ImportError(
                    "MySQL connector required. Install with: "
                    "pip install mysql-connector-python or pip install pymysql"
                )

        creds = self.config.credentials or {}

        connect_args = {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': creds.get('username'),
            'password': creds.get('password', ''),
            'connect_timeout': self.config.timeout
        }

        if self.config.ssl:
            connect_args['ssl_disabled'] = False

        self.connection = connector.connect(**connect_args)
        self._connected = True

    def fetch_data(self) -> pl.DataFrame:
        """Execute query and return results as DataFrame."""
        if not self._connected:
            self.connect()

        query = self.config.query
        if not query:
            raise ValueError("No query specified for MySQL source")

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

