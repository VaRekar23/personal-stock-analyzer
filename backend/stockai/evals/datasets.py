"""EVAL datasets + runner.

Synthetic cases are clearly labelled `synthetic` and are NOT real-world facts.
They demonstrate the grader catching hallucinations (e.g. AI stating RSI=42 when
the deterministic RSI is 67.2, or Entry=1400 when the Risk Engine says 1432).
"""
from __future__ import annotations
import uuid
import json
from datetime import datetime, timezone

from ..core import db
from ..providers.registry import ai_provider
from ..data.nifty50 import SYMBOLS
from .framework import grade_ai_output, extract_numbers, _close

# --- Static synthetic AI-eval cases (labelled synthetic) ---
SYNTHETIC_AI_CASES = [
    {
        "case_id": "syn_rsi_consistency_pass",
        "label": "AI restates RSI correctly",
        "evaluation_type": "factual_consistency",
        "input": {"rsi": 67.2, "ema20": 1450, "ema50": 1438, "supertrend": "bullish",
                  "entry": 1432, "stop_loss": 1398, "target_1": 1475},
        "ai_stated": {"rsi": 67.2, "entry": 1432},
        "expected_output": {"passed": True},
    },
    {
        "case_id": "syn_rsi_consistency_fail",
        "label": "AI hallucinates RSI=42 vs deterministic 67.2",
        "evaluation_type": "factual_consistency",
        "input": {"rsi": 67.2, "ema20": 1450, "ema50": 1438, "supertrend": "bullish",
                  "entry": 1432, "stop_loss": 1398, "target_1": 1475},
        "ai_stated": {"rsi": 42, "entry": 1432},
        "expected_output": {"passed": False},
    },
    {
        "case_id": "syn_entry_override_fail",
        "label": "AI overrides Risk Engine entry (1400 vs 1432)",
        "evaluation_type": "factual_consistency",
        "input": {"rsi": 67.2, "entry": 1432, "stop_loss": 1398, "target_1": 1475},
        "ai_stated": {"rsi": 67.2, "entry": 1400},
        "expected_output": {"passed": False},
    },
]


def _grade_synthetic(case: dict) -> dict:
    inp, stated = case["input"], case["ai_stated"]
    checks = []
    for key, val in stated.items():
        if key in inp:
            ok = _close(float(val), float(inp[key]), tol_pct=1.5)
            checks.append({"field": key, "stated": val, "deterministic": inp[key],
                           "passed": ok})
    passed = all(c["passed"] for c in checks)
    return {"passed": passed, "score": 1.0 if passed else 0.0, "checks": checks}


async def seed_datasets() -> None:
    if not db.is_up():
        return
    await db.execute(
        """INSERT INTO evaluation.eval_datasets (id,name,description,kind,version)
           VALUES ('ai_synthetic_v1','AI Synthetic Consistency','Synthetic hallucination-detection cases','ai_synthetic','v1'),
                  ('ai_live_pipeline_v1','AI Live Pipeline','AI grading over deterministic pipeline output','ai_pipeline','v1'),
                  ('strategy_foundation_v1','Strategy Eval Foundation','Placeholder dataset for future historical trade-setup evaluation','strategy','v1')
           ON CONFLICT (id) DO NOTHING""")
    for c in SYNTHETIC_AI_CASES:
        await db.execute(
            """INSERT INTO evaluation.eval_cases
               (case_id,dataset_id,evaluation_type,label,input,expected_output,version)
               VALUES ($1,'ai_synthetic_v1',$2,$3,$4,$5,'v1')
               ON CONFLICT (case_id) DO NOTHING""",
            c["case_id"], c["evaluation_type"], c["label"],
            json.dumps(c["input"]), json.dumps(c["expected_output"]))


async def run_evals(sample_size: int = 6) -> dict:
    """Run synthetic + live-pipeline AI evals and persist a run."""
    from ..analysis.orchestrator import get_orchestrator
    orch = get_orchestrator()
    run_id = uuid.uuid4()
    results = []

    # A. Synthetic cases (hallucination detection).
    for c in SYNTHETIC_AI_CASES:
        graded = _grade_synthetic(c)
        expected_pass = c["expected_output"]["passed"]
        # A case "passes the eval suite" if the grader's verdict matches expectation.
        suite_pass = graded["passed"] == expected_pass
        results.append({
            "case_id": c["case_id"], "evaluation_type": c["evaluation_type"],
            "passed": suite_pass, "score": 1.0 if suite_pass else 0.0,
            "actual": graded, "label": c["label"], "dataset": "ai_synthetic_v1",
        })

    # B. Live-pipeline AI evals over a deterministic sample.
    for sym in SYMBOLS[:sample_size]:
        analysis = await orch.analyze_stock(sym, "swing", run_ai=True)
        ctx = {"score": analysis["score"], "risk_setup": analysis["trade_setup"]}
        graded = grade_ai_output(analysis["ai"], ctx)
        results.append({
            "case_id": f"live_swing_{sym}", "evaluation_type": "ai_pipeline",
            "passed": graded["passed"], "score": graded["score"],
            "actual": graded, "label": f"Swing AI grounding — {sym}",
            "dataset": "ai_live_pipeline_v1",
        })

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    avg = round(sum(r["score"] for r in results) / len(results), 3) if results else 0

    if db.is_up():
        await db.execute(
            """INSERT INTO evaluation.eval_runs (id,dataset_id,passed,failed,total,avg_score,metadata)
               VALUES ($1,'mixed',$2,$3,$4,$5,$6)""",
            run_id, passed, failed, len(results), avg,
            json.dumps({"sample_size": sample_size}))
        for r in results:
            await db.execute(
                """INSERT INTO evaluation.eval_results
                   (run_id,case_id,evaluation_type,passed,score,actual_output,detail)
                   VALUES ($1,$2,$3,$4,$5,$6,$7)""",
                run_id, r["case_id"], r["evaluation_type"], r["passed"],
                r["score"], json.dumps(r["actual"]), json.dumps({"label": r["label"]}))

    return {
        "run_id": str(run_id),
        "as_of": datetime.now(timezone.utc).isoformat(),
        "passed": passed, "failed": failed, "total": len(results),
        "pass_rate": round(passed / len(results), 3) if results else 0,
        "avg_score": avg, "results": results,
    }
