/**
 * ASR Service — Speech-to-Text
 * For demo: primary ASR happens in browser (Web Speech API).
 * Server-side fallback: simple keyword extraction from audio metadata.
 * Production: replace with iFlytek/Deepgram API call.
 */
export function getAsrService() {
  return {
    /** Process base64 audio → text (server-side) */
    async speechToText(audioBase64: string): Promise<string> {
      // In production, send to ASR API:
      // const resp = await axios.post('https://api.deepgram.com/v1/listen', { audio: audioBase64 });
      // return resp.data.channel.alternatives[0].transcript;

      // Demo: audio received but can't decode server-side
      // Return placeholder — browser-side Web Speech API handles actual recognition
      console.log('[ASR] Audio received, ' + audioBase64.length + ' chars base64');
      return '[语音消息]';
    },

    /** Direct text (from browser ASR or typed input) */
    async speechToTextDirect(text: string): Promise<string> {
      return text;
    },
  };
}
