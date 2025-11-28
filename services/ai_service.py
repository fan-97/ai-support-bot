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
    AI_TIMEOUT,
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
Act as a world-class Crypto Technical Analyst & Swing Trader. 
Your task is to analyze the {symbol} ({interval}) chart to generate a high-precision trading signal.

**INPUT DATA:**
1. **Chart Image**: Contains Candlesticks (Main), MACD (Subplot), Volume.
2. **Market Data**:
   - Current Price: {close_price}
   - RSI(14): {rsi:.2f} (Consider >70 Overbought, <30 Oversold)
   - Funding Rate: {funding_rate:.4f}% (Negative = Short Squeeze risk)
   - MACD Data: DIF={macd_dif:.4f}, Hist={macd_hist:.4f}
   - Scanner Signal: {patterns if patterns else "None"} (Verify this visually!)

**ANALYSIS PROTOCOL (Strict Order):**
1. **Visual Structure (PRIMARY)**: 
   - Look at the last 3-5 candles. Are there long wicks (rejection)? Is the body shrinking?
   - Check Volume: Is price rising on declining volume (divergence)?
   - Check MACD Image: Look for visual divergence between Price highs/lows and MACD peaks.
2. **Trend & Levels**: Identify the immediate Trendline and Key Support/Resistance zones relative to the current price.
3. **Data Confirmation (SECONDARY)**: Use RSI and Funding Rate to confirm over-extension. Do NOT trade solely on indicators.
4. **Risk Filter**: If the chart looks messy, choppy, or contradictory, output ACTION: WAIT.
5. **SL/TP**: Determine the trend and generate a trade setup with specific Entry/SL/TP levels.

**RULES FOR SL/TP:**
- **Stop Loss (SL)**: Must be placed beyond invalidation points (e.g., above swing high for Shorts).
- **Take Profit (TP)**: Must be at logical support/resistance or liquidity pools.
- **Risk/Reward**: Ensure the setup offers decent R:R ratio (>1.5 is preferred).
- If the signal is weak or contradictory, set action to "WAIT" and leave SL/TP as null.

**OUTPUT RULES:**
- **Reasoning**: Must be bullet-point style, ultra-concise (< 50 words). Focus on "Why now?".
- **Score**: 0-10. (8+ requires strict confluence of Trend + Pattern + Indicator).
- **JSON ONLY**: No markdown blocks (```), no conversational text.

**JSON SCHEMA:**
{{
  "trend": "Bullish | Bearish | Neutral",
  "pattern": "Chart pattern name. Answer in Chinese.",
  "key_levels": "Describe visually (e.g., 'Resistance at recent high ~{close_price*1.02:.2f}')",
  "score": 0-10,
  "reason": "Concise logic (bullet points) . Answer in Chinese.",
  "action": "LONG | SHORT | WAIT",
  "confidence": 0.0-1.0,
  "trade_setup": {{
    "entry": {{price}},
    "sl": float (Price level),
    "tp": float (Price level),
    "rr_ratio": float (e.g. 2.1)
    }}
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
        timeout=AI_TIMEOUT,
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

    resp = client.chat.completions.create(
        model=use_model,
        extra_headers=extra_headers,
        messages=[
                {
                    "role": "system",
                    "content": "You are a concise crypto market analyst. Reply only JSON."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": b64}
                    ]
                }
            ],
            temperature=0.3,
    )

    raw_text = resp.choices[0].message.content.replace("```json", "").replace("```", "").strip()
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
        logging.exception(f"AI Error: {exc}")
        return _fallback_response(f"AI Error: {exc}")
