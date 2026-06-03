# AI Video Customer Service System — Demo Design

> Date: 2026-06-01 | Status: Approved

## 1. Project Overview

| Dimension | Decision |
|-----------|----------|
| **Project Name** | AI Video CS (`kefu_ai_video`) |
| **Demo Purpose** | Architect/Full-stack job interviews + Client presentation |
| **Tech Stack Approach** | Hybrid: CC System (Java Spring Boot), remaining services (Node.js/TypeScript) |
| **Media Server** | SRS 5.0 (Docker `ossrs/srs:5`) |
| **AI Capabilities** | ASR (Browser Web Speech API) + DeepSeek API + ChromaDB RAG |
| **Digital Human** | Pre-recorded AI agent reply videos, matched by answer keywords |
| **Clients** | Full Web: Customer mobile web + Agent web panel + Admin dashboard |
| **Database** | Redis (session/cache) + SQLite (persistence) |
| **Deployment** | Docker Compose (SRS + Redis + ChromaDB) + local dev servers |

### Demo Flow

One machine opens 3 browser windows simultaneously:
- **Window A**: Customer mobile web (simulates WeChat Mini Program)
- **Window B**: Agent workbench (simulates Windows C++ client)
- **Window C**: Admin monitoring dashboard

### Interview Talking Points

- **Architecture design**: Million-concurrency video processing, 1.2PB/day CDN traffic
- **Gateway optimization**: Distributed gateway with P99 < 200ms API latency
- **Cost optimization**: H.265 encoding optimization, ~40% CDN cost reduction
- **Business value**: Serves 1.2M+ insurance agents

## 2. Architecture

### Service Topology

```
┌──────────────────────────────────────────────────────────┐
│  Browser: Customer Web │ Agent Web │ Admin Dashboard      │
└──────────┬──────────────────┬────────────────────────────┘
           │ WS/HTTP/WebRTC   │
     ┌─────▼──────┐  ┌───────▼────────┐  ┌──────────────┐
     │ CC System  │  │ AI Video Platform│  │ AI Pipeline  │
     │(Java :8080)│  │  (Node :3001)   │  │ (Node :3002)  │
     │            │  │                 │  │               │
     │ Queue      │  │ Room Manager    │  │ ASR           │
     │ Session    │─▶│ SRS API         │─▶│ RAG + DeepSeek│
     │ WebSocket  │  │ Stream Gen      │  │ Avatar Match  │
     └─────┬──────┘  └───────┬────────┘  └───────┬───────┘
           │                 │                    │
     ┌─────▼─────────────────▼────────────────────▼───────┐
     │  SRS :1935/1985  │  Redis :6379  │  SQLite/ChromaDB │
     └────────────────────────────────────────────────────┘
```

### Service Responsibilities

**CC System (Java Spring Boot :8080)**
- WebSocket endpoints for customer/agent long connections, heartbeat keepalive
- Queue engine: FIFO queue, auto-matching with idle agents
- Session lifecycle: create sid → allocate → in-progress → end
- Distributed gateway: rate limiting, circuit breaking, routing (demonstrating P99 < 200ms)
- Event forwarding: customer audio → AI pipeline

**AI Video Platform (Node.js :3001)**
- SRS HTTP API wrapper: create room, query streams, close room
- Stream URL generation: RTMP push URL + WebRTC/FLV pull URLs
- H.265 transcode configuration: demonstrate CDN cost optimization
- Room-session mapping: Redis cache `roomId ↔ sid`

**AI Pipeline (Node.js :3002)**
- ASR entry: receive audio Base64 → browser Web Speech API / iFlytek API
- RAG retrieval: ChromaDB vector similarity search on knowledge base
- DeepSeek call: prompt = context + question → generate answer
- Digital human matching: answer keywords → match pre-recorded video file

**Web Frontend (React/Vite :5173)**
- Customer mobile page: video call, AI reply display, transfer-to-human button
- Agent workbench: incoming call notification, video call, customer info
- Admin dashboard: session monitoring, queue status, system metrics

## 3. Core Flows

### Flow 1: Customer Call → Video Session Established

```
Customer Web → WS connect → CC System
Customer Web → {"type":"call"} → CC System
CC System → generate sid → Redis SET
CC System → POST /api/rooms → AI Video Platform
AI Video Platform → POST SRS API → SRS (create room + streams)
AI Video Platform → {roomId, pushUrl, pullUrl} → CC System
CC System → WS {sid, roomId, pushUrl, pullUrl} → Customer Web
Customer Web ↔ WebRTC push/pull ↔ SRS ↔ AI Video Platform
```

### Flow 2: AI Intelligent Q&A

```
Customer audio → CC System
CC System → extract PCM audio → AI Pipeline
AI Pipeline → ASR → text
AI Pipeline → embedding query → ChromaDB → top5 similar docs
AI Pipeline → prompt+context → DeepSeek → answer text
AI Pipeline → answer keywords → match pre-recorded video
AI Pipeline → {answer, videoPath} → CC System
CC System → push digital human video to SRS room
Customer Web → pull digital human reply video from SRS
```

### Flow 3: Transfer to Human Agent

```
Customer Web → {"transfer"} → CC System
CC System → query idle agents → pick one
CC System → WS call → Agent Web (show incoming call)
Agent Web → WS accept → CC System
CC System → GET streams from SRS → pushUrl + pullUrl
CC System → WS send stream URLs → Agent Web
Agent Web → WebRTC push video → SRS
Agent Web → WebRTC pull customer video → SRS
Customer Web → continue push/pull → SRS
```

## 4. Project Structure

```
kefu_ai_video/
├── docker-compose.yml
├── package.json                    # root workspace
│
├── services/
│   ├── cc-system/                  # Java Spring Boot
│   │   ├── pom.xml
│   │   └── src/main/java/com/kefu/cc/
│   │       ├── CcApplication.java
│   │       ├── config/             # WebSocket, Redis, Gateway config
│   │       ├── controller/         # HTTP REST endpoints
│   │       ├── websocket/          # WS handler + message router
│   │       ├── service/            # Queue, Session, Agent services
│   │       └── model/              # Session, Agent models
│   │
│   ├── ai-video-platform/          # Node.js TypeScript
│   │   ├── package.json
│   │   └── src/
│   │       ├── index.ts
│   │       ├── routes/room.ts
│   │       ├── services/           # srs-client, stream-manager
│   │       └── types/
│   │
│   └── ai-pipeline/                # Node.js TypeScript
│       ├── package.json
│       └── src/
│           ├── index.ts
│           ├── routes/pipeline.ts
│           ├── services/           # asr, rag, deepseek, avatar
│           └── data/knowledge/     # RAG knowledge docs
│
├── web/                            # React/Vite frontend
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── pages/                  # Customer, Agent, Admin
│       ├── components/             # VideoPlayer, ChatPanel, StatusBar
│       ├── hooks/                  # useWebSocket, useWebRTC
│       └── services/api.ts
│
├── assets/
│   └── avatar-videos/              # Pre-recorded AI agent reply videos
│
└── docs/
    └── superpowers/specs/          # Design docs
```

## 5. API Endpoints

| Service | Method | Path | Description |
|---------|--------|------|-------------|
| CC System | WS | `ws://:8080/ws/cc` | Customer/Agent WebSocket |
| CC System | GET | `/api/sessions/:sid` | Query session status |
| CC System | POST | `/api/sessions/:sid/transfer` | Transfer to human agent |
| AI Video | POST | `/api/rooms` | Create SRS room |
| AI Video | GET | `/api/rooms/:rid/streams` | Get push/pull URLs |
| AI Pipeline | POST | `/api/pipeline/ask` | Audio → text → RAG → answer → video |
| AI Pipeline | POST | `/api/pipeline/speech` | Text → TTS audio |

## 6. Tech Stack Details

| Component | Technology | Version |
|-----------|-----------|---------|
| CC System | Java 17 + Spring Boot 3.x | :8080 |
| AI Video | Node.js 20 + Express + TypeScript | :3001 |
| AI Pipeline | Node.js 20 + Express + TypeScript | :3002 |
| Frontend | React 18 + Vite + TypeScript | :5173 |
| Media Server | SRS 5.0 (Docker) | :1935/:1985/:8088 |
| Cache | Redis 7 (Docker) | :6379 |
| Database | SQLite (better-sqlite3) | file |
| Vector DB | ChromaDB (Docker) | :8000 |
| ASR | Browser Web Speech API / iFlytek | - |
| LLM | DeepSeek API (chat/completions) | - |
| RAG | ChromaDB + custom embedding | - |
| Digital Human | Pre-recorded MP4 videos | - |

## 7. Key Display Features (Interview/Client Demo)

1. **Gateway Rate Limiting**: Guava RateLimiter + Sentinel circuit breaker, visualized in admin dashboard
2. **CDN Cost Optimization**: H.265 encoding toggle, bandwidth comparison charts
3. **Session Monitoring**: Real-time concurrent sessions, queue depth, agent availability
4. **AI Pipeline Latency**: End-to-end tracing from audio input to digital human video output
5. **Transfer Flow**: Seamless handoff from AI to human agent

## 8. Non-Goals (Out of Scope for Demo)

- Actual WeChat Mini Program deployment (use mobile web)
- Real C++ Windows client (use Web-based agent panel)
- TiDB distributed database (use SQLite)
- Production authentication/authorization
- Real digital human rendering engine (use pre-recorded videos)
- Multi-region CDN deployment
