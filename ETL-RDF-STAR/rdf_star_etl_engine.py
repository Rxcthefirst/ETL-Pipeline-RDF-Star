"""
ETL Engine for YARRRML-star to RDF-star using polars and pyoxigraph
====================================================================

⚠️  DEPRECATION NOTICE: This is the old hardcoded version.
    Please use rdf_star_etl_engine_dynamic.py instead, which:
    - Dynamically parses YARRRML mappings (no hardcoded properties)
    - Supports multiple CSV sources
    - Handles RDF-star quoted triples
    - Is fully configurable via YAML

This script follwos the eEXACT same reification pattern as rdf_star_transform_v2.py:
- Each dataset is an owl:NamedIndividual
- Each dataset is typed as meta:Dataset (linking to ontology concept)
- Every triple gets rdf:reifies provenance annotations
- Uses BlankNode reifier with full provenance chain

This enables AI grounding by linking instance data to ontology definitions, and allows for rich metadata on every triple.
"""
import yaml
import polars as pl
import os
import re
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from pyoxigraph import (
    Store, Quad, Triple, NamedNode, BlankNode, Literal, RdfFormat
)

# =========================================================================
# Namespace URIs - match rdf_star_transform_v2.py for consistency
# =========================================================================
META = "http://models.example.org/semantics/meta/"
EX = "http://example.org/ontology/"
PROV = "http://www.w3.org/ns/prov#"
DQV = "http://www.w3.org/ns/dqv#"
DCT = "http://purl.org/dc/terms/"
DCAT = "http://www.w3.org/ns/dcat#"
RDFSTAR = "http://example.org/rdf-star/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
XSD = "http://www.w3.org/2001/XMLSchema#"
OWL = "http://www.w3.org/2002/07/owl#"

def sanitize_uri(value):
    """Sanitize a string for use in a URI."""
    if value is None:
        return "unknown"
    sanitized = re.sub(r'[^\w\-]', '_', str(value))
    return sanitized if sanitized else "unknown"


def add_provenance_annotations(store, triple, source_config, generation_time):
    """
    Add RDF-Star provenance annotations using rdf:reifies pattern with BlankNode reifier.

    This is the EXACT same pattern used in rdf_star_transform_v2.py:
    - Create a BlankNode as the reifier for the triple
    - Link it to the triple via rdf:reifies
    - Add provenance properties to the reifier
    :param store:
    :param triple:
    :param source_config:
    :param generation_time:
    :return:
    """
    # Create a blank node as the reifier for this triple's annotations
    reifier = BlankNode()

    # Link the reifier to the triple via rdf_reifies
    store.add(Quad(
        reifier,
        NamedNode(RDF + "reifies"),
        triple
    ))

    # prov:wasDerivedFrom - source dataset URI
    store.add(Quad(
        reifier,
        NamedNode(PROV + "wasDerivedFrom"),
        NamedNode(source_config["source_uri"])
    ))

    # prov:generatedAtTime - timestamp of generation
    store.add(Quad(
        reifier,
        NamedNode(PROV + "generatedAtTime"),
        Literal(generation_time.isoformat(), datatype=NamedNode(XSD + "dateTime"))
    ))

    # prov:wasAttributedTo - publisher
    store.add(Quad(
        reifier,
        NamedNode(PROV + "wasAttributedTo"),
        NamedNode(source_config["publisher_uri"])
    ))

    # dct:source - source file identifier
    store.add(Quad(
        reifier,
        NamedNode(DCT + "source"),
        Literal(source_config["source_id"])
    ))

    # rdfstar:confidence - confidence score
    store.add(Quad(
        reifier,
        NamedNode(RDFSTAR + "confidence"),
        Literal(source_config["confidence"], datatype=NamedNode(XSD + "decimal"))
    ))

    #rdfstar:trustLevel
    store.add(Quad(
        reifier,
        NamedNode(RDFSTAR + "trustLevel"),
        Literal(source_config["trust_level"])
    ))

    # rdfstar:verificationStatus
    store.add(Quad(
        reifier,
        NamedNode(RDFSTAR + "verificationStatus"),
        Literal("unverified")
    ))

    return 7  # Number of provenance quads added per triple


def add_dataset_metadata(store, source_config, generation_time):
    """Add DCAT dataset metadata - same as rdf_star_transform_v2.py"""
    dataset = NamedNode(source_config["source_uri"])

    store.add(Quad(
        dataset,
        NamedNode(RDF + "type"),
        NamedNode(OWL + "Dataset")
    ))
    store.add(Quad(
        dataset,
        NamedNode(DCT + "title"),
        Literal(source_config["source_name"])
    ))
    store.add(Quad(
        dataset,
        NamedNode(DCT + "description"),
        Literal(source_config["description"])
    ))
    store.add(Quad(
        dataset,
        NamedNode(DCT + "publisher"),
        NamedNode(source_config["publisher_uri"])
    ))
    store.add(Quad(
        dataset,
        NamedNode(DCT + "created"),
        Literal(generation_time.isoformat(), datatype=NamedNode(XSD + "dateTime"))
    ))


def build_output_with_prefixes(store):
    """Buld output content with proper prefixes - same as rdf_star_transform_v2.py"""
    prefixes = f"""@prefix rdf: <{RDF}> .
@prefix rdfs: <{RDFS}> .
@prefix xsd: <{XSD}> .
@prefix owl: <{OWL}> .
@prefix meta: <{META}> .
@prefix ex: <{EX}> .
@prefix prov: <{PROV}> .
@prefix dqv: <{DQV}> .
@prefix dct: <{DCT}> .
@prefix dcat: <{DCAT}> .
@prefix rdfstar: <{RDFSTAR}> .
"""

    # Serialize the store content
    buffer = BytesIO()
    store.dump(buffer, RdfFormat.TRIG)
    content = buffer.getvalue().decode("utf-8")

    #Remove duplicate prefixes (pyoxigraph adds them to every quad)
    lines = content.split("\n")
    filtered_lines = []
    for line in lines:
        if not (line.startswith("@prefix") or line.startswith("PREFIX")):
            filtered_lines.append(line)

    final_content = prefixes + "\n".join(filtered_lines)
    return final_content.encode("utf-8")


def main(config_path):
    generation_time = datetime.now(timezone.utc).isoformat()
    print(f"[{datetime.now()}] Starting ETL Engine (aligned with RDF-Star Transform v2 pattern)")

    # Load pipeline config
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    csv_path = config['pipeline']['input_csv']
    output_path = config['pipeline']['output_rdfstar']

    # Source configuration - matches rdf_star_transform_v2.py pattern
    source_config = {
        "source_id": "ETL-DatasetView",
        "source_name": "Dataset ETL Import",
        "source_uri": f"{EX}dataset/etl_import",
        "publisher_uri": f"{EX}organization/etl_team",
        "description": "Dataset imported via ETL engine with RDF-Star provenance annotations",
        "confidence": 0.80,
        "trust_level": "medium"
    }

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[{datetime.now()}] Created output directory: {output_dir}")

    print(f"[{datetime.now()}] Loading CSV data from: {csv_path}")

    # Loav CSV with polars for speed
    df = pl.read_csv(csv_path, ignore_errors=True, infer_schema_length=10000)
    print(f"[{datetime.now()}] CSV loaded with {df.height} rows and {df.width} columns")

    # Initialize pyoxigraph store
    store = Store()

    # Add dataset metadata (DCAT) - same as rdf_star_transform_v2.py
    add_dataset_metadata(store, source_config, generation_time)

    # Property mappings - CSV column to meta: property
    property_mappings = {
        'name': 'Name',
        'fullName': 'Full Name',
        'description': 'Description',
        'status': 'Status',
        'domain': 'Domain',
        'datasetName': 'Dataset Name',
        'dataSourceSystem': 'Data Source System',
        'datasetLayer': 'Dataset Layer',
        'confidentialityLevel': 'Confidentiality Level',
        'businessDataOwner': 'Business Data Owner',
        'technicalPOC': 'Technical POC',
        'datasetFileFormat': 'Dataset File Format',
        'datasetRefreshType': 'Dataset Refresh Type',
        'datasetRefreshFrequency': 'Dataset Refresh Frequency',
        'registeredBy': 'Registered By',
        'datasetCurator': 'Dataset Curator',
        'createdOn': 'CreatedOn',
        'lastModifiedOn': 'LastModifiedOn',
        's3BucketName': 'S3 Bucket Name',
        'databaseSchema': 'Database Schema',
        'databaseEndpoint': 'Database Endpoint',
    }

    # Process rows and generate triples
    triple_count = 0
    rdf_star_count = 0

    print(f"[{datetime.now()}] Transforming data and adding RDF-Star provenance annotations...")

    for row in df.iter_rows(named=True):
        try:
            # Get Asset Id for subject URI
            asset_id = row.get("Asset Id")
            if not asset_id:
                continue

            subj_uri = f"{EX}dataset/{sanitize_uri(asset_id)}"
            subj = NamedNode(subj_uri)

            # ==================================================
            # Triple 1: rdf:type owl:NamedIndividual
            # This marks it as an instance in the ontology, enabling AI grounding to ontology concepts
            # ==================================================
            type_individual_triple = Triple(
                subj,
                NamedNode(RDF + "type"),
                NamedNode(OWL + "NamedIndividual")
            )
            store.add(Quad(subj, NamedNode(RDF + "type"), NamedNode(OWL + "NamedIndividual")))
            triple_count += 1

            # Add provenance for this triple
            if config['pipeline']['provenance']['enable']:
                rdf_star_count += add_provenance_annotations(store, type_individual_triple, source_config, generation_time)

            # ==================================================
            # Triple 2: rdf:type meta:Dataset
            # This links the instance to the meta:Dataset concept in the ontology, enabling semantic reasoning
            # ==================================================
            type_dataset_triple = Triple(
                subj,
                NamedNode(RDF + "type"),
                NamedNode(META + "Dataset")
            )
            store.add(Quad(subj, NamedNode(RDF + "type"), NamedNode(META + "Dataset")))
            triple_count += 1

            # Add provenance for this triple
            if config['pipeline']['provenance']['enable']:
                rdf_star_count += add_provenance_annotations(store, type_dataset_triple, source_config, generation_time)

            # ==================================================
            # Property triples with provenance
            # ==================================================
            for prop_name, col_name in property_mappings.items():
                value = row.get(col_name)
                if value is not None and str(value).strip():
                    prop_triple = Triple(
                        subj,
                        NamedNode(EX + prop_name),
                        Literal(str(value))
                    )
                    store.add(Quad(subj, NamedNode(EX + prop_name), Literal(str(value))))
                    triple_count += 1

                    # Add provenance for this triple
                    if config['pipeline']['provenance']['enable']:
                        rdf_star_count += add_provenance_annotations(store, prop_triple, source_config, generation_time)
        except Exception as e:
            print(f"Error processing row with Asset Id {row.get('Asset Id')}: {e}")
            continue

    print(f"[{datetime.now()}] Transformation complete. Generated {triple_count} triples with {rdf_star_count} RDF-Star provenance annotations.")

    # Serialize to RDF-star TriG format with proper prefixes
    print(f"[{datetime.now()}] Serializing RDF-Star format to {output_path}...")

    output_content = build_output_with_prefixes(store)

    with open(output_path, "wb") as f:
        f.write(output_content)

    print(f"[{datetime.now()}] RDF-Star export complete: {output_path}")
    print(f"✓ Total triples: {triple_count}")
    print(f"✓ Total RDF-Star provenance quads: {rdf_star_count}")
    print(f"✓ Total quads in store: {len(list(store))}")

    return store

if __name__ == "__main__":
    config_file = "etl_config.yaml"
    if not os.path.exists(config_file):
        print(f"Config file not found: {config_file}")
        exit(1)

    main(config_file)

