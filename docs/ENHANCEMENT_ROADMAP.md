# RDF-star ETL Engine - Enhancement Roadmap

## Current State Assessment

### ✅ What We Have
- Full YARRRML specification parser (~70% coverage)
- CSV data source support
- RDF-star/quoted triples support
- Named graphs
- Language tags
- Multiple subjects/predicates/objects
- Vectorized processing with Polars
- 46 comprehensive tests passing

### 🚀 Enhancement Priorities

---

## Phase 1: Multi-Format Data Sources (High Priority)

### 1.1 JSON Support with JSONPath
```yaml
sources:
  json-source:
    access: data/people.json
    referenceFormulation: jsonpath
    iterator: $.people[*]
```

**Implementation:**
- Add `jsonpath-ng` library for JSONPath queries
- Support nested JSON structures
- Handle arrays and objects

### 1.2 XML Support with XPath
```yaml
sources:
  xml-source:
    access: data/catalog.xml
    referenceFormulation: xpath
    iterator: //product
```

**Implementation:**
- Use `lxml` library for XPath queries
- Support namespaces
- Handle attributes and text nodes

### 1.3 Excel/XLSX Support
```yaml
sources:
  excel-source:
    access: data/report.xlsx
    referenceFormulation: csv
    sheet: Sheet1
```

**Implementation:**
- Use `openpyxl` or Polars Excel support
- Multiple sheet support
- Named ranges

---

## Phase 2: Database Connectors (High Priority)

### 2.1 PostgreSQL
```yaml
sources:
  pg-source:
    type: postgresql
    access: localhost:5432/mydb
    credentials:
      username: ${PG_USER}
      password: ${PG_PASSWORD}
    query: SELECT * FROM customers WHERE active = true
    referenceFormulation: csv
```

### 2.2 MySQL/MariaDB
```yaml
sources:
  mysql-source:
    type: mysql
    access: localhost:3306/mydb
    credentials:
      username: ${MYSQL_USER}
      password: ${MYSQL_PASSWORD}
    query: SELECT id, name, email FROM users
```

### 2.3 SQL Server
```yaml
sources:
  mssql-source:
    type: mssqlserver
    access: server\instance/database
    credentials:
      username: ${MSSQL_USER}
      password: ${MSSQL_PASSWORD}
    query: SELECT * FROM Products
```

### 2.4 SQLite (Local)
```yaml
sources:
  sqlite-source:
    type: sqlite
    access: data/local.db
    query: SELECT * FROM orders
```

### 2.5 Oracle
```yaml
sources:
  oracle-source:
    type: oracle
    access: localhost:1521/ORCL
    credentials:
      username: ${ORACLE_USER}
      password: ${ORACLE_PASSWORD}
    query: SELECT * FROM employees
```

**Security Features:**
- Environment variable interpolation for credentials
- Connection pooling
- SSL/TLS support
- Query parameterization (prevent SQL injection)
- Read-only connections by default

---

## Phase 3: Remote Data Sources (Medium Priority)

### 3.1 HTTP/REST APIs
```yaml
sources:
  api-source:
    type: remotefile
    access: https://api.example.com/data
    contentType: application/json
    referenceFormulation: jsonpath
    iterator: $.results[*]
    headers:
      Authorization: Bearer ${API_TOKEN}
```

### 3.2 SPARQL Endpoints
```yaml
sources:
  sparql-source:
    type: sparql
    access: https://dbpedia.org/sparql
    queryFormulation: sparql11
    query: |
      SELECT ?person ?name WHERE {
        ?person a dbo:Person ;
                rdfs:label ?name .
        FILTER(LANG(?name) = 'en')
      } LIMIT 100
    referenceFormulation: csv
```

### 3.3 GraphQL Endpoints
```yaml
sources:
  graphql-source:
    type: graphql
    access: https://api.example.com/graphql
    query: |
      query {
        users {
          id
          name
          email
        }
      }
    referenceFormulation: jsonpath
    iterator: $.data.users[*]
```

---

## Phase 4: Output Targets (Medium Priority)

### 4.1 Multiple Serialization Formats
- TriG (current)
- Turtle
- N-Triples
- N-Quads
- JSON-LD
- RDF/XML

### 4.2 Direct Database Output
```yaml
targets:
  graph-db:
    type: sparql
    access: http://localhost:7200/repositories/myrepo
    method: sparql-update
```

### 4.3 Compression
```yaml
targets:
  compressed-output:
    access: output/data.trig.gz
    compression: gzip
```

---

## Phase 5: Function Execution (Medium Priority)

### 5.1 Built-in Functions
```yaml
objects:
  - function: grel:toLowerCase
    parameters:
      - [grel:valueParam, $(name)]
```

**Common Functions:**
- String: toLowerCase, toUpperCase, trim, replace, concat
- Date: parseDate, formatDate, now
- Math: add, subtract, multiply, divide, round
- Logic: if, equals, notEquals, contains

### 5.2 Custom Functions
```yaml
functions:
  ex:normalizePhone:
    implementation: python
    code: |
      def normalize_phone(value):
        return re.sub(r'[^\d]', '', value)
```

---

## Phase 6: Security & Enterprise Features (High Priority)

### 6.1 Credential Management
- Environment variable interpolation: `${VAR_NAME}`
- Secrets file support
- AWS Secrets Manager integration
- Azure Key Vault integration
- HashiCorp Vault integration

### 6.2 Connection Security
- SSL/TLS for all database connections
- Certificate validation
- SSH tunneling for remote databases
- IP whitelisting support

### 6.3 Audit Logging
- Log all database queries
- Track data lineage
- Record transformation history

### 6.4 Rate Limiting
- API request throttling
- Connection pooling
- Retry with exponential backoff

---

## Phase 7: Testing Infrastructure

### 7.1 Format-Specific Tests
- CSV edge cases (encoding, delimiters, quotes)
- JSON nested structures
- XML namespaces
- Excel formulas and formats

### 7.2 Database Integration Tests
- Docker-based test databases
- Mock database responses
- Connection failure handling

### 7.3 Performance Benchmarks
- Large file processing
- Memory usage tracking
- Parallel processing tests

---

## Implementation Priority Matrix

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| JSON/JSONPath | High | Medium | 🔥 P1 |
| PostgreSQL | High | Medium | 🔥 P1 |
| Environment Variables | High | Low | 🔥 P1 |
| XML/XPath | Medium | Medium | P2 |
| MySQL | Medium | Low | P2 |
| REST APIs | High | Medium | P2 |
| Built-in Functions | High | High | P2 |
| SPARQL Sources | Medium | Medium | P3 |
| SQL Server | Medium | Low | P3 |
| Multiple Output Formats | Medium | Low | P3 |
| Compression | Low | Low | P3 |
| Custom Functions | Medium | High | P4 |
| Cloud Secrets | Medium | Medium | P4 |

---

## Quick Wins (Can Implement Now)

1. **Environment Variable Support** - Secure credential handling
2. **JSON Source Support** - Very common data format
3. **PostgreSQL Connector** - Most popular open-source DB
4. **Better Error Messages** - Developer experience
5. **Dry Run Mode** - Validate mappings without execution

---

## File Structure After Enhancements

```
ETL-RDF-STAR/
├── rdf_star_etl_yarrrml.py      # Main entry point
├── yarrrml_parser.py            # YARRRML parser
├── sources/                      # Data source connectors
│   ├── __init__.py
│   ├── base.py                  # Abstract base class
│   ├── csv_source.py            # CSV (current)
│   ├── json_source.py           # JSON + JSONPath
│   ├── xml_source.py            # XML + XPath
│   ├── database/
│   │   ├── __init__.py
│   │   ├── postgresql.py
│   │   ├── mysql.py
│   │   ├── mssql.py
│   │   ├── sqlite.py
│   │   └── oracle.py
│   └── remote/
│       ├── __init__.py
│       ├── http.py
│       ├── sparql.py
│       └── graphql.py
├── targets/                      # Output targets
│   ├── __init__.py
│   ├── file.py
│   ├── sparql_update.py
│   └── streaming.py
├── functions/                    # FnO function implementations
│   ├── __init__.py
│   ├── string.py
│   ├── date.py
│   ├── math.py
│   └── custom.py
├── security/                     # Security utilities
│   ├── __init__.py
│   ├── credentials.py
│   ├── encryption.py
│   └── audit.py
└── tests/
    ├── test_sources/
    ├── test_targets/
    ├── test_functions/
    └── test_integration/
```

---

## Next Steps

1. **Implement JSON Support** - Start with Phase 1.1
2. **Add Environment Variables** - Security foundation
3. **Create Database Base Class** - Prepare for multiple DBs
4. **Implement PostgreSQL** - First database connector
5. **Add Comprehensive Tests** - For each new feature

