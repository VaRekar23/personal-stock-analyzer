"""MockFundamentalDataProvider — deterministic synthetic fundamentals.

Clearly labelled source='mock' / synthetic. Mirrors the field set a real
FundamentalDataProvider (e.g. TrueData, pending verification) would supply:
income statement, balance sheet, cash flow, valuation ratios, shareholding,
corporate actions. Values are reproducible per symbol. NOT real financials.
"""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone

from ...data.nifty50 import NAME_OF, SECTOR_OF


def _h(symbol: str, salt: str = "") -> float:
    d = int(hashlib.sha256((symbol + salt).encode()).hexdigest(), 16)
    return (d % 1000) / 1000.0  # 0..1


class MockFundamentalDataProvider:
    mode = "mock"

    async def get_fundamentals(self, symbol: str) -> dict:
        r = lambda s: _h(symbol, s)  # noqa: E731
        revenue = round(50000 + r("rev") * 800000, 1)          # ₹ cr
        rev_growth = round(2 + r("rg") * 24, 1)                 # %
        pat = round(revenue * (0.06 + r("pm") * 0.20), 1)
        pat_growth = round(-5 + r("pg") * 35, 1)
        eps = round(10 + r("eps") * 120, 2)
        ebitda_margin = round(12 + r("em") * 30, 1)
        roe = round(8 + r("roe") * 24, 1)
        roce = round(9 + r("roce") * 22, 1)
        de = round(r("de") * 1.8, 2)
        pe = round(12 + r("pe") * 45, 1)
        pb = round(1 + r("pb") * 9, 1)
        div_yield = round(r("dy") * 3.2, 2)
        ocf = round(pat * (1 + r("ocf") * 0.6), 1)
        capex = round(ocf * (0.2 + r("cx") * 0.4), 1)
        fcf = round(ocf - capex, 1)
        promoter = round(35 + r("prom") * 40, 1)
        fii = round(5 + r("fii") * 30, 1)
        dii = round(5 + r("dii") * 25, 1)
        public = round(max(0.0, 100 - promoter - fii - dii), 1)
        now = datetime.now(timezone.utc).isoformat()
        return {
            "symbol": symbol,
            "company_name": NAME_OF.get(symbol, symbol),
            "sector": SECTOR_OF.get(symbol),
            "source": "mock",
            "retrieved_at": now,
            "period": "FY2025 (synthetic)",
            "income_statement": {
                "revenue": revenue, "revenue_growth_pct": rev_growth,
                "ebitda_margin_pct": ebitda_margin,
                "pat": pat, "pat_growth_pct": pat_growth, "eps": eps,
            },
            "balance_sheet": {
                "total_assets": round(revenue * (1.5 + r("ta")), 1),
                "equity": round(revenue * (0.6 + r("eq") * 0.8), 1),
                "debt": round(revenue * de * 0.4, 1),
                "cash": round(revenue * (0.05 + r("cash") * 0.2), 1),
                "net_debt": round(revenue * de * 0.4 - revenue * 0.1, 1),
            },
            "cash_flow": {"operating_cash_flow": ocf, "capex": capex, "free_cash_flow": fcf},
            "valuation": {
                "pe": pe, "pb": pb, "roe_pct": roe, "roce_pct": roce,
                "debt_to_equity": de, "dividend_yield_pct": div_yield,
                "ebitda_margin_pct": ebitda_margin,
            },
            "shareholding": {
                "promoter_pct": promoter, "fii_pct": fii,
                "dii_pct": dii, "public_pct": public,
            },
            "corporate_actions": [
                {"action_type": "dividend", "ex_date": "2025-07-15",
                 "details": {"amount_per_share": round(eps * 0.2, 2)}, "source": "mock"},
            ],
        }
