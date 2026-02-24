# =============================================================================
# Knowledge Graph Batch Management System
# =============================================================================
#
# Manages materialized RDF data as versioned batches with:
# - Named graphs for each batch
# - Batch metadata (creation time, source, status)
# - Temporal provenance tracking
# - Batch comparison and diff capabilities
# - Point-in-time queries ("What did we know when?")
#
# =============================================================================

import os
import hashlib
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from io import BytesIO

from pyoxigraph import Store, Quad, Triple, NamedNode, BlankNode, Literal, RdfFormat


class BatchStatus(Enum):
    """Status of a batch in the system."""
    PENDING = "pending"          # Batch created but not yet loaded
    ACTIVE = "active"            # Currently active batch
    SUPERSEDED = "superseded"    # Replaced by newer batch
    ARCHIVED = "archived"        # Archived for historical reference
    DELETED = "deleted"          # Marked for deletion


@dataclass
class BatchMetadata:
    """Metadata for a single batch of materialized data."""
    batch_id: str
    batch_number: int
    created_at: datetime
    graph_uri: str
    source_mapping: str
    source_files: List[str]
    status: BatchStatus = BatchStatus.PENDING
    triple_count: int = 0
    quad_count: int = 0
    loaded_at: Optional[datetime] = None
    superseded_at: Optional[datetime] = None
    superseded_by: Optional[str] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)
    checksum: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'batch_id': self.batch_id,
            'batch_number': self.batch_number,
            'created_at': self.created_at.isoformat(),
            'graph_uri': self.graph_uri,
            'source_mapping': self.source_mapping,
            'source_files': self.source_files,
            'status': self.status.value,
            'triple_count': self.triple_count,
            'quad_count': self.quad_count,
            'loaded_at': self.loaded_at.isoformat() if self.loaded_at else None,
            'superseded_at': self.superseded_at.isoformat() if self.superseded_at else None,
            'superseded_by': self.superseded_by,
            'description': self.description,
            'tags': self.tags,
            'checksum': self.checksum
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'BatchMetadata':
        return cls(
            batch_id=d['batch_id'],
            batch_number=d['batch_number'],
            created_at=datetime.fromisoformat(d['created_at']),
            graph_uri=d['graph_uri'],
            source_mapping=d['source_mapping'],
            source_files=d['source_files'],
            status=BatchStatus(d['status']),
            triple_count=d.get('triple_count', 0),
            quad_count=d.get('quad_count', 0),
            loaded_at=datetime.fromisoformat(d['loaded_at']) if d.get('loaded_at') else None,
            superseded_at=datetime.fromisoformat(d['superseded_at']) if d.get('superseded_at') else None,
            superseded_by=d.get('superseded_by'),
            description=d.get('description', ''),
            tags=d.get('tags', []),
            checksum=d.get('checksum')
        )


@dataclass
class BatchDiff:
    """Represents the difference between two batches."""
    from_batch: str
    to_batch: str
    computed_at: datetime
    added_triples: List[str]      # Triples in to_batch but not in from_batch
    removed_triples: List[str]    # Triples in from_batch but not in to_batch
    modified_subjects: List[str]  # Subjects with changed predicates/objects
    unchanged_count: int

    @property
    def summary(self) -> Dict:
        return {
            'from_batch': self.from_batch,
            'to_batch': self.to_batch,
            'added': len(self.added_triples),
            'removed': len(self.removed_triples),
            'modified_subjects': len(self.modified_subjects),
            'unchanged': self.unchanged_count
        }


class BatchManager:
    """
    Manages batches of materialized RDF data.

    Features:
    - Create and register batches with metadata
    - Load batches into named graphs
    - Track batch lineage and supersession
    - Compare batches to see changes
    - Query point-in-time state
    - Archive and delete old batches
    """

    # Namespace prefixes
    BATCH_NS = "http://example.org/batch/"
    PROV_NS = "http://www.w3.org/ns/prov#"
    XSD_NS = "http://www.w3.org/2001/XMLSchema#"
    DCT_NS = "http://purl.org/dc/terms/"
    RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

    def __init__(self, store: Optional[Store] = None, metadata_dir: str = "batch_metadata"):
        """
        Initialize the batch manager.

        Args:
            store: PyOxigraph Store instance (creates new if None)
            metadata_dir: Directory to store batch metadata JSON files
        """
        self.store = store or Store()
        self.metadata_dir = metadata_dir
        self.batches: Dict[str, BatchMetadata] = {}

        # Ensure metadata directory exists
        os.makedirs(metadata_dir, exist_ok=True)

        # Load existing batch metadata
        self._load_metadata()

    def _load_metadata(self):
        """Load batch metadata from disk."""
        metadata_file = os.path.join(self.metadata_dir, "batches.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                data = json.load(f)
                for batch_data in data.get('batches', []):
                    batch = BatchMetadata.from_dict(batch_data)
                    self.batches[batch.batch_id] = batch

    def _save_metadata(self):
        """Save batch metadata to disk."""
        metadata_file = os.path.join(self.metadata_dir, "batches.json")
        data = {
            'version': '1.0',
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'batches': [b.to_dict() for b in self.batches.values()]
        }
        with open(metadata_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _generate_batch_id(self, batch_number: int) -> str:
        """Generate a unique batch ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"batch_{batch_number:04d}_{timestamp}"

    def _get_next_batch_number(self) -> int:
        """Get the next batch number."""
        if not self.batches:
            return 1
        return max(b.batch_number for b in self.batches.values()) + 1

    def create_batch(
        self,
        source_mapping: str,
        source_files: List[str],
        description: str = "",
        tags: List[str] = None
    ) -> BatchMetadata:
        """
        Create a new batch (without loading data yet).

        Args:
            source_mapping: Path to the YARRRML mapping file used
            source_files: List of source data files
            description: Human-readable description
            tags: Optional tags for categorization

        Returns:
            BatchMetadata for the new batch
        """
        batch_number = self._get_next_batch_number()
        batch_id = self._generate_batch_id(batch_number)
        graph_uri = f"{self.BATCH_NS}{batch_id}"

        batch = BatchMetadata(
            batch_id=batch_id,
            batch_number=batch_number,
            created_at=datetime.now(timezone.utc),
            graph_uri=graph_uri,
            source_mapping=source_mapping,
            source_files=source_files,
            status=BatchStatus.PENDING,
            description=description,
            tags=tags or []
        )

        self.batches[batch_id] = batch
        self._save_metadata()

        print(f"[BatchManager] Created batch: {batch_id}")
        print(f"  Graph URI: {graph_uri}")
        print(f"  Source: {source_mapping}")

        return batch

    def load_batch_from_file(
        self,
        batch_id: str,
        rdf_file: str,
        rdf_format: RdfFormat = RdfFormat.TRIG
    ) -> BatchMetadata:
        """
        Load RDF data from a file into a batch's named graph.

        Args:
            batch_id: ID of the batch to load into
            rdf_file: Path to the RDF file
            rdf_format: Format of the RDF file

        Returns:
            Updated BatchMetadata
        """
        if batch_id not in self.batches:
            raise ValueError(f"Batch not found: {batch_id}")

        batch = self.batches[batch_id]
        graph = NamedNode(batch.graph_uri)

        print(f"[BatchManager] Loading batch {batch_id} from {rdf_file}")

        # Read file content
        with open(rdf_file, 'rb') as f:
            content = f.read()

        # Calculate checksum
        batch.checksum = hashlib.sha256(content).hexdigest()

        # Load into store
        initial_count = len(list(self.store))
        self.store.load(BytesIO(content), rdf_format, base_iri=batch.graph_uri)

        # Count quads added
        batch.quad_count = len(list(self.store)) - initial_count
        batch.loaded_at = datetime.now(timezone.utc)
        batch.status = BatchStatus.ACTIVE

        # Add batch metadata to the store
        self._add_batch_metadata_triples(batch)

        # Supersede previous active batch
        self._supersede_previous_batch(batch)

        self._save_metadata()

        print(f"  Loaded {batch.quad_count} quads")
        print(f"  Status: {batch.status.value}")

        return batch

    def load_batch_from_store(
        self,
        batch_id: str,
        source_store: Store,
        graph_uri: Optional[str] = None
    ) -> BatchMetadata:
        """
        Load quads from another store into this batch.

        Args:
            batch_id: ID of the batch to load into
            source_store: Source Store containing the quads
            graph_uri: Optional specific graph to copy (copies all if None)

        Returns:
            Updated BatchMetadata
        """
        if batch_id not in self.batches:
            raise ValueError(f"Batch not found: {batch_id}")

        batch = self.batches[batch_id]
        target_graph = NamedNode(batch.graph_uri)

        print(f"[BatchManager] Loading batch {batch_id} from store")

        quad_count = 0
        for quad in source_store:
            # Rewrite quad to use batch graph
            new_quad = Quad(
                quad.subject,
                quad.predicate,
                quad.object,
                target_graph
            )
            self.store.add(new_quad)
            quad_count += 1

        batch.quad_count = quad_count
        batch.loaded_at = datetime.now(timezone.utc)
        batch.status = BatchStatus.ACTIVE

        # Add batch metadata
        self._add_batch_metadata_triples(batch)

        # Supersede previous
        self._supersede_previous_batch(batch)

        self._save_metadata()

        print(f"  Loaded {quad_count} quads")

        return batch

    def _add_batch_metadata_triples(self, batch: BatchMetadata):
        """Add metadata triples about the batch to the store."""
        graph = NamedNode(batch.graph_uri)
        batch_node = NamedNode(batch.graph_uri)

        # Type
        self.store.add(Quad(
            batch_node,
            NamedNode(f"{self.RDF_NS}type"),
            NamedNode(f"{self.PROV_NS}Entity"),
            graph
        ))

        # Creation time
        self.store.add(Quad(
            batch_node,
            NamedNode(f"{self.PROV_NS}generatedAtTime"),
            Literal(
                batch.created_at.isoformat(),
                datatype=NamedNode(f"{self.XSD_NS}dateTime")
            ),
            graph
        ))

        # Description
        if batch.description:
            self.store.add(Quad(
                batch_node,
                NamedNode(f"{self.DCT_NS}description"),
                Literal(batch.description),
                graph
            ))

        # Source mapping
        self.store.add(Quad(
            batch_node,
            NamedNode(f"{self.PROV_NS}wasGeneratedBy"),
            Literal(batch.source_mapping),
            graph
        ))

        # Batch number
        self.store.add(Quad(
            batch_node,
            NamedNode(f"{self.BATCH_NS}batchNumber"),
            Literal(str(batch.batch_number), datatype=NamedNode(f"{self.XSD_NS}integer")),
            graph
        ))

    def _supersede_previous_batch(self, new_batch: BatchMetadata):
        """Mark previous active batch as superseded."""
        for batch_id, batch in self.batches.items():
            if batch_id != new_batch.batch_id and batch.status == BatchStatus.ACTIVE:
                batch.status = BatchStatus.SUPERSEDED
                batch.superseded_at = datetime.now(timezone.utc)
                batch.superseded_by = new_batch.batch_id
                print(f"  Superseded batch: {batch_id}")

    def get_batch(self, batch_id: str) -> Optional[BatchMetadata]:
        """Get metadata for a specific batch."""
        return self.batches.get(batch_id)

    def get_active_batch(self) -> Optional[BatchMetadata]:
        """Get the currently active batch."""
        for batch in self.batches.values():
            if batch.status == BatchStatus.ACTIVE:
                return batch
        return None

    def list_batches(
        self,
        status: Optional[BatchStatus] = None,
        limit: int = 100
    ) -> List[BatchMetadata]:
        """
        List batches, optionally filtered by status.

        Args:
            status: Optional status filter
            limit: Maximum number to return

        Returns:
            List of BatchMetadata, newest first
        """
        batches = list(self.batches.values())

        if status:
            batches = [b for b in batches if b.status == status]

        # Sort by batch number descending
        batches.sort(key=lambda b: b.batch_number, reverse=True)

        return batches[:limit]

    def compare_batches(
        self,
        from_batch_id: str,
        to_batch_id: str,
        sample_limit: int = 100
    ) -> BatchDiff:
        """
        Compare two batches and return the differences.

        Args:
            from_batch_id: Earlier batch ID
            to_batch_id: Later batch ID
            sample_limit: Max number of changed triples to include

        Returns:
            BatchDiff with the changes
        """
        from_batch = self.batches.get(from_batch_id)
        to_batch = self.batches.get(to_batch_id)

        if not from_batch or not to_batch:
            raise ValueError("Both batches must exist")

        print(f"[BatchManager] Comparing {from_batch_id} -> {to_batch_id}")

        # Get triples from each batch
        from_graph = NamedNode(from_batch.graph_uri)
        to_graph = NamedNode(to_batch.graph_uri)

        from_triples = set()
        from_subjects = set()
        for quad in self.store.quads_for_pattern(None, None, None, from_graph):
            triple_str = f"{quad.subject} {quad.predicate} {quad.object}"
            from_triples.add(triple_str)
            from_subjects.add(str(quad.subject))

        to_triples = set()
        to_subjects = set()
        for quad in self.store.quads_for_pattern(None, None, None, to_graph):
            triple_str = f"{quad.subject} {quad.predicate} {quad.object}"
            to_triples.add(triple_str)
            to_subjects.add(str(quad.subject))

        # Calculate diff
        added = to_triples - from_triples
        removed = from_triples - to_triples
        unchanged = from_triples & to_triples

        # Find modified subjects (present in both but with different triples)
        modified_subjects = []
        common_subjects = from_subjects & to_subjects
        for subj in common_subjects:
            from_subj_triples = {t for t in from_triples if t.startswith(subj)}
            to_subj_triples = {t for t in to_triples if t.startswith(subj)}
            if from_subj_triples != to_subj_triples:
                modified_subjects.append(subj)

        diff = BatchDiff(
            from_batch=from_batch_id,
            to_batch=to_batch_id,
            computed_at=datetime.now(timezone.utc),
            added_triples=list(added)[:sample_limit],
            removed_triples=list(removed)[:sample_limit],
            modified_subjects=modified_subjects[:sample_limit],
            unchanged_count=len(unchanged)
        )

        print(f"  Added: {len(added)}")
        print(f"  Removed: {len(removed)}")
        print(f"  Modified subjects: {len(modified_subjects)}")
        print(f"  Unchanged: {len(unchanged)}")

        return diff

    def get_state_at_batch(self, batch_id: str) -> Store:
        """
        Get a store containing the state at a specific batch.

        This includes all data from the batch's named graph.

        Args:
            batch_id: The batch ID to get state for

        Returns:
            New Store with just that batch's data
        """
        batch = self.batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        graph = NamedNode(batch.graph_uri)
        result_store = Store()

        for quad in self.store.quads_for_pattern(None, None, None, graph):
            result_store.add(quad)

        return result_store

    def query_at_batch(self, batch_id: str, sparql_query: str) -> Any:
        """
        Execute a SPARQL query scoped to a specific batch.

        The query is modified to use FROM <batch_graph>.

        Args:
            batch_id: Batch to query
            sparql_query: SPARQL query (SELECT or CONSTRUCT)

        Returns:
            Query results
        """
        batch = self.batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        # Inject FROM clause if not present
        if 'FROM' not in sparql_query.upper():
            # Find WHERE and insert FROM before it
            import re
            sparql_query = re.sub(
                r'(WHERE\s*\{)',
                f'FROM <{batch.graph_uri}> \\1',
                sparql_query,
                flags=re.IGNORECASE
            )

        return self.store.query(sparql_query)

    def delete_batch(self, batch_id: str, permanent: bool = False):
        """
        Delete a batch.

        Args:
            batch_id: Batch to delete
            permanent: If True, removes from store and metadata.
                      If False, just marks as DELETED.
        """
        batch = self.batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        if batch.status == BatchStatus.ACTIVE:
            raise ValueError("Cannot delete active batch. Load a new batch first.")

        print(f"[BatchManager] Deleting batch: {batch_id}")

        if permanent:
            # Remove from store
            graph = NamedNode(batch.graph_uri)
            quads_to_remove = list(self.store.quads_for_pattern(None, None, None, graph))
            for quad in quads_to_remove:
                self.store.remove(quad)

            # Remove from metadata
            del self.batches[batch_id]
            print(f"  Permanently deleted {len(quads_to_remove)} quads")
        else:
            batch.status = BatchStatus.DELETED
            print(f"  Marked as deleted")

        self._save_metadata()

    def archive_batch(self, batch_id: str):
        """Archive a batch (keeps data but marks as archived)."""
        batch = self.batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        if batch.status == BatchStatus.ACTIVE:
            raise ValueError("Cannot archive active batch")

        batch.status = BatchStatus.ARCHIVED
        self._save_metadata()
        print(f"[BatchManager] Archived batch: {batch_id}")

    def export_batch(
        self,
        batch_id: str,
        output_file: str,
        rdf_format: RdfFormat = RdfFormat.TRIG
    ):
        """
        Export a batch to a file.

        Args:
            batch_id: Batch to export
            output_file: Output file path
            rdf_format: Output format
        """
        batch = self.batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        graph = NamedNode(batch.graph_uri)

        # Create temporary store with just this batch
        temp_store = Store()
        for quad in self.store.quads_for_pattern(None, None, None, graph):
            temp_store.add(quad)

        # Export
        buffer = BytesIO()
        temp_store.dump(buffer, rdf_format)

        with open(output_file, 'wb') as f:
            f.write(buffer.getvalue())

        print(f"[BatchManager] Exported batch {batch_id} to {output_file}")

    def get_provenance_for_subject(
        self,
        subject_uri: str,
        batch_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get provenance information for a subject.

        Args:
            subject_uri: URI of the subject to get provenance for
            batch_id: Optional batch to scope the query (uses active if None)

        Returns:
            List of provenance records
        """
        if batch_id:
            batch = self.batches.get(batch_id)
        else:
            batch = self.get_active_batch()

        if not batch:
            return []

        # Query for provenance using RDF-star reification
        query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX prov: <http://www.w3.org/ns/prov#>
        PREFIX ex: <http://example.org/>
        
        SELECT ?predicate ?object ?confidence ?source ?timestamp
        FROM <{batch.graph_uri}>
        WHERE {{
            <{subject_uri}> ?predicate ?object .
            OPTIONAL {{
                ?reifier rdf:reifies << <{subject_uri}> ?predicate ?object >> .
                OPTIONAL {{ ?reifier ex:confidence ?confidence }}
                OPTIONAL {{ ?reifier prov:wasGeneratedBy ?source }}
                OPTIONAL {{ ?reifier prov:generatedAtTime ?timestamp }}
            }}
        }}
        """

        results = []
        try:
            for row in self.store.query(query):
                results.append({
                    'predicate': str(row['predicate']),
                    'object': str(row['object']),
                    'confidence': str(row['confidence']) if row['confidence'] else None,
                    'source': str(row['source']) if row['source'] else None,
                    'timestamp': str(row['timestamp']) if row['timestamp'] else None
                })
        except Exception as e:
            print(f"Query error: {e}")

        return results

    def print_status(self):
        """Print current batch management status."""
        print("\n" + "=" * 70)
        print("BATCH MANAGEMENT STATUS")
        print("=" * 70)

        active = self.get_active_batch()
        if active:
            print(f"\nActive Batch: {active.batch_id}")
            print(f"  Created: {active.created_at}")
            print(f"  Quads: {active.quad_count}")
        else:
            print("\nNo active batch")

        print(f"\nTotal Batches: {len(self.batches)}")

        by_status = {}
        for batch in self.batches.values():
            status = batch.status.value
            by_status[status] = by_status.get(status, 0) + 1

        print("By Status:")
        for status, count in by_status.items():
            print(f"  {status}: {count}")

        print("\nRecent Batches:")
        for batch in self.list_batches(limit=5):
            print(f"  [{batch.status.value:10}] {batch.batch_id} - {batch.quad_count} quads")

        print("=" * 70)

