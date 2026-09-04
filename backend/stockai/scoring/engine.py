"""Central scoring engine (scoring_version = scoring_v1).

Takes structured factor inputs, applies strategy-specific weights, produces a
0–100 score and a SEPARATE confidence (0–1) driven by data availability. It
exposes factor-level contributions and distinguishes "no data" from a negative
signal — missing factors are excluded and lower confidence, never treated as 0.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Factor:
    key: str
    label: str
    weight: float
    value: float | None      # normalized 0..100 (None = data unavailable)
    detail: str = ""

    @property
    def available(self) -> bool:
        return self.value is not None


@dataclass
class ScoreResult:
    score: float
    confidence: float
    bias: str
    factors: list[dict] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    scoring_version: str = "scoring_v1"

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 1),
            "confidence": round(self.confidence, 2),
            "bias": self.bias,
            "factors": self.factors,
            "missing": self.missing,
            "scoring_version": self.scoring_version,
        }


def _bias_from_score(score: float) -> str:
    if score >= 60:
        return "bullish"
    if score <= 40:
        return "bearish"
    return "neutral"


def score_factors(factors: list[Factor]) -> ScoreResult:
    available = [f for f in factors if f.available]
    missing = [f.label for f in factors if not f.available]

    total_weight = sum(f.weight for f in available)
    if total_weight == 0:
        return ScoreResult(score=0.0, confidence=0.0, bias="neutral",
                           factors=[], missing=missing)

    # Re-normalize weights across available factors so missing data neither
    # inflates nor deflates the score.
    score = 0.0
    contributions = []
    for f in available:
        norm_w = f.weight / total_weight
        contribution = norm_w * f.value  # value already 0..100
        # centered contribution (relative to neutral 50) for display
        centered = norm_w * (f.value - 50) / 50 * 100
        score += contribution
        contributions.append({
            "key": f.key, "label": f.label,
            "weight": round(f.weight, 3),
            "value": round(f.value, 1),
            "contribution": round(centered, 1),
            "detail": f.detail,
        })

    # Confidence = fraction of intended weight that had data.
    intended_weight = sum(f.weight for f in factors)
    confidence = total_weight / intended_weight if intended_weight else 0.0

    return ScoreResult(
        score=score, confidence=confidence, bias=_bias_from_score(score),
        factors=contributions, missing=missing)
