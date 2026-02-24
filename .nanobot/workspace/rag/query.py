#!/usr/bin/env python3
"""
RAG Query Script

This script demonstrates querying the RAG system for relevant documents.
"""

from __future__ import annotations

# stdlib
import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

# third-party
import lancedb
import numpy as np
from sentence_transformers import SentenceTransformer

# first-party
from nanobot.config.loader import load_config

if TYPE_CHECKING:
    from nanobot.config.schema import Config


class RAGQuery:
    """Handles queries against the RAG system."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.workspace = Path(config.workspace_path)
        self.db_path = self.workspace / "rag" / "db" / "lancedb"
        self.embeddings_model = "all-MiniLM-L6-v2"
        self._embedding_model = None

    def _get_embedding_model(self) -> SentenceTransformer:
        """Get or create the embedding model."""
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(self.embeddings_model)
        return self._embedding_model

    async def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        """Query the RAG system for relevant documents."""
        # Get embedding for query
        model = self._get_embedding_model()
        query_embedding = model.encode([query_text])[0]

        # Connect to database
        db = lancedb.connect(str(self.db_path))

        try:
            table = db.open_table("documents")
        except Exception:
            return [{"error": "No documents found in RAG database. Run ingest.py first."}]

        # Search
        results = (
            table.search(query_embedding.tolist())
            .limit(top_k)
            .select(["text", "source", "chunk_index"])
            .to_pandas()
        )

        # Convert to list of dicts
        output = []
        for _, row in results.iterrows():
            output.append({
                "text": row["text"],
                "source": row["source"],
                "chunk_index": int(row["chunk_index"]),
                "score": float(row["_distance"]),
            })

        return output


async def main() -> None:
    """Main entry point for the query script."""
    print("=" * 60)
    print("RAG Query Demo")
    print("=" * 60)

    # Load configuration
    config = load_config()

    # Create query instance
    rag = RAGQuery(config)

    # Example queries
    queries = [
        "What is RAG?",
        "How do vector embeddings work?",
        "What is LanceDB?",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        results = await rag.query(query, top_k=3)

        for i, result in enumerate(results, 1):
            print(f"\nResult {i} (score: {result['score']:.4f})")
            print(f"Source: {result['source']}")
            print(f"Text: {result['text'][:200]}...")


if __name__ == "__main__":
    asyncio.run(main())
