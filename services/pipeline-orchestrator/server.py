"""
AI Video Pipeline Orchestrator — real-time stream processing
1. Receives audio → ASR (Whisper) → text
2. Text → DeepSeek → answer
3. Answer → TTS → audio
4. TTS audio + avatar → generate video
5. Push video to SRS RTMP room
"""
import asyncio, json, base64, time, os, sys, subprocess, tempfile, shutil

# Config
ASR_URL = "http://localhost:5006/asr"
PIPELINE_URL = "http://localhost:3002/api/pipeline/ask"
TTS_URL = "http://localhost:5005/tts"
SRS_RTMP = "rtmp://localhost:1935/live"
NODE_RTMP_PUSH = os.path.join(os.path.dirname(__file__), "..", "rtmp-push.js")
AVATAR_VIDEO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "avatar-videos")

import aiohttp
from aiohttp import web

routes = web.RouteTableDef()

@routes.post('/process')
async def process_audio(request):
    """Process audio: ASR → DeepSeek → TTS → push to SRS"""
    start = time.time()
    try:
        data = await request.json()
        audio_data = data.get('audioData', '')
        text_input = data.get('text', '')
        sid = data.get('sid', '')
        room_id = data.get('roomId', '')
        
        logs = []
        
        # Stage 1: ASR
        if text_input:
            question = text_input
            logs.append(f"ASR(text): {question[:50]}")
        elif audio_data:
            async with aiohttp.ClientSession() as session:
                async with session.post(ASR_URL, json={'audio': audio_data}, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    asr_result = await resp.json()
                    question = asr_result.get('text', '')
                    logs.append(f"ASR(audio): {question[:50]} in {asr_result.get('elapsed',0)}ms")
        else:
            return web.json_response({'error': 'audioData or text required'}, status=400)
        
        if not question.strip():
            logs.append("ASR: empty text")
            question = "你好"
        
        # Stage 2: DeepSeek + RAG
        async with aiohttp.ClientSession() as session:
            async with session.post(PIPELINE_URL, json={
                'text': question, 'sid': sid, 'type': 'text-query'
            }, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                ai = await resp.json()
                answer = ai.get('text', '')
                video_path = ai.get('videoPath', '')
                logs.append(f"DeepSeek: {answer[:60]}...")
        
        # Stage 3: TTS
        tts_audio = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(TTS_URL, json={
                    'text': answer[:200], 'voice': 'zh-CN-XiaoxiaoNeural'
                }, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    tts = await resp.json()
                    tts_audio = tts.get('audio', '')
                    logs.append(f"TTS: {len(tts_audio)} chars")
        except Exception as e:
            logs.append(f"TTS error: {e}")
        
        # Stage 4: Push video to SRS
        push_status = 'skipped'
        if room_id and video_path and tts_audio:
            try:
                push_status = await push_to_srs(room_id, video_path, tts_audio, answer, logs)
            except Exception as e:
                logs.append(f"Push error: {e}")
        
        elapsed = int((time.time() - start) * 1000)
        logs.append(f"Total: {elapsed}ms")
        
        return web.json_response({
            'text': answer,
            'videoPath': video_path,
            'ttsAudio': tts_audio,
            'elapsed': elapsed,
            'logs': logs,
            'pushStatus': push_status,
        })
    
    except Exception as e:
        return web.json_response({'error': str(e), 'text': '系统繁忙，请稍后再试'}, status=500)

async def push_to_srs(room_id, video_path, tts_audio, text, logs):
    """Generate video with TTS audio + avatar, push to SRS RTMP."""
    try:
        # Decode TTS audio
        audio_bytes = base64.b64decode(tts_audio)
        audio_file = os.path.join(tempfile.gettempdir(), f"tts_{room_id}.mp3")
        with open(audio_file, 'wb') as f:
            f.write(audio_bytes)
        
        # Get base avatar video
        avatar_file = os.path.join(AVATAR_VIDEO_DIR, os.path.basename(video_path))
        if not os.path.exists(avatar_file):
            avatar_file = os.path.join(AVATAR_VIDEO_DIR, 'greeting.webm')
        
        if not os.path.exists(avatar_file):
            logs.append("Push: no avatar video found")
            return 'no_video'
        
        # Try FFmpeg if available
        output_file = os.path.join(tempfile.gettempdir(), f"push_{room_id}.flv")
        
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            # Combine video + audio
            cmd = [
                ffmpeg_path, '-y',
                '-i', avatar_file,
                '-i', audio_file,
                '-c:v', 'libx264', '-preset', 'ultrafast',
                '-c:a', 'aac',
                '-shortest',
                '-f', 'flv', f'{SRS_RTMP}/{room_id}-ai'
            ]
            logs.append(f"Push: FFmpeg to SRS")
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return 'pushed'
        else:
            # Fallback: use Node.js RTMP push
            node_cmd = [
                'node', NODE_RTMP_PUSH,
                '--room', f'{room_id}-ai',
                '--video', avatar_file,
                '--audio', audio_file
            ]
            subprocess.Popen(node_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logs.append("Push: Node.js RTMP fallback")
            return 'pushed_node'
    
    except Exception as e:
        logs.append(f"Push exception: {e}")
        return f'error: {e}'

@routes.get('/health')
async def health(request):
    return web.json_response({'status': 'ok', 'service': 'pipeline-orchestrator'})

@routes.get('/logs')
async def get_logs(request):
    return web.json_response({'status': 'ok'})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    print("[Orchestrator] Starting on port 5007")
    web.run_app(app, port=5007)
