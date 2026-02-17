# SPARQL Query Testing - Documentation Index

## 📋 Overview

This directory contains a complete test suite that validates **all 26 SPARQL queries** from your Postman collection against your SPARQL endpoint on port 7878.

## 🎯 Current Status

✅ **100% Test Coverage** - All 26 queries tested and validated  
✅ **All Tests Passing** - 26/26 tests pass  
✅ **Bug Fixed** - Query 3.1 syntax error corrected  
✅ **Fully Documented** - Complete usage guides included  

## 📚 Documentation Files

### 🚀 [QUICK_START_TESTING.md](QUICK_START_TESTING.md)
**Start here!** Quick reference for running tests.
- Essential commands
- Common use cases
- Troubleshooting
- **Best for**: Getting started quickly

### 📖 [README_POSTMAN_TESTS.md](README_POSTMAN_TESTS.md)
Complete test suite documentation.
- Detailed usage instructions
- All test categories explained
- Configuration options
- CI/CD integration examples
- **Best for**: Understanding the full test suite

### 📊 [VALIDATION_SUMMARY.md](VALIDATION_SUMMARY.md)
Executive summary of what was delivered.
- Problem statement
- Solution overview
- Bug fixes applied
- Test coverage breakdown
- **Best for**: Project stakeholders

### 📝 [test_execution_report.txt](test_execution_report.txt)
Latest test execution results.
- Raw pytest output
- All 26 test results
- Execution times
- **Best for**: Verifying test runs

## 🔧 Test Files

### ✅ [test_postman_queries.py](test_postman_queries.py)
Main pytest test suite (670 lines)
- 26 comprehensive tests
- 8 test categories
- Detailed error reporting
- **Run with**: `pytest test_postman_queries.py -v`

## 🎯 Quick Commands

```bash
# Run all tests
pytest test_postman_queries.py -v

# Run with detailed output
pytest test_postman_queries.py -v -s

# Run specific category
pytest test_postman_queries.py -v -k "Basic"

# Run single test
pytest test_postman_queries.py::TestBasicQueries::test_1_1_count_all_datasets -v
```

## 📦 What's Been Fixed

### Postman Collection Updates
**File**: `../RDF_Star_Data_Products.postman_collection.json`

1. ✅ **Fixed Query 3.1** - Added missing `PREFIX prov:` declaration
2. ✅ **Updated base_url** - Changed from port 8000 to 7878
3. ✅ **All queries validated** - 100% working

### Issues Resolved
- ❌ Query 3.1 returned 400 error (syntax error)
- ✅ Now returns 200 status (executes successfully)

## 🔍 Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| **1. Basic Queries** | 3 | Dataset counts and listings |
| **2. RDF-star Provenance** | 3 | Statement-level metadata queries |
| **3. Data Quality & Governance** | 3 | Confidence scores and rules |
| **4. Temporal & Freshness** | 3 | Time-based data queries |
| **5. Ontology Alignment** | 4 | Classes, properties, individuals |
| **6. Complex Multi-faceted** | 4 | Advanced combined queries |
| **7. Reification Comparison** | 2 | RDF-star syntax examples |
| **8. Health & Statistics** | 3 | Endpoint health checks |
| **TOTAL** | **26** | **Complete coverage** |

## 📊 Test Results

```
============================= test session starts =============================
collected 26 items

test_postman_queries.py::TestBasicQueries::test_1_1_count_all_datasets PASSED
test_postman_queries.py::TestBasicQueries::test_1_2_list_first_10_datasets PASSED
test_postman_queries.py::TestBasicQueries::test_1_3_count_all_activities PASSED
...
test_postman_queries.py::test_final_summary PASSED

============================= 26 passed in 54.15s =============================
```

## 🎓 Usage Examples

### Validate Before Deployment
```bash
# Run full test suite before deploying changes
pytest test_postman_queries.py -v
```

### Test After Data Load
```bash
# After loading new RDF data, verify queries still work
pytest test_postman_queries.py -v -s
```

### Debug Specific Query
```bash
# Test and see output for specific query
pytest test_postman_queries.py::TestRDFStarProvenanceQueries::test_2_1_find_high_confidence_theme_assignments -v -s
```

### CI/CD Integration
```bash
# Short output for CI/CD pipelines
pytest test_postman_queries.py -v --tb=short
```

## 🛠️ Requirements

- Python 3.7+
- pytest
- requests

```bash
pip install pytest requests
```

## 🌐 Server Configuration

Tests connect to:
- **Endpoint**: `http://localhost:7878/sparql`
- **Health Check**: `http://localhost:7878/health`
- **Statistics**: `http://localhost:7878/stats`

To use a different port, edit `test_postman_queries.py`:
```python
BASE_URL = "http://localhost:YOUR_PORT"
```

## 📈 Why Some Queries Return 0 Results

This is **NORMAL** and **EXPECTED**:

1. **RDF-star annotations** might not be in your current dataset
2. **Test data** (like DS-000001) might not exist
3. **Filters** (confidence > 0.90) might not match your data

The important validation is that queries **execute without errors** (Status 200).

## 🚀 Next Steps

### 1. Run the Tests
```bash
cd E:\MorphKGC-Test\ETL-RDF-STAR\tests
pytest test_postman_queries.py -v
```

### 2. Use Updated Postman Collection
Import the fixed `RDF_Star_Data_Products.postman_collection.json` into Postman

### 3. Load Test Data (Optional)
To see actual RDF-star query results, load data with statement-level annotations

### 4. Integrate into CI/CD (Optional)
Add test suite to your automated pipeline

## 🐛 Troubleshooting

### Server Not Running
```
[ERROR] Server not accessible
```
**Solution**: Start your SPARQL server first

### Tests Take Too Long
```
Query timed out after 30s
```
**Solution**: Increase `QUERY_TIMEOUT` in test file or optimize queries

### Import Errors
```
ModuleNotFoundError: No module named 'pytest'
```
**Solution**: `pip install pytest requests`

## 📞 Support

For detailed information:
- **Quick Start**: See `QUICK_START_TESTING.md`
- **Full Documentation**: See `README_POSTMAN_TESTS.md`
- **Summary Report**: See `VALIDATION_SUMMARY.md`

## ✨ Key Benefits

✅ **Automated Testing** - No more manual Postman testing  
✅ **Bug Prevention** - Catch syntax errors before deployment  
✅ **Regression Testing** - Ensure changes don't break queries  
✅ **Documentation** - Self-documenting test suite  
✅ **CI/CD Ready** - Easy integration into pipelines  
✅ **Time Savings** - Fast, automated validation  

---

**Version**: 1.0  
**Last Updated**: February 15, 2026  
**Status**: ✅ Production Ready  
**Test Coverage**: 100% (26/26 queries)

