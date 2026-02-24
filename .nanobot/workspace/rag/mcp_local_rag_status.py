#!/usr/bin/env python3
"""
RAG Status Module

This module provides status information about the RAG system,
including document count and database statistics.

Usage:
    python3 -m mcp_local_rag_status
"""

from __future__ import annotations

# stdlib
import sys
from pathlib import Path

# third-party
import lancedb


def main() -> int:
    """Main entry point for the RAG status module."""
    # Determine workspace path
    # Try to find workspace from various locations
    workspace_paths = [
        Path.home() / ".nanobot" / "workspace",
        Path(__file__).parent.parent,
        Path.cwd(),
    ]

    workspace = None
    for path in workspace_paths:
        if (path / "rag" / "db" / "lancedb").exists():
            workspace = path
            break

    if workspace is None:
        print("Error: Could not find workspace with RAG database")
        print("Please run this from the workspace directory or set the workspace path")
        return 1

    rag_dir = workspace / "rag"
    db_path = rag_dir / "db" / "lancedb"

    if not db_path.exists():
        print(f"Error: RAG database not found at {db_path}")
        return 1

    try:
        db = lancedb.connect(str(db_path))
    except Exception as e:
        print(f"Error: Could not connect to RAG database: {e}")
        return 1

    try:
        documents_table = db.open_table("documents")
        documents_count = documents_table.count_rows()

        chunks_table = db.open_table("chunks")
        chunks_count = chunks_table.count_rows()

        print("=" * 60)
        print("RAG System Status")
        print("=" * 60)
        print(f"Workspace: {workspace}")
        print(f"Database: {db_path}")
        print()
        print("Document Statistics:")
        print(f"  Documents: {documents_count}")
        print(f"  Chunks: {chunks_count}")
        print()

        if documents_count > 0:
            print("✓ RAG ingestion verified - document count > 0")
            print()
            print("Sample documents:")
            results = documents_table.search().limit(3).to_pandas()
            for idx, row in results.iterrows():
                print(f"  - {row['source']}")
                print(f"    Text: {row['text'][:100]}...")
        else:
            print("✗ No documents ingested - run ingest.py first")

        return 0

    except Exception as e:
        print(f"Error: Could not read RAG database: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
