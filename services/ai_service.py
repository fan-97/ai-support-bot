import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI

from config.settings import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    SITE_URL,
    SITE_NAME,
    AI_TIMEOUT,
    KLINE_LIMIT,
)

_openrouter_client = None

# Load prompt content
PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "prompt.md"
try:
    SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding="utf-8")
except Exception as e:
    logging.error(f"Failed to read prompt file: {e}")
    SYSTEM_PROMPT = "You are a crypto analyst. Reply JSON."


def _build_user_message(symbol: str, interval: str, df, funding_rate: float, open_interest: float, patterns) -> str:
    """Build the user message with data sequences."""
    # Number of candles considered is configurable
    recent_df = df.tail(KLINE_LIMIT)
    
    # Format sequences
    dates = recent_df.index.strftime('%Y-%m-%d %H:%M').tolist()
    closes = recent_df["close"].tolist()
    highs = recent_df["high"].tolist()
    lows = recent_df["low"].tolist()
    volumes = recent_df["volume"].tolist()
    
    # Indicators
    ema20 = recent_df["ema20"].tolist() if "ema20" in recent_df else []
    rsi7 = recent_df["rsi7"].tolist() if "rsi7" in recent_df else []
    rsi14 = recent_df["rsi"].tolist()
    macd = recent_df["macd"].tolist()
    macd_hist = recent_df["macd_hist"].tolist()
    
    # New Indicators
    k = recent_df["k"].tolist() if "k" in recent_df else []
    d = recent_df["d"].tolist() if "d" in recent_df else []
    j = recent_df["j"].tolist() if "j" in recent_df else []
    upper = recent_df["bb_upper"].tolist() if "bb_upper" in recent_df else []
    lower = recent_df["bb_lower"].tolist() if "bb_lower" in recent_df else []

    last_row = df.iloc[-1]
    current_price = last_row["close"]

    return f"""
**ANALYSIS REQUEST**
Symbol: {symbol}
Interval: {interval}
Current Price: {current_price}
Funding Rate: {funding_rate:.4f}%
Open Interest: {open_interest}
Detected Patterns: {patterns if patterns else "None"}

**DATA SEQUENCES (Last {len(recent_df)} periods):**
Time: {dates}
Close: {closes}
High: {highs}
Low: {lows}
Volume: {volumes}

**INDICATOR SEQUENCES:**
EMA20: {[round(x, 2) for x in ema20]}
RSI7: {[round(x, 2) for x in rsi7]}
RSI14: {[round(x, 2) for x in rsi14]}
MACD (DIF): {[round(x, 4) for x in macd]}
MACD Hist: {[round(x, 4) for x in macd_hist]}
KDJ (K,D,J): {list(zip([round(x, 1) for x in k], [round(x, 1) for x in d], [round(x, 1) for x in j]))}
Bollinger (Upper, Lower): {list(zip([round(x, 2) for x in upper], [round(x, 2) for x in lower]))}

Please analyze this data according to your system instructions.
"""


def _get_openrouter_client():
    """Lazy init OpenRouter client."""
    global _openrouter_client
    if _openrouter_client:
        return _openrouter_client
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    _openrouter_client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
        timeout=AI_TIMEOUT,
    )
    return _openrouter_client


def _analyze_openrouter(user_msg: str, model: str = None) -> Dict[str, Any]:
    client = _get_openrouter_client()
    
    use_model = model or OPENROUTER_MODEL
    
    extra_headers = {}
    if SITE_URL:
        extra_headers["HTTP-Referer"] = SITE_URL
    if SITE_NAME:
        extra_headers["X-Title"] = SITE_NAME

    resp = client.chat.completions.create(
        model=use_model,
        extra_headers=extra_headers,
        messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_msg
                }
            ],
            temperature=0.3,
    )
    logging.info(f"AI response: {resp}")

    content = resp.choices[0].message.content.strip()
    logging.debug(f"AI raw content: {content}")

    json_block_pattern = re.compile(r"```json\s*(\{.*\})\s*```", re.IGNORECASE | re.DOTALL)
    json_match = json_block_pattern.search(content)
    if json_match:
        json_text = json_match.group(1)
    else:
        fallback_match = re.search(r"\{.*\}", content, re.DOTALL)
        if not fallback_match:
            raise json.JSONDecodeError("No JSON object found in AI response", content, 0)
        json_text = fallback_match.group(0)

    reasoning_text = json_block_pattern.sub("", content).strip()

    result = json.loads(json_text)
    result['ai_model'] = use_model
    if reasoning_text:
        result.setdefault("analysis_process", reasoning_text)
        result["raw_reasoning"] = reasoning_text
    return result


def _fallback_response(reason: str) -> Dict[str, Any]:
    return {
        "analysis_process": "N/A",
        "decision": "hold",
        "confidence": 0,
        "reasoning": reason,
        "next_watch_levels": {"resistance": [], "support": []},
        "position_size_usd": 0,
        "leverage": 0,
        "stop_loss": None,
        "take_profit": None,
    }


async def analyze_with_ai(symbol: str, interval: str, df, funding_rate: float, open_interest: float, patterns=None, model: str = None) -> Dict[str, Any]:
    """
    Unified entry for AI analysis using OpenRouter.
    model: Optional model override (e.g. "google/gemini-flash-1.5")
    """
    user_msg = _build_user_message(symbol, interval, df, funding_rate, open_interest, patterns)
    try:
        return await asyncio.to_thread(_analyze_openrouter, user_msg, model)
    except json.JSONDecodeError as exc:
        logging.error(f"AI JSON parse error: {exc}")
        return _fallback_response(f"JSON parse error: {exc}")
    except Exception as exc:
        logging.exception(f"AI Error: {exc}")
        return _fallback_response(f"AI Error: {exc}")
