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
    private String audioData;
    private Map<String, Object> payload;
}
