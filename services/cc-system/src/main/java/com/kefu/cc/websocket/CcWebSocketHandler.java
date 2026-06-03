package com.kefu.cc.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
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

    public static final Map<String, WebSocketSession> customerSessions = new ConcurrentHashMap<>();
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
