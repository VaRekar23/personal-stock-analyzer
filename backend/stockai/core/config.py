"""Application configuration.

Non-sensitive, runtime-tunable settings (strategy weights, thresholds, cache
TTLs, provider/model selection, risk assumptions) live here with defaults and
can be overridden via the system.configuration table (Settings page).
Sensitive values (DB/Redis URLs, API keys) come only from environment.
"""
import os
from pathlib import Path
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent  # backend/stockai
CONFIG_DIR = ROOT_DIR / "config"


def _env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


# --- Secrets / infra (environment only) ---
DATABASE_URL = _env("DATABASE_URL")
REDIS_URL = _env("REDIS_URL")

# --- API credentials (environment only; never sent to the frontend) ---
OPENAI_API_KEY = _env("OPENAI_API_KEY")
ZERODHA_API_KEY = _env("ZERODHA_API_KEY")
ZERODHA_API_SECRET = _env("ZERODHA_API_SECRET")
ZERODHA_ACCESS_TOKEN = _env("ZERODHA_ACCESS_TOKEN")

# --- Provider selection ---
DATA_PROVIDER = _env("DATA_PROVIDER", "mock")
FUNDAMENTAL_PROVIDER = _env("FUNDAMENTAL_PROVIDER", "mock")
NEWS_PROVIDER = _env("NEWS_PROVIDER", "mock")
AI_PROVIDER = _env("AI_PROVIDER", "mock")
AI_MODEL = _env("AI_MODEL", "mock-analyst-v1")
AI_TEMPERATURE = float(_env("AI_TEMPERATURE", "0.1"))
AI_MAX_TOKENS = int(_env("AI_MAX_TOKENS", "1200"))

# A provider is "live" only when its credentials/config are verified. All mock.
LIVE_PROVIDERS: dict[str, bool] = {
    "zerodha": False,
    "fundamental": False,
    "news": False,
    "ai": AI_PROVIDER != "mock",
}


def load_weights() -> dict:
    """Strategy scoring weights — configurable, documented, not hard-coded."""
    path = CONFIG_DIR / "weights.yaml"
    with open(path, "r") as f:
        return yaml.safe_load(f)


# Default runtime settings (overridable via Settings page / DB).
DEFAULT_SETTINGS = {
    "risk": {
        "account_capital": 1000000,      # ₹ hypothetical capital for sizing
        "risk_per_trade_pct": 1.0,       # % of capital risked per trade
        "atr_stop_multiplier_swing": 1.5,
        "atr_target1_multiplier_swing": 2.0,
        "atr_target2_multiplier_swing": 3.5,
        "atr_stop_multiplier_intraday": 1.0,
        "atr_target1_multiplier_intraday": 1.2,
        "atr_target2_multiplier_intraday": 2.0,
    },
    "cache": {
        "analysis_ttl_seconds": 3600,
        "scanner_ttl_seconds": 1800,
        "market_data_ttl_seconds": 300,
        "ai_ttl_seconds": 86400,
    },
    "thresholds": {
        "shortlist_min_score": 60,      # only run AI on finalists above this
        "shortlist_top_n": 8,
        "stale_market_minutes": 20,
        "stale_fundamental_days": 120,
    },
    "providers": {
        "data": DATA_PROVIDER,
        "fundamental": FUNDAMENTAL_PROVIDER,
        "news": NEWS_PROVIDER,
        "ai": AI_PROVIDER,
        "ai_model": AI_MODEL,
    },
}
