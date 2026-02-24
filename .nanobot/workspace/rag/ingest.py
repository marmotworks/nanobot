#!/usr/bin/env python3
"""
RAG Document Ingestion Script

This script ingests test documents into the RAG system for retrieval-augmented generation.
It handles document loading, chunking, embedding, and storage in LanceDB.
"""

from __future__ import annotations

# stdlib
import asyncio
import json
import os
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


class RAGIngestionPipeline:
    """Handles document ingestion for RAG systems."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.workspace = Path(config.workspace_path)
        self.docs_dir = self.workspace / "rag" / "docs"
        self.db_path = self.workspace / "rag" / "db" / "lancedb"
        self.embeddings_model = "all-MiniLM-L6-v2"
        self.chunk_size = 512
        self.chunk_overlap = 50
        self._embedding_model = None

    async def ingest_all_documents(self) -> dict[str, int]:
        """Ingest all documents from the docs directory."""
        results = {
            "total_documents": 0,
            "total_chunks": 0,
            "successful": 0,
            "failed": 0,
        }

        # Find all markdown files
        markdown_files = list(self.docs_dir.glob("*.md"))

        if not markdown_files:
            print("No markdown files found in docs directory")
            return results

        results["total_documents"] = len(markdown_files)

        # Initialize LanceDB
        db = lancedb.connect(str(self.db_path))

        # Create or get table
        try:
            table = db.open_table("documents")
        except Exception:
            table = None

        # Process each document
        for doc_path in markdown_files:
            try:
                chunks = await self._load_and_chunk_document(doc_path)
                embeddings = await self._generate_embeddings(chunks)

                # Prepare data for LanceDB
                data = []
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    data.append({
                        "vector": embedding,
                        "text": chunk,
                        "source": str(doc_path),
                        "chunk_index": i,
                    })

                if table is None:
                    table = db.create_table("documents", data)
                else:
                    table.add(data)

                results["successful"] += 1
                results["total_chunks"] += len(chunks)
                print(f"✓ Ingested {doc_path.name}: {len(chunks)} chunks")

            except Exception as e:
                results["failed"] += 1
                print(f"✗ Failed to ingest {doc_path.name}: {e}")

        return results

    async def _load_and_chunk_document(self, path: Path) -> list[str]:
        """Load a document and split it into chunks."""
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        # Simple chunking - split by paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(paragraph) > self.chunk_size:
                    # Split long paragraph
                    sentences = paragraph.split(". ")
                    temp_chunk = ""
                    for sentence in sentences:
                        if len(temp_chunk) + len(sentence) <= self.chunk_size:
                            temp_chunk += sentence + ". "
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                            temp_chunk = sentence + ". "
                    if temp_chunk:
                        current_chunk = temp_chunk.strip()
                else:
                    current_chunk = paragraph

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def _generate_embeddings(self, chunks: list[str]) -> list[list[float]]:
        """Generate embeddings for chunks using sentence-transformers."""
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(self.embeddings_model)

        embeddings = self._embedding_model.encode(chunks)
        return [embedding.tolist() for embedding in embeddings]


async def main() -> None:
    """Main entry point for the ingestion script."""
    print("=" * 60)
    print("RAG Document Ingestion Pipeline")
    print("=" * 60)

    # Load configuration
    config = load_config()

    # Create ingestion pipeline
    pipeline = RAGIngestionPipeline(config)

    # Run ingestion
    results = await pipeline.ingest_all_documents()

    # Print summary
    print("\n" + "=" * 60)
    print("Ingestion Summary")
    print("=" * 60)
    print(f"Total Documents: {results['total_documents']}")
    print(f"Total Chunks: {results['total_chunks']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")

    if results["successful"] > 0:
        print("\n✓ Ingestion completed successfully!")
    else:
        print("\n✗ No documents were ingested")


if __name__ == "__main__":
    asyncio.run(main())
