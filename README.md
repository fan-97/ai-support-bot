# AI Crypto Analyst Bot (AI 加密货币分析助手)

这是一个强大的 Telegram 机器人，结合了传统技术分析与先进的 AI 人工智能洞察，旨在帮助交易者做出更明智的投资决策。本项目支持通过 OpenRouter 接入多种顶级 AI 模型（如 Google Gemini, OpenAI GPT-4, DeepSeek 等），并提供实时市场监控、专业图表生成以及智能风险管理工具。

## 🚀 功能特性 (Features)

### 🤖 强大的 AI 分析引擎

- **多模型支持**: 通过 OpenRouter 统一接口，灵活切换 **GPT-4o**, **Gemini 1.5 Pro**, **DeepSeek** 等主流大模型。
- **深度研报**: 自动生成包含**市场背景**、**技术信号**、**情绪面分析**的详细交易报告。
- **智能决策**: AI 根据盘面数据给出明确的 **买入/持有/卖出** 建议，并附带信心指数。

### 📊 专业技术分析

- **多指标集成**: 内置 **RSI**, **MACD**, **Bollinger Bands (布林带)** 等核心技术指标。
- **形态识别**: 自动识别 K 线形态（如吞没形态、启明星/黄昏星等）。
- **图表生成**: 生成包含指标叠加的专业 K 线截图，直观展示行情走势。

### 🛡 科学的风险管理

- **仓位计算**: 基于账户余额和风险偏好（Risk %），自动计算合理的开仓大小。
- **止盈止损**: AI 智能推荐止损位（Stop Loss）和分批止盈位（Take Profit）。
- **杠杆建议**: 根据波动率和风险模型推荐合适的杠杆倍数。

### 📱 便捷的 Telegram 交互

- **实时监控**: 7x24 小时自动扫描关注列表中的代币，发现机会即时推送。
- **交互式指令**: 通过 `/ai`, `/calc` 等指令快速获取分析或计算数据。
- **精美排版**: 消息格式清晰，关键信息一目了然（支持 Markdown 渲染）。

---

## � 后续计划 (Roadmap)

我们致力于将此项目打造为最全能的加密货币辅助工具。以下是未来的开发计划：

- [ ] **多交易所支持**: 扩展支持 Bybit, OKX, Bitget 等更多主流交易所的数据与交易。
- [ ] **自动交易执行**: 对接交易所 API，实现 AI 信号的一键跟单与自动执行。
- [ ] **链上数据分析**: 集成链上鲸鱼追踪、资金流向监控，提供更维度的分析视角。
- [ ] **Web 管理后台**: 开发可视化的 Web 界面，方便管理关注列表、查看历史绩效与配置机器人。
- [ ] **多渠道通知**: 除了 Telegram，增加对 **Discord**, **Slack**, **Email** 等渠道的通知支持。
- [ ] **回测系统**: 支持对 AI 策略进行历史数据回测，验证策略有效性。

---

## 🛠 安装与部署 (Installation)

### 1. 克隆项目

```bash
git clone <repository-url>
cd ai-support-bot
```

### 2. 环境准备

建议使用虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

### 3. 配置设置

复制示例配置文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入您的 API Key 和配置信息：

```ini
# Telegram Bot Token (从 @BotFather 获取)
BOT_TOKEN=your_telegram_bot_token

# OpenRouter (推荐) / AI Provider
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free

# 代理设置 (可选)
# PROXY_URL=http://127.0.0.1:7890
```

### 4. 启动机器人

```bash
python main.py
```

---

## 🐳 Docker 部署

如果您熟悉 Docker，可以使用 Docker Compose 快速启动：

1. **配置环境**: 确保 `.env` 文件已配置完毕。
2. **创建数据文件**: 确保 `watchlist.json` 存在。
   ```bash
   echo "{}" > watchlist.json
   ```
3. **启动服务**:
   ```bash
   docker-compose up -d
   ```
4. **查看日志**:
   ```bash
   docker-compose logs -f
   ```

---

## 🎮 指令列表 (Commands)

| 指令     | 描述                       | 示例                |
| :------- | :------------------------- | :------------------ |
| `/start` | 显示主菜单和仪表盘         | `/start`            |
| `/add`   | 添加代币到监控列表         | `/add BTC 1h`       |
| `/list`  | 查看当前监控列表           | `/list`             |
| `/set`   | 设置风险参数 (余额, 风险%) | `/set 1000 2`       |
| `/calc`  | 计算仓位大小               | `/calc 65000 66000` |
| `/ai`    | 手动触发 AI 分析           | `/ai ETH 4h`        |

---

## 📄 许可证 (License)

本项目采用 [MIT License](LICENSE) 开源授权。
