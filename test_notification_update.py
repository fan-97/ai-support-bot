from services.notification import NotificationService

result = {
  "market_context": "BTC is bullish",
  "signal_analysis": {
    "technical": "RSI divergence",
    "volume_oi": "OI increasing",
    "sentiment": "High funding"
  },
  "confidence_score": 85,
  "decision": "SHORT",
  "trade_plan": {
    "entry_zone": "98000-99000",
    "stop_loss_price": "99500",
    "take_profit_levels": ["97000", "96000"],
    "leverage": 5,
    "position_size_usd": 100,
    "reasoning_for_size": "High confidence"
  }
}

market_data = {
    "close": 98500,
    "rsi": 75,
    "funding_rate": 0.01,
    "open_interest": 1000000
}

caption, report = NotificationService.format_report("BTCUSDT", "15m", result, market_data)
print("CAPTION:\n", caption)
print("\nREPORT:\n", report)
