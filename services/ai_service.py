import asyncio
import base64
import json
import logging
from typing import Any, Dict

from PIL import Image
from openai import OpenAI

from config.settings import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    SITE_URL,
    SITE_NAME,
)

_openrouter_client = None


def _build_prompt(symbol: str, interval: str, df, funding_rate: float, patterns) -> str:
    """Shared prompt body for all providers."""
    last_row = df.iloc[-1]
    rsi = last_row["rsi"]
    macd_dif = last_row["macd"]
    macd_hist = last_row["macd_hist"]
    macd_signal = last_row["macd_signal"]
    close_price = last_row["close"]

    return f"""
You are a Top-Tier Crypto Analyst. Analyze {symbol} on {interval} timeframe.
Data includes: Candlesticks, MACD subplot, Volume.

Numeric context:
- Price: {close_price}
- RSI: {rsi}
- Funding Rate: {funding_rate}%
- MACD: DIF={macd_dif}, Hist={macd_hist}, Signal={macd_signal}
- Detected Pattern: {patterns if patterns else "None"}

Rules:
1) Identify structure/trend/patterns
2) Momentum & divergences
3) Key levels (support/resistance)
4) Action must be risk-adjusted, not a guess

Return ONLY valid JSON with fields:
{{
  "trend": "Bullish | Bearish | Neutral",
  "pattern": "Name or None",
  "key_levels": {{"support": ["..."], "resistance": ["..."]}},
  "score": 0-10,
  "reason": "Short reasoning (<300 words)",
  "action": "LONG | SHORT | WAIT",
  "confidence": 0.0-1.0
}}
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
    )
    return _openrouter_client


def _image_to_b64(image_buf) -> str:
    image_buf.seek(0)
    encoded = base64.b64encode(image_buf.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _analyze_openrouter(image_buf, prompt: str, model: str = None) -> Dict[str, Any]:
    client = _get_openrouter_client()
    b64 = _image_to_b64(image_buf)
    
    use_model = model or OPENROUTER_MODEL
    
    extra_headers = {}
    if SITE_URL:
        extra_headers["HTTP-Referer"] = SITE_URL
    if SITE_NAME:
        extra_headers["X-Title"] = SITE_NAME

    resp = client.responses.create(
        model=use_model,
        extra_headers=extra_headers,
        instructions="You are a concise crypto market analyst. Reply only JSON.",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": b64},
                ],
            },
        ],
        temperature=0.3,
    )

    raw_text = resp.text.replace("```json", "").replace("```", "").strip()
    logging.info(f"AI response: {raw_text}")
    return json.loads(raw_text)


def _fallback_response(reason: str) -> Dict[str, Any]:
    return {
        "trend": "Neutral",
        "pattern": "Error",
        "key_levels": {"support": [], "resistance": []},
        "score": 0,
        "reason": reason,
        "action": "WAIT",
        "confidence": 0.0,
    }


async def analyze_with_ai(image_buf, symbol: str, interval: str, df, funding_rate: float, patterns=None, model: str = None) -> Dict[str, Any]:
    """
    Unified entry for AI analysis using OpenRouter.
    model: Optional model override (e.g. "google/gemini-flash-1.5")
    """
    prompt = _build_prompt(symbol, interval, df, funding_rate, patterns)

    try:
        return await asyncio.to_thread(_analyze_openrouter, image_buf, prompt, model)
    except json.JSONDecodeError as exc:
        logging.error(f"AI JSON parse error: {exc}")
        return _fallback_response(f"JSON parse error: {exc}")
    except Exception as exc:
        logging.error(f"AI Error: {exc}")
        return _fallback_response(f"AI Error: {exc}")
