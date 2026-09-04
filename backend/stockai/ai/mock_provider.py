"""MockAIProvider — deterministic, fully grounded explanation generator.

Critically, it ONLY uses numbers already present in the structured context
(score, factor contributions, Risk Engine trade levels). It never fabricates
indicator values or trade prices. This makes AI EVALS (factual consistency /
grounding) pass by construction and demonstrates the required architecture
without consuming API credits.
"""
from __future__ import annotations

from .schemas import AIAnalysis


class MockAIProvider:
    name = "mock"
    model = "mock-analyst-v1"

    async def generate(self, prompt: str, context: dict,
                       response_schema: dict | None = None) -> dict:
        score = context.get("score", {})
        risk = context.get("risk_setup") or {}
        factors = score.get("factors", [])
        bias = (risk.get("direction") or score.get("bias") or "NEUTRAL").upper()
        if bias == "LONG":
            bias = "LONG"
        elif bias in ("SHORT", "BEARISH"):
            bias = "SHORT"
        elif bias == "BULLISH":
            bias = "LONG"
        else:
            bias = "NEUTRAL"

        pos = [f for f in factors if f.get("contribution", 0) > 0]
        neg = [f for f in factors if f.get("contribution", 0) < 0]
        pos.sort(key=lambda f: -f["contribution"])
        neg.sort(key=lambda f: f["contribution"])

        bullish = [f"{f['label']} supportive (+{round(f['contribution'],1)})" for f in pos[:5]]
        bearish = [f"{f['label']} weak ({round(f['contribution'],1)})" for f in neg[:5]]
        missing = score.get("missing", [])

        sval = round(score.get("score", 0), 1)
        conf = round(score.get("confidence", 0.5), 2)

        summary_parts = [
            f"{context.get('symbol','')} shows a {bias.lower()} bias with a "
            f"deterministic score of {sval}/100 (confidence {conf})."
        ]
        if risk:
            summary_parts.append(
                f"Hypothetical setup: entry ~₹{risk.get('entry')}, "
                f"stop ₹{risk.get('stop_loss')}, targets ₹{risk.get('target_1')}"
                + (f"/₹{risk.get('target_2')}" if risk.get('target_2') else "")
                + f" (R:R {risk.get('risk_reward_1')})."
            )
        summary = " ".join(summary_parts)

        risks = ["Setup invalidated if price closes beyond the stop level."]
        if missing:
            risks.append("Some evidence is incomplete; treat confidence accordingly.")

        invalidation = []
        if risk.get("stop_loss") is not None:
            d = "below" if bias == "LONG" else "above"
            invalidation.append(f"Daily close {d} ₹{risk['stop_loss']} invalidates the thesis.")
        invalidation.append("Adverse shift in market/sector direction invalidates the bias.")

        commentary = (
            "Trade levels are computed by the deterministic Risk Engine (ATR + "
            "structure based); this explanation does not alter them."
            if risk else "No trade setup generated for this mode."
        )

        result = AIAnalysis(
            bias=bias, confidence=conf, summary=summary,
            bullish_factors=bullish or ["No strongly positive factors."],
            bearish_factors=bearish or ["No strongly negative factors."],
            risks=risks, invalidation_conditions=invalidation,
            setup_commentary=commentary,
            missing_data_warnings=[f"{m}: data unavailable" for m in missing],
            provider=self.name, model=self.model,
            prompt_version=context.get("prompt_version", ""), grounded=True,
        )
        return result.model_dump()
