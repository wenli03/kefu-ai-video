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
