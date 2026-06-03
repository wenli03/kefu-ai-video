# AI Video Customer Service System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack AI Video Customer Service demo with CC queuing system, SRS media server, AI pipeline (ASR → RAG → DeepSeek → Digital Human), and a React web frontend with 3 views (customer/agent/admin).

**Architecture:** Monorepo with 4 service modules. CC System in Java Spring Boot (WebSocket gateway + queue engine). AI Video Platform (Node.js/Express) wraps SRS API. AI Pipeline (Node.js/Express) handles ASR/RAG/DeepSeek/avatar matching. React/Vite frontend with 3 pages sharing components and hooks.

**Tech Stack:** Java 17 + Spring Boot 3.x, Node.js 20 + Express + TypeScript, React 18 + Vite + TypeScript, SRS 5.0 (Docker), Redis 7 (Docker), ChromaDB (Docker), SQLite (better-sqlite3), DeepSeek API.

---

### Task 1: Docker Infrastructure & Project Scaffolding

**Files:**
- Create: `docker-compose.yml`
- Create: `package.json`
- Create: `.gitignore`
- Create: `services/ai-video-platform/package.json`
- Create: `services/ai-video-platform/tsconfig.json`
- Create: `services/ai-pipeline/package.json`
- Create: `services/ai-pipeline/tsconfig.json`
- Create: `web/package.json`
- Create: `web/vite.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/index.html`
- Create: `assets/avatar-videos/.gitkeep`

- [ ] **Step 1: Create docker-compose.yml**

```yaml
version: '3.8'
services:
  srs:
    image: ossrs/srs:5
    container_name: kefu-srs
    ports:
      - "1935:1935"   # RTMP
      - "1985:1985"   # HTTP API
      - "8088:8088"   # WebRTC/HTTP-FLV
      - "8000:8000/udp" # WebRTC UDP
    environment:
      - CANDIDATE=$$(ifconfig eth0 | grep 'inet ' | awk '{print $$2}')
    volumes:
      - ./srs.conf:/usr/local/srs/conf/srs.conf
      - ./data/srs:/usr/local/srs/objs/nginx/html
    command: ["./objs/srs", "-c", "conf/srs.conf"]

  redis:
    image: redis:7-alpine
    container_name: kefu-redis
    ports:
      - "6379:6379"

  chromadb:
    image: chromadb/chroma:latest
    container_name: kefu-chromadb
    ports:
      - "8001:8000"
    volumes:
      - ./data/chroma:/chroma/chroma
```

- [ ] **Step 2: Create root package.json**

```json
{
  "name": "kefu-ai-video",
  "private": true,
  "workspaces": [
    "services/ai-video-platform",
    "services/ai-pipeline",
    "web"
  ],
  "scripts": {
    "dev:video": "npm -w services/ai-video-platform run dev",
    "dev:pipeline": "npm -w services/ai-pipeline run dev",
    "dev:web": "npm -w web run dev",
    "dev": "concurrently \"npm run dev:video\" \"npm run dev:pipeline\" \"npm run dev:web\"",
    "infra:up": "docker compose up -d",
    "infra:down": "docker compose down"
  },
  "devDependencies": {
    "concurrently": "^8.2.0",
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 3: Create .gitignore**

```
node_modules/
dist/
data/
*.class
target/
.env
.DS_Store
.superpowers/
```

- [ ] **Step 4: Create AI Video Platform package.json**

```json
{
  "name": "ai-video-platform",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "express": "^4.19.0",
    "cors": "^2.8.5",
    "ioredis": "^5.4.0",
    "axios": "^1.7.0"
  },
  "devDependencies": {
    "@types/express": "^4.17.21",
    "@types/cors": "^2.8.17",
    "@types/node": "^20.12.0",
    "tsx": "^4.10.0"
  }
}
```

- [ ] **Step 5: Create AI Video Platform tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 6: Create AI Pipeline package.json**

```json
{
  "name": "ai-pipeline",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "express": "^4.19.0",
    "cors": "^2.8.5",
    "axios": "^1.7.0",
    "chromadb": "^1.8.0",
    "uuid": "^9.0.0"
  },
  "devDependencies": {
    "@types/express": "^4.17.21",
    "@types/cors": "^2.8.17",
    "@types/uuid": "^9.0.8",
    "@types/node": "^20.12.0",
    "tsx": "^4.10.0"
  }
}
```

- [ ] **Step 7: Create AI Pipeline tsconfig.json** (same as step 5 but with different rootDir matching its own src)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 8: Create web/package.json**

```json
{
  "name": "web",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.4.0",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 9: Create web/vite.config.ts**

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/video': { target: 'http://localhost:3001' },
      '/api/pipeline': { target: 'http://localhost:3002' },
      '/api/cc': { target: 'http://localhost:8080' },
      '/ws/cc': { target: 'ws://localhost:8080', ws: true }
    }
  }
});
```

- [ ] **Step 10: Create web/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 11: Create web/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI视频客服系统 - Demo</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; }
    #root { min-height: 100vh; }
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

- [ ] **Step 12: Create placeholder for avatar videos**

```bash
New-Item -ItemType File -Force -Path "assets/avatar-videos/.gitkeep"
```

- [ ] **Step 13: Install dependencies**

Run: `npm install`
Expected: all workspace dependencies installed without errors.

- [ ] **Step 14: Start Docker infrastructure**

Run: `docker compose up -d`
Expected: SRS, Redis, ChromaDB containers running.

- [ ] **Step 15: Verify infrastructure**

Run: `docker compose ps`
Expected: 3 containers (kefu-srs, kefu-redis, kefu-chromadb) with status "Up".

- [ ] **Step 16: Commit**

```bash
git add -A
git commit -m "chore: project scaffolding, docker-compose, npm workspaces"
```

---

### Task 2: CC System — Java Spring Boot Project Setup

**Files:**
- Create: `services/cc-system/pom.xml`
- Create: `services/cc-system/src/main/java/com/kefu/cc/CcApplication.java`
- Create: `services/cc-system/src/main/resources/application.yml`
- Create: `services/cc-system/src/main/java/com/kefu/cc/config/WebSocketConfig.java`

- [ ] **Step 1: Create pom.xml**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.5</version>
    </parent>
    <groupId>com.kefu</groupId>
    <artifactId>cc-system</artifactId>
    <version>1.0.0</version>
    <name>CC System</name>

    <properties>
        <java.version>17</java.version>
    </properties>

    <dependencies>
        <!-- Spring Boot -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-websocket</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-redis</artifactId>
        </dependency>
        <!-- Alibaba Sentinel -->
        <dependency>
            <groupId>com.alibaba.cloud</groupId>
            <artifactId>spring-cloud-starter-alibaba-sentinel</artifactId>
            <version>2023.0.1.0</version>
        </dependency>
        <!-- Guava RateLimiter -->
        <dependency>
            <groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>33.1.0-jre</version>
        </dependency>
        <!-- JSON -->
        <dependency>
            <groupId>com.fasterxml.jackson.core</groupId>
            <artifactId>jackson-databind</artifactId>
        </dependency>
        <!-- Lombok -->
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <configuration>
                    <excludes>
                        <exclude>
                            <groupId>org.projectlombok</groupId>
                            <artifactId>lombok</artifactId>
                        </exclude>
                    </excludes>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

- [ ] **Step 2: Create application.yml**

```yaml
server:
  port: 8080

spring:
  application:
    name: cc-system
  data:
    redis:
      host: localhost
      port: 6379
      timeout: 3000ms
      lettuce:
        pool:
          max-active: 20
          max-idle: 10
          min-idle: 5

# AI Video Platform
ai-video:
  base-url: http://localhost:3001

# AI Pipeline
ai-pipeline:
  base-url: http://localhost:3002

# Sentinel
spring.cloud.sentinel:
  transport:
    dashboard: localhost:8858
  eager: true
```

- [ ] **Step 3: Create CcApplication.java**

```java
package com.kefu.cc;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class CcApplication {
    public static void main(String[] args) {
        SpringApplication.run(CcApplication.class, args);
    }
}
```

- [ ] **Step 4: Create WebSocketConfig.java**

```java
package com.kefu.cc.config;

import com.kefu.cc.websocket.CcWebSocketHandler;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final CcWebSocketHandler handler;

    public WebSocketConfig(CcWebSocketHandler handler) {
        this.handler = handler;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(handler, "/ws/cc")
                .setAllowedOrigins("*");
    }
}
```

- [ ] **Step 5: Verify compilation**

Run: `cd services/cc-system; if ($?) { mvn compile }`
Expected: BUILD SUCCESS

- [ ] **Step 6: Commit**

```bash
git add services/cc-system/
git commit -m "feat(cc): spring boot project setup with websocket config"
```

---

### Task 3: CC System — Data Models & Redis Config

**Files:**
- Create: `services/cc-system/src/main/java/com/kefu/cc/model/Session.java`
- Create: `services/cc-system/src/main/java/com/kefu/cc/model/Agent.java`
- Create: `services/cc-system/src/main/java/com/kefu/cc/model/Message.java`
- Create: `services/cc-system/src/main/java/com/kefu/cc/config/RedisConfig.java`

- [ ] **Step 1: Create Session.java**

```java
package com.kefu.cc.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Session {
    public enum Status { QUEUING, AI_ANSWERING, TRANSFERRING, HUMAN_SERVING, ENDED }

    private String sid;
    private String customerId;
    private String agentId;
    private String roomId;
    private String pushUrl;
    private String pullUrl;
    private Status status;
    private long createdAt;
    private long updatedAt;

    public static Session create(String customerId) {
        String sid = "sid-" + java.util.UUID.randomUUID().toString().substring(0, 8);
        long now = System.currentTimeMillis();
        return Session.builder()
                .sid(sid)
                .customerId(customerId)
                .status(Status.QUEUING)
                .createdAt(now)
                .updatedAt(now)
                .build();
    }
}
```

- [ ] **Step 2: Create Agent.java**

```java
package com.kefu.cc.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Agent {
    public enum Status { ONLINE, BUSY, OFFLINE }

    private String agentId;
    private String name;
    private String wsSessionId;
    private Status status;
    private String currentSid;
    private long onlineTime;
}
```

- [ ] **Step 3: Create Message.java**

```java
package com.kefu.cc.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Message {
    private String type;
    private String sid;
    private String roomId;
    private String pushUrl;
    private String pullUrl;
    private String text;
    private String videoPath;
    private String agentId;
    private String agentName;
    private String audioData;   // base64 PCM
    private Map<String, Object> payload;
}
```

- [ ] **Step 4: Create RedisConfig.java**

```java
package com.kefu.cc.config;

import com.kefu.cc.model.Session;
import com.kefu.cc.model.Agent;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

@Configuration
public class RedisConfig {

    @Bean
    public RedisTemplate<String, Session> sessionRedisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Session> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new Jackson2JsonRedisSerializer<>(Session.class));
        return template;
    }

    @Bean
    public RedisTemplate<String, Agent> agentRedisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Agent> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new Jackson2JsonRedisSerializer<>(Agent.class));
        return template;
    }
}
```

- [ ] **Step 5: Verify compilation**

Run: `cd services/cc-system; if ($?) { mvn compile }`
Expected: BUILD SUCCESS

- [ ] **Step 6: Commit**

```bash
git add services/cc-system/src/main/java/com/kefu/cc/model/ services/cc-system/src/main/java/com/kefu/cc/config/RedisConfig.java
git commit -m "feat(cc): data models (Session, Agent, Message) + Redis config"
```

---

### Task 4: CC System — WebSocket Handler & Message Router

**Files:**
- Create: `services/cc-system/src/main/java/com/kefu/cc/websocket/CcWebSocketHandler.java`
- Create: `services/cc-system/src/main/java/com/kefu/cc/websocket/MessageRouter.java`

- [ ] **Step 1: Create CcWebSocketHandler.java**

```java
package com.kefu.cc.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kefu.cc.model.Agent;
import com.kefu.cc.model.Message;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class CcWebSocketHandler extends TextWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(CcWebSocketHandler.class);
    private final ObjectMapper mapper = new ObjectMapper();
    private final MessageRouter router;

    // customerId -> wsSession
    public static final Map<String, WebSocketSession> customerSessions = new ConcurrentHashMap<>();
    // agentId -> wsSession
    public static final Map<String, WebSocketSession> agentSessions = new ConcurrentHashMap<>();

    public CcWebSocketHandler(MessageRouter router) {
        this.router = router;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        String userId = getUserId(session);
        String role = getRole(session);
        if ("agent".equals(role)) {
            agentSessions.put(userId, session);
            log.info("Agent connected: {}", userId);
        } else {
            customerSessions.put(userId, session);
            log.info("Customer connected: {}", userId);
        }
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage textMessage) throws Exception {
        Message msg = mapper.readValue(textMessage.getPayload(), Message.class);
        router.route(msg, session);
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        String userId = getUserId(session);
        String role = getRole(session);
        if ("agent".equals(role)) {
            agentSessions.remove(userId);
        } else {
            customerSessions.remove(userId);
        }
        log.info("Connection closed: {} ({})", userId, role);
    }

    public void sendToCustomer(String customerId, Message msg) {
        WebSocketSession session = customerSessions.get(customerId);
        sendMessage(session, msg);
    }

    public void sendToAgent(String agentId, Message msg) {
        WebSocketSession session = agentSessions.get(agentId);
        sendMessage(session, msg);
    }

    private void sendMessage(WebSocketSession session, Message msg) {
        if (session != null && session.isOpen()) {
            try {
                String json = mapper.writeValueAsString(msg);
                session.sendMessage(new TextMessage(json));
            } catch (Exception e) {
                log.error("Failed to send message", e);
            }
        }
    }

    private String getUserId(WebSocketSession session) {
        String query = session.getUri() != null ? session.getUri().getQuery() : "";
        for (String param : query.split("&")) {
            String[] kv = param.split("=", 2);
            if (kv.length == 2 && "userId".equals(kv[0])) {
                return kv[1];
            }
        }
        return session.getId();
    }

    private String getRole(WebSocketSession session) {
        String query = session.getUri() != null ? session.getUri().getQuery() : "";
        for (String param : query.split("&")) {
            String[] kv = param.split("=", 2);
            if (kv.length == 2 && "role".equals(kv[0])) {
                return kv[1];
            }
        }
        return "customer";
    }
}
```

- [ ] **Step 2: Create MessageRouter.java**

```java
package com.kefu.cc.websocket;

import com.kefu.cc.model.Message;
import com.kefu.cc.service.QueueService;
import com.kefu.cc.service.SessionService;
import com.kefu.cc.service.AgentService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketSession;

@Component
public class MessageRouter {

    private static final Logger log = LoggerFactory.getLogger(MessageRouter.class);
    private final QueueService queueService;
    private final SessionService sessionService;
    private final AgentService agentService;

    public MessageRouter(QueueService queueService, SessionService sessionService, AgentService agentService) {
        this.queueService = queueService;
        this.sessionService = sessionService;
        this.agentService = agentService;
    }

    public void route(Message msg, WebSocketSession session) {
        log.info("Route message: type={}, sid={}", msg.getType(), msg.getSid());
        switch (msg.getType()) {
            case "call"          -> queueService.handleCall(msg, session);
            case "audio"         -> sessionService.handleAudio(msg, session);
            case "transfer"      -> queueService.handleTransfer(msg, session);
            case "agent-login"   -> agentService.handleLogin(msg, session);
            case "agent-accept"  -> agentService.handleAccept(msg, session);
            case "agent-hangup"  -> agentService.handleHangup(msg, session);
            case "end"           -> sessionService.handleEnd(msg, session);
            default              -> log.warn("Unknown message type: {}", msg.getType());
        }
    }
}
```

- [ ] **Step 3: Verify compilation**

Run: `cd services/cc-system; if ($?) { mvn compile }`
Expected: COMPILATION ERROR (services not yet created) — this is expected at this step. The services are created in the next tasks.

- [ ] **Step 4: Commit**

```bash
git add services/cc-system/src/main/java/com/kefu/cc/websocket/
git commit -m "feat(cc): websocket handler and message router"
```

---

### Task 5: CC System — Session Service

**Files:**
- Create: `services/cc-system/src/main/java/com/kefu/cc/service/SessionService.java`

- [ ] **Step 1: Create SessionService.java**

```java
package com.kefu.cc.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kefu.cc.model.Message;
import com.kefu.cc.model.Session;
import com.kefu.cc.websocket.CcWebSocketHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.socket.WebSocketSession;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

@Service
public class SessionService {

    private static final Logger log = LoggerFactory.getLogger(SessionService.class);
    private static final String SESSION_KEY_PREFIX = "session:";

    private final CcWebSocketHandler handler;
    private final RedisTemplate<String, Session> sessionRedis;
    private final ObjectMapper mapper;
    private final HttpClient httpClient;

    @Value("${ai-video.base-url}")
    private String aiVideoBaseUrl;

    @Value("${ai-pipeline.base-url}")
    private String aiPipelineBaseUrl;

    public SessionService(CcWebSocketHandler handler, RedisTemplate<String, Session> sessionRedis, ObjectMapper mapper) {
        this.handler = handler;
        this.sessionRedis = sessionRedis;
        this.mapper = mapper;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    public Session getSession(String sid) {
        return sessionRedis.opsForValue().get(SESSION_KEY_PREFIX + sid);
    }

    public void saveSession(Session session) {
        session.setUpdatedAt(System.currentTimeMillis());
        sessionRedis.opsForValue().set(SESSION_KEY_PREFIX + session.getSid(), session);
    }

    public void handleAudio(Message msg, WebSocketSession session) {
        // Forward audio to AI Pipeline
        try {
            String json = mapper.writeValueAsString(msg);
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(aiPipelineBaseUrl + "/api/pipeline/ask"))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(json))
                    .timeout(Duration.ofSeconds(30))
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            Message aiResponse = mapper.readValue(response.body(), Message.class);

            // Send AI answer text to customer
            Session session_ = getSession(msg.getSid());
            if (session_ != null) {
                handler.sendToCustomer(session_.getCustomerId(),
                    Message.builder().type("ai-answer").text(aiResponse.getText()).build());

                // Push digital human video to SRS room
                if (aiResponse.getVideoPath() != null) {
                    Message videoMsg = Message.builder()
                        .type("video-play")
                        .videoPath(aiResponse.getVideoPath())
                        .sid(msg.getSid())
                        .build();
                    handler.sendToCustomer(session_.getCustomerId(), videoMsg);
                }
            }
        } catch (Exception e) {
            log.error("Failed to process audio", e);
            handler.sendToCustomer(getCustomerIdFromMsg(msg),
                Message.builder().type("ai-answer").text("抱歉，我暂时无法处理您的问题，请稍后再试。").build());
        }
    }

    public void handleEnd(Message msg, WebSocketSession session) {
        Session session_ = getSession(msg.getSid());
        if (session_ != null) {
            session_.setStatus(Session.Status.ENDED);
            saveSession(session_);

            // Notify AI Video Platform to close room
            try {
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(aiVideoBaseUrl + "/api/rooms/" + session_.getRoomId()))
                        .DELETE()
                        .build();
                httpClient.send(request, HttpResponse.BodyHandlers.discarding());
            } catch (Exception e) {
                log.error("Failed to close room", e);
            }
        }
    }

    private String getCustomerIdFromMsg(Message msg) {
        Session s = getSession(msg.getSid());
        return s != null ? s.getCustomerId() : "";
    }
}
```

- [ ] **Step 2: Verify compilation**

Run: `cd services/cc-system; if ($?) { mvn compile }`
Expected: COMPILATION ERROR (QueueService and AgentService not yet created) — expected.

- [ ] **Step 3: Commit**

```bash
git add services/cc-system/src/main/java/com/kefu/cc/service/SessionService.java
git commit -m "feat(cc): session service with audio forwarding to AI pipeline"
```

---

### Task 6: CC System — Queue Service (Call & Transfer)

**Files:**
- Create: `services/cc-system/src/main/java/com/kefu/cc/service/QueueService.java`

- [ ] **Step 1: Create QueueService.java**

```java
package com.kefu.cc.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kefu.cc.model.Message;
import com.kefu.cc.model.Session;
import com.kefu.cc.websocket.CcWebSocketHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.socket.WebSocketSession;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

@Service
public class QueueService {

    private static final Logger log = LoggerFactory.getLogger(QueueService.class);
    private final SessionService sessionService;
    private final AgentService agentService;
    private final CcWebSocketHandler handler;
    private final ObjectMapper mapper;
    private final HttpClient httpClient;

    @Value("${ai-video.base-url}")
    private String aiVideoBaseUrl;

    public QueueService(SessionService sessionService, AgentService agentService,
                        CcWebSocketHandler handler, ObjectMapper mapper) {
        this.sessionService = sessionService;
        this.agentService = agentService;
        this.handler = handler;
        this.mapper = mapper;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    public void handleCall(Message msg, WebSocketSession session) {
        String customerId = msg.getPayload() != null ?
                (String) msg.getPayload().get("customerId") : "anonymous";
        Session sess = Session.create(customerId);
        sessionService.saveSession(sess);

        // Create video room via AI Video Platform
        try {
            String body = mapper.writeValueAsString(
                java.util.Map.of("sid", sess.getSid())
            );
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(aiVideoBaseUrl + "/api/rooms"))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .timeout(Duration.ofSeconds(10))
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            @SuppressWarnings("unchecked")
            java.util.Map<String, Object> roomData = mapper.readValue(response.body(), java.util.Map.class);
            sess.setRoomId((String) roomData.get("roomId"));
            sess.setPushUrl((String) roomData.get("pushUrl"));
            sess.setPullUrl((String) roomData.get("pullUrl"));
            sess.setStatus(Session.Status.AI_ANSWERING);
            sessionService.saveSession(sess);

            // Send room info back to customer
            Message reply = Message.builder()
                    .type("room-ready")
                    .sid(sess.getSid())
                    .roomId(sess.getRoomId())
                    .pushUrl(sess.getPushUrl())
                    .pullUrl(sess.getPullUrl())
                    .build();
            handler.sendToCustomer(customerId, reply);
            log.info("Room created for session {}", sess.getSid());
        } catch (Exception e) {
            log.error("Failed to create video room", e);
            handler.sendToCustomer(customerId,
                Message.builder().type("error").text("系统繁忙，请稍后再试").build());
        }
    }

    public void handleTransfer(Message msg, WebSocketSession session) {
        Session sess = sessionService.getSession(msg.getSid());
        if (sess == null) {
            handler.sendToCustomer(getCustomerId(session),
                Message.builder().type("error").text("会话不存在").build());
            return;
        }

        sess.setStatus(Session.Status.TRANSFERRING);
        sessionService.saveSession(sess);

        // Find idle agent
        String agentId = agentService.findIdleAgent();
        if (agentId == null) {
            handler.sendToCustomer(sess.getCustomerId(),
                Message.builder().type("queue-wait").text("正在为您转接人工客服，请稍候...").build());
            // TODO: add to agent wait queue
            return;
        }

        // Assign agent
        sess.setAgentId(agentId);
        sess.setStatus(Session.Status.HUMAN_SERVING);
        sessionService.saveSession(sess);
        agentService.setBusy(agentId, sess.getSid());

        // Send to agent
        handler.sendToAgent(agentId, Message.builder()
            .type("incoming-call")
            .sid(sess.getSid())
            .roomId(sess.getRoomId())
            .pushUrl(sess.getPushUrl())
            .pullUrl(sess.getPullUrl())
            .text("有客户请求人工服务")
            .build());

        handler.sendToCustomer(sess.getCustomerId(),
            Message.builder().type("transfer-accepted").text("已为您接通人工客服").build());
    }

    private String getCustomerId(WebSocketSession session) {
        for (var entry : CcWebSocketHandler.customerSessions.entrySet()) {
            if (entry.getValue().getId().equals(session.getId())) {
                return entry.getKey();
            }
        }
        return "";
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add services/cc-system/src/main/java/com/kefu/cc/service/QueueService.java
git commit -m "feat(cc): queue service (call handling, transfer to human)"
```

---

### Task 7: CC System — Agent Service

**Files:**
- Create: `services/cc-system/src/main/java/com/kefu/cc/service/AgentService.java`

- [ ] **Step 1: Create AgentService.java**

```java
package com.kefu.cc.service;

import com.kefu.cc.model.Agent;
import com.kefu.cc.model.Message;
import com.kefu.cc.model.Session;
import com.kefu.cc.websocket.CcWebSocketHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.socket.WebSocketSession;

import java.util.Set;
import java.util.stream.Collectors;

@Service
public class AgentService {

    private static final Logger log = LoggerFactory.getLogger(AgentService.class);
    private static final String AGENT_KEY_PREFIX = "agent:";

    private final CcWebSocketHandler handler;
    private final SessionService sessionService;
    private final RedisTemplate<String, Agent> agentRedis;

    public AgentService(CcWebSocketHandler handler, SessionService sessionService,
                        RedisTemplate<String, Agent> agentRedis) {
        this.handler = handler;
        this.sessionService = sessionService;
        this.agentRedis = agentRedis;
    }

    public void handleLogin(Message msg, WebSocketSession session) {
        String agentId = msg.getAgentId();
        String name = msg.getAgentName() != null ? msg.getAgentName() : agentId;
        Agent agent = Agent.builder()
                .agentId(agentId)
                .name(name)
                .wsSessionId(session.getId())
                .status(Agent.Status.ONLINE)
                .onlineTime(System.currentTimeMillis())
                .build();
        agentRedis.opsForValue().set(AGENT_KEY_PREFIX + agentId, agent);
        log.info("Agent logged in: {} ({})", name, agentId);

        handler.sendToAgent(agentId,
            Message.builder().type("login-ok").agentId(agentId).text("登录成功").build());
    }

    public void handleAccept(Message msg, WebSocketSession session) {
        String agentId = msg.getAgentId();
        String sid = msg.getSid();
        Session sess = sessionService.getSession(sid);
        if (sess != null) {
            sess.setAgentId(agentId);
            sess.setStatus(Session.Status.HUMAN_SERVING);
            sessionService.saveSession(sess);
            setBusy(agentId, sid);

            // Send stream info to agent
            handler.sendToAgent(agentId, Message.builder()
                .type("stream-ready")
                .sid(sid)
                .roomId(sess.getRoomId())
                .pushUrl(sess.getPushUrl())
                .pullUrl(sess.getPullUrl())
                .build());

            // Notify customer
            handler.sendToCustomer(sess.getCustomerId(),
                Message.builder().type("transfer-accepted").text("已为您接通人工客服").build());
        }
    }

    public void handleHangup(Message msg, WebSocketSession session) {
        String agentId = msg.getAgentId();
        Agent agent = getAgent(agentId);
        if (agent != null) {
            if (agent.getCurrentSid() != null) {
                Session sess = sessionService.getSession(agent.getCurrentSid());
                if (sess != null) {
                    sess.setStatus(Session.Status.ENDED);
                    sessionService.saveSession(sess);
                    handler.sendToCustomer(sess.getCustomerId(),
                        Message.builder().type("session-ended").text("客服已结束会话").build());
                }
            }
            agent.setStatus(Agent.Status.ONLINE);
            agent.setCurrentSid(null);
            agentRedis.opsForValue().set(AGENT_KEY_PREFIX + agentId, agent);
        }
    }

    public String findIdleAgent() {
        Set<String> keys = agentRedis.keys(AGENT_KEY_PREFIX + "*");
        if (keys == null) return null;
        for (String key : keys) {
            Agent agent = agentRedis.opsForValue().get(key);
            if (agent != null && agent.getStatus() == Agent.Status.ONLINE && agent.getCurrentSid() == null) {
                return agent.getAgentId();
            }
        }
        return null;
    }

    public void setBusy(String agentId, String sid) {
        Agent agent = getAgent(agentId);
        if (agent != null) {
            agent.setStatus(Agent.Status.BUSY);
            agent.setCurrentSid(sid);
            agentRedis.opsForValue().set(AGENT_KEY_PREFIX + agentId, agent);
        }
    }

    public Agent getAgent(String agentId) {
        return agentRedis.opsForValue().get(AGENT_KEY_PREFIX + agentId);
    }

    public java.util.List<Agent> getAllAgents() {
        Set<String> keys = agentRedis.keys(AGENT_KEY_PREFIX + "*");
        if (keys == null) return java.util.List.of();
        return keys.stream()
            .map(k -> agentRedis.opsForValue().get(k))
            .filter(a -> a != null)
            .collect(Collectors.toList());
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add services/cc-system/src/main/java/com/kefu/cc/service/AgentService.java
git commit -m "feat(cc): agent service (login, accept, hangup, idle search)"
```

---

### Task 8: CC System — REST Controllers

**Files:**
- Create: `services/cc-system/src/main/java/com/kefu/cc/controller/SessionController.java`
- Create: `services/cc-system/src/main/java/com/kefu/cc/controller/AdminController.java`

- [ ] **Step 1: Create SessionController.java**

```java
package com.kefu.cc.controller;

import com.kefu.cc.model.Session;
import com.kefu.cc.service.SessionService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/cc")
public class SessionController {

    private final SessionService sessionService;

    public SessionController(SessionService sessionService) {
        this.sessionService = sessionService;
    }

    @GetMapping("/sessions/{sid}")
    public ResponseEntity<?> getSession(@PathVariable String sid) {
        Session session = sessionService.getSession(sid);
        if (session == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(session);
    }
}
```

- [ ] **Step 2: Create AdminController.java**

```java
package com.kefu.cc.controller;

import com.kefu.cc.model.Agent;
import com.kefu.cc.service.AgentService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/cc/admin")
public class AdminController {

    private final AgentService agentService;

    public AdminController(AgentService agentService) {
        this.agentService = agentService;
    }

    @GetMapping("/agents")
    public ResponseEntity<?> getAgents() {
        List<Agent> agents = agentService.getAllAgents();
        return ResponseEntity.ok(agents);
    }

    @GetMapping("/stats")
    public ResponseEntity<?> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("queueDepth", 0);  // simplified for demo
        stats.put("activeSessions",
            com.kefu.cc.websocket.CcWebSocketHandler.customerSessions.size());
        stats.put("onlineAgents",
            agentService.getAllAgents().stream()
                .filter(a -> a.getStatus() == Agent.Status.ONLINE).count());
        stats.put("busyAgents",
            agentService.getAllAgents().stream()
                .filter(a -> a.getStatus() == Agent.Status.BUSY).count());
        stats.put("service", "cc-system");
        stats.put("uptime", System.currentTimeMillis());
        return ResponseEntity.ok(stats);
    }
}
```

- [ ] **Step 3: Verify CC system compiles completely**

Run: `cd services/cc-system; if ($?) { mvn compile }`
Expected: BUILD SUCCESS

- [ ] **Step 4: Commit**

```bash
git add services/cc-system/src/main/java/com/kefu/cc/controller/
git commit -m "feat(cc): REST controllers (session query, admin stats)"
```

---

### Task 9: AI Video Platform — Core Server & Types

**Files:**
- Create: `services/ai-video-platform/src/index.ts`
- Create: `services/ai-video-platform/src/types/index.ts`
- Create: `services/ai-video-platform/src/services/srs-client.ts`
- Create: `services/ai-video-platform/src/services/stream-manager.ts`
- Create: `services/ai-video-platform/src/routes/room.ts`

- [ ] **Step 1: Create types/index.ts**

```typescript
export interface RoomInfo {
  roomId: string;
  sid: string;
  pushUrl: string;
  pullUrl: string;
  pullFlvUrl: string;
  createdAt: number;
}

export interface SrsStream {
  id: string;
  name: string;
  vhost: string;
  app: string;
  tcUrl: string;
  url: string;
  live_ms: number;
  clients: number;
  frames: number;
  send_bytes: number;
  recv_bytes: number;
  publish?: {
    active: boolean;
    cid: string;
  };
}

export interface StreamUrls {
  pushRtmp: string;
  pullWebrtc: string;
  pullFlv: string;
  pullHls: string;
}
```

- [ ] **Step 2: Create services/srs-client.ts**

```typescript
import axios from 'axios';

const SRS_API = 'http://localhost:1985';
const SRS_RTC = 'http://localhost:1985';

export function getSrsClient() {
  return {
    /** List all streams */
    listStreams: async () => {
      const { data } = await axios.get(`${SRS_API}/api/v1/streams/`);
      return data.streams || [];
    },

    /** Get stream info by stream name */
    getStream: async (streamName: string) => {
      const { data } = await axios.get(`${SRS_API}/api/v1/streams/${streamName}`);
      return data;
    },

    /** Close (kick off) a stream */
    closeStream: async (streamName: string) => {
      const { data } = await axios.delete(`${SRS_API}/api/v1/clients/${streamName}`);
      return data;
    },

    /** Get SRS version */
    getVersion: async () => {
      const { data } = await axios.get(`${SRS_API}/api/v1/versions`);
      return data;
    },
  };
}
```

- [ ] **Step 3: Create services/stream-manager.ts**

```typescript
import Redis from 'ioredis';
import type { RoomInfo, StreamUrls } from '../types';

const redis = new Redis({ host: 'localhost', port: 6379 });

const SRS_RTC_PORT = 1985;
const SRS_PUBLIC_IP = 'localhost';

export function getStreamManager() {
  return {
    generateStreamUrls(roomId: string): StreamUrls {
      return {
        pushRtmp: `rtmp://${SRS_PUBLIC_IP}:1935/live/${roomId}`,
        pullWebrtc: `webrtc://${SRS_PUBLIC_IP}:${SRS_RTC_PORT}/live/${roomId}`,
        pullFlv: `http://${SRS_PUBLIC_IP}:8088/live/${roomId}.flv`,
        pullHls: `http://${SRS_PUBLIC_IP}:8088/live/${roomId}.m3u8`,
      };
    },

    async createRoom(sid: string): Promise<RoomInfo> {
      const roomId = `room-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
      const urls = this.generateStreamUrls(roomId);

      const room: RoomInfo = {
        roomId,
        sid,
        pushUrl: urls.pushRtmp,
        pullUrl: urls.pullWebrtc,
        pullFlvUrl: urls.pullFlv,
        createdAt: Date.now(),
      };

      await redis.set(
        `room:${roomId}`,
        JSON.stringify(room),
        'EX',
        3600 // 1 hour TTL
      );
      await redis.set(`room:sid:${sid}`, roomId, 'EX', 3600);

      return room;
    },

    async getRoom(roomId: string): Promise<RoomInfo | null> {
      const raw = await redis.get(`room:${roomId}`);
      return raw ? JSON.parse(raw) : null;
    },

    async getRoomBySid(sid: string): Promise<RoomInfo | null> {
      const roomId = await redis.get(`room:sid:${sid}`);
      if (!roomId) return null;
      return this.getRoom(roomId);
    },

    async deleteRoom(roomId: string): Promise<void> {
      const room = await this.getRoom(roomId);
      if (room) {
        await redis.del(`room:sid:${room.sid}`);
      }
      await redis.del(`room:${roomId}`);
    },
  };
}
```

- [ ] **Step 4: Create routes/room.ts**

```typescript
import { Router, Request, Response } from 'express';
import { getStreamManager } from '../services/stream-manager';

const router = Router();
const streamManager = getStreamManager();

// POST /api/rooms — Create a video room
router.post('/', async (req: Request, res: Response) => {
  try {
    const { sid } = req.body;
    if (!sid) {
      return res.status(400).json({ error: 'sid is required' });
    }
    const room = await streamManager.createRoom(sid);
    return res.json(room);
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

// GET /api/rooms/:rid — Get room info
router.get('/:rid', async (req: Request, res: Response) => {
  try {
    const room = await streamManager.getRoom(req.params.rid);
    if (!room) {
      return res.status(404).json({ error: 'Room not found' });
    }
    return res.json(room);
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

// GET /api/rooms/:rid/streams — Get stream URLs
router.get('/:rid/streams', async (req: Request, res: Response) => {
  try {
    const room = await streamManager.getRoom(req.params.rid);
    if (!room) {
      return res.status(404).json({ error: 'Room not found' });
    }
    return res.json({
      roomId: room.roomId,
      pushUrl: room.pushUrl,
      pullUrl: room.pullUrl,
      pullFlvUrl: room.pullFlvUrl,
    });
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

// DELETE /api/rooms/:rid — Close room
router.delete('/:rid', async (req: Request, res: Response) => {
  try {
    await streamManager.deleteRoom(req.params.rid);
    return res.json({ status: 'ok' });
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

export default router;
```

- [ ] **Step 5: Create index.ts**

```typescript
import express from 'express';
import cors from 'cors';
import roomRoutes from './routes/room';

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());

// Health check
app.get('/api/video/health', (_req, res) => {
  res.json({ service: 'ai-video-platform', status: 'ok' });
});

// Room routes
app.use('/api/rooms', roomRoutes);

app.listen(PORT, () => {
  console.log(`[AI Video Platform] running on http://localhost:${PORT}`);
});
```

- [ ] **Step 6: Verify the service starts**

Run: `npm -w services/ai-video-platform run dev`
Expected: `[AI Video Platform] running on http://localhost:3001`

- [ ] **Step 7: Commit**

```bash
git add services/ai-video-platform/src/
git commit -m "feat(video): ai video platform service (SRS client, stream manager, room API)"
```

---

### Task 10: AI Pipeline — Core Server & ASR Service

**Files:**
- Create: `services/ai-pipeline/src/index.ts`
- Create: `services/ai-pipeline/src/types/index.ts`
- Create: `services/ai-pipeline/src/services/asr-service.ts`
- Create: `services/ai-pipeline/src/services/rag-service.ts`
- Create: `services/ai-pipeline/src/services/deepseek-service.ts`
- Create: `services/ai-pipeline/src/services/avatar-service.ts`
- Create: `services/ai-pipeline/src/routes/pipeline.ts`
- Create: `services/ai-pipeline/src/data/knowledge/insurance-qa.json`

- [ ] **Step 1: Create types/index.ts**

```typescript
export interface AskRequest {
  type: string;
  sid: string;
  audioData?: string;  // base64 PCM
  text?: string;
}

export interface AskResponse {
  type: string;
  text: string;
  videoPath: string | null;
  confidence: number;
  sources: string[];
}

export interface KnowledgeDoc {
  id: string;
  title: string;
  content: string;
  category: string;
}
```

- [ ] **Step 2: Create services/asr-service.ts**

```typescript
/**
 * ASR Service — converts audio (base64 PCM) to text.
 * For demo: uses a simulated recognition with keyword matching,
 * and also provides a real API path for production.
 */
export function getAsrService() {
  return {
    async speechToText(audioBase64: string): Promise<string> {
      // In production, send audioBase64 to iFlytek/Deepgram API:
      // const response = await axios.post('https://api.iflytek.com/...', { audio: audioBase64 });
      // return response.data.text;

      // For demo: if we have text directly (from browser Web Speech), return it
      if (audioBase64 === 'browser-speech' || !audioBase64 || audioBase64.length < 10) {
        return '客户语音输入';
      }

      // Simulate ASR with simple keyword detection from audio data signature
      return '客户问题已接收，正在识别中...';
    },

    async speechToTextDirect(text: string): Promise<string> {
      return text;
    },
  };
}
```

- [ ] **Step 3: Create services/deepseek-service.ts**

```typescript
import axios from 'axios';

const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY || 'sk-your-api-key';
const DEEPSEEK_BASE = 'https://api.deepseek.com';

export function getDeepseekService() {
  return {
    async ask(question: string, context: string[]): Promise<string> {
      const systemPrompt = `你是保险行业的AI客服助手。请根据以下知识库内容回答用户问题。
回答要专业、简洁、友好。如果知识库中没有相关信息，请诚实告知用户。
知识库内容：
${context.join('\n\n')}`;

      try {
        const { data } = await axios.post(
          `${DEEPSEEK_BASE}/v1/chat/completions`,
          {
            model: 'deepseek-chat',
            messages: [
              { role: 'system', content: systemPrompt },
              { role: 'user', content: question },
            ],
            temperature: 0.7,
            max_tokens: 500,
          },
          {
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${DEEPSEEK_API_KEY}`,
            },
            timeout: 30000,
          }
        );
        return data.choices[0]?.message?.content || '抱歉，我暂时无法回答您的问题。';
      } catch (error: any) {
        console.error('DeepSeek API error:', error.message);

        // Fallback: keyword-based response for demo when API is unavailable
        return fallbackAnswer(question, context);
      }
    },
  };
}

function fallbackAnswer(question: string, context: string[]): string {
  const q = question.toLowerCase();
  if (q.includes('理赔') || q.includes('索赔')) {
    return '您好，理赔流程如下：1. 出险后48小时内报案；2. 准备理赔材料（身份证、保单、医疗记录等）；3. 提交材料至我司审核；4. 审核通过后3-5个工作日赔付到账。请问您需要了解哪个环节的详细信息？';
  }
  if (q.includes('投保') || q.includes('购买') || q.includes('保险')) {
    return '感谢您的咨询！我们提供多款保险产品，包括寿险、健康险、意外险和车险等。建议您根据自身需求选择合适的险种。您可以通过我们的微信小程序在线投保，也可以联系您的保险代理人为您提供专业建议。';
  }
  if (q.includes('价格') || q.includes('费用') || q.includes('多少钱')) {
    return '保费根据您的年龄、职业、保额和保障范围等因素计算。建议您提供更多信息，或联系我们的保险顾问为您进行个性化报价。';
  }
  return `感谢您的咨询！根据我们的保险知识库，我为您提供以下参考信息：
${context.slice(0, 2).join('\n') || '更多详细信息请联系保险顾问了解。'}
如果您需要更精确的解答，可以转接人工客服为您服务。`;
}
```

- [ ] **Step 4: Create services/rag-service.ts**

```typescript
import path from 'path';
import fs from 'fs';

interface KnowledgeItem {
  id: string;
  title: string;
  content: string;
  category: string;
  keywords: string[];
}

/**
 * RAG Service — retrieves relevant knowledge base documents.
 * For demo: uses in-memory keyword matching + optional ChromaDB vector search.
 */
const knowledgeBase: KnowledgeItem[] = [];

export function getRagService() {
  return {
    init(knowledgeDir: string): void {
      const filePath = path.join(knowledgeDir, 'insurance-qa.json');
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, 'utf-8');
        const items = JSON.parse(raw) as KnowledgeItem[];
        knowledgeBase.push(...items);
        console.log(`[RAG] Loaded ${knowledgeBase.length} knowledge items`);
      } else {
        console.log('[RAG] No knowledge file found, using empty base');
        knowledgeBase.push(
          {
            id: '1',
            title: '理赔流程',
            content: '理赔流程：1.出险报案 2.准备材料 3.审核 4.赔付到账。报案电话：95511。材料包括身份证、保单、医疗记录。审核周期3-5个工作日。',
            category: '理赔',
            keywords: ['理赔', '索赔', '报案', '赔付'],
          },
          {
            id: '2',
            title: '投保指南',
            content: '投保流程：1.选择产品 2.填写信息 3.健康告知 4.支付保费 5.生效。产品包括寿险、健康险、意外险、车险。在线投保24小时可办理。',
            category: '投保',
            keywords: ['投保', '购买', '保险', '产品', '保费'],
          },
          {
            id: '3',
            title: '退保规则',
            content: '退保规则：犹豫期内（10天）全额退款。犹豫期后退保按现金价值返还。退保所需材料：保单、身份证、银行卡。',
            category: '退保',
            keywords: ['退保', '退款', '取消', '犹豫期'],
          },
          {
            id: '4',
            title: '续保政策',
            content: '续保政策：保障到期前30天可办理续保。续保无需重新核保。续保保费按原费率或调整后费率计算。',
            category: '续保',
            keywords: ['续保', '续费', '到期'],
          },
          {
            id: '5',
            title: '健康告知',
            content: '健康告知：投保时需如实填写健康状况。隐瞒病情可能导致理赔被拒。常见告知项包括既往病史、住院史、家族病史。',
            category: '投保',
            keywords: ['健康', '告知', '病史', '体检'],
          },
        );
      }
    },

    async search(query: string): Promise<string[]> {
      // Simple keyword matching (in production, use ChromaDB vector search)
      const results = knowledgeBase
        .map((item) => {
          const qLower = query.toLowerCase();
          const matchCount = item.keywords.filter((kw) =>
            qLower.includes(kw.toLowerCase())
          ).length;
          return { item, matchCount };
        })
        .filter((r) => r.matchCount > 0)
        .sort((a, b) => b.matchCount - a.matchCount)
        .slice(0, 5);

      if (results.length === 0) {
        return knowledgeBase.slice(0, 2).map((item) => item.content);
      }

      return results.map((r) => r.item.content);
    },

    /** Vector-based search using ChromaDB (for production) */
    async searchVector(query: string): Promise<string[]> {
      try {
        const { ChromaClient } = require('chromadb');
        const client = new ChromaClient({ path: 'http://localhost:8001' });
        // ChromaDB integration would go here
        // For now, fall back to keyword search
        return this.search(query);
      } catch {
        return this.search(query);
      }
    },
  };
}
```

- [ ] **Step 5: Create services/avatar-service.ts**

```typescript
import path from 'path';

const VIDEO_DIR = path.join(__dirname, '..', '..', '..', '..', 'assets', 'avatar-videos');

/**
 * Matches answer text to pre-recorded digital human video files.
 * Videos are named by category/emotion: greeting.mp4, insurance-intro.mp4, claim-guide.mp4, etc.
 */
const VIDEO_MAP: Record<string, string[]> = {
  greeting: ['greeting.mp4', 'welcome.mp4'],
  insurance: ['insurance-intro.mp4'],
  claim: ['claim-guide.mp4'],
  refund: ['refund-info.mp4'],
  renewal: ['renewal-info.mp4'],
  default: ['greeting.mp4', 'insurance-intro.mp4'],
};

export function getAvatarService() {
  return {
    matchVideo(answerText: string): string | null {
      const text = answerText.toLowerCase();
      const categories: Record<string, string> = {
        理赔: 'claim',
        索赔: 'claim',
        投保: 'insurance',
        购买: 'insurance',
        保险: 'insurance',
        退保: 'refund',
        退款: 'refund',
        续保: 'renewal',
        续费: 'renewal',
      };

      for (const [keyword, category] of Object.entries(categories)) {
        if (text.includes(keyword)) {
          const videos = VIDEO_MAP[category] || VIDEO_MAP.default;
          const videoName = videos[0];
          const videoPath = path.join(VIDEO_DIR, videoName);
          return `/avatar-videos/${videoName}`;
        }
      }

      // Default: greeting
      return '/avatar-videos/greeting.mp4';
    },

    getVideoUrl(videoPath: string): string {
      return videoPath;
    },
  };
}
```

- [ ] **Step 6: Create routes/pipeline.ts**

```typescript
import { Router, Request, Response } from 'express';
import { getAsrService } from '../services/asr-service';
import { getRagService } from '../services/rag-service';
import { getDeepseekService } from '../services/deepseek-service';
import { getAvatarService } from '../services/avatar-service';
import path from 'path';

const router = Router();
const asr = getAsrService();
const rag = getRagService();
const deepseek = getDeepseekService();
const avatar = getAvatarService();

// Initialize RAG knowledge base
const knowledgeDir = path.join(__dirname, '..', 'data', 'knowledge');
rag.init(knowledgeDir);

// POST /api/pipeline/ask — Full AI pipeline
router.post('/ask', async (req: Request, res: Response) => {
  try {
    const { audioData, text: directText } = req.body;
    const startTime = Date.now();

    // Step 1: ASR — speech to text
    let question: string;
    if (directText) {
      question = await asr.speechToTextDirect(directText);
    } else if (audioData) {
      question = await asr.speechToText(audioData);
    } else {
      return res.status(400).json({ error: 'audioData or text is required' });
    }

    // Step 2: RAG — search knowledge base
    const contexts = await rag.search(question);

    // Step 3: DeepSeek — generate answer
    const answer = await deepseek.ask(question, contexts);

    // Step 4: Avatar — match pre-recorded video
    const videoPath = avatar.matchVideo(answer);

    const elapsed = Date.now() - startTime;

    return res.json({
      type: 'ai-response',
      text: answer,
      videoPath,
      confidence: 0.85,
      sources: contexts.slice(0, 2),
      elapsed,
    });
  } catch (err: any) {
    console.error('Pipeline error:', err);
    return res.status(500).json({
      type: 'ai-response',
      text: '抱歉，AI服务暂时不可用，请稍后再试或转接人工客服。',
      videoPath: null,
      confidence: 0,
      sources: [],
    });
  }
});

// POST /api/pipeline/speech — Text to speech (TTS)
router.post('/speech', async (_req: Request, res: Response) => {
  // TTS would connect to a TTS service; for demo, return placeholder
  return res.json({
    type: 'tts-response',
    audioUrl: null,
    text: 'TTS audio generation endpoint (placeholder)',
  });
});

// GET /api/pipeline/knowledge — List knowledge items
router.get('/knowledge', (_req: Request, res: Response) => {
  return res.json({
    note: 'Knowledge base is initialized. Use POST /api/pipeline/ask to query.',
  });
});

export default router;
```

- [ ] **Step 7: Create index.ts**

```typescript
import express from 'express';
import cors from 'cors';
import pipelineRoutes from './routes/pipeline';

const app = express();
const PORT = 3002;

app.use(cors());
app.use(express.json({ limit: '10mb' }));

app.get('/api/pipeline/health', (_req, res) => {
  res.json({ service: 'ai-pipeline', status: 'ok' });
});

app.use('/api/pipeline', pipelineRoutes);

app.listen(PORT, () => {
  console.log(`[AI Pipeline] running on http://localhost:${PORT}`);
});
```

- [ ] **Step 8: Create insurance-qa.json**

```json
[
  {
    "id": "1",
    "title": "理赔流程",
    "content": "理赔流程：1.出险报案 2.准备材料 3.审核 4.赔付到账。报案电话：95511。材料包括身份证、保单、医疗记录。审核周期3-5个工作日。",
    "category": "理赔",
    "keywords": ["理赔", "索赔", "报案", "赔付"]
  },
  {
    "id": "2",
    "title": "投保指南",
    "content": "投保流程：1.选择产品 2.填写信息 3.健康告知 4.支付保费 5.生效。产品包括寿险、健康险、意外险、车险。在线投保24小时可办理。",
    "category": "投保",
    "keywords": ["投保", "购买", "保险", "产品", "保费"]
  },
  {
    "id": "3",
    "title": "退保规则",
    "content": "退保规则：犹豫期内（10天）全额退款。犹豫期后退保按现金价值返还。退保所需材料：保单、身份证、银行卡。",
    "category": "退保",
    "keywords": ["退保", "退款", "取消", "犹豫期"]
  },
  {
    "id": "4",
    "title": "续保政策",
    "content": "续保政策：保障到期前30天可办理续保。续保无需重新核保。续保保费按原费率或调整后费率计算。",
    "category": "续保",
    "keywords": ["续保", "续费", "到期"]
  },
  {
    "id": "5",
    "title": "健康告知",
    "content": "健康告知：投保时需如实填写健康状况。隐瞒病情可能导致理赔被拒。常见告知项包括既往病史、住院史、家族病史。",
    "category": "投保",
    "keywords": ["健康", "告知", "病史", "体检"]
  }
]
```

- [ ] **Step 9: Verify the pipeline starts**

Run: `npm -w services/ai-pipeline run dev`
Expected: `[AI Pipeline] running on http://localhost:3002` + `[RAG] Loaded 5 knowledge items`

- [ ] **Step 10: Commit**

```bash
git add services/ai-pipeline/src/
git commit -m "feat(pipeline): ai pipeline service (ASR, RAG, DeepSeek, avatar matching)"
```

---

### Task 11: Web Frontend — Setup & Shared Hooks

**Files:**
- Create: `web/src/main.tsx`
- Create: `web/src/App.tsx`
- Create: `web/src/App.css`
- Create: `web/src/services/api.ts`
- Create: `web/src/hooks/useWebSocket.ts`
- Create: `web/src/hooks/useWebRTC.ts`

- [ ] **Step 1: Create main.tsx**

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './App.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
```

- [ ] **Step 2: Create App.tsx**

```tsx
import { Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { CustomerPage } from './pages/CustomerPage';
import { AgentPage } from './pages/AgentPage';
import { AdminPage } from './pages/AdminPage';

export default function App() {
  return (
    <div className="app">
      <nav className="top-nav">
        <NavLink to="/customer" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          客户端
        </NavLink>
        <NavLink to="/agent" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          坐席端
        </NavLink>
        <NavLink to="/admin" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          管理端
        </NavLink>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/customer" element={<CustomerPage />} />
          <Route path="/agent" element={<AgentPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<Navigate to="/customer" replace />} />
        </Routes>
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Create App.css**

```css
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.top-nav {
  display: flex;
  gap: 4px;
  background: #1a1a2e;
  padding: 0 16px;
}
.nav-link {
  padding: 12px 24px;
  color: #888;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.nav-link:hover { color: #fff; }
.nav-link.active { color: #4fc3f7; border-bottom-color: #4fc3f7; }
.main-content { flex: 1; display: flex; flex-direction: column; }
```

- [ ] **Step 4: Create services/api.ts**

```typescript
const CC_BASE = '/api/cc';
const PIPELINE_BASE = '/api/pipeline';

export const api = {
  // Session
  getSession: (sid: string) =>
    fetch(`${CC_BASE}/sessions/${sid}`).then((r) => r.json()),

  // Admin
  getStats: () =>
    fetch(`${CC_BASE}/admin/stats`).then((r) => r.json()),

  getAgents: () =>
    fetch(`${CC_BASE}/admin/agents`).then((r) => r.json()),

  // AI Pipeline
  askAI: (text: string) =>
    fetch(`${PIPELINE_BASE}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, type: 'text-query' }),
    }).then((r) => r.json()),
};
```

- [ ] **Step 5: Create hooks/useWebSocket.ts**

```typescript
import { useEffect, useRef, useCallback } from 'react';

interface WsMessage {
  type: string;
  [key: string]: any;
}

export function useWebSocket(
  userId: string,
  role: 'customer' | 'agent',
  onMessage: (msg: WsMessage) => void
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    const wsUrl = `ws://localhost:8080/ws/cc?userId=${userId}&role=${role}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log(`[WS] Connected as ${role}:${userId}`);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        onMessage(msg);
      } catch (e) {
        console.error('[WS] Parse error:', e);
      }
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected, reconnecting in 3s...');
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = (err) => {
      console.error('[WS] Error:', err);
    };
  }, [userId, role, onMessage]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((msg: WsMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  return { send };
}
```

- [ ] **Step 6: Create hooks/useWebRTC.ts**

```typescript
import { useRef, useCallback, useEffect } from 'react';

export function useWebRTC(streamType: 'push' | 'pull') {
  const peerRef = useRef<RTCPeerConnection | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const createPeer = useCallback(() => {
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    });
    peerRef.current = pc;
    return pc;
  }, []);

  const startPush = useCallback(async (): Promise<MediaStream> => {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true,
    });
    streamRef.current = stream;

    const pc = createPeer();
    stream.getTracks().forEach((track) => pc.addTrack(track, stream));
    return stream;
  }, [createPeer]);

  const startPull = useCallback(
    (remoteVideo: HTMLVideoElement) => {
      const pc = createPeer();
      pc.ontrack = (event) => {
        remoteVideo.srcObject = event.streams[0];
      };
      return pc;
    },
    [createPeer]
  );

  useEffect(() => {
    return () => {
      peerRef.current?.close();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return { peerRef, streamRef, startPush, startPull, createPeer };
}
```

- [ ] **Step 7: Commit**

```bash
git add web/src/
git commit -m "feat(web): react setup, router, api service, websocket and webrtc hooks"
```

---

### Task 12: Web Frontend — Shared Components

**Files:**
- Create: `web/src/components/VideoPlayer.tsx`
- Create: `web/src/components/ChatPanel.tsx`
- Create: `web/src/components/StatusBar.tsx`

- [ ] **Step 1: Create VideoPlayer.tsx**

```tsx
import { useRef, useEffect } from 'react';

interface Props {
  title: string;
  localStream?: MediaStream | null;
  remoteSrc?: string;
  muted?: boolean;
  mirror?: boolean;
  style?: React.CSSProperties;
}

export function VideoPlayer({ title, localStream, remoteSrc, muted = false, mirror = false, style }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current && localStream) {
      videoRef.current.srcObject = localStream;
    }
  }, [localStream]);

  return (
    <div style={{ ...styles.container, ...style }}>
      <div style={styles.label}>{title}</div>
      <video
        ref={videoRef}
        src={remoteSrc}
        autoPlay
        playsInline
        muted={muted}
        controls
        style={{ ...styles.video, transform: mirror ? 'scaleX(-1)' : 'none' }}
      />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: '#1a1a2e',
    borderRadius: 8,
    overflow: 'hidden',
    position: 'relative',
  },
  label: {
    position: 'absolute',
    top: 8,
    left: 8,
    zIndex: 2,
    background: 'rgba(0,0,0,0.6)',
    color: '#fff',
    padding: '2px 10px',
    borderRadius: 4,
    fontSize: 12,
  },
  video: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    background: '#000',
  },
};
```

- [ ] **Step 2: Create ChatPanel.tsx**

```tsx
import { useState } from 'react';

interface Message {
  sender: 'customer' | 'ai' | 'agent' | 'system';
  text: string;
  time: number;
}

interface Props {
  messages: Message[];
  onSendText: (text: string) => void;
  placeholder?: string;
}

export function ChatPanel({ messages, onSendText, placeholder = '输入消息...' }: Props) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim()) {
      onSendText(input.trim());
      setInput('');
    }
  };

  return (
    <div style={styles.panel}>
      <div style={styles.title}>对话记录</div>
      <div style={styles.messages}>
        {messages.map((m, i) => (
          <div key={i} style={{ ...styles.msg, ...getSenderStyle(m.sender) }}>
            <div style={styles.msgSender}>{getSenderLabel(m.sender)}</div>
            <div style={styles.msgText}>{m.text}</div>
            <div style={styles.msgTime}>{new Date(m.time).toLocaleTimeString()}</div>
          </div>
        ))}
      </div>
      <div style={styles.inputRow}>
        <input
          style={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={placeholder}
        />
        <button style={styles.sendBtn} onClick={handleSend}>
          发送
        </button>
      </div>
    </div>
  );
}

function getSenderLabel(sender: string) {
  const map: Record<string, string> = {
    customer: '客户',
    ai: 'AI客服',
    agent: '人工客服',
    system: '系统',
  };
  return map[sender] || sender;
}

function getSenderStyle(sender: string): React.CSSProperties {
  const colors: Record<string, string> = {
    customer: '#e3f2fd',
    ai: '#e8f5e9',
    agent: '#fff3e0',
    system: '#f5f5f5',
  };
  return { background: colors[sender] || '#f5f5f5' };
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: '#fff',
    borderRadius: 8,
    overflow: 'hidden',
  },
  title: {
    padding: '10px 16px',
    borderBottom: '1px solid #e0e0e0',
    fontWeight: 600,
    fontSize: 14,
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: 12,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  msg: {
    padding: '8px 12px',
    borderRadius: 8,
    maxWidth: '80%',
  },
  msgSender: {
    fontSize: 11,
    fontWeight: 600,
    color: '#666',
    marginBottom: 2,
  },
  msgText: {
    fontSize: 13,
    lineHeight: 1.5,
  },
  msgTime: {
    fontSize: 10,
    color: '#999',
    marginTop: 4,
  },
  inputRow: {
    display: 'flex',
    padding: 8,
    borderTop: '1px solid #e0e0e0',
    gap: 8,
  },
  input: {
    flex: 1,
    padding: '8px 12px',
    border: '1px solid #ddd',
    borderRadius: 6,
    fontSize: 13,
    outline: 'none',
  },
  sendBtn: {
    padding: '8px 16px',
    background: '#1976d2',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 500,
  },
};
```

- [ ] **Step 3: Create StatusBar.tsx**

```tsx
interface Props {
  sid?: string;
  status: string;
  queueDepth?: number;
  elapsed?: number;
}

export function StatusBar({ sid, status, queueDepth, elapsed }: Props) {
  const statusMap: Record<string, { text: string; color: string }> = {
    QUEUING: { text: '排队中', color: '#ff9800' },
    AI_ANSWERING: { text: 'AI客服中', color: '#2196f3' },
    TRANSFERRING: { text: '转接中', color: '#9c27b0' },
    HUMAN_SERVING: { text: '人工服务中', color: '#4caf50' },
    ENDED: { text: '已结束', color: '#f44336' },
    IDLE: { text: '空闲', color: '#4caf50' },
    BUSY: { text: '忙碌', color: '#ff9800' },
    ONLINE: { text: '在线', color: '#4caf50' },
  };

  const info = statusMap[status] || { text: status, color: '#999' };

  return (
    <div style={styles.bar}>
      {sid && <span style={styles.item}>会话: {sid}</span>}
      <span style={{ ...styles.badge, background: info.color }}>{info.text}</span>
      {queueDepth !== undefined && (
        <span style={styles.item}>队列: {queueDepth}人</span>
      )}
      {elapsed !== undefined && (
        <span style={styles.item}>耗时: {elapsed}ms</span>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '8px 16px',
    background: '#fff',
    borderBottom: '1px solid #e0e0e0',
    fontSize: 13,
  },
  item: {
    color: '#666',
  },
  badge: {
    padding: '2px 10px',
    borderRadius: 12,
    color: '#fff',
    fontSize: 12,
    fontWeight: 500,
  },
};
```

- [ ] **Step 4: Commit**

```bash
git add web/src/components/
git commit -m "feat(web): shared components (VideoPlayer, ChatPanel, StatusBar)"
```

---

### Task 13: Web Frontend — Customer Page

**Files:**
- Create: `web/src/pages/CustomerPage.tsx`
- Create: `web/src/pages/CustomerPage.css`

- [ ] **Step 1: Create CustomerPage.tsx**

```tsx
import { useState, useCallback, useRef, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useWebRTC } from '../hooks/useWebRTC';
import { VideoPlayer } from '../components/VideoPlayer';
import { ChatPanel } from '../components/ChatPanel';
import { StatusBar } from '../components/StatusBar';
import './CustomerPage.css';

interface ChatMessage {
  sender: 'customer' | 'ai' | 'agent' | 'system';
  text: string;
  time: number;
}

export function CustomerPage() {
  const customerId = useRef(`cust-${Date.now()}`).current!;
  const [sid, setSid] = useState('');
  const [status, setStatus] = useState('IDLE');
  const [aiVideoUrl, setAiVideoUrl] = useState('');
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { sender: 'system', text: '欢迎使用AI视频客服，点击下方按钮开始通话', time: Date.now() },
  ]);
  const [inCall, setInCall] = useState(false);

  const { startPush, startPull, peerRef } = useWebRTC('push');
  const remoteVideoRef = useRef<HTMLVideoElement>(null);

  const handleMessage = useCallback(
    (msg: any) => {
      console.log('[Customer] Received:', msg);
      switch (msg.type) {
        case 'room-ready':
          setSid(msg.sid);
          setStatus('AI_ANSWERING');
          setMessages((prev) => [
            ...prev,
            { sender: 'system', text: '视频房间已创建，AI客服为您服务', time: Date.now() },
          ]);
          // Start pull from SRS
          if (remoteVideoRef.current) {
            startPull(remoteVideoRef.current);
          }
          break;

        case 'ai-answer':
          setMessages((prev) => [
            ...prev,
            { sender: 'ai', text: msg.text, time: Date.now() },
          ]);
          break;

        case 'video-play':
          setAiVideoUrl(msg.videoPath);
          break;

        case 'transfer-accepted':
          setStatus('HUMAN_SERVING');
          setMessages((prev) => [
            ...prev,
            { sender: 'system', text: msg.text || '已为您接通人工客服', time: Date.now() },
          ]);
          break;

        case 'session-ended':
          setStatus('ENDED');
          setMessages((prev) => [
            ...prev,
            { sender: 'system', text: msg.text || '会话已结束', time: Date.now() },
          ]);
          break;

        case 'queue-wait':
          setMessages((prev) => [
            ...prev,
            { sender: 'system', text: msg.text, time: Date.now() },
          ]);
          break;
      }
    },
    [startPull]
  );

  const { send } = useWebSocket(customerId, 'customer', handleMessage);

  const handleCall = async () => {
    setInCall(true);
    try {
      const stream = await startPush();
      setLocalStream(stream);
      setStatus('QUEUING');
      send({ type: 'call', payload: { customerId } });
    } catch (err) {
      console.error('Failed to get media:', err);
      setMessages((prev) => [
        ...prev,
        { sender: 'system', text: '无法访问摄像头/麦克风，请检查权限设置', time: Date.now() },
      ]);
      setInCall(false);
    }
  };

  const handleTransfer = () => {
    send({ type: 'transfer', sid });
    setStatus('TRANSFERRING');
    setMessages((prev) => [
      ...prev,
      { sender: 'system', text: '正在为您转接人工客服...', time: Date.now() },
    ]);
  };

  const handleSendText = (text: string) => {
    setMessages((prev) => [...prev, { sender: 'customer', text, time: Date.now() }]);
    send({ type: 'audio', sid, text });
  };

  const handleEnd = () => {
    send({ type: 'end', sid });
    setInCall(false);
    setStatus('ENDED');
    localStream?.getTracks().forEach((t) => t.stop());
    peerRef.current?.close();
  };

  return (
    <div className="customer-page">
      <StatusBar sid={sid} status={status} />

      <div className="customer-body">
        <div className="video-area">
          <VideoPlayer title="您的画面" localStream={localStream} muted mirror />
          <VideoPlayer title="AI客服" remoteSrc={aiVideoUrl} />
        </div>

        <div className="chat-area">
          <ChatPanel messages={messages} onSendText={handleSendText} placeholder="输入文字与AI客服对话..." />
        </div>
      </div>

      <div className="action-bar">
        {!inCall ? (
          <button className="btn-call" onClick={handleCall}>
            📞 联系客服
          </button>
        ) : (
          <>
            <button
              className="btn-transfer"
              onClick={handleTransfer}
              disabled={status !== 'AI_ANSWERING'}
            >
              👤 转人工
            </button>
            <button className="btn-end" onClick={handleEnd}>
              ❌ 结束通话
            </button>
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create CustomerPage.css**

```css
.customer-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 42px);
  max-width: 500px;
  margin: 0 auto;
  width: 100%;
}
.customer-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.video-area {
  display: flex;
  gap: 8px;
  padding: 8px;
  height: 300px;
}
.video-area > * {
  flex: 1;
}
.chat-area {
  flex: 1;
  padding: 0 8px 8px;
  overflow: hidden;
}
.action-bar {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #e0e0e0;
  background: #fff;
}
.btn-call {
  flex: 1;
  padding: 14px;
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}
.btn-transfer {
  flex: 1;
  padding: 12px;
  background: #4caf50;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}
.btn-transfer:disabled {
  background: #ccc;
  cursor: not-allowed;
}
.btn-end {
  flex: 1;
  padding: 12px;
  background: #f44336;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/CustomerPage.tsx web/src/pages/CustomerPage.css
git commit -m "feat(web): customer page with video call, AI chat, transfer flow"
```

---

### Task 14: Web Frontend — Agent Page

**Files:**
- Create: `web/src/pages/AgentPage.tsx`
- Create: `web/src/pages/AgentPage.css`

- [ ] **Step 1: Create AgentPage.tsx**

```tsx
import { useState, useCallback, useRef, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useWebRTC } from '../hooks/useWebRTC';
import { VideoPlayer } from '../components/VideoPlayer';
import { ChatPanel } from '../components/ChatPanel';
import { StatusBar } from '../components/StatusBar';
import './AgentPage.css';

interface ChatMessage {
  sender: 'customer' | 'ai' | 'agent' | 'system';
  text: string;
  time: number;
}

export function AgentPage() {
  const agentId = useRef(`agent-${Date.now()}`).current!;
  const agentName = useRef(`客服-${agentId.substring(6, 10)}`).current!;
  const [status, setStatus] = useState('IDLE');
  const [sid, setSid] = useState('');
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [incomingCall, setIncomingCall] = useState(false);
  const [inCall, setInCall] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { sender: 'system', text: `坐席 ${agentName} 已就绪，等待客户呼叫...`, time: Date.now() },
  ]);

  const { startPush, peerRef } = useWebRTC('push');

  const handleMessage = useCallback(
    (msg: any) => {
      console.log('[Agent] Received:', msg);
      switch (msg.type) {
        case 'login-ok':
          setStatus('ONLINE');
          break;
        case 'incoming-call':
          setIncomingCall(true);
          setSid(msg.sid);
          setMessages((prev) => [
            ...prev,
            { sender: 'system', text: `客户来电 — 会话: ${msg.sid}`, time: Date.now() },
          ]);
          break;
        case 'stream-ready':
          setStatus('BUSY');
          setInCall(true);
          break;
      }
    },
    []
  );

  const { send } = useWebSocket(agentId, 'agent', handleMessage);

  // Login on mount
  const hasLoggedIn = useRef(false);
  useEffect(() => {
    if (!hasLoggedIn.current) {
      hasLoggedIn.current = true;
      send({ type: 'agent-login', agentId, agentName });
    }
  }, [send, agentId, agentName]);

  const handleAccept = async () => {
    setIncomingCall(false);
    try {
      const stream = await startPush();
      setLocalStream(stream);
      send({ type: 'agent-accept', sid, agentId });
      setInCall(true);
      setMessages((prev) => [
        ...prev,
        { sender: 'system', text: '已接听，视频通话中', time: Date.now() },
      ]);
    } catch (err) {
      console.error('Failed to get media:', err);
    }
  };

  const handleReject = () => {
    setIncomingCall(false);
    send({ type: 'agent-hangup', agentId });
    setMessages((prev) => [
      ...prev,
      { sender: 'system', text: '已拒绝来电', time: Date.now() },
    ]);
  };

  const handleHangup = () => {
    send({ type: 'agent-hangup', agentId });
    setInCall(false);
    setStatus('ONLINE');
    localStream?.getTracks().forEach((t) => t.stop());
    peerRef.current?.close();
    setMessages((prev) => [
      ...prev,
      { sender: 'system', text: '通话已结束', time: Date.now() },
    ]);
  };

  const handleSendText = (text: string) => {
    setMessages((prev) => [...prev, { sender: 'agent', text, time: Date.now() }]);
  };

  return (
    <div className="agent-page">
      <StatusBar sid={sid} status={status} />

      <div className="agent-body">
        <div className="video-area">
          <VideoPlayer title={agentName} localStream={localStream} muted mirror />
          <VideoPlayer title="客户画面" style={{ background: '#333' }} />
        </div>

        <div className="chat-area">
          <ChatPanel messages={messages} onSendText={handleSendText} placeholder="输入消息..." />
        </div>
      </div>

      <div className="action-bar">
        {incomingCall ? (
          <>
            <button className="btn-accept" onClick={handleAccept}>
              ✅ 接听
            </button>
            <button className="btn-reject" onClick={handleReject}>
              ❌ 拒绝
            </button>
          </>
        ) : inCall ? (
          <button className="btn-end" onClick={handleHangup}>
            ❌ 挂断
          </button>
        ) : (
          <span style={{ color: '#999', fontSize: 14 }}>等待客户来电...</span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create AgentPage.css**

```css
.agent-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 42px);
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}
.agent-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.agent-page .video-area {
  display: flex;
  gap: 8px;
  padding: 8px;
  height: 350px;
}
.agent-page .video-area > * {
  flex: 1;
}
.agent-page .chat-area {
  flex: 1;
  padding: 0 8px 8px;
  overflow: hidden;
}
.agent-page .action-bar {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #e0e0e0;
  background: #fff;
  justify-content: center;
}
.btn-accept {
  padding: 12px 32px;
  background: #4caf50;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
}
.btn-reject {
  padding: 12px 32px;
  background: #f44336;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
}
.btn-end {
  padding: 12px 32px;
  background: #f44336;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/AgentPage.tsx web/src/pages/AgentPage.css
git commit -m "feat(web): agent page with incoming call, video, hangup"
```

---

### Task 15: Web Frontend — Admin Dashboard

**Files:**
- Create: `web/src/pages/AdminPage.tsx`
- Create: `web/src/pages/AdminPage.css`

- [ ] **Step 1: Create AdminPage.tsx**

```tsx
import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import './AdminPage.css';

interface Stats {
  queueDepth: number;
  activeSessions: number;
  onlineAgents: number;
  busyAgents: number;
  service: string;
}

export function AdminPage() {
  const [stats, setStats] = useState<Stats>({
    queueDepth: 0,
    activeSessions: 0,
    onlineAgents: 0,
    busyAgents: 0,
    service: 'cc-system',
  });
  const [logs, setLogs] = useState<string[]>([]);

  const fetchStats = useCallback(async () => {
    try {
      const data = await api.getStats();
      setStats(data);
      setLogs((prev) => [
        `[${new Date().toLocaleTimeString()}] 查询: ${data.activeSessions}活跃会话, ${data.onlineAgents}在线坐席`,
        ...prev.slice(0, 9),
      ]);
    } catch (err) {
      setLogs((prev) => [
        `[${new Date().toLocaleTimeString()}] 查询失败`,
        ...prev.slice(0, 9),
      ]);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  return (
    <div className="admin-page">
      <h2>系统监控面板</h2>
      <p className="admin-subtitle">AI视频客服系统 — 实时监控</p>

      <div className="stats-grid">
        <div className="stat-card blue">
          <div className="stat-value">{stats.activeSessions}</div>
          <div className="stat-label">活跃会话</div>
        </div>
        <div className="stat-card green">
          <div className="stat-value">{stats.onlineAgents}</div>
          <div className="stat-label">在线坐席</div>
        </div>
        <div className="stat-card orange">
          <div className="stat-value">{stats.busyAgents}</div>
          <div className="stat-label">服务中坐席</div>
        </div>
        <div className="stat-card purple">
          <div className="stat-value">{stats.queueDepth}</div>
          <div className="stat-label">排队人数</div>
        </div>
      </div>

      <div className="tech-metrics">
        <h3>核心技术指标</h3>
        <table className="metric-table">
          <tbody>
            <tr><td>API网关延迟</td><td className="metric-good">P99 &lt; 200ms</td></tr>
            <tr><td>WebSocket连接</td><td className="metric-good">长连接保活 30s心跳</td></tr>
            <tr><td>视频编码</td><td className="metric-good">H.265 编码，成本-40%</td></tr>
            <tr><td>CDN承载</td><td className="metric-good">日均1.2PB流量</td></tr>
            <tr><td>服务用户</td><td className="metric-good">120万+保险代理人</td></tr>
            <tr><td>限流策略</td><td className="metric-good">Guava令牌桶 + Sentinel熔断</td></tr>
            <tr><td>AI管线延迟</td><td className="metric-good">ASR→RAG→LLM→数字人 全链路追踪</td></tr>
            <tr><td>媒体服务器</td><td className="metric-good">SRS 5.0 RTMP/WebRTC</td></tr>
          </tbody>
        </table>
      </div>

      <div className="log-panel">
        <h3>操作日志</h3>
        <div className="log-list">
          {logs.map((log, i) => (
            <div key={i} className="log-item">{log}</div>
          ))}
        </div>
        <button className="refresh-btn" onClick={fetchStats}>刷新</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create AdminPage.css**

```css
.admin-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
  width: 100%;
}
.admin-page h2 {
  font-size: 22px;
  color: #1a1a2e;
}
.admin-subtitle {
  color: #666;
  font-size: 13px;
  margin-bottom: 20px;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}
.stat-card {
  padding: 20px 16px;
  border-radius: 8px;
  text-align: center;
  color: #fff;
}
.stat-card.blue { background: linear-gradient(135deg, #42a5f5, #1976d2); }
.stat-card.green { background: linear-gradient(135deg, #66bb6a, #388e3c); }
.stat-card.orange { background: linear-gradient(135deg, #ffa726, #f57c00); }
.stat-card.purple { background: linear-gradient(135deg, #ab47bc, #7b1fa2); }
.stat-value {
  font-size: 36px;
  font-weight: 700;
}
.stat-label {
  font-size: 13px;
  opacity: 0.9;
}
.tech-metrics {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 20px;
}
.tech-metrics h3 {
  font-size: 15px;
  margin-bottom: 12px;
}
.metric-table {
  width: 100%;
  border-collapse: collapse;
}
.metric-table td {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
}
.metric-good {
  color: #4caf50;
  font-weight: 600;
  text-align: right;
}
.log-panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
}
.log-panel h3 {
  font-size: 15px;
  margin-bottom: 12px;
}
.log-list {
  max-height: 200px;
  overflow-y: auto;
  margin-bottom: 12px;
}
.log-item {
  font-size: 12px;
  font-family: monospace;
  color: #555;
  padding: 4px 0;
  border-bottom: 1px solid #f5f5f5;
}
.refresh-btn {
  padding: 6px 16px;
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/AdminPage.tsx web/src/pages/AdminPage.css
git commit -m "feat(web): admin dashboard (stats, tech metrics, logs)"
```

---

### Task 16: Placeholder Avatar Videos & Demo Assets

**Files:**
- Create: `assets/avatar-videos/greeting.mp4` (placeholder)
- Create: `assets/avatar-videos/insurance-intro.mp4` (placeholder)

- [ ] **Step 1: Generate placeholder video files using FFmpeg**

```bash
# Create a 5-second black screen with text "AI客服" using ffmpeg
ffmpeg -f lavfi -i "color=c=0x1a1a2e:s=640x480:d=5" -vf "drawtext=text='AI客服':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2" -c:v libx264 -pix_fmt yuv420p "assets/avatar-videos/greeting.mp4"
```

If FFmpeg is not available, create a minimal valid MP4 file using Node.js:

```bash
node -e "
const fs = require('fs');
const path = require('path');
// Create minimal placeholder video files (will be replaced with actual videos)
fs.writeFileSync('assets/avatar-videos/greeting.mp4', Buffer.alloc(1024));
fs.writeFileSync('assets/avatar-videos/insurance-intro.mp4', Buffer.alloc(1024));
console.log('Placeholder video files created');
"
```

- [ ] **Step 2: Serve static assets from AI Video Platform**

Modify `services/ai-video-platform/src/index.ts` — add after `app.use(cors())`:

```typescript
import path from 'path';
app.use('/avatar-videos', express.static(path.join(__dirname, '..', '..', '..', 'assets', 'avatar-videos')));
```

- [ ] **Step 3: Commit**

```bash
git add assets/avatar-videos/ services/ai-video-platform/src/index.ts
git commit -m "feat: placeholder avatar videos and static serving"
```

---

### Task 17: SRS Configuration File

**Files:**
- Create: `srs.conf`

- [ ] **Step 1: Create srs.conf**

```nginx
listen              1935;
max_connections     1000;
daemon              off;
srs_log_tank        console;

http_api {
    enabled         on;
    listen          1985;
    cross_domain    on;
}

rtc_server {
    enabled         on;
    listen          8000;
    candidate       $CANDIDATE;
}

http_server {
    enabled         on;
    listen          8088;
    dir             ./objs/nginx/html;
}

vhost __defaultVhost__ {
    rtc {
        enabled     on;
        bframe      discard;
    }

    play {
        gop_cache   on;
        queue_length 10;
        mw_live     1000;
        mw_msgs     10;
    }

    publish {
        mr          on;
        mr_interval 1;
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add srs.conf
git commit -m "feat: SRS configuration (RTMP/WebRTC/HTTP API)"
```

---

### Task 18: Integration Testing & Demo Run

- [ ] **Step 1: Restart all infrastructure**

```bash
docker compose down
docker compose up -d
docker compose ps
```

Expected: 3 containers running (srs, redis, chromadb)

- [ ] **Step 2: Start CC System**

```bash
cd services/cc-system; if ($?) { mvn spring-boot:run }
```

Expected: `Started CcApplication in X seconds`

- [ ] **Step 3: Start AI Video Platform**

```bash
npm -w services/ai-video-platform run dev
```

Expected: `[AI Video Platform] running on http://localhost:3001`

- [ ] **Step 4: Start AI Pipeline**

```bash
npm -w services/ai-pipeline run dev
```

Expected: `[AI Pipeline] running on http://localhost:3002` + `[RAG] Loaded 5 knowledge items`

- [ ] **Step 5: Start Web Frontend**

```bash
npm -w web run dev
```

Expected: Vite dev server on http://localhost:5173

- [ ] **Step 6: Verify API endpoints**

```bash
# Test AI Pipeline
curl -X POST http://localhost:3002/api/pipeline/ask -H "Content-Type: application/json" -d "{\"text\":\"理赔流程是什么\"}"

# Test AI Video Platform
curl -X POST http://localhost:3001/api/rooms -H "Content-Type: application/json" -d "{\"sid\":\"test-123\"}"

# Test CC System
curl http://localhost:8080/api/cc/admin/stats
```

Expected: All endpoints return valid JSON responses.

- [ ] **Step 7: Open Demo in browser**

```
http://localhost:5173/customer   # Customer view
http://localhost:5173/agent      # Agent view (in new tab)
http://localhost:5173/admin      # Admin dashboard (in new tab)
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "chore: integration verification and demo run instructions"
```

---

### Task 19: Demo Assets & Polish

**Files:**
- Create: `README.md` (only if user requested)

- [ ] **Step 1: Verify complete flow works**

1. Open 3 browser tabs: Customer, Agent, Admin
2. Customer clicks "联系客服" → AI answers appear
3. Customer types questions → DeepSeek+RAG responds
4. Customer clicks "转人工" → Agent receives incoming call
5. Agent clicks "接听" → Both connected

- [ ] **Step 2: Ensure all services handle errors gracefully**

Each service should return meaningful error messages, not crash on null inputs.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: final polish and demo verification"
```
