import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI
from services.data_processor import CryptoDataProcessor

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


def _build_user_message(symbol: str, interval: str, df, df_btc, balance: float) -> str:
    """Build the user message with target + BTC 4h data (no merge)."""
    processor = CryptoDataProcessor(limit=KLINE_LIMIT)  # 只发给AI最近N根K线

    df_target = processor.calculate_target_indicators(df)
    df_btc = processor.calculate_indicators(df_btc)

    json_output = processor.format_for_ai(df_target, df_btc, symbol=symbol, balance=balance)
    return json_output


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
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
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
        fallback_match = re.search(r"\\{.*\\}", content, re.DOTALL)
        if not fallback_match:
            raise json.JSONDecodeError("No JSON object found in AI response", content, 0)
        json_text = fallback_match.group(0)

    reasoning_text = json_block_pattern.sub("", content).strip()

    result = json.loads(json_text)
    result["ai_model"] = use_model
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


async def analyze_with_ai(symbol: str, interval: str, df, df_btc, balance: float, model: str = None) -> Dict[str, Any]:
    """
    Unified entry for AI analysis using OpenRouter.
    model: Optional model override (e.g. "google/gemini-flash-1.5")
    """
    user_msg = _build_user_message(symbol, interval, df, df_btc, balance)
    try:
        return await asyncio.to_thread(_analyze_openrouter, user_msg, model)
    except json.JSONDecodeError as exc:
        logging.error(f"AI JSON parse error: {exc}")
        return _fallback_response(f"JSON parse error: {exc}")
    except Exception as exc:
        logging.exception(f"AI Error: {exc}")
        return _fallback_response(f"AI Error: {exc}")
