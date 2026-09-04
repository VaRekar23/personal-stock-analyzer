"""KnowledgeProvider stub — RAG integration point for V2 (not overbuilt).

V1 ships a no-op provider so business logic has a clean seam. Future document
retrieval (annual/quarterly reports, transcripts, filings, investor notes)
plugs in here (e.g. a vector store). Never used to compute prices/indicators/
trade levels — those remain deterministic.
"""
from __future__ import annotations


class NullKnowledgeProvider:
    mode = "disabled"
    STATUS = "pending_v2"

    async def retrieve(self, query: str, symbol: str | None = None,
                       k: int = 5) -> list[dict]:
        return []  # RAG not enabled in V1.
