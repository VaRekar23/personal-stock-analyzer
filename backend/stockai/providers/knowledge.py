"""KnowledgeProvider — PostgreSQL full-text RAG (V3).

Document ingestion + retrieval backed entirely by PostgreSQL (no vector DB, no
paid embeddings). Retrieval uses `tsvector`/`plainto_tsquery` + `ts_rank`.
Never computes prices/indicators/trade levels — it only supplies text evidence.

Design notes:
- Content-hash dedupe prevents re-ingesting identical documents.
- Chunks are bounded and carry provenance (doc id/title/symbol/page/seq).
- Retrieved text is EVIDENCE, never instructions (prompt-injection guard lives
  in the research prompt; this layer just stores/returns text).
"""
from __future__ import annotations
import hashlib
import re
import uuid

from ..core import db
from ..core.logging_config import get_logger

logger = get_logger("stockai.knowledge")

EXTRACTION_VERSION = "extract_v1"
CHUNK_CHARS = 1100
CHUNK_OVERLAP = 150
MAX_RETRIEVE = 8


def _norm(text: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\r\n?", "\n", text)).strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()


def extract_pdf(data: bytes) -> tuple[str, list[int]]:
    """Return (full_text, page_offsets). Raises ValueError for scanned/empty
    PDFs (no selectable text) — never returns an empty doc as success."""
    from pypdf import PdfReader
    import io
    reader = PdfReader(io.BytesIO(data))
    parts, offsets, cursor = [], [], 0
    for pg in reader.pages:
        txt = pg.extract_text() or ""
        offsets.append(cursor)
        parts.append(txt)
        cursor += len(txt) + 1
    full = "\n".join(parts)
    if len(full.strip()) < 30:
        raise ValueError("No selectable text extracted (likely a scanned PDF; "
                         "OCR is not supported in V3).")
    return full, offsets


def _page_for(offset: int, page_offsets: list[int]) -> int | None:
    if not page_offsets:
        return None
    page = 0
    for i, start in enumerate(page_offsets):
        if offset >= start:
            page = i
    return page + 1  # 1-indexed


def chunk_text(text: str, page_offsets: list[int] | None = None):
    text = _norm(text)
    out, i, seq = [], 0, 0
    n = len(text)
    while i < n:
        piece = text[i:i + CHUNK_CHARS]
        if piece.strip():
            out.append({"seq": seq, "content": piece.strip(),
                        "page": _page_for(i, page_offsets or [])})
            seq += 1
        i += CHUNK_CHARS - CHUNK_OVERLAP
    return out


class PgKnowledgeProvider:
    name = "postgres_fts"
    mode = "live"

    async def ingest(self, *, text: str, title: str, symbol: str | None = None,
                     doc_type: str = "other", source: str | None = None,
                     publication_date: str | None = None,
                     page_offsets: list[int] | None = None) -> dict:
        if not db.is_up():
            raise RuntimeError("Knowledge store unavailable (database down).")
        chash = content_hash(text)
        existing = await db.fetchrow(
            "SELECT id, title FROM knowledge.documents WHERE content_hash=$1", chash)
        if existing:
            return {"id": existing["id"], "duplicate": True, "status": "indexed",
                    "title": existing["title"]}
        doc_id = uuid.uuid4().hex
        chunks = chunk_text(text, page_offsets)
        try:
            await db.execute(
                """INSERT INTO knowledge.documents
                   (id,title,symbol,doc_type,source,publication_date,content_hash,
                    status,extraction_version,indexing_status,chunk_count,char_count)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,'indexed',$8,'indexed',$9,$10)""",
                doc_id, title, symbol.upper() if symbol else None, doc_type, source,
                publication_date, chash, EXTRACTION_VERSION, len(chunks), len(text))
            for c in chunks:
                await db.execute(
                    """INSERT INTO knowledge.chunks (id,document_id,symbol,seq,page,content)
                       VALUES ($1,$2,$3,$4,$5,$6)""",
                    uuid.uuid4().hex, doc_id, symbol.upper() if symbol else None,
                    c["seq"], c["page"], c["content"])
        except Exception as e:  # noqa: BLE001 — record failure, never fake success
            await db.execute(
                "UPDATE knowledge.documents SET status='failed',indexing_status='failed',"
                "error_detail=$2 WHERE id=$1", doc_id, str(e)[:500])
            logger.error("ingest failed for %s: %s", title, e)
            raise
        return {"id": doc_id, "duplicate": False, "status": "indexed",
                "title": title, "chunks": len(chunks)}

    async def retrieve(self, query: str, symbol: str | None = None,
                       k: int = 5) -> list[dict]:
        if not db.is_up() or not query.strip():
            return []
        k = max(1, min(k, MAX_RETRIEVE))
        # OR significant tokens (recall-friendly) and rank by ts_rank. A full
        # natural-language question with plainto_tsquery ANDs every lexeme and
        # under-retrieves, so we build "term1 | term2 | ..." instead.
        tokens = [t for t in re.findall(r"[A-Za-z0-9]+", query.lower()) if len(t) > 2]
        if not tokens:
            return []
        tsq = " | ".join(dict.fromkeys(tokens))  # dedupe, preserve order
        params = [tsq]
        sym_filter = ""
        if symbol:
            params.append(symbol.upper())
            sym_filter = "AND (c.symbol = $2 OR c.symbol IS NULL)"
        rows = await db.fetch(
            f"""SELECT c.id AS chunk_id, c.document_id, c.seq, c.page, c.content,
                       d.title, d.symbol, d.source, d.doc_type, d.publication_date,
                       ts_rank(c.ts, to_tsquery('english', $1)) AS rank
                FROM knowledge.chunks c JOIN knowledge.documents d ON d.id=c.document_id
                WHERE c.ts @@ to_tsquery('english', $1) {sym_filter}
                ORDER BY rank DESC LIMIT {k}""", *params)
        return [{
            "chunk_id": r["chunk_id"], "document_id": r["document_id"],
            "document_title": r["title"], "symbol": r["symbol"],
            "source": r["source"], "doc_type": r["doc_type"],
            "page": r["page"], "seq": r["seq"],
            "publication_date": r["publication_date"].isoformat() if r["publication_date"] else None,
            "excerpt": r["content"], "rank": float(r["rank"]),
        } for r in rows]

    async def list_documents(self, symbol: str | None = None) -> list[dict]:
        if not db.is_up():
            return []
        where, params = "", []
        if symbol:
            where = "WHERE symbol=$1"
            params.append(symbol.upper())
        rows = await db.fetch(
            f"""SELECT id,title,symbol,doc_type,source,publication_date,uploaded_at,
                       status,indexing_status,error_detail,chunk_count,char_count
                FROM knowledge.documents {where} ORDER BY uploaded_at DESC""", *params)
        return [dict(r) | {
            "publication_date": r["publication_date"].isoformat() if r["publication_date"] else None,
            "uploaded_at": r["uploaded_at"].isoformat() if r["uploaded_at"] else None,
        } for r in rows]

    async def delete_document(self, doc_id: str) -> bool:
        if not db.is_up():
            return False
        await db.execute("DELETE FROM knowledge.documents WHERE id=$1", doc_id)
        return True  # ON DELETE CASCADE removes chunks

    async def stats(self) -> dict:
        if not db.is_up():
            return {"documents": 0, "chunks": 0, "available": False}
        d = await db.fetchrow("SELECT count(*) n FROM knowledge.documents")
        c = await db.fetchrow("SELECT count(*) n FROM knowledge.chunks")
        return {"documents": d["n"] if d else 0, "chunks": c["n"] if c else 0,
                "available": True, "backend": "postgres_fts"}


class NullKnowledgeProvider:
    """Retained for compatibility / explicit-disable."""
    name = "null"
    mode = "disabled"

    async def retrieve(self, query: str, symbol: str | None = None,
                       k: int = 5) -> list[dict]:
        return []
