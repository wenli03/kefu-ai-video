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
