# Agents

This document defines the AI agents and logical components within the AI Support Bot ecosystem.

## 1. Crypto Analyst Agent (Core)

**Role**: Senior Cryptocurrency Trader & Technical Analyst
**Responsibilities**:

- Analyze market trends using technical indicators (RSI, MACD, Bollinger Bands).
- Identify candlestick patterns (e.g., Hammer, Shooting Star).
- Provide actionable trading signals (Entry, Stop Loss, Take Profit).
- Generate comprehensive market reports.
  **Tools**:
- `services/ai_service.py`: Main interface for AI analysis.
- `services/indicators.py`: Technical analysis calculations.
- `services/patterns.py`: Pattern recognition logic.
- `services/charting.py`: Visualizing market data.

## 2. Market Monitor Agent (Background)

**Role**: 24/7 Market Watchdog
**Responsibilities**:

- Continuously monitor watchlist symbols.
- Detect price movements and technical signals in real-time.
- Trigger alerts when pre-defined conditions are met.
  **Tools**:
- `tasks/monitor.py`: Scheduled monitoring task.
- `services/data_fetcher.py`: Real-time data acquisition.

## 3. Risk Manager Agent

**Role**: Position Sizing & Risk Control Specialist
**Responsibilities**:

- Calculate optimal position sizes based on account balance and risk tolerance.
- Suggest leverage settings.
- Ensure trades align with user-defined risk parameters.
  **Tools**:
- `handlers/commands.py` (`set_risk`, `calc_position`): User interaction for risk settings.

## 4. Notification Agent

**Role**: Communication Bridge
**Responsibilities**:

- Format and deliver alerts to users via Telegram.
- Handle user interactions and command routing.
  **Tools**:
- `services/notification.py`: Message formatting and delivery.
- `handlers/`: Command and callback handling.
