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

        String agentId = agentService.findIdleAgent();
        if (agentId == null) {
            handler.sendToCustomer(sess.getCustomerId(),
                Message.builder().type("queue-wait").text("正在为您转接人工客服，请稍候...").build());
            return;
        }

        sess.setAgentId(agentId);
        sess.setStatus(Session.Status.HUMAN_SERVING);
        sessionService.saveSession(sess);
        agentService.setBusy(agentId, sess.getSid());

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
