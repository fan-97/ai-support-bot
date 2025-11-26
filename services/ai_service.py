import json
import logging
import google.generativeai as genai
from PIL import Image
from config.settings import GEMINI_API_KEY, GEMINI_MODEL

# 初始化 Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

def analyze_with_gemini(image_buf, symbol, interval, df, funding_rate, prompt_override=None):
    """通用 AI 分析函数"""
    try:
        image_buf.seek(0)
        img = Image.open(image_buf)
        
        # 提取最新指标数据
        print
        rsi = df['rsi']
        macd_dif = df['macd']
        macd_hist = df['macd_hist']
        macd_signal = df['macd_signal']
        close_price = df['close']
        
        # 默认 Prompt (自动监控用)
        base_prompt = f"""
        Role: Crypto Expert Trader.
        Symbol: {symbol} ({interval}) | Price: {close_price}
        
        **Technical Indicators:**
        1. **RSI**: {rsi:.1f}
        2. **Funding Rate**: {funding_rate:.4f}%
        3. **MACD**: DIF={macd_dif:.4f}, Histogram={macd_hist:.4f} (Check for divergence or crossover)
        
        **Visual Task:** Analyze the chart image (Candles + MACD + Volume).
        Identify patterns (Head & Shoulders, Flags, Pinbars) and Trend status.
        
        **Output ONLY JSON:**
        {{
            "score": 0-10 (10 = Strong Short Signal),
            "reason": "Technical analysis summary.",
            "action": "WAIT" or "SHORT"
        }}
        """
        
        # 如果是手动调用 /ai，使用更详细的 Prompt
        if prompt_override:
            base_prompt = prompt_override.format(
                symbol=symbol, interval=interval, price=close_price,
                rsi=rsi, funding=funding_rate, dif=macd_dif, hist=macd_hist
            )

        response = model.generate_content([base_prompt, img])
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return {"score": 0, "reason": f"AI Error: {e}", "action": "WAIT"}
