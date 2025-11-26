# AI 智能客服：从概念到智能

> 从零开始构建生产级 AI 客户支持代理 (Agent) 的完整旅程。

## 📖 项目概述

**AI Support Bot** 是一个兼具教育意义与专业深度的项目，旨在演示构建智能对话代理的端到端流程。与简单的 API 包装教程不同，本项目从 **大语言模型 (LLM)** 的基础概念出发，逐步构建一个能够处理真实客户咨询、具备上下文感知能力的复杂系统。

**核心理念：**

- **第一性原理：** 在通过代码实现之前，先理解 _为什么_ 要这样做。
- **模块化设计：** 组件解耦，确保系统的可扩展性与维护性。
- **生产级标准：** 关注错误处理、日志记录、性能优化与安全性。

## 🏗️ 架构概览

系统采用模块化架构设计，以确保可维护性和扩展性：

1.  **交互层 (Interaction Layer)**：处理用户输入/输出（CLI 命令行、Web API）。
2.  **编排引擎 (Orchestration Engine)**：管理对话流转与工具选择 (Agent Core)。
3.  **知识库 (RAG Knowledge Base)**：基于向量检索 (Vector Search) 获取相关文档上下文。
4.  **LLM 网关 (LLM Gateway)**：模型交互的抽象层（支持 OpenAI, Gemini, 本地 LLM 等）。
5.  **记忆系统 (Memory System)**：管理会话状态与历史上下文。

## 🚀 路线图 (Roadmap)

本项目遵循 "从 0 到 1" 的实施路径：

- [ ] **第一阶段：基石 (Foundations)**

  - 理解 LLM 与提示工程 (Prompt Engineering)
  - 配置 Python 开发环境
  - 实现 LLM 的 "Hello World"

- [ ] **第二阶段：知识大脑 (RAG)**

  - 向量数据库 (Vector DB) 与 Embeddings
  - 文档摄入与处理流水线
  - 上下文检索逻辑

- [ ] **第三阶段：Agent 核心 (The Agentic Core)**

  - 对话历史与记忆管理
  - 意图识别 (Intent Classification)
  - 工具使用与函数调用 (Function Calling)

- [ ] **第四阶段：接口与部署 (Interface & Deployment)**
  - 基于 FastAPI 构建 REST API
  - WebSocket 流式响应
  - Docker 容器化与云端部署

## 🛠️ 技术栈 (Tech Stack)

- **开发语言:** Python 3.10+
- **LLM 编排:** LangChain / 自研轻量级实现 (待定)
- **向量数据库:** ChromaDB / FAISS
- **API 框架:** FastAPI
- **运行环境:** Docker

## 🚦 快速开始 (Getting Started)

_敬请期待。我们正在搭建基础设施。_
