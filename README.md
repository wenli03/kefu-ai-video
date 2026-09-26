# E-commerce AI Video Customer Service

基于 **LiveKit Agents** + **LangChain** 的电商AI视频客服系统。

> **v3.0 · 全栈 AI Agent** — 通过 117 项测试，覆盖 LangGraph / Multi-Agent / LangSmith / FastAPI / React

## 项目概述

这是一个AI驱动的视频客服系统，为电商平台提供智能化的客户服务体验。客户可以通过视频与AI数字人客服进行实时交互，获得商品咨询、订单查询、售后处理等服务。

### 核心能力

- **视频客服**：基于 LiveKit WebRTC 的实时音视频通信
- **数字人形象**：使用 Lemonslice 生成的AI客服形象
- **智能问答**：LangChain + RAG 驱动的商品知识检索
- **订单服务**：订单状态查询、物流追踪、退换货处理
- **商品推荐**：基于客户偏好的智能推荐

### v3.0 新增能力

- **LangGraph 流程编排**：StateGraph 实现 START → Router → Agent → Response → END 工作流
- **Multi-Agent 架构**：Supervisor 模式，ProductAgent / OrderAgent / SupportAgent 三专家协作
- **LangSmith 集成**：全链路 Tracing、Evaluation Harness（8条 Golden Dataset）、Cost Tracking
- **FastAPI REST API**：/api/chat、/api/session、/api/metrics、/api/health、/api/eval、/api/cost、/api/traces
- **LiteLLM 模型路由**：按复杂度自动选模型（SIMPLE→gpt-4o-mini, STANDARD→gpt-4o, ADVANCED→gpt-4o）
- **本地模型部署**：Ollama (qwen2:7b) 作为最终降级兜底，零成本运行
- **React/Next.js 前端**：Next.js 14 + TypeScript 聊天界面，实时指标面板

### 生产保障 (P0)

- **熔断降级**：Circuit Breaker 状态机 + GPT-4o → GPT-4o-mini 自动降级
- **限流防护**：Token Bucket 算法，每用户每分钟 60 次请求上限
- **安全检测**：手机号/身份证/银行卡自动识别 + AES-GCM 加密存储
- **监控告警**：实时指标采集（请求量/错误率/P95延迟）+ 规则告警
- **备份恢复**：ChromaDB 定时全量备份 + 会话归档 + 完整性校验
- **健康检查**：6 个外部服务每 30 秒探测，异常自动触发降级

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│           Frontend (Next.js 14 + React 18 + TypeScript)      │
└────────────────────────────┬────────────────────────────────┘
                             │ REST API / WebRTC
┌────────────────────────────▼────────────────────────────────┐
│              FastAPI Backend (REST API Layer)                 │
│         /api/chat  /api/health  /api/metrics  /api/eval      │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│           LangGraph StateGraph (流程编排引擎)                  │
│     START → Router → [Product|Order|Support] → Response → END│
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│            Multi-Agent Supervisor (多Agent协作)                │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│   │ ProductAgent │  │  OrderAgent  │  │  SupportAgent    │  │
│   └──────────────┘  └──────────────┘  └──────────────────┘  │
│                             │                                 │
│  ┌──────────────────────────▼─────────────────────────────┐  │
│  │         LiteLLM Router (模型路由 + 成本优化)              │  │
│  │   SIMPLE → gpt-4o-mini  |  STANDARD → gpt-4o           │  │
│  │   ADVANCED → gpt-4o     |  FALLBACK → ollama/qwen2:7b  │  │
│  └────────────────────────────────────────────────────────┘  │
│                             │                                 │
│  ┌──────────────────────────▼─────────────────────────────┐  │
│  │    LangSmith (Tracing + Eval + Cost Tracking)           │  │
│  └────────────────────────────────────────────────────────┘  │
│                             │                                 │
│  ┌──────────────────────────▼─────────────────────────────┐  │
│  │              LangChain RAG Engine                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │  │
│  │  │  ChromaDB   │  │  Embeddings │  │  Product Data  │  │  │
│  │  └─────────────┘  └─────────────┘  └────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 实时通信 | LiveKit | WebRTC 音视频基础设施 |
| 语音识别 | Deepgram | 实时语音转文字 |
| 大语言模型 | OpenAI GPT-4o | 对话理解与生成 |
| 语音合成 | Cartesia | 文字转语音 |
| 数字人 | Lemonslice | AI视频形象生成 |
| RAG框架 | LangChain | 知识检索增强生成 |
| 流程编排 | LangGraph | StateGraph 多Agent工作流 |
| Agent框架 | Multi-Agent Supervisor | 意图路由 + 专家分工 |
| 可观测性 | LangSmith | Tracing / Eval / Cost Tracking |
| 模型路由 | LiteLLM | 复杂度分级 + 自动选模型 |
| 本地模型 | Ollama (qwen2:7b) | 零成本降级兜底 |
| 后端API | FastAPI | REST API + CORS + Pydantic |
| 前端 | Next.js 14 + React 18 | TypeScript 聊天UI |
| 向量数据库 | ChromaDB | 商品知识存储 |
| 嵌入模型 | OpenAI Embeddings | 文本向量化 |

## 快速开始

### 前置要求

- Python 3.10+
- LiveKit Cloud 账号（或本地 LiveKit Server）
- API Keys:
  - OpenAI API Key
  - Deepgram API Key
  - Cartesia API Key
  - LiveKit API Key/Secret

### 安装

```bash
# 克隆项目
cd ecommerce-video-cs

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -e .

# 复制环境配置
cp .env.example .env
# 编辑 .env 填入你的 API Keys
```

### 运行

```bash
# 开发模式（带热重载）
python src/agent.py dev

# 或控制台模式（本地测试）
python src/agent.py console
```

### 启动 FastAPI 后端

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# API 端点：
# POST /api/chat       — 发送消息获取AI回复
# GET  /api/health     — 健康检查
# GET  /api/metrics    — 系统指标
# GET  /api/cost       — 成本追踪
# POST /api/eval       — 运行评估
# GET  /api/traces     — 查看追踪记录
```

### 启动前端

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
```

### 运行测试

```bash
.venv\Scripts\python.exe -m pytest tests/ -v
# 117 passed
```

### 连接前端

使用 [LiveKit Agents Playground](https://agents-playground.livekit.io) 连接测试：

1. 打开 Playground
2. 输入你的 LiveKit 项目 URL
3. 点击 "Connect"
4. 开始与AI客服对话！

## 项目结构

```
ecommerce-video-cs/
├── src/
│   ├── agent.py              # 主入口
│   ├── agent/
│   │   ├── ecommerce_agent.py  # 电商客服Agent (Function Calling)
│   │   └── multi_agent.py      # Multi-Agent Supervisor
│   ├── graph/
│   │   └── workflow.py         # LangGraph StateGraph 工作流
│   ├── api/
│   │   └── server.py           # FastAPI REST API
│   ├── tools/
│   │   ├── product_tools.py    # 商品工具
│   │   └── order_tools.py      # 订单工具
│   ├── knowledge/
│   │   └── rag_engine.py       # RAG知识引擎
│   └── utils/
│       ├── logging.py            # 结构化日志
│       ├── resilience.py         # 熔断降级 + 模型降级链 (含Ollama)
│       ├── security.py           # 加密 + 限流 + 敏感信息检测
│       ├── monitoring.py         # 指标采集 + 告警 + 健康检查
│       ├── backup.py             # 备份管理 + 会话归档
│       ├── langsmith_integration.py  # LangSmith Tracing + Eval + Cost
│       └── litellm_router.py     # LiteLLM 模型路由 + 成本优化
├── frontend/                   # Next.js 14 React 前端
│   ├── src/app/
│   │   ├── layout.tsx
│   │   └── page.tsx            # 聊天UI + 指标面板
│   ├── next.config.js
│   └── package.json
├── data/
│   ├── products/               # 商品数据
│   └── knowledge_base/         # 知识库
├── tests/                      # 测试（117项）
├── docs/                       # 文档
│   ├── demo.html               # 交互式演示 (v3.0)
│   ├── screenshots/            # 操作截图
│   ├── 操作指南.md             # 操作指南
│   └── 生产就绪测试报告.md     # 生产就绪报告
├── scripts/                    # 脚本
├── _base-livekit/              # LiveKit Agents 上游（参考）
├── pyproject.toml
├── .env.example
└── README.md
```

## 功能演示

### 交互式演示页面

打开 `docs/demo.html` 查看专业级交互式演示控制台 (v2.0)，包含：

- 深色主题三栏布局（数字人客服 | 实时对话 | 工具与日志）
- 4个业务场景一键演示（商品咨询、订单查询、退换货、智能推荐）
- 6个生产保障演示（熔断降级、限流防护、安全检测、监控面板、备份恢复、健康检查）
- 基础设施监控卡片（熔断器状态、限流计数、加密类型、健康评分）
- 实时工具调用状态指示（绿色高亮）
- 结构化日志面板（等宽字体，颜色分级）

### 操作指南

详见 [docs/操作指南.md](docs/操作指南.md)，包含13张完整界面截图、4个业务场景和6个生产保障模块的详细操作流程。

### 商品咨询

```
客户：我想找一款适合跑步的耳机
AI客服：好的，我为您推荐智能蓝牙耳机 Pro...
```

### 订单查询

```
客户：我的订单 ORD20240101001 到哪了？
AI客服：您的订单已发货，顺丰速运承运...
```

### 退换货

```
客户：我想退掉刚收到的鞋子
AI客服：好的，请问退换原因是什么？...
```

## 结构化日志（Structured Logging）

本项目按照 [code-review.md](../../_upstream/activepieces-src/.agents/skills/review-logging-patterns/references/code-review.md) 的最佳实践，实现了 Python 版本的结构化日志模式：

### 核心模式

| 模式 | TypeScript/evlog | Python 实现 |
|------|------------------|-------------|
| 会话级日志 | `useLogger(event)` | `SessionLogger("name", **ctx)` |
| 上下文累积 | `log.set({...})` | `log.set(key=value)` |
| 宽事件输出 | 自动 `emit()` | `log.info("event")` 单行输出全部上下文 |
| 结构化错误 | `createError({message, why, fix, cause})` | `AgentError.wrap(exc, message=, fix=, step=)` |

### 示例

```python
from utils.logging import SessionLogger, AgentError

# 会话级日志（类似 useLogger）
log = SessionLogger("session", room=ctx.room.name)
log.set(user={"id": customer_id})
log.set(cart={"items": 3, "total": 299.00})
log.info("checkout_completed", payment_method="alipay")
# 输出: [session_started] {"room": "RM_abc", "user": {"id": "C001"}, "cart": {"items": 3, "total": 299.0}, "payment_method": "alipay"}

# 结构化错误（类似 createError）
try:
    await process_order()
except Exception as exc:
    raise AgentError.wrap(
        exc,
        message="订单处理失败",
        step="process_order",
        fix="请检查订单数据后重试"
    )
```

### 设计原则

1. **单次输出**：每个操作只输出一条日志，包含所有累积的上下文（避免多条散乱的 log）
2. **结构化错误**：错误包含 message（发生了什么）、why（根因）、fix（如何修复）、step（哪一步出错）
3. **会话隔离**：每个客户会话有独立的 logger，上下文不会混淆
4. **降级友好**：RAG 搜索失败时自动降级为关键词搜索，并记录 warning

## 二次开发

### 添加新工具

在 `src/tools/` 下创建新工具文件，然后在 `ecommerce_agent.py` 中注册：

```python
@function_tool
async def my_new_tool(self, context: RunContext, param: str) -> str:
    """工具描述..."""
    return "result"
```

### 扩展知识库

在 `data/knowledge_base/` 添加 Markdown 文件，运行：

```bash
python scripts/ingest_knowledge.py
```

## 参考项目

- [LiveKit Agents](https://github.com/livekit/agents) - 实时AI Agent框架
- [LangChain](https://github.com/langchain-ai/langchain) - LLM应用开发框架

## 许可

MIT License
