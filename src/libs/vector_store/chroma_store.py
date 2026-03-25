"""Chroma VectorStore implementation."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.libs.vector_store.base_vector_store import BaseVectorStore


class ChromaStore(BaseVectorStore):
    """Chroma VectorStore implementation."""

    def __init__(self, persist_path: str = "./data/db/chroma"):
        """Initialize Chroma VectorStore.

        Args:
            persist_path: Path to persist the Chroma database.
        """
        self.persist_path = persist_path
        self._client = None
        self._collection_cache: Dict[str, Any] = {}

    def _get_client(self):
        """Get or create the Chroma client."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings as ChromaSettings
            except ImportError:
                raise ImportError(
                    "chromadb package is required for Chroma VectorStore. "
                    "Install it with: pip install chromadb"
                )

            self._client = chromadb.Client(
                ChromaSettings(
                    persist_directory=self.persist_path,
                    anonymized_telemetry=False,
                )
            )
        return self._client

    def upsert(
        self,
        records: List[Dict[str, Any]],
        collection: str = "default",
        **kwargs
    ) -> None:
        """Insert or update records in Chroma.

        Args:
            records: List of records with 'id', 'embedding', and 'metadata' keys.
            collection: Collection name.
            **kwargs: Additional parameters.
        """
        client = self._get_client()
        coll = client.get_or_create_collection(name=collection)

        ids = [str(r["id"]) for r in records]
        embeddings = [r["embedding"] for r in records]
        metadatas = [r.get("metadata", {}) for r in records]
        documents = [r.get("text", "") for r in records]

        coll.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        collection: str = "default",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query Chroma for similar records.

        Args:
            vector: Query embedding vector.
            top_k: Number of results to return.
            filters: Optional metadata filters.
            collection: Collection name.
            **kwargs: Additional parameters.

        Returns:
            List of matching records.
        """
        client = self._get_client()
        coll = client.get_collection(name=collection)

        results = coll.query(
            query_embeddings=[vector],
            n_results=top_k,
            where=filters,
        )

        records = []
        if results and results.get("ids"):
            for i in range(len(results["ids"][0])):
                records.append({
                    "id": results["ids"][0][i],
                    "score": results.get("distances", [[]])[0][i],
                    "metadata": results.get("metadatas", [[]])[0][i],
                    "text": results.get("documents", [[]])[0][i],
                })
        return records

    def get_by_ids(
        self, ids: List[str], collection: str = "default", **kwargs
    ) -> List[Dict[str, Any]]:
        """Get records by their IDs from Chroma.

        Args:
            ids: List of record IDs.
            collection: Collection name.
            **kwargs: Additional parameters.

        Returns:
            List of records.
        """
        client = self._get_client()
        coll = client.get_collection(name=collection)

        results = coll.get(ids=ids)

        records = []
        if results and results.get("ids"):
            for i in range(len(results["ids"])):
                records.append({
                    "id": results["ids"][i],
                    "metadata": results.get("metadatas", [{}])[i],
                    "text": results.get("documents", [""])[i],
                })
        return records

    def delete_by_metadata(
        self,
        filter: Dict[str, Any],
        collection: str = "default",
        **kwargs
    ) -> None:
        """Delete records by metadata filter from Chroma.

        Args:
            filter: Metadata filter conditions.
            collection: Collection name.
            **kwargs: Additional parameters.
        """
        client = self._get_client()
        coll = client.get_collection(name=collection)
        coll.delete(where=filter)
