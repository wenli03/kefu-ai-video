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
        java.util.List<Agent> agents = agentService.getAllAgents();
        return ResponseEntity.ok(agents);
    }

    @GetMapping("/stats")
    public ResponseEntity<?> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("queueDepth", 0);
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
