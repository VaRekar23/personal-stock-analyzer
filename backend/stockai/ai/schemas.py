"""Pydantic schema for structured, validated AI output (all analysis types).

Trade prices always come from the deterministic Risk Engine; the AI may explain
them but must not override them. If the AI proposes a contradictory value, the
deterministic value remains authoritative.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class AIAnalysis(BaseModel):
    bias: Literal["LONG", "SHORT", "NEUTRAL"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    bullish_factors: list[str] = []
    bearish_factors: list[str] = []
    risks: list[str] = []
    invalidation_conditions: list[str] = []
    setup_commentary: str = ""
    missing_data_warnings: list[str] = []
    # Provenance
    provider: str = "mock"
    model: str = "mock-analyst-v1"
    prompt_version: str = ""
    grounded: bool = True
    error: str | None = None

    @staticmethod
    def json_schema() -> dict:
        return AIAnalysis.model_json_schema()
