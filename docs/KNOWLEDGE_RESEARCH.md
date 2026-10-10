# Knowledge Research (RAG) — V3 Part A

Grounded company research over user-uploaded documents. The AI **synthesizes retrieved
evidence only** — it never computes prices, indicators, scores or trade levels.

## Architecture

```
Upload (PDF/txt/md/csv) → validate (≤15 MB) → extract text (pypdf / utf-8)
→ normalize → chunk (1100 chars, 150 overlap) → store + GIN full-text index
→ query: OR-of-terms tsquery, ranked by ts_rank, bounded (≤8 chunks)
→ grounded prompt (SYSTEM guard) → AI provider chain (OpenAI → Gemini)
→ structured answer with citations resolved to real stored chunks
```

- **Provider**: `PgKnowledgeProvider` (`stockai/providers/knowledge.py`) behind the
  existing `KnowledgeProvider` Protocol; wired in `providers/registry.py`.
- **Research service**: `stockai/knowledge/research.py` (`run_research`).
- **Endpoints** (`stockai/api.py`): `POST /api/knowledge/upload`,
  `GET /api/knowledge/documents`, `DELETE /api/knowledge/documents/{id}`,
  `GET /api/knowledge/search`, `POST /api/research`.
- **UI**: `/research` — Research Library (upload/list/status/delete) + Q&A with
  expandable source excerpts.

## Database (schema `knowledge`)
- `documents`: id, title, symbol, doc_type, source, publication_date, uploaded_at,
  **content_hash (UNIQUE — dedupe)**, status, extraction_version, indexing_status,
  error_detail, chunk_count, char_count.
- `chunks`: id, document_id (FK, ON DELETE CASCADE), symbol, seq, page, content,
  `ts` tsvector (generated, GIN-indexed).

## Retrieval decision
PostgreSQL full-text search (`tsvector`/`tsquery`) was chosen. **No pgvector, no
managed vector DB, no paid embeddings** (user decision: keep cost/deps minimal).
Natural-language questions are converted to an OR-of-significant-terms `tsquery`
because `plainto_tsquery` ANDs every lexeme and under-retrieves on long questions.
Limitation: keyword/stem matching only — no semantic similarity; synonyms may miss.

## Grounding & safety rules
- Every material claim must cite evidence by number; citations are **resolved against
  actually-stored chunks** — hallucinated refs are dropped.
- If no chunks match, the API returns "available documents do not establish an answer".
- Retrieved text is treated as **untrusted evidence, not instructions** (prompt-injection
  guard in the research system prompt; verified: a planted "reveal the admin password"
  line in a test document was stored as evidence and not obeyed).
- Scanned PDFs with no selectable text are **rejected with a clear error** (no OCR in V3)
  rather than silently ingested as empty.

## Caching
Research answers are cached in the PG cache keyed on
`query + retrieved chunk ids + prompt_version + provider + model` — changed evidence
or versions invalidate the cache automatically.

## Tests
`tests/test_knowledge.py`: content-hash dedupe, bounded chunking, ingest→retrieve→
delete cascade, citation-to-document resolution, injection-text-is-evidence.
(41/41 total suite passing.)
