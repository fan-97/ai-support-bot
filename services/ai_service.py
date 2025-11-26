import traceback
import json
import logging
import google.generativeai as genai
from PIL import Image
from config.settings import GEMINI_API_KEY, GEMINI_MODEL

# 初始化 Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

def analyze_with_gemini(image_buf, symbol, interval, df, funding_rate, patterns=None, prompt_override=None):
    """通用 AI 分析函数"""
    try:
        image_buf.seek(0)
        img = Image.open(image_buf)
        
        # 提取最新指标数据
        last_row = df.iloc[-1]
        rsi = last_row['rsi']
        macd_dif = last_row['macd']
        macd_hist = last_row['macd_hist']
        macd_signal = last_row['macd_signal']
        close_price = last_row['close']
        
        # 默认 Prompt (自动监控用)
        base_prompt = f"""

        You are a Top-Tier Crypto Analyst. Analyze {symbol} on {interval} timeframe.
        Image provided contains: Candlesticks + MACD Subplot + Volume.

        Your job is to read the chart visually and combine it with the given numeric indicators.

        DATA:
        - Current Price: {close_price}
        - RSI: {rsi:.1f}
        - Funding Rate: {funding_rate:.4f}%
        - MACD: DIF={macd_dif:.4f}, Histogram={macd_hist:.4f}
        - Detected Pattern (numerical scan): {patterns if patterns else "None"}

        ANALYSIS RULES:
        1. Identify the visual market structure (trend + pattern if exists).
        2. Detect momentum strength and any bullish/bearish divergence.
        3. Determine key price levels visible on the chart (support & resistance).
        4. Action should be based on risk-adjusted probability, not guessing.

        SCORING RULE (for "score"):
        - 0-3 → weak / choppy / low confidence
        - 4-6 → moderate probability setup
        - 7-10 → high-conviction setup

        OUTPUT FORMAT (REQUIRED):
        Return **ONLY** valid JSON. No commentary, no markdown, no explanation.

        {{
            "trend": "Bullish | Bearish | Neutral",
            "pattern": "Name of pattern or None",
            "key_levels": {
                "support": ["xxxx", "xxxx"],
                "resistance": ["xxxx", "xxxx"]
            },
            "score": 0-10,
            "reason": "Short and concise reasoning (< 300 words).",
            "action": "LONG | SHORT | WAIT",
            "confidence": "0.0 - 1.0 (probability of correctness)"
        }}

        """
        
        # 如果是手动调用 /ai，使用更详细的 Prompt
        # if prompt_override:
        #     base_prompt = prompt_override.format(
        #         symbol=symbol, interval=interval, price=close_price,
        #         rsi=rsi, funding=funding_rate, dif=macd_dif, hist=macd_hist
        #     )

        response = model.generate_content([base_prompt, img])
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        logging.error(f"AI Error: {e}")
        traceback.print_exc()   
        return {"score": 0, "reason": f"AI Error: {e}", "action": "WAIT"}
