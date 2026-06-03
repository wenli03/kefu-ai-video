"""TTS with word-level timing via edge-tts + proportional word splitting."""
import json, sys, os, subprocess, tempfile, base64, re
from pypinyin import pinyin, Style

def get_final(py_text: str) -> str:
    if not py_text: return ''
    initials = ['zh','ch','sh','b','p','m','f','d','t','n','l','g','k','h','j','q','x','r','z','c','s','y','w']
    final = py_text
    for init in sorted(initials, key=len, reverse=True):
        if final.startswith(init):
            final = final[len(init):]
            break
    return final

def get_viseme(py_text: str) -> str:
    f = get_final(py_text).rstrip('0123456789')
    if not f: return 'neutral'
    if f[0] in ('a',): return 'wide'
    if f[0] in ('o', 'u'): return 'round'
    if f[0] in ('i',): return 'spread'
    if f[0] in ('v', '\u00fc'): return 'tight'
    return 'neutral'

def split_chinese(text: str) -> list:
    """Split Chinese text into word segments by punctuation."""
    segs = []
    cur = ''
    for ch in text:
        if ch in r'，。！？；：、 \t\r\n':
            if cur:
                segs.append(cur)
                cur = ''
        else:
            cur += ch
    if cur: segs.append(cur)
    return segs

def expand_words(segments: list, vtt_start_ms: int, vtt_duration_ms: int) -> list:
    """Distribute sentence timing across word segments proportionally."""
    total_chars = sum(len(s) for s in segments)
    if total_chars == 0: return []
    words = []
    elapsed = 0
    for seg in segments:
        seg_dur = max(50, int(len(seg) / total_chars * vtt_duration_ms))
        py_list = pinyin(seg, style=Style.TONE3, errors='ignore')
        py_str = ' '.join([p[0] for p in py_list if p])
        viseme = get_viseme(py_str.split()[-1] if py_str.split() else '')
        words.append({
            "text": seg,
            "pinyin": py_str,
            "startMs": vtt_start_ms + elapsed,
            "durationMs": seg_dur,
            "viseme": viseme
        })
        elapsed += seg_dur
    return words

def parse_vtt(vtt_path: str) -> list:
    words = []
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n\s*(.+?)(?:\n\n|\n(?=\d)|\Z)'
    for m in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
        def to_ms(s):
            s = s.replace(',', '.')
            h, m_sec, rest = s.split(':')
            return int(h)*3600000 + int(m_sec)*60000 + int(float(rest)*1000)
        start_ms = to_ms(m.group(1))
        dur_ms = to_ms(m.group(2)) - start_ms
        sent_text = m.group(3).strip()
        if not sent_text: continue
        segs = split_chinese(sent_text)
        words.extend(expand_words(segs, start_ms, dur_ms))
    return words

def tts(text: str, voice: str = 'zh-CN-XiaoxiaoNeural') -> dict:
    tmp_audio = tempfile.mktemp(suffix='.mp3')
    tmp_vtt = tempfile.mktemp(suffix='.vtt')
    try:
        subprocess.run([
            sys.executable, '-m', 'edge_tts',
            '--voice', voice,
            '--text', text,
            '--write-media', tmp_audio,
            '--write-subtitles', tmp_vtt
        ], capture_output=True, timeout=30, check=True)
        with open(tmp_audio, 'rb') as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        words = parse_vtt(tmp_vtt) if os.path.exists(tmp_vtt) else []
        return {"audio": audio_b64, "format": "mp3", "voice": voice, "words": words}
    finally:
        for f in [tmp_audio, tmp_vtt]:
            try:
                os.unlink(f)
            except:
                pass

def tts(text: str, voice: str = 'zh-CN-XiaoxiaoNeural') -> dict:
    tmp_audio = tempfile.mktemp(suffix='.mp3')
    tmp_vtt = tempfile.mktemp(suffix='.vtt')
    try:
        subprocess.run([
            sys.executable, '-m', 'edge_tts',
            '--voice', voice,
            '--text', text,
            '--write-media', tmp_audio,
            '--write-subtitles', tmp_vtt
        ], capture_output=True, timeout=30, check=True)
        with open(tmp_audio, 'rb') as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        words = parse_vtt(tmp_vtt) if os.path.exists(tmp_vtt) else []
        return {"audio": audio_b64, "format": "mp3", "voice": voice, "words": words}
    finally:
        for f in [tmp_audio, tmp_vtt]:
            try: os.unlink(f)
            except: pass

if __name__ == '__main__':
    text = sys.argv[1] if len(sys.argv) > 1 else ''
    if not text: sys.exit(1)
    result = tts(text)
    print(json.dumps(result, ensure_ascii=False))
