# AI Crypto Analyst Bot

A powerful Telegram bot that combines technical analysis with AI-powered insights to help traders make informed decisions. The bot supports multiple AI providers (Gemini, OpenAI, DeepSeek) and offers real-time market monitoring, chart generation, and risk management tools.

## Features

- **🤖 Multi-Provider AI Analysis**:

  - Supports **Google Gemini** (Vision capabilities).
  - Supports **OpenAI** (GPT-4o with Vision).
  - Supports **DeepSeek** (Text-based analysis).
  - Generates detailed market reports including trend, patterns, key levels, and action recommendations.

- **📊 Technical Analysis**:

  - **Indicators**: RSI, MACD (DIF, DEA, Histogram).
  - **Pattern Recognition**: Automatically detects bearish patterns (e.g., Shooting Star, Bearish Engulfing, Evening Star).
  - **Chart Generation**: Generates professional candlestick charts with overlay indicators.

- **🛡 Risk Management**:

  - **Position Calculator**: Calculates position size and leverage based on entry, stop-loss, and risk percentage.
  - **Risk Settings**: customizable balance and risk percentage per user.

- **📱 Telegram Integration**:
  - **Watchlist**: Manage a list of coins to monitor.
  - **Scanner**: Automated monitoring task that checks for trading signals.
  - **Interactive Buttons**: Easy-to-use interface for common actions.

## Installation

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd ai-support-bot
   ```

2. **Create a virtual environment** (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your API keys and settings:

   ```ini
   # Telegram
   BOT_TOKEN=your_telegram_bot_token

   # AI Provider (gemini | openai | deepseek)
   AI_PROVIDER=gemini

   # Google Gemini
   GEMINI_API_KEY=your_gemini_api_key
   GEMINI_MODEL=gemini-2.5-flash

   # OpenAI
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_MODEL=gpt-4o-mini

   # DeepSeek
   DEEPSEEK_API_KEY=your_deepseek_api_key
   DEEPSEEK_MODEL=deepseek-chat

   # Proxy (Optional)
   PROXY_URL=http://127.0.0.1:7890
   ```

## Usage

Run the bot:

```bash
python main.py
```

### Commands

| Command  | Description                             | Example             |
| :------- | :-------------------------------------- | :------------------ |
| `/start` | Show the main menu and dashboard.       | `/start`            |
| `/add`   | Add a symbol to the watchlist.          | `/add BTC 1h`       |
| `/list`  | Show current watchlist.                 | `/list`             |
| `/set`   | Set risk parameters (Balance, Risk %).  | `/set 1000 2`       |
| `/calc`  | Calculate position size.                | `/calc 65000 66000` |
| `/ai`    | Perform manual AI analysis on a symbol. | `/ai ETH 4h`        |

## Project Structure

- `main.py`: Entry point of the application.
- `handlers/`: Telegram command and callback handlers.
- `services/`: Core logic (AI, Data Fetching, Charting, Indicators).
- `tasks/`: Background tasks (Monitoring).
- `config/`: Configuration and settings.
- `utils/`: Utility functions and decorators.

## License

[MIT License](LICENSE)
