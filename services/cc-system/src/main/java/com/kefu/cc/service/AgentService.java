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

            handler.sendToAgent(agentId, Message.builder()
                .type("stream-ready")
                .sid(sid)
                .roomId(sess.getRoomId())
                .pushUrl(sess.getPushUrl())
                .pullUrl(sess.getPullUrl())
                .build());

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
