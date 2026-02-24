- [ ] 41.4 Ingest test documents for RAG
      Criterion: `python3 -m mcp_local_rag_status` shows document count > 0; ingestion process completes without errors
      File: N/A
      Blocker: none
- [ ] 41.5 Verify RAG ingestion and search functionality
      Criterion: `python3 -m mcp_local_rag_status` shows increased document count; `python3 -m mcp_local_rag_query_documents "OCI SDK example"` returns at least one relevant document with a non‑zero relevance score → output contains `doc_id` and `score` fields
      File: N/A
      Blocker: 41.4