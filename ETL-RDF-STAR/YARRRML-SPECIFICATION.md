1. Terminology

subject
    the subject of an RDF triple
predicate
    the predicate of an RDF triple
object
    the object of an RDF triple
class
    the type of an entity
datatype
    the type of a literal value
reference
    the reference to a data fraction in a data source
function
    a programmatic function that takes 0 or more input parameters and returns a single result

2. Profiles

This specification includes the following main profiles for tools that process YARRRML documents:

    R2RML: applies the semantics specified by [R2RML];
    RML: applies the semantics specified by [RML]; and
    RMLT: applies the semantics specified by [RMLT].
    RMLStar: applies the semantics specified by [RMLStar].

These profiles can be extended with additional profiles, which cannot be used on their own:

    FORMATS: applies the semantics specified by the W3C Formats namespace.
    COMP: applies the semantics specified by the Compression namespace.
    VOID: applies the semantics specified by [VoID];
    FnO: applies the semantics specified by [FnO];
    DCAT: applies the semantics specified by [DCAT];
    D2RQ: applies the semantics specified by [D2RQ];
    SD: applies the semantics specified by SD ([sparql11-service-description]); and
    CSVW: applies the semantics specified by CSVW ([csv2rdf]).
    WOT: applies the semantics specified by WoT Thing Description and WoT Security ([wot-thing-description], [wot-security])

3. Base IRI

A base IRI can be defined. This IRI will be used for the creation of the IRIs of the term maps and sources of the [R2]RML rules.

A base IRI can be added by adding key base with as value the IRI itself to the root of the document. In the following example the base IRI is set to http://mybaseiri.com#.
Example 1: base IRI

base: http://mybaseiri.com#

4. Prefixes and namespaces

A set of prefixes and namespaces are predefined by default in every YARRRML document. There are the same as the predefined prefixes for RDFa.

Custom prefixes can be added by adding the collection prefixes to the root of the document. Each combination of a prefix and namespace is added to this collection as a key-value pair. In the following example two prefixes are defined: ex and test.
Example 2: custom prefixes

prefixes:
  ex: http://www.example.com
  test: http://www.test.com

5. Authors

The authors of the YARRRML rules can be added via the key authors. The value is an array with an object for each author. Each author can have the following keys:

name
    the name of the author
email
    the email of the author
website
    the website of the author

In the following example two authors are defined.

    YARRRML
    RML

Example 3: mapping with multiple authors

authors:
  - name: John Doe
    email: john@doe.com
  - name: Jane Doe
    website: https://janedoe.com

A string template exists that provides a shortcut version: name <email> (website). In the following example the same two authors are defined.

    YARRRML
    RML

Example 5: mapping with multiple authors

authors:
  - John Doe <john@doe.com>
  - Jane Doe (https://janedoe.com)

In the case that authors have a WebID, it can be used instead of providing the name, email and so on. In the following example the same two authors are added via their WebIDs.

    YARRRML
    RML

Example 7: mapping with multiple authors

authors:
  - http://johndoe.com/#me
  - http://janedoe.com/#me

In all the above cases when there is only author, an array is not needed. In the following example one author is defined.

    YARRRML
    RML

Example 9: mapping with multiple authors

authors: John Doe <john@doe.com>

6. Template

A template contains 0 or more constant strings and 0 or more references to data in a data. References are prefixed with $( and suffixed with ). For example, foo is a template with one constant string. $(id) is a template with one reference to id. foo-$(id) is a template with one constant string foo- and one reference to id.
7. Data sources

The data sources are defined in the sources collection in the root of the document. Each source is added to this collection via a key-value pair. The key has to be unique for every source. The value is a collection with the keys described below.
7.1 Keys

type
    Type of the data source.
    Required profiles: RML.
    Datatype: string. 
access
    Local or remote location of the data source.
    Required profiles: RML.
    Datatype: string. 
credentials
    Credentials required to access the data source.
    Required profiles: RML.
    Datatype: collection. 
queryFormulation
    Query formulation used to query the data source.
    Required profiles: RML or R2RML.
    Datatype: string. 
query
    Query to execute on the data source to retrieve the desired data.
    Required profiles: RML or R2RML.
    Datatype: string. 
encoding
    Encoding used by the data.
    Required profiles: RML and CSVW.
    Datatype: string. 
delimiter
    Delimiter to separate fields in a record.
    Required profiles: RML and CSVW.
    Datatype: string. 
contentType
    Content type to expect expressed as MIME types.
    Required profiles: RML and WOT.
    Datatype: string. 
operationType
    Indicates the operation type of the Web of Things description.
    Required profiles: RML and WOT.
    Datatype: string. 
referenceFormulation
    Reference formulation used to access the data retrieved from the data source.
    Required profiles: RML.
    Datatype: string. 
iterator
    Path to the records over which to iterate.
    Required profiles: RML.
    Datatype: string. 


7.2 Type

This key's value describes what type of data source is used, so that the correct way of connecting to the data source can be determined. By default a local file is assumed when the access value is a path such as file.json. The value of type is then implicitly localfile. By default a remote file is assumed and retrieved via an HTTP GET when a URL is given such as http://example.org/file.json. The value of type is then implicitly remotefile. The following values are supported:
Data source type	Value	Required profiles
Oracle Database	oracle	RML and D2RQ
MySQL	mysql	RML and D2RQ
HSQLDB	hsql	RML and D2RQ
PostgreSQL	postgresql	RML and D2RQ
IBM DB2	db2	RML and D2RQ
IBM Informix	informix	RML and D2RQ
Ingres	ingres	RML and D2RQ
SAP Adaptive Server Enterprise	sapase	RML and D2RQ
SAP SQL Anywhere	sapsqlanywhere	RML and D2RQ
Firebird	firebird	RML and D2RQ
Microsoft SQL Server	mssqlserver	RML and D2RQ
Virtuoso	virtuoso	RML and D2RQ
Web of Things	wot	RML and WOT
SPARQL endpoint	sparql	RML and SD
Local file	localfile	RML
Remote file	remotefile	RML
Note

R2RML rules do not include this information: it is supplied directly to the used R2RML processor. Also, it does not support SPARQL endpoints, local files, and remote files.
7.3 Access

This key's value describes where the data source can be accessed. Examples are file.json and http://example.org/my/db.
7.4 Query formulation

Query formulations define what type of query is used query to a data source. This key's supported values are the same as the values for the type, together with the additional values below. Therefore, if only a type is provided the query formulation is implicitly the same. But if you want for example to use a MySQL query with an Oracle Database, then you need to specify both the type and the query formulation.

In the case of SPARQL endpoints, defined by the value sparql for type, the query formulation is by default sparql11: the data sources are queried via a SPARQL 1.1 query.
Query formulation	Value	Required profiles
SPARQL 1.1 query (default for SPARQL endpoint)	sparql11	RML and SD
SQL:2008	sql2008	RML and D2RQ, or R2RML
SQL:2011	sql2011	RML and D2RQ, or R2RML
SQL:2016	sql2016	RML and D2RQ, or R2RML
7.5 Query

This key's value is a query that conforms the selected query formulation. For example, if the query formulation is mysql, then the value of query needs to be a valid MySQL query.
7.6 Reference formulation

Reference formulations define how to access the data retrieved from the data source. For example, this retrieved data can be query results coming from a database or a JSON file on the local file system. The value of this key is a string. This key's supported values are.
Reference formulation	Value	Required profiles
CSV (tables with columns and rows)	csv	RML
JSONPath	jsonpath	RML
XPath	xpath	RML
XQuery	xquery	RML
7.7 Iterator

This key's value defines what records are processed. It has to conform to the selected reference formulation.

Consider the following JSON example with an array of two people. One person is one record.

{
  "people": [
    {...},
    {...}
  ]
}
        

To iterate over all the people, the iterator is $.people[*] when using jsonpath as a reference formulation. If no iterator is provided, it is unclear what the records are.
7.8 Delimiter

This key's value defines the delimiter when working with CSV files. The default is ,.
7.9 Encoding

This key's value defines the encoding of the retrieved data. The default is utf-8.
7.10 Credentials

Credentials are provided when accessing a data source requires authentication. This key's value is a collection with the keys described below.

username
    User name required to access the data source.
    Required profiles: RML and D2RQ. 
password
    Password required to access the data source.
    Required profiles: RML and D2RQ. 

7.11 Content type

This key's value defines the content type of the retrieved data with a MIME type.
7.12 Operation type

This key's value defines the operation type for the Web of Things description.
Operation	Value	Operation type
Retrieve data from Web API or stream	read	td:readproperty
Push data to Web API or stream	write	td:writeproperty
7.13 Security

Web of Things Security description to describe how authentication should be performed againast a Web API or stream when accessing its data.
Security	Value	Web of Things Security scheme
Security through API key	apikey	wotsec:APISecurityScheme

type
    Security scheme to apply.
    Required profiles: RML and WOT.
in
    Where to store the security information when performing authentication against a Web API or stream.
    Required profiles: RML and WOT.
name
    Name of the property holding the private security information such as API key.
    Required profiles: RML and WOT.
value
    Value of the property holding the private security information such as API key.
    Required profiles: RML and WOT.

7.14 Query formulation vs reference formulation
Sequence diagram showing difference between query and reference formulation

In the figure above, you find a sequence diagram showing at what point the query and query formulation are used and a what point the iterator and reference formulation are used. The component "Processor" represents the software application that executes the converted YARRRML rules, e.g., RML rules. For clarity, this conversion is not included in the figure. The processor gets the type and access from the YARRRML rules. It uses this information to create a connection with the data source. Next, the processor gets the query formulation and query. It uses this information to query the desired data from the data source, making use of the earlier created connection. Once the data is retrieved the connection is closed. The processor gets the reference formulation and iterator. It uses this information to iterate over the retrieved data.
Sequence diagram showing difference between query and reference formulation for a SPARQL endpoint

In the figure above, you find a sequence diagram showing an example of the use of query, query formulation, iterator, and reference formulation. The data source is a SPARQL endpoint, available at http://example.org/sparql, which is queried using a SPARQL 1.1 query. The query formulation is sparql11 and the query is SELECT * WHERE{?s ?p ?o} The result is an XML document which is iterated upon using the iterator /sparql/results/result that conforms to the XPath specification.
7.15 Examples

In the following example a single data source is defined person-source.

    YARRRML
    RML

Example 11: one data source

sources:
  person-source:
    access: data/person.json
    referenceFormulation: jsonpath
    iterator: $

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 13: one data source using shortcuts

sources:
  person-source: [data/person.json~jsonpath, $]

The collection is replaced with an array where the first element contains the value for access appended with the ~ and the value for referenceFormulation, and the second element contains the iterator.

The following mapping access a SQL database and select the required data via a query.

    YARRRML
    RML

Example 15: mapping with database as source

mapping:
  person:
    sources:
      access: http://localhost/example
      type: mysql
      credentials:
        username: root
        password: root
      queryFormulation: sql2008
      query: |
        SELECT DEPTNO, DNAME, LOC,
        (SELECT COUNT(*) FROM EMP WHERE EMP.DEPTNO=DEPT.DEPTNO) AS STAFF
        FROM DEPT;
      referenceFormulation: csv

8. Targets
8.1 Keys

type
    Type of the target.
    Required profiles: RMLT.
    Datatype: string. 
access
    Local or remote location of the target.
    Required profiles: RMLT.
    Datatype: string. 
serialization
    Serialization format to use when exporting to the target.
    Required profiles: RMLT and FORMATS.
    Datatype: string. 
ompression
    Compression algorithm to use when exporting to the target.
    Required profiles: RMLT and COMP.
    Datatype: string. 

8.2 Type

This key's value describes what type of target is used, so that the correct way of accessing to the target can be determined. By default a local file is assumed when the access value is a path such as file.nq. The value of type is then implicitly localfile. The following values are supported:
Target type	Value	Required profiles
SPARQL endpoint	sparql	RML, RMLT and SD
Local file	localfile	RML, RMLT and VOID/DCAT
8.3 Access

This key's value describes where the target can be accessed. Example: file.nq.
8.4 Serialization

This key's value is the serialization format that should be used to serialize the RDF when exporting to the target. By default, the serialization format is N-Quads [DataIO]. The supported serialization formats are listed by the W3C Formats namespace.
Serialization format	Value
JSON-LD	jsonld
N3	n3
N-Triples	ntriples
N-Quads	nquads
LD Patch	ldpatch
microdata	microdata
OWL XML Serialization	owlxml
OWL Functional Syntax	owlfunctional
OWL Manchester Syntax	owlmanchester
POWDER	powder
POWDER-S	powder-s
PROV-N	prov-n
PROV-XML	prov-xml
RDFa	rdfa
RDF/JSON	rdfjson
RDF/XML	rdfxml
RIF XML Syntax	rifxml
SPARQL Results in XML	sparqlxml
SPARQL Results in JSON	sparqljson
SPARQL Results in CSV	sparqlcsv
SPARQL Results in TSV	sparqltsv
Turtle	turtle
TriG	trig
8.5 Compression

Compression defines which compression algorithm should be applied when exporting to a target. By default, no compression algorithm is applied [DataIO]. The supported compression algorithms are listed by the Compression namespace.
Compression algorithm	Value
GZip	gzip
Zip	zip
TarGZip	targzip
TarXz	tarxz
8.6 Examples

In the following example a single target is defined person-target.

    YARRRML
    RML

Example 17: one target

targets:
  person-target:
    access: data/dump.ttl.gz
    type: void
    serialization: turtle
    compression: gzip

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 19: one target using shortcuts

targets:
  person-target: [data/dump.ttl.gz~void, turtle, gzip]

The collection is replaced with an array where the first element contains the value for access appended with the ~ and the value for type, the second element contains serialization format, and the third element contains the compression algorithm. The serialization format and compression algorithm are not required. By default N-Quads is used a serialization format and no compression is applied.

The following mapping access a SPARQL endpoint as target using SPARQL UPDATE queries:

    YARRRML
    RML

Example 21: mapping with SPARQL endpoint as target

mapping:
  person:
    subjects:
      - value: http://example.org/{id}
        targets:
          access: http://localhost/sparql
          type: sparql

9. Mappings

The mappings collection contains all the mappings of the document. Each mapping is added to this collection via key-value pair. The key is unique for each mapping. The value is collection containing rules to generate the subjects, predicates, and objects. In the following example two mappings are defined: person and project.

    YARRRML
    RML

Example 23: two mappings

mappings:
  person: ...
  project: ...

9.1 Data sources

Besides defining data sources at the root of the document, data sources can also be defined inside a mapping via the collection sources. However, no unique key is specified for a source, and, thus, it cannot be referred to from other mappings. The key-value to add to a source are the same when defining sources at the root of the document. In the following example the mapping person has one source.

    YARRRML
    RML

Example 25: mapping with one data source

mapping:
  person:
    sources:
      access: data/person.json
      referenceFormulation: jsonpath
      iterator: $

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 27: mapping with one data source using shortcuts

mapping:
  person:
    sources: 
      - [data/person.json~jsonpath, $]

In case a mapping needs to be applied to multiple data sources, multiple sources can be added to the scources collection. In the following example the person mapping has two data sources.

    YARRRML
    RML

Example 29: mapping with two data sources

mapping:
  person:
    sources:
      - access: data/person.json
        referenceFormulation: jsonpath
        iterator: $
      - access: data/person2.json
        referenceFormulation: jsonpath
        iterator: "$.persons[*]"

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 31: mapping with two data sources using shortcuts

mapping:
  person:
    sources:
      - [data/person.json~jsonpath, $]
      - [data/person2.json~jsonpath, "$.persons[*]"]

If you describe a data source outside of the mappings, you can include via their unique key.

    YARRRML
    RML

Example 33: mapping with one data sources

sources:
  person-source:
    access: data/person.json
    referenceFormulation: jsonpath
    iterator: $

mapping:
  person:
    sources: person-source

Multiple sources can be used by using an array of source keys as value for the key sources.

    YARRRML
    RML

Example 35: mapping with two data sources

sources:
  person-source:
    access: data/person.json
    referenceFormulation: jsonpath
    iterator: $
  person-source2:
    access: data/person2.json
    referenceFormulation: jsonpath
    iterator: "$.person[*]"

mapping:
  person:
    sources:
      - person-source
      - person-source2

A combination of both sources defined outside and inside a mapping is possible. 


Example 37: mapping with two data sources

sources:
  person-source:
    access: data/person.json
    referenceFormulation: jsonpath
    iterator: $

mapping:
  person:
    sources:
     - person-source
     - access: data/person2.json
       referenceFormulation: jsonpath
       iterator: "$.persons[*]"

9.2 Targets

Besides defining targets at the root of the document, targets can also be defined inside a mapping via the collection targets. However, no unique key is specified for a target, and, thus, it cannot be referred to from other mappings. The key-value to add to a target are the same when defining targets at the root of the document. In the following example the mapping person has one target.

    YARRRML
    RML

Example 39: mapping with one target

mapping:
  person:
    subjects:
      - value: "http://example.org/{id}"
        targets:
          access: data/dump.ttl.gz
          type: void
          serialization: turtle
          compression: gzip

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 41: mapping with one target using shortcuts

mapping:
  person:
    subjects:
      - value: "http://example.org/{id}"
        targets:
          - ["data/dump.ttl.gz~void", "turtle", "gzip"]

In case the output of a mapping needs to be exported to multiple targets, multiple targets can be added to the targets collection. In the following example the person mapping has two data sources.

    YARRRML
    RML

Example 43: mapping with two targets for subject

mapping:
  person:
    subjects:
      - value: "http://example.org/{id}"
        targets:
          - access: data/dump1.nq
            type: void
          - access: data/dump2.nq
            type: void

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 45: mapping with two targets for subject using shortcuts

mapping:
  person:
    subjects:
      - value: "http://example.org/{id}"
        targets:
          - ["data/dump1.nq~void"]
          - ["data/dump2.nq~void"]

If you describe a target outside of the mappings, you can include via their unique key.

    YARRRML
    RML

Example 47: mapping with one target for subject

targets:
  person-target:
    access: data/dump.jsonld.gz
    type: dcat
    serialization: jsonld
    compression: gzip

mapping:
  person:
    subjects:
      - value: "http://example.org/{id}"
        targets: person-target

Multiple targets can be used by using an array of target keys as value for the key targets.

    YARRRML
    RML

Example 49: mapping with two targets for subject

targets:
  person-target1:
    access: data/dump.jsonld.gz
    type: dcat
    serialization: jsonld
    compression: gzip
  person-target2:
    access: data/dump2.rdf
    type: void
    serialization: rdfxml

mapping:
  person:
    subjects:
      - value: "http://example.org/{id}"
        targets:
          - person-target1
          - person-target2

A combination of both targets defined outside and inside a mapping is possible.

    YARRRML
    RML

Example 51: mapping with two targets for subject

targets:
  person-target:
    access: data/dump1.nq

mapping:
  person:
    subjects:
      - value: "http://example.org/{id}"
        targets: 
          - person-target
          - access: data/dump2.nq

9.3 Subjects

For every triple is required to define whether a IRI or blank node needs to used. This information is added to a mapping via the collection subjects. In the case of an IRI, this collection contains 0 or more templates that specify the IRI. In the case of a blank node, this collection is set to null or is not specified at all. In the following example the mapping person generate IRI for the subjects based on the template http://wwww.example.com/person/$(id).

    YARRRML
    RML

Example 53: mapping with one subject

mappings:
  person:
    subjects: http://wwww.example.com/person/$(id)

It is also possible to specify multiple subjects. In this case an array of templates is used. In the following example the mapping person generate subjects based on the templates http://wwww.example.com/person/$(id) and http://www.test.com/$(firstname).

    YARRRML
    RML

Example 55: mapping with two subjects

mappings:
  person:
    subjects: [http://wwww.example.com/person/$(id), http://www.test.com/$(firstname)]

It is possible to apply functions on subjects.
9.4 Predicates and objects
In the following example the mapping person generates combinations of predicates and objects, where the predicate is foaf:firstName and the object is the firstname of each person.

    YARRRML
    RML

Example 57: mapping with one predicate and object

mappings:
  person:
    predicateobjects:
      - predicates: foaf:firstName
        objects: $(firstname)

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 59: mapping with one predicate and object using shortcuts

mappings:
  person:
    predicateobjects:
      - [foaf:firstName, $(firstname)]

It is possible to specify multiple predicates and objects. In this case an array of templates is used.

    YARRRML
    RML

Example 61: mapping with two predicates and objects

mappings:
  person:
    predicateobjects:
      - predicates: [foaf:name, rdfs:label]
        objects: [$(firstname), $(lastname)]

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 63: mapping with two predicates and objects using shortcuts

mappings:
  person:
    predicateobjects:
      - [[foaf:name, rdfs:label], [$(firstname), $(lastname)]]

    YARRRML
    RML

Example 65: mapping with object that generates an IRI

mappings:
  person:
    predicateobjects:
      - predicates: foaf:knows
        objects:
          value: $(colleague)
          type: iri

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 67: mapping with object that generates an IRI using shortcuts

mappings:
  person:
    predicateobjects:
      - [[foaf:knows, rdfs:label], $(colleague)~iri]

The inverse predicate can also be added. This is only valid when the object is an IRI or a blank node.
Example 69: mapping with one inverse predicate

mappings:
  work:
    predicateobjects:
      - predicates: ex:createdBy
        inversepredicates: ex:created
        objects: $(foafprofile)
        type: iri

9.5 Datatypes

    YARRRML
    RML

Example 70: mapping with one datatype

mappings:
  person:
    predicateobjects:
      - predicates: foaf:firstName
        objects:
          value: $(firstname)
          datatype: xsd:string

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 72: mapping with one datatype using shortcuts

mappings:
  person:
    predicateobjects:
      - [foaf:firstName, $(firstname), xsd:string]

    YARRRML
    RML

Example 74: mapping with two datatypes

mappings:
  person:
    predicateobjects:
      - predicates: foaf:name
        objects:
          - value: $(firstname)
            datatype: ex:string
          - value: $(lastname)
            datatype: ex:anotherString
      - predicates: rdfs:label
        objects:
          - value: $(firstname)
            datatype: ex:string
          - value: $(lastname)
            datatype: ex:anotherString

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 76: mapping with two datatypes using shortcuts

mappings:
  person:
    predicateobjects:
      - predicates: [foaf:name, rdfs:label]
        objects: [[$(firstname), ex:string], [$(lastname), ex:anotherString]]

The datatype can be also a data reference

    YARRRML
    RML

Example 78: mapping with one reference datatype

mappings:
  person:
    predicateobjects:
      - predicates: foaf:firstName
        objects:
          value: $(firstname)
          datatype: $(my_datatype)

9.6 Languages

    YARRRML
    RML

Example 80: mapping with one language

mappings:
  person:
    predicateobjects:
      - predicates: foaf:firstName
        objects:
          value: $(firstname)
          language: en

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 82: mapping with one language using shortcuts

mappings:
  person:
    predicateobjects:
      - [foaf:firstName, $(firstname), en~lang]

    YARRRML
    RML

Example 84: mapping with two languages

mappings:
  person:
    predicateobjects:
      - predicates: foaf:name
        objects:
          - value: $(firstname)
            language: en
          - value: $(lastname)
            language: nl

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 86: mapping with two languages using shortcuts

mappings:
  person:
    predicateobjects:
      - predicates: [foaf:name, rdfs:label]
        objects: [[$(firstname), en~lang], [$(lastname), nl~lang]]

The language can be also a data reference

    YARRRML
    RML

Example 88: mapping with one reference language

mappings:
  person:
    predicateobjects:
      - predicates: foaf:firstName
        objects:
          value: $(firstname)
          language: $(my_language)

9.7 Referring to other mappings

In certain use cases triples need to be generated between the records of two mappings. For example, in the following example we have two mappings: persons and projects. In the existing data there is for every person a field projectID referring to the project on which the person is working. Therefore, we want to generate triples between every person and his/her project. The objects collection has an object with the key mapping. The value of this key refers to the mapping that provides the IRIs that will serve as object for the predicate-object combination. Furthermore, a condition is added, so that only persons and projects are linked when they are actually related, based on the projectID of the person and the ID of the project. Note that a condition is not required. But when a condition is used an extra value can be given to a parameter of a function. This is either s or o. s means that the value of the parameter is coming from the subject of the relationship, while o means that the value is coming from the object of the relationship. The default value is s. In this example it would result in relationships between every person and their projects.

    YARRRML
    RML

Example 90: interlinking two mappings

mappings:
  person:
    subjects: http://example.com/person/$(ID)
    predicateobjects:
      - predicates: foaf:worksFor
        objects:
        - mapping: project
          condition:
            function: equal
            parameters:
              - [str1, $(projectID), s]
              - [str2, $(ID), o]
  project:
    subjects: http://example.com/project/$(ID)

9.8 Graphs

9.8.1 All triples

    YARRRML
    RML

Example 92: mapping with graph for all triples

mappings:
  person:
    graphs: ex:myGraph

9.8.2 All triples with a specific predicate and object

    YARRRML
    RML

Example 94: mapping with graph for all triples with a specific predicate and object

mappings:
  person:
    predicateobjects:
     - predicates: foaf:firstName
       objects: $(firstname)
       graphs: ex:myGraph

10. Functions
Functions can be added to subjects, predicates, and objects.

    YARRRML
    RML

Example 96: mapping with function on firstname

mappings:
  person:
    predicateobjects:
     - predicates: foaf:firstName
       objects:
        - function: ex:toLowerCase
          parameters:
           - parameter: ex:input
             value: $(firstname)

A shortcut version of this example looks as follows.

    YARRRML
    RML

Example 98: mapping with function on firstname using shortcuts

mappings:
  person:
    predicateobjects:
     - predicates: foaf:firstName
       objects:
        - function: ex:toLowerCase
          parameters:
           - [ex:input, $(firstname)]

Datatypes can also be assigned to the results of functions.

    YARRRML
    RML

Example 100: mapping with function on age and setting datatype to integer

mappings:
  person:
    predicateobjects:
     - predicates: ex:age
       objects:
        - function: ex:double
          parameters:
           - [ex:input, $(age)]
          datatype: xsd:integer

It possible to combine multiple functions, i.e., the value of a parameter of a function is the result of another function.

    YARRRML
    RML

Example 102: mapping with multiple functions

mappings:
  person:
    predicateobjects:
     - predicates: schema:name
       objects:
        - function: ex:escape
          parameters:
           - parameter: ex:valueParameter
             value:
               function: ex:toUpperCase
               parameters:
                 - [ex:valueParameter, $(name)]
           - [ex:modeParameter, html]

Additionally, it is possible to combine the function and its parameters in one line. The function is followed by brackets ((...)), every parameter-value pair is separated by a comma (,), and parameters are separated from their value by an equal sign (=).

    YARRRML
    RML

Example 104: mapping with function on firstname using one line

mappings:
  person:
    predicateobjects:
     - predicates: foaf:firstName
       objects:
        - function: ex:toLowerCase(ex:input = $(firstname))

Note that it is possible to exclude the prefix of the parameters if it is the same as the prefix of the function:

    YARRRML
    RML

Example 106: mapping with function on firstname using one line without prefix

mappings:
  person:
    predicateobjects:
     - predicates: foaf:firstName
       objects:
        - function: ex:toLowerCase(input = $(firstname))

11. Conditions

A subject or predicate-object combination is in certain cases only generated when a condition is fulfilled. In the following example, the predicate-object is only generated when the firstname is valid.
Example 108: mapping with condition on predicate object

mappings:
  person:
    predicateobjects:
     - predicates: foaf:firstName
       objects: $(firstname)
       condition:
        function: ex:isValid
        parameters:
         - [ex:input, $(firstname)]

In the following example, the mapping is only executed for every record that has set its ID.
Example 109: mapping with condition

mappings:
  person:
    subjects: http://example.com/{ID}
    condition:
        function: ex:isSet
        parameters:
         - [ex:input, $(ID)]
    predicateobjects:
     - predicates: foaf:firstName
       objects: $(firstname)

12. RDF-Star
An YARRRML-star mapping defines a mapping from any data in a structured source format to RDF-star. It enables the generation of quoted triples in the position of subject and/or object. Quoted triples can be created by referencing the mapping identifier using the quoted keyword. It is also possible to create non-asserted quoted triples using the quotedNonAsserted keyword.
12.1 Keys

quoted
    Quoted mapping.
    Required profiles: RMLStar.
    Datatype: Mapping reference. 
quotedNonAsserted
    Non-asserted quoted mapping.
    Required profiles: RMLStar.
    Datatype: Mapping reference. 

12.2 Examples

    YARRRML
    RML

Example 110: Quoted mapping in object

mappings:
  person:
    subject: http://example.org/person/$(Name)
    predicateobjects:
     - predicates: ex:confirms
       objects:
        - quoted: student
  student:
    subject: http://example.org/student/$(Student)
    predicateobjects:
     - [a, ex:Student]

Quoted mappings can be also defined in subjects

    YARRRML
    RML

Example 112: Quoted mapping in subject

mappings:
  person:
    subject:
     - quoted: student
    predicateobjects:
     - predicates: ex:accordingTo
       objects: http://example.org/person/$(Name)
  student:
    subject: http://example.org/student/$(Student)
    predicateobjects:
     - [a, ex:Student]

Quoted triples can be non-asserted in the RDF-star graph using the QuotedNonAsserted key

    YARRRML
    RML

Example 114: Quoted non-asserted mapping in object

mappings:
  person:
    subject: http://example.org/person/$(Name)
    predicateobjects:
     - predicates: ex:confirms
       objects:
        - quotedNonAsserted: student
  student:
    subject: http://example.org/student/$(Student)
    predicateobjects:
     - [a, ex:Student]

Joins can also be defined in the same way with quoted and quotedNonAsserted

    YARRRML
    RML

Example 116: Join in quoted mapping in subject

mappings:
  person:
    subject:
     - quoted: student
       condition:
         function: equal
         parameters:
           - [str1, $(condition1)]
           - [str2, $(condition2)]
    predicateobjects:
     - predicates: foaf:firstName
       objects: $(Name)
  student:
    subject: http://example.org/student/{Student}
    predicateobjects:
     - [a, ex:Student]

Quoted and QuotedNonAsserted joins can also be defined inline wih shortcut

    YARRRML
    RML

Example 118: Join in quoted mapping in subject inline

mappings:
  person:
    subject:
     - function: join(quoted=student, equal(str1=$(condition1), str2=$(condition2)))
    predicateobjects:
     - predicates: foaf:firstName
       objects: $(Name)
  student:
    subject: http://example.org/student/$(Student)
    predicateobjects:
     - [a, ex:Student]

13. External references

It is possible to define references that do not refer to data in a data source. These references are called "external references". They are provided via the external key that has as value a list of references with their values. In the following example two external references are defined: name and city with as values John and Ghent.
Example 120: defining external references

external:
  name: John
  city: Ghent

mappings:
  person:
    subjects: http://example.org/$(id)
    po:
      - [ex:name, $(_name)]
      - [ex:firstName, $(_name)]
      - [ex:city, $(_city)]

Replacing the external references with their actual values results in the following.
Example 121: external references are filled in

mappings:
  person:
    s: http://example.org/$(id)
    po:
      - [ex:name, John]
      - [ex:firstName, John]
      - [ex:city, Ghent]

If the value for an external reference is not provided, then the reference is not replaced. In the following example no value is provided for name.
Example 122: defining some external references

external:
  city: Ghent

mappings:
  person:
    subjects: http://example.org/$(id)
    po:
      - [ex:name, $(_name)]
      - [ex:firstName, $(_name)]
      - [ex:city, $(_city)]

Replacing the remaining external reference with its actual value results in the following.
Example 123: some external references are filled in

mappings:
  person:
    subjects: http://example.org/$(id)
    po:
      - [ex:name, $(_name)]
      - [ex:firstName, $(_name)]
      - [ex:city, Ghent]

$(_name) is not replaced.

If you want use a reference as both a regular and an external reference, you add a \ before the regular reference. In the following example $(_name) is an external reference and $(\_name) is a regular reference.
Example 124: defining both regular and external references

external:
  name: John

mappings:
  person:
    subjects: http://example.org/$(id)
    po:
      - [ex:name, $(_name)]
      - [ex:firstName, $(\_name)]

Replacing the external reference with its actual value results in the following.
Example 125: external reference is filled in, ignoring reular reference

mappings:
  person:
    subjects: http://example.org/$(id)
    po:
      - [ex:name, John]
      - [ex:firstName, $(_name)]

14. Shortcuts
14.1 Keys

    mappings: mapping, m
    subjects: subject, s
    predicates: predicate, p
    inversepredicates: inversepredicate, i
    objects: object, o
    predicateobjects: po
    function: fn, f
    parameters: pms
    parameter: pm
    value: v
    authors: author, a

14.2 Predicates

    http://www.w3.org/1999/02/22-rdf-syntax-ns#type: a

15. Implementations

The YARRRML Parser is a reference implementation that generates [R2]RML rules based on YARRRML. The parser's code also includes tests to validate a parser's conformance to the YARRRML specification.

YARRRML-Translator is a Python implementation that generates [R2]RML rules based on YARRRML, and vice versa. The source code includes more than 50 tests to validate a parser's conformance to the YARRRML specification.
A. References
A.1 Informative references

[csv2rdf]
    Generating RDF from Tabular Data on the Web. Jeremy Tandy; Ivan Herman; Gregg Kellogg. W3C. 17 December 2015. W3C Recommendation. URL: https://www.w3.org/TR/csv2rdf/ 
[D2RQ]
    The D2RQ Mapping Language. Richard Cyganiak; Chris Bizer; Jörg Garbers; Oliver Maresch; Christian Becker. Freie Universität Berlin - DERI. 12 March 2012. Unofficial Draft. URL: https://d2rq.org/d2rq-language 
[DataIO]
    DataIO. Dylan Van Assche; Anastasia Dimou. IDLab - imec - Ghent University. 18 May 2021. Unofficial Draft. URL: https://rml.io/specs/dataio 
[DCAT]
    Data Catalog Vocabulary (DCAT) - Version 2. W3C. 22 February 2020. W3C Recommendation. URL: https://www.w3.org/TR/vocab-dcat/ 
[FnO]
    The Function Ontology. Ben De Meester; Anastasia Dimou. IDLab - imec - Ghent University. 10 November 2021. Unofficial Draft. URL: https://fno.io/spec/ 
[R2RML]
    R2RML: RDB to RDF Mapping Language. Souripriya Das; Seema Sundara; Richard Cyganiak. W3C. 27 September 2012. W3C Recommendation. URL: https://www.w3.org/TR/r2rml/ 
[RML]
    RDF Mapping Language (RML). Anastasia Dimou; Miel Vander Sande. IDLab - imec - Ghent University. October 2020. Unofficial Draft. URL: https://rml.io/specs/rml/ 
[RMLStar]
    Star in RML. Ana Iglesias-Molina; Julián Arenas-Guerrero; Thomas Delva; David Chaves-Fraga; Anastasia Dimou. W3C CG in KGC. 05 May 2022. Unofficial Draft. URL: https://w3id.org/kg-construct/rml-star 
[RMLT]
    Target in RML. Dylan Van Assche; Anastasia Dimou. IDLab - imec - Ghent University. 18 May 2021. Unofficial Draft. URL: https://rml.io/specs/rml-target 
[sparql11-service-description]
    SPARQL 1.1 Service Description. Gregory Williams. W3C. 21 March 2013. W3C Recommendation. URL: https://www.w3.org/TR/sparql11-service-description/ 
[VoID]
    Describing Linked Datasets with the VoID Vocabulary. Keith Alexander; Richard Cyganiak; Michael Hausenblas; Jun Zhao. W3C. 3 March 2011. W3C Note. URL: https://www.w3.org/TR/void/ 
[wot-security]
    Web of Things (WoT) Security and Privacy Guidelines. Elena Reshetova; Michael McCool. W3C. 6 November 2019. W3C Note. URL: https://www.w3.org/TR/wot-security/ 
[wot-thing-description]
    Web of Things (WoT) Thing Description. Sebastian Käbisch; Takuki Kamiya; Michael McCool; Victor Charpenay; Matthias Kovatsch. W3C. 9 April 2020. W3C Recommendation. URL: https://www.w3.org/TR/wot-thing-description/ 
[YAML]
    YAML Ain’t Markup Language (YAML™) Version 1.2. Oren Ben-Kiki; Clark Evans; Ingy döt Net.1 October 2009. URL: http://yaml.org/spec/1.2/spec.html 