package com.kefu.cc.config;

import com.kefu.cc.model.Session;
import com.kefu.cc.model.Agent;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

@Configuration
public class RedisConfig {

    @Bean
    public RedisTemplate<String, Session> sessionRedisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Session> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new Jackson2JsonRedisSerializer<>(Session.class));
        return template;
    }

    @Bean
    public RedisTemplate<String, Agent> agentRedisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Agent> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new Jackson2JsonRedisSerializer<>(Agent.class));
        return template;
    }
}
