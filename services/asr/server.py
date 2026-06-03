"""
ASR HTTP Service - Speech to Text using OpenAI Whisper
POST /asr - accepts base64 audio, returns transcribed text
"""
from aiohttp import web
import whisper
import base64
import tempfile
import os
import asyncio
import time

# Load model once at startup
print("[ASR] Loading whisper model (base)...")
model = whisper.load_model("base")
print("[ASR] Whisper model loaded")

async def transcribe(request):
    """POST /asr — audio base64 → text"""
    start = time.time()
    try:
        data = await request.json()
        audio_b64 = data.get('audio', '')
        if not audio_b64:
            return web.json_response({'error': 'audio is required'}, status=400)
        
        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_b64)
        
        # Write to temp file (whisper needs a file path)
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        
        try:
            # Transcribe
            result = model.transcribe(tmp_path, language='zh', fp16=False)
            text = result['text'].strip()
        finally:
            os.unlink(tmp_path)
        
        elapsed = int((time.time() - start) * 1000)
        print(f"[ASR] {elapsed}ms: {text[:60]}")
        
        return web.json_response({
            'text': text,
            'elapsed': elapsed,
            'confidence': result.get('segments', [{}])[0].get('confidence', 0) if result.get('segments') else 0
        })
    
    except Exception as e:
        print(f"[ASR] Error: {e}")
        return web.json_response({'error': str(e), 'text': ''}, status=500)

async def health(request):
    return web.json_response({'status': 'ok', 'service': 'asr-whisper', 'model': 'base'})

app = web.Application()
app.router.add_post('/asr', transcribe)
app.router.add_get('/health', health)

if __name__ == '__main__':
    print("[ASR] Starting on port 5006")
    web.run_app(app, port=5006)
