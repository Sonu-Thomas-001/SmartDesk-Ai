import structlog
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.models import SimilarIncident

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "incident_knowledge_base"


class EmbeddingEngine:
    """Manages ChromaDB storage and similarity search for incidents.

    Uses ChromaDB's built-in default embedding function (all-MiniLM-L6-v2)
    so no external API calls are needed for embeddings.
    """

    def __init__(self) -> None:
        self._chroma = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # ChromaDB uses its default embedding function (all-MiniLM-L6-v2)
        # automatically when no embedding_function is specified.
        self._collection = self._chroma.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("embedding_engine_init", collection=COLLECTION_NAME)

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    def store_incident(
        self,
        incident_id: str,
        description: str,
        assigned_team: str,
        resolution_notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store an incident in ChromaDB (embeddings generated locally)."""
        doc_metadata = {
            "assigned_team": assigned_team,
            "resolution_notes": resolution_notes,
            **(metadata or {}),
        }
        self._collection.upsert(
            ids=[incident_id],
            documents=[description],
            metadatas=[doc_metadata],
        )
        logger.info("stored_incident", incident_id=incident_id)

    def store_incidents_batch(
        self,
        incidents: list[dict[str, Any]],
    ) -> None:
        """Batch-store multiple incidents."""
        if not incidents:
            return
        ids = [inc["id"] for inc in incidents]
        descriptions = [inc["description"] for inc in incidents]
        metadatas = [
            {
                "assigned_team": inc.get("assigned_team", ""),
                "resolution_notes": inc.get("resolution_notes", ""),
            }
            for inc in incidents
        ]
        self._collection.upsert(
            ids=ids,
            documents=descriptions,
            metadatas=metadatas,
        )
        logger.info("stored_incidents_batch", count=len(incidents))

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_similar(
        self, description: str, top_k: int = 5
    ) -> list[SimilarIncident]:
        """Find the most similar historical incidents."""
        results = self._collection.query(
            query_texts=[description],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        similar: list[SimilarIncident] = []
        if not results["ids"] or not results["ids"][0]:
            return similar

        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i] if results["distances"] else 1.0
            similarity = 1.0 - distance  # cosine distance → similarity
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            similar.append(
                SimilarIncident(
                    id=doc_id,
                    description=results["documents"][0][i] if results["documents"] else "",
                    assigned_team=meta.get("assigned_team", ""),
                    resolution_notes=meta.get("resolution_notes", ""),
                    similarity_score=round(max(similarity, 0.0), 4),
                )
            )

        logger.info("search_similar", query_len=len(description), results=len(similar))
        return similar

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def collection_count(self) -> int:
        return self._collection.count()
