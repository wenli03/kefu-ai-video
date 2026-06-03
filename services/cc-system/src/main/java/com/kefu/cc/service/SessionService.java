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

            Session session_ = getSession(msg.getSid());
            if (session_ != null) {
                handler.sendToCustomer(session_.getCustomerId(),
                    Message.builder().type("ai-answer").text(aiResponse.getText()).build());

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
