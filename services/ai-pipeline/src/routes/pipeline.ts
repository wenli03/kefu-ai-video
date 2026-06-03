import { Router, Request, Response } from 'express';
import { getAsrService } from '../services/asr-service';
import { getRagService } from '../services/rag-service';
import { getDeepseekService } from '../services/deepseek-service';
import { getAvatarService } from '../services/avatar-service';
import path from 'path';

const router = Router();
const asr = getAsrService();
const rag = getRagService();
const deepseek = getDeepseekService();
const avatar = getAvatarService();

const knowledgeDir = path.join(__dirname, '..', 'data', 'knowledge');
rag.init(knowledgeDir);

router.post('/ask', async (req: Request, res: Response) => {
  console.log(`[Pipeline] REQ text="${req.body.text}" audio=${!!req.body.audioData}`);
  try {
    const { audioData, text: directText } = req.body;
    const startTime = Date.now();

    // Stage 1: ASR — Speech to Text
    let question: string;
    if (directText) {
      question = await asr.speechToTextDirect(directText);
      console.log(`[Pipeline] Stage1-ASR: text="${question.substring(0, 40)}"`);
    } else if (audioData) {
      question = await asr.speechToText(audioData);
      console.log(`[Pipeline] Stage1-ASR: audio(${audioData.length}B)→"${question.substring(0, 40)}"`);
    } else {
      return res.status(400).json({ error: 'audioData or text is required' });
    }

    // Stage 2: RAG — Knowledge Retrieval
    const contexts = await rag.search(question);
    console.log(`[Pipeline] Stage2-RAG: found ${contexts.length} documents`);

    // Stage 3: DeepSeek — LLM Answer Generation
    const answer = await deepseek.ask(question, contexts);
    console.log(`[Pipeline] Stage3-DeepSeek: "${answer.substring(0, 60)}..."`);

    // Stage 4: Digital Human — Avatar Video Matching
    const videoPath = avatar.matchVideo(answer, question);
    console.log(`[Pipeline] Stage4-Avatar: matched ${videoPath}`);

    // Stage 5: TTS — Text to Speech (generate voice for digital human)
    let ttsAudio: string | null = null;
    try {
      const ttsResp = await fetch('http://localhost:5005/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: answer.substring(0, 200), voice: 'zh-CN-XiaoxiaoNeural' }),
        signal: AbortSignal.timeout(15000),
      });
      if (ttsResp.ok) {
        const ttsData = await ttsResp.json();
        ttsAudio = ttsData.audio;
        console.log(`[Pipeline] Stage5-TTS: generated ${ttsAudio!.length}B audio`);
      }
    } catch (e: any) {
      console.log(`[Pipeline] Stage5-TTS: ${e.message}`);
    }

    const elapsed = Date.now() - startTime;
    console.log(`[Pipeline] Done in ${elapsed}ms — ASR→RAG→DeepSeek→Avatar→TTS`);

    return res.json({
      type: 'ai-response',
      text: answer,
      videoPath,
      ttsAudio,
      confidence: 0.85,
      sources: contexts.slice(0, 2),
      elapsed,
    });
  } catch (err: any) {
    console.error('Pipeline error:', err);
    return res.status(500).json({
      type: 'ai-response',
      text: '抱歉，AI服务暂时不可用，请稍后再试或转接人工客服。',
      videoPath: null,
      confidence: 0,
      sources: [],
    });
  }
});

router.post('/speech', async (_req: Request, res: Response) => {
  return res.json({ type: 'tts-response', audioUrl: null, text: 'TTS placeholder' });
});

router.get('/knowledge', (_req: Request, res: Response) => {
  return res.json({ note: 'Knowledge base initialized. Use POST /api/pipeline/ask to query.' });
});

export default router;
