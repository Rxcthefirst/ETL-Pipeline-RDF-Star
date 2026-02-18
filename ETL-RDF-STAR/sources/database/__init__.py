"""
Database Source Connectors Package
===================================

Provides connectors for various SQL databases:
- PostgreSQL
- MySQL/MariaDB
- SQL Server
- SQLite
- Oracle

All database connectors support:
- Secure credential handling via environment variables
- Connection pooling
- SSL/TLS encryption
- Query parameterization
"""

from .postgresql import PostgreSQLSource
from .mysql import MySQLSource
from .sqlite import SQLiteSource

# Note: SQL Server and Oracle require additional drivers
# and are imported conditionally

__all__ = [
    'PostgreSQLSource',
    'MySQLSource',
    'SQLiteSource',
]

