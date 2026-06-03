package com.kefu.cc.controller;

import com.kefu.cc.model.Session;
import com.kefu.cc.service.SessionService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

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
