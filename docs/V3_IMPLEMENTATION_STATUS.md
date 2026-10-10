# V3 Implementation Status

Last updated: 2026-10-10 (V3 Part A session).

## PART A — Knowledge-Based Company Research: **COMPLETED**

| Item | Status | Notes |
|---|---|---|
| KnowledgeProvider seam implemented | COMPLETED | `PgKnowledgeProvider` replaces the no-op; Protocol unchanged. |
| Upload via UI + protected endpoint | COMPLETED | `POST /api/knowledge/upload` (multipart, ≤15 MB), `/research` page. |
| PDF + text extraction | COMPLETED | `pypdf` (text PDFs) + utf-8 txt/md/csv. Scanned PDFs rejected with explicit error (no OCR). |
| Chunking with provenance | COMPLETED | 1100/150 config; chunks keep doc id, title, symbol, page (PDF), publication date, seq. |
| Content-hash dedupe | COMPLETED | SHA-256 of normalized text, UNIQUE constraint; re-upload returns `duplicate: true`. |
| PostgreSQL FTS retrieval | COMPLETED | GIN tsvector; OR-of-terms query; ts_rank; bounded ≤8 chunks; symbol filter. |
| pgvector / embeddings | DEFERRED (by decision) | User chose FTS-only: no extra cost/deps. Documented in KNOWLEDGE_RESEARCH.md. |
| Document-grounded AI research | COMPLETED | `run_research` via existing AIProvider chain (OpenAI → Gemini fallback). Structured answer: answer, key_findings, supporting_evidence, citations, contradictions, missing_information, caveats. |
| Citations resolve to real docs | COMPLETED | Hallucinated refs dropped; UI expands source excerpts. Tested. |
| "Answer not established" behavior | COMPLETED | Explicit response when no chunks match. |
| Prompt-injection guard | COMPLETED | Verified: planted injection in test doc stored as evidence, not obeyed. |
| Deletion cascades | COMPLETED | `ON DELETE CASCADE` removes chunks; tested. |
| Retry failed ingestion | PARTIAL | Failures recorded with `error_detail`; explicit retry button not added (re-upload is the retry path; dedupe by content hash applies). |
| Research considers deterministic analysis context | DEFERRED | Currently research uses document evidence only; deterministic context injection is a follow-up. RAG never overrides trade levels (by design). |

**Tests run**: 41/41 backend tests pass (37 pre-existing + 4 new knowledge tests).
Live AI answering validated end-to-end via Gemini (OpenAI key has no credits — user action at platform.openai.com; fallback works automatically).

## PART B — Historical Strategy Evaluation: **DEFERRED (not started)**

Approved scope for follow-up session: swing + intraday backtester (swing first) —
daily candles, next-open entry, conservative same-candle stop/target rule, no
look-ahead, existing Risk Engine for levels, synthetic OHLC EVAL fixtures,
PG-backed run records, Backtesting UI. No optimization. No new infra (no
Celery/Redis; bounded FastAPI task + PG job record + polling).

## PART C — Storage/API/Cost: **COMPLETED for Part A**
- PostgreSQL only; no new services; no Redis reintroduced; no paid APIs added.
- Upload validation, size limits, structured errors, secrets server-side.

## Configuration changes
- `backend/requirements.txt`: added `pypdf==4.3.1`.
- `stockai/core/schema.sql`: new `knowledge.documents` + `knowledge.chunks` (auto-created at startup).

## Known limitations
1. FTS is lexical (no synonyms/semantics) — pgvector upgrade path documented.
2. Scanned PDFs unsupported (no OCR).
3. OpenAI quota exhausted — research uses Gemini fallback until credits added.
4. `docs/STRATEGY_EVALUATION.md` will be written with Part B (metrics definitions).

## Additional costs
None. pypdf is open-source; FTS runs inside existing PostgreSQL; AI calls use existing keys.
