"""Central version registry. Every analysis is traceable to these versions.

When strategy/indicator/prompt logic changes materially, bump the version here
(e.g. swing_v1 -> swing_v2) instead of silently replacing behaviour. This is
essential for EVALS, caching and future backtesting.
"""

INDICATOR_VERSION = "technical_v1"

STRATEGY_VERSIONS = {
    "long_term": "long_term_v1",
    "swing": "swing_v1",
    "intraday": "intraday_v1",
}

PROMPT_VERSIONS = {
    "long_term": "longterm_analysis_v1",
    "swing": "swing_analysis_v1",
    "intraday": "intraday_analysis_v1",
}

SCORING_VERSION = "scoring_v1"
RISK_VERSION = "risk_v1"
