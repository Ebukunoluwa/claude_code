from __future__ import annotations

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "call_transcripts"


class VectorStore:
    """Thin wrapper around a ChromaDB persistent collection."""

    def __init__(self, persist_path: str) -> None:
        self._client = chromadb.PersistentClient(
            path=persist_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("VectorStore ready — collection '%s'", _COLLECTION_NAME)

    def upsert(
        self,
        call_id: str,
        embedding: list[float],
        document: str,
        urgency: str,
        patient_name: str,
    ) -> None:
        self._collection.upsert(
            ids=[call_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[{"urgency": urgency, "patient_name": patient_name}],
        )
        logger.debug("Upserted embedding for call %s (urgency=%s)", call_id, urgency)

    def semantic_search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        urgency_filter: Optional[str] = None,
    ) -> list[dict]:
        where = {"urgency": urgency_filter} if urgency_filter else None
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        output: list[dict] = []
        if results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                output.append(
                    {
                        "call_id": doc_id,
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                    }
                )
        return output
