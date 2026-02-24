# RAG (Retrieval-Augmented Generation) System

This directory contains the RAG infrastructure for the nanobot system.

## Directory Structure

```
rag/
├── docs/          # Source documents for ingestion
│   └── *.md       # Markdown documents to be ingested
├── db/            # Vector database storage
│   ├── lancedb/   # LanceDB vector database
│   └── cache/     # Embedding cache
├── ingest.py      # Ingestion script
└── README.md      # This file
```

## What is RAG?

Retrieval-Augmented Generation (RAG) is a technique that combines:
- **Information retrieval**: Finding relevant documents from a knowledge base
- **Generative AI**: Using retrieved information to produce responses

This approach reduces hallucination and enables domain-specific knowledge integration.

## How It Works

1. **Ingestion**: Documents are loaded, chunked, embedded, and stored
2. **Retrieval**: User queries are embedded and similar documents are found
3. **Generation**: Retrieved documents are combined with the query for response generation

## Usage

### Ingest Documents

```bash
cd ~/.nanobot/workspace/rag
python3 ingest.py
```

### Query the RAG System

```python
from rag.query import RAGQuery

rag = RAGQuery()
results = rag.query("What is RAG?", top_k=5)
print(results)
```

## Configuration

RAG configuration is managed through the main nanobot configuration file (`~/.nanobot/config.yaml`).

Key settings:
- `rag.chunk_size`: Maximum chunk size in tokens
- `rag.chunk_overlap`: Overlap between chunks
- `rag.embedding_model`: Embedding model to use
- `rag.vector_db_path`: Path to vector database

## Test Documents

The `docs/` directory contains test documents for RAG:

- `test_document_1.md`: Introduction to RAG systems
- `test_document_2.md`: Vector embeddings concepts
- `test_document_3.md`: LanceDB vector database
- `test_document_4.md`: RAG ingestion pipeline

## Technologies

- **LanceDB**: Open-source vector database
- **Sentence Transformers**: Embedding generation
- **Python 3.11+**: Core implementation

## Development

To add new documents:
1. Place markdown files in `docs/`
2. Run `python3 ingest.py`
3. Test queries against the new documents
