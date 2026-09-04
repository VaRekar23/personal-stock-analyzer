"""Versioned prompt templates. Centralized & configurable (not scattered).

Grounding rules are baked into the system instruction: the model may only use
facts present in the supplied structured context, must not compute indicators
or invent trade levels, and must flag missing data.
"""

SYSTEM_GROUNDING = (
    "You are a disciplined equity research explanation layer. You DO NOT "
    "calculate indicators or invent prices, trade levels, RSI/EMA/ATR/VWAP or "
    "fundamentals. You ONLY explain the structured facts provided. If a fact is "
    "not in the context, say data is unavailable. Trade levels from the Risk "
    "Engine are authoritative; never override them. Use research language "
    "(bias, potential setup, hypothetical), never guarantees."
)

_TEMPLATES = {
    "long_term": (
        "Explain the long-term investment picture for {symbol} using the score "
        "breakdown, fundamentals and long-term technical context provided."
    ),
    "swing": (
        "Explain the swing-trading setup for {symbol} using the score factors, "
        "technical features and Risk Engine trade levels provided."
    ),
    "intraday": (
        "Explain the intraday setup for {symbol} using the intraday features, "
        "market/sector direction and Risk Engine trade levels provided."
    ),
}


def build_prompt(analysis_type: str, symbol: str) -> str:
    body = _TEMPLATES.get(analysis_type, _TEMPLATES["swing"]).format(symbol=symbol)
    return f"{SYSTEM_GROUNDING}\n\nTASK: {body}\nReturn ONLY valid JSON matching the schema."
