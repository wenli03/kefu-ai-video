"""TTS service with word timing and viseme data."""
import json
import sys
import base64
import asyncio

import edge_tts
from pypinyin import pinyin, Style

def get_final(py_text: str) -> str:
    """Extract the final (vowel part) from pinyin."""
    if not py_text:
        return ''
    # Remove initial consonant
    initials = ['zh','ch','sh','b','p','m','f','d','t','n','l','g','k','h','j','q','x','r','z','c','s','y','w']
    final = py_text
    for init in sorted(initials, key=len, reverse=True):
        if final.startswith(init):
            final = final[len(init):]
            break
    return final

def get_viseme(py_text: str) -> str:
    """Map Chinese pinyin final to viseme type: wide, round, spread, neutral, closed."""
    f = get_final(py_text).rstrip('0123456789')  # remove tone numbers
    if not f:
        return 'neutral'
    # Wide: a-based finals
    if f[0] in ('a',):
        return 'wide'
    # Round: o, u, uo, ou, ong
    if f[0] in ('o', 'u'):
        return 'round'
    # Spread (smile): i-based finals
    if f[0] in ('i',):
        return 'spread'
    # Purse: v/ü-based finals
    if f[0] in ('v', '\u00fc'):  # v or ü
        return 'tight'
    # Neutral: e-based
    return 'neutral'

async def tts_with_timing(text: str, voice: str = 'zh-CN-XiaoxiaoNeural') -> dict:
    communicate = edge_tts.Communicate(text, voice)
    words = []
    audio_parts = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_parts.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            word_text = chunk.get("text", "")
            py_str = ''
            viseme = 'neutral'
            if word_text:
                py_list = pinyin(word_text, style=Style.TONE3, errors='ignore')
                py_str = ' '.join([p[0] for p in py_list if p])
                viseme = get_viseme(py_str.split()[-1] if py_str.split() else '')
            words.append({
                "text": word_text,
                "pinyin": py_str,
                "startMs": round(chunk["offset"] / 10000, 1),
                "durationMs": round(chunk["duration"] / 10000, 1),
                "viseme": viseme
            })

    raw = bytearray()
    for b64 in audio_parts:
        # Add padding if needed
        padding = 4 - len(b64) % 4
        if padding != 4:
            b64 += '=' * padding
        raw.extend(base64.b64decode(b64))

    return {
        "audio": base64.b64encode(bytes(raw)).decode(),
        "format": "mp3",
        "voice": voice,
        "words": words
    }

if __name__ == '__main__':
    text = sys.argv[1] if len(sys.argv) > 1 else "你好，欢迎使用智能客服"
    result = asyncio.run(tts_with_timing(text))
    print(json.dumps(result, ensure_ascii=False))
