"""TTS HTTP Server - Text to Speech using edge-tts."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess, tempfile, os, json, base64, sys

PORT = 5005

class TTSHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/tts':
            self.send_error(404)
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length))
        text = body.get('text', '')
        voice = body.get('voice', 'zh-CN-XiaoxiaoNeural')
        
        if not text:
            self.send_error(400, 'text is required')
            return
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                tmp = f.name
            
            cmd = [sys.executable, '-m', 'edge_tts', '--voice', voice, '--text', text, '--write-media', tmp]
            subprocess.run(cmd, capture_output=True, timeout=30)
            
            with open(tmp, 'rb') as f:
                audio = f.read()
            os.unlink(tmp)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'audio': base64.b64encode(audio).decode(),
                'format': 'mp3',
                'voice': voice
            }).encode())
        except Exception as e:
            self.send_error(500, str(e))
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'service': 'tts'}).encode())
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    print(f'[TTS] Starting on port {PORT}')
    server = HTTPServer(('0.0.0.0', PORT), TTSHandler)
    server.serve_forever()
