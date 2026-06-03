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
