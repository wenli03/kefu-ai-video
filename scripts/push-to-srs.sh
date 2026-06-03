#!/bin/bash
# SRS WebRTC streaming pipeline
# Push avatar video -> SRS -> WebRTC -> frontend

# 1. Check SRS is running
echo "Checking SRS..."
curl -s http://localhost:1985/api/v1/versions | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'SRS {d[\"data\"][\"version\"]} OK')" 2>/dev/null || echo "SRS not running"

# 2. Push animating video to SRS via RTMP
# Using FFmpeg to loop greeting.webm
echo "Starting RTMP push..."
ffmpeg -stream_loop -1 -re -i assets/avatar-videos/greeting.webm \
  -c:v libx264 -preset ultrafast -tune zerolatency -b:v 800k \
  -c:a aac -b:a 64k -f flv \
  rtmp://localhost:1935/live/ai_avatar 2>&1 &

echo "Stream URL:"
echo "  RTMP: rtmp://localhost:1935/live/ai_avatar"
echo "  WebRTC: webrtc://localhost:1985/live/ai_avatar"
echo "  FLV: http://localhost:8088/live/ai_avatar.flv"
echo "  HLS: http://localhost:8088/live/ai_avatar.m3u8"
