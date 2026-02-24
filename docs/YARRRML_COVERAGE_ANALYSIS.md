# YARRRML Specification Coverage Analysis

## Date: February 17, 2026

## Executive Summary

This document analyzes the current implementation of `rdf_star_etl_engine_optimized.py` and `yarrrml_parser.py` against the full YARRRML specification to identify gaps and implement missing features.

---

## Current Support Status

### ✅ FULLY SUPPORTED

1. **Prefixes and Namespaces** (Section 4)
   - Custom prefix definitions
   - Prefix expansion in URIs

2. **Basic Mappings** (Section 9)
   - Multiple mappings per document
   - Subject templates with variable substitution
   - Predicate-object pairs (basic)
   - Type statements (rdf:type / a)

3. **Data Sources** (Section 7 - Partial)
   - CSV files with path
   - Reference formulation (csv implicit)
   - Source definition in mappings
   - Multiple sources per mapping

4. **Templates** (Section 6)
   - Variable references: `$(variable)`
   - Constant strings in templates
   - URI sanitization

5. **Objects** (Section 9.4)
   - Literal objects
   - IRI objects with `~iri` suffix
   - Basic datatype support (xsd:*)

6. **RDF-Star** (Section 12 - Partial)
   - Quoted triple subjects using `function: join(quoted=...)`
   - Join conditions with equal() function
   - Annotations on quoted triples
   - RDF reification with rdf:reifies

---

## ⚠️ PARTIALLY SUPPORTED (Needs Enhancement)

### 1. **Data Sources** (Section 7)
**Current:** Only CSV with implicit reference formulation
**Missing:**
- Explicit `referenceFormulation` key
- `iterator` key for nested data
- `delimiter` customization
- `encoding` specification
- Multiple reference formulations (jsonpath, xpath, xquery)
- Database sources (mysql, postgresql, oracle, etc.)
- SPARQL endpoints
- Remote files via HTTP
- Query formulation (SQL, SPARQL)
- Credentials for protected sources
- Web of Things (WoT) sources

### 2. **Subjects** (Section 9.3)
**Current:** Simple template strings
**Missing:**
- Multiple subjects per mapping (array)
- Blank nodes (null/empty subjects)
- Functions on subjects
- Subject-specific conditions

### 3. **Predicate-Objects** (Section 9.4)
**Current:** Basic predicates and objects
**Missing:**
- Multiple predicates for same objects (array)
- Multiple objects for same predicates (array)
- Cartesian product behavior
- Inverse predicates
- Long format with explicit `predicates`/`objects` keys
- Object-specific graphs

### 4. **Datatypes** (Section 9.5)
**Current:** Basic datatype support
**Missing:**
- Reference datatypes: `datatype: $(my_datatype)`
- Datatypes on function results
- Full datatype validation

### 5. **Languages** (Section 9.6)
**Current:** NOT SUPPORTED
**Missing:**
- Language tags: `language: en`
- Shortcut: `en~lang`
- Reference languages: `language: $(my_language)`
- Multiple languages per predicate

### 6. **RDF-Star** (Section 12)
**Current:** Basic quoted triples in subjects
**Missing:**
- Quoted triples in **objects** position
- `quotedNonAsserted` keyword
- More complex join conditions
- Shortcut inline join syntax

---

## ❌ NOT SUPPORTED (Critical Gaps)

### 1. **Base IRI** (Section 3)
```yaml
base: http://mybaseiri.com#
```
- Not parsed
- Not applied to relative URIs

### 2. **Authors** (Section 5)
```yaml
authors:
  - name: John Doe
    email: john@doe.com
  - Jane Doe <jane@doe.com>
```
- Not parsed
- Not included in output metadata

### 3. **Targets** (Section 8)
```yaml
targets:
  my-target:
    access: output.ttl
    type: void
    serialization: turtle
    compression: gzip
```
- Not parsed
- Cannot specify output format per mapping
- Cannot specify multiple targets
- No compression support
- No SPARQL endpoint targets

### 4. **Functions** (Section 10)
```yaml
objects:
  - function: ex:toLowerCase
    parameters:
      - [ex:input, $(firstname)]
```
- Not parsed
- Cannot transform data
- No FnO support
- Critical for data cleaning/transformation

### 5. **Conditions** (Section 11)
```yaml
condition:
  function: ex:isValid
  parameters:
    - [ex:input, $(firstname)]
```
- Not parsed
- Cannot filter records
- Cannot conditionally generate triples

### 6. **Graphs** (Section 9.8)
```yaml
graphs: ex:myGraph
```
- Not parsed
- All triples go to default graph
- No per-mapping graph support
- No per-predicate-object graph support

### 7. **Referring to Other Mappings** (Section 9.7)
```yaml
objects:
  - mapping: project
    condition:
      function: equal
      parameters:
        - [str1, $(projectID), s]
        - [str2, $(ID), o]
```
- Only supported for RDF-star quoted triples
- Not supported for regular object linking
- Cannot join two mappings for regular triples

### 8. **External References** (Section 13)
```yaml
external:
  name: John
  city: Ghent
```
- Not parsed
- Cannot use constant values across mappings
- No `$(_variable)` support

### 9. **Shortcuts** (Section 14)
**Current:** Using full keys
**Missing:**
- `s` for `subjects`
- `po` for `predicateobjects`
- `p` for `predicates`
- `o` for `objects`
- `fn` for `function`
- etc.

### 10. **Advanced Source Features**
- Iterator for nested JSON/XML
- Query on databases
- SPARQL on endpoints
- Content type negotiation
- Compression handling

---

## Priority Implementation Plan

### 🔥 HIGH PRIORITY (Required for Full Spec Compliance)

1. **Functions** (Section 10)
   - Critical for real-world use cases
   - Data transformation is essential
   - Impact: High

2. **Conditions** (Section 11)
   - Data filtering is essential
   - Conditional triple generation
   - Impact: High

3. **Language Tags** (Section 9.6)
   - Common requirement for i18n
   - Simple to implement
   - Impact: Medium

4. **Graphs** (Section 9.8)
   - Named graphs are important for organization
   - Impact: Medium

5. **Multiple Subjects/Predicates/Objects**
   - Common pattern in mappings
   - Impact: Medium

6. **Inverse Predicates**
   - Useful for bidirectional relationships
   - Impact: Medium

### 📊 MEDIUM PRIORITY

7. **Base IRI** (Section 3)
   - Quality of life improvement
   - Impact: Low

8. **Authors** (Section 5)
   - Metadata/provenance
   - Impact: Low

9. **External References** (Section 13)
   - Useful for constants
   - Impact: Medium

10. **Referring to Other Mappings** (Section 9.7)
    - Essential for complex joins
    - Impact: High (but complex)

11. **Shortcuts** (Section 14)
    - Convenience feature
    - Impact: Low

### 🔮 LOW PRIORITY (Advanced Features)

12. **Targets** (Section 8)
    - Currently hardcoded in config
    - Impact: Low (workaround exists)

13. **Advanced Sources**
    - JSON/XML with iterators
    - Database sources
    - SPARQL endpoints
    - Impact: High (but complex)

14. **RDF-Star in Objects**
    - Advanced use case
    - Impact: Low

15. **QuotedNonAsserted**
    - Niche use case
    - Impact: Low

---

## Implementation Roadmap

### Phase 1: Critical Features (Estimated: 2-3 days)
- [ ] Language tags (full support)
- [ ] Multiple subjects/predicates/objects (arrays)
- [ ] Basic function support (framework)
- [ ] Basic condition support (framework)
- [ ] Inverse predicates
- [ ] Graph support

### Phase 2: Essential Features (Estimated: 3-4 days)
- [ ] Function library integration (FnO)
- [ ] Condition evaluation
- [ ] Base IRI support
- [ ] External references
- [ ] Object-to-mapping references
- [ ] Reference datatypes/languages

### Phase 3: Advanced Features (Estimated: 4-5 days)
- [ ] JSON source support (jsonpath)
- [ ] Iterator support
- [ ] Target specification
- [ ] RDF-Star in objects
- [ ] QuotedNonAsserted
- [ ] Shortcuts parsing

### Phase 4: Enterprise Features (Future)
- [ ] Database source support
- [ ] SPARQL endpoint sources
- [ ] WoT sources
- [ ] Compression
- [ ] Multiple targets

---

## Testing Requirements

Each new feature must have:
1. Unit tests in parser
2. Integration tests in ETL engine
3. Example YARRRML mapping
4. Documentation

---

## Backward Compatibility

All changes must maintain backward compatibility with existing mappings:
- `data_products_rml.yaml` must continue to work
- Existing optimizations must be preserved
- Performance must not degrade

---

## Conclusion

Current implementation supports ~30% of the full YARRRML specification. The most critical gaps are:

1. **Functions** - blocking real-world data transformation
2. **Conditions** - blocking data filtering
3. **Language tags** - blocking i18n support
4. **Graphs** - blocking proper RDF organization

Implementing Phase 1 and 2 would bring coverage to ~70% and satisfy most real-world use cases.

