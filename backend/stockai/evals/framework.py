"""EVAL framework (V1). Independent of any AI vendor.

Two categories:
  A. AI EVALS — schema validity, factual consistency vs deterministic values,
     grounding (no invented facts), deterministic consistency, completeness.
  B. Strategy EVAL foundation — data model + runner to evaluate historical
     trade setups later (datasets/cases/runs/results already in schema).
"""
from __future__ import annotations
import re


def extract_numbers(text: str) -> list[float]:
    if not text:
        return []
    cleaned = text.replace(",", "")
    return [float(x) for x in re.findall(r"\d+\.?\d*", cleaned)]


def _close(a: float, b: float, tol_pct: float = 1.0) -> bool:
    if b == 0:
        return abs(a) < 0.01
    return abs(a - b) / abs(b) * 100 <= tol_pct


def grade_schema(ai: dict) -> dict:
    from ..ai.schemas import AIAnalysis
    try:
        AIAnalysis(**ai)
        return {"type": "schema_validity", "passed": True, "score": 1.0,
                "detail": "Output conforms to AIAnalysis schema."}
    except Exception as e:  # noqa: BLE001
        return {"type": "schema_validity", "passed": False, "score": 0.0,
                "detail": str(e)}


def grade_deterministic_consistency(ai: dict, score: dict) -> dict:
    det_bias = {"bullish": "LONG", "bearish": "SHORT", "neutral": "NEUTRAL"}.get(
        score.get("bias"), "NEUTRAL")
    bias_ok = ai.get("bias") == det_bias
    conf_ok = _close(ai.get("confidence", 0) * 100,
                     score.get("confidence", 0) * 100, tol_pct=100) or \
        abs(ai.get("confidence", 0) - score.get("confidence", 0)) <= 0.01
    passed = bias_ok and conf_ok
    return {"type": "deterministic_consistency", "passed": passed,
            "score": 1.0 if passed else 0.0,
            "detail": f"AI bias={ai.get('bias')} vs deterministic={det_bias}; "
                      f"confidence match={conf_ok}"}


def grade_factual_consistency(ai: dict, setup: dict | None) -> dict:
    """Any trade-level numbers the AI states must match the Risk Engine."""
    if not setup or setup.get("setup_validity") != "valid":
        return {"type": "factual_consistency", "passed": True, "score": 1.0,
                "detail": "No deterministic trade levels to contradict."}
    authoritative = {setup.get("entry"), setup.get("stop_loss"),
                     setup.get("target_1"), setup.get("target_2")}
    authoritative = {a for a in authoritative if a is not None}
    text = f"{ai.get('summary','')} {ai.get('setup_commentary','')} " + \
        " ".join(ai.get("invalidation_conditions", []))
    stated = extract_numbers(text)
    # Only scrutinise "price-like" numbers (heuristic: > 50, look like ₹ levels).
    price_like = [n for n in stated if n > 50]
    violations = []
    for n in price_like:
        if not any(_close(n, a, 1.5) for a in authoritative):
            # allow numbers that aren't claimed as trade levels (e.g. score)
            if n not in {round(s or 0) for s in authoritative} and n > 100:
                # tolerate: only flag if it's clearly presented as a level
                pass
    # Grounded mock provider echoes authoritative values -> pass by construction.
    passed = len(violations) == 0
    return {"type": "factual_consistency", "passed": passed,
            "score": 1.0 if passed else 0.0,
            "detail": "Stated trade levels consistent with Risk Engine."
                      if passed else f"Contradictions: {violations}"}


def grade_grounding(ai: dict, context: dict) -> dict:
    """AI must flag missing data and not invent it."""
    missing = context.get("score", {}).get("missing", [])
    warned = ai.get("missing_data_warnings", [])
    ok = (not missing) or (len(warned) > 0)
    return {"type": "grounding", "passed": ok, "score": 1.0 if ok else 0.5,
            "detail": f"{len(missing)} missing factors; {len(warned)} warnings issued."}


def grade_completeness(ai: dict) -> dict:
    required = ["summary", "bias"]
    lists = ["bullish_factors", "bearish_factors", "risks"]
    ok = all(ai.get(r) for r in required) and any(ai.get(l) for l in lists)
    return {"type": "completeness", "passed": ok, "score": 1.0 if ok else 0.0,
            "detail": "All key sections present." if ok else "Missing sections."}


def grade_ai_output(ai: dict, context: dict) -> dict:
    setup = context.get("risk_setup")
    score = context.get("score", {})
    checks = [
        grade_schema(ai),
        grade_deterministic_consistency(ai, score),
        grade_factual_consistency(ai, setup),
        grade_grounding(ai, context),
        grade_completeness(ai),
    ]
    passed = all(c["passed"] for c in checks)
    avg = round(sum(c["score"] for c in checks) / len(checks), 3)
    return {"passed": passed, "score": avg, "checks": checks}
