import { useState, useCallback, useRef, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useWebRTC } from '../hooks/useWebRTC';
import { VideoPlayer } from '../components/VideoPlayer';
import { VideoAvatar } from '../components/VideoAvatar';
import { ChatPanel } from '../components/ChatPanel';
import { StatusBar } from '../components/StatusBar';
import './CustomerPage.css';

interface ChatMessage {
  sender: 'customer' | 'ai' | 'agent' | 'system';
  text: string;
  time: number;
}

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export function CustomerPage() {
  const customerId = useRef(`cust-${Date.now()}`).current!;
  const [sid, setSid] = useState('');
  const sidRef = useRef('');
  useEffect(() => { sidRef.current = sid; }, [sid]);  // Keep ref in sync
  const [status, setStatus] = useState('IDLE');
  const [aiVideoUrl, setAiVideoUrl] = useState('');
  const [avatarText, setAvatarText] = useState('');
  const [audioBase64, setAudioBase64] = useState('');
  const [ttsWords, setTtsWords] = useState<any[]>([]);
  const [speechCount, setSpeechCount] = useState(0);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { sender: 'system', text: '欢迎使用AI视频客服，点击下方按钮开始通话', time: Date.now() },
  ]);
  const [inCall, setInCall] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [interimText, setInterimText] = useState('');
  const [listeningHint, setListeningHint] = useState('');
  const recognitionRef = useRef<any>(null);
  const accumulatedTextRef = useRef('');
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const listeningStatusRef = useRef('idle');

  const { startPush, startPull, peerRef } = useWebRTC('push');

  const handleMessage = useCallback(
    (msg: any) => {
      console.log('[Customer] Received:', msg);
      switch (msg.type) {
        case 'room-ready':
          setSid(msg.sid);
          setStatus('AI_ANSWERING');
          setMessages((prev) => [
            ...prev,
            { sender: 'system', text: 'AI客服已接入，正在聆听您的问题...', time: Date.now() },
          ]);
          // Auto-start voice recognition
          setTimeout(() => startListening(), 500);
          break;

        case 'ai-answer':
          setAvatarText(msg.text);
          setSpeechCount(c => c + 1);
          setMessages((prev) => [
            ...prev,
            { sender: 'ai', text: msg.text, time: Date.now() },
          ]);
          break;

        case 'video-play':
          setAiVideoUrl(msg.videoPath);
          break;

        case 'tts-audio':
          if (msg.audio) {
            setAudioBase64(msg.audio);
            setSpeechCount(c => c + 1);
          }
          break;

        case 'transfer-accepted':
          setStatus('HUMAN_SERVING');
          setMessages((prev) => [
            ...prev,
            { sender: 'system', text: msg.text || '已为您接通人工客服', time: Date.now() },
          ]);
          break;

        case 'session-ended':
          setStatus('ENDED');
          setInCall(false);
          setAiVideoUrl('');
          setAudioBase64('');
          setTtsWords([]);
          stopListening();
          // Stop camera and close peer connection
          localStreamRef.current?.getTracks().forEach(t => t.stop());
          localStreamRef.current = null;
          setLocalStream(null);
          peerRef.current?.close();
          peerRef.current = null;
          setMessages((prev) => [...prev, { sender: 'system', text: msg.text || '会话已结束，感谢使用智能客服', time: Date.now() }]);
          break;

        case 'queue-wait':
          setMessages((prev) => [...prev, { sender: 'system', text: msg.text, time: Date.now() }]);
          break;
      }
    },
    []
  );

  const { send } = useWebSocket(customerId, 'customer', handleMessage);

  // ===== ASR: Web Speech API with 2s silence auto-send =====
  const startListening = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMessages((prev) => [...prev, { sender: 'system', text: '浏览器不支持语音识别，请使用文字输入', time: Date.now() }]);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'zh-CN';
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.maxAlternatives = 1;

    const sendAccumulated = () => {
      const text = accumulatedTextRef.current.trim();
      if (text && sidRef.current) {
        console.log('[ASR] Auto-sending after 1s silence:', text);
        setListeningHint('');
        setMessages((prev) => [...prev, { sender: 'customer', text, time: Date.now() }]);
        send({ type: 'audio', sid: sidRef.current, text });
        accumulatedTextRef.current = '';
      }
    };

    const resetSilenceTimer = () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = setTimeout(sendAccumulated, 200);
    };

    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          accumulatedTextRef.current += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
        }
      }
      // Show what's being recognized as listening hint
      if (interimTranscript || accumulatedTextRef.current) {
        setListeningHint(accumulatedTextRef.current + interimTranscript);
      }
      resetSilenceTimer();
    };

    recognition.onstart = () => {
      setListeningHint('正在聆听...');
    };

    recognition.onerror = (event: any) => {
      console.warn('[ASR] Error:', event.error);
      if (event.error === 'no-speech' || event.error === 'aborted') {
        if (listeningStatusRef.current === 'active') {
          try { recognition.start(); } catch (e) {}
        }
      }
    };

    recognition.onend = () => {
      if (listeningStatusRef.current === 'active') {
        try { recognition.start(); } catch (e) { }
      }
    };

    recognition.start();
    recognitionRef.current = recognition;
    listeningStatusRef.current = 'active';
    setIsListening(true);
    accumulatedTextRef.current = '';
    setMessages((prev) => [...prev, { sender: 'system', text: '语音已开启，说话后停顿1秒自动发送', time: Date.now() }]);
    console.log('[ASR] Listening started, sid=', sidRef.current);
  }, [send]); // Only depend on send, use sidRef for current sid

  const stopListening = useCallback(() => {
    listeningStatusRef.current = 'stopped';
    setIsListening(false);
    setInterimText('');
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
      recognitionRef.current = null;
    }
    console.log('[ASR] Listening stopped');
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) {}
      }
    };
  }, []);

  // ===== Call handling =====
  const handleCall = async () => {
    setInCall(true);
    setStatus('QUEUING');
    send({ type: 'call', payload: { customerId } });
    try {
      const stream = await startPush();
      setLocalStream(stream);
      localStreamRef.current = stream;
    } catch (err) {
      console.warn('Camera unavailable:', err);
      setMessages((prev) => [...prev, { sender: 'system', text: '摄像头未就绪，请使用语音模式', time: Date.now() }]);
    }
  };

  const handleTransfer = () => {
    send({ type: 'transfer', sid: sidRef.current });
    setStatus('TRANSFERRING');
    setMessages((prev) => [...prev, { sender: 'system', text: '正在为您转接人工客服...', time: Date.now() }]);
  };

  const handleSendText = (text: string) => {
    setMessages((prev) => [...prev, { sender: 'customer', text, time: Date.now() }]);
    send({ type: 'audio', sid: sidRef.current, text });
  };

  const handleEnd = () => {
    stopListening();
    send({ type: 'end', sid: sidRef.current });
    setInCall(false);
    setStatus('ENDED');
    localStreamRef.current?.getTracks().forEach(t => t.stop());
    localStreamRef.current = null;
    setLocalStream(null);
    peerRef.current?.close();
    peerRef.current = null;
  };
  
  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  return (
    <div className="customer-page">
      <StatusBar sid={sid} status={status} />

      {listeningHint && (
        <div style={{
          background: '#e3f2fd', padding: '8px 16px', textAlign: 'center',
          borderBottom: '2px solid #2196f3', fontSize: 14, color: '#1565c0',
          fontWeight: 500, animation: 'pulse 1.5s infinite'
        }}>
          {listeningHint}
        </div>
      )}

      <div className="customer-body">
        <div className="video-area">
          <VideoPlayer title="您的画面" localStream={localStream} muted mirror />
          <div style={{ position:'relative', background:'#1a1a2e', borderRadius:0, overflow:'hidden' }}>
            <VideoAvatar videoSrc={aiVideoUrl} audioBase64={audioBase64} trigger={speechCount} />
          </div>
        </div>

        <div className="chat-area">
          <ChatPanel
            messages={messages}
            onSendText={handleSendText}
            speechText={interimText}
            placeholder="输入文字或直接说话..."
          />
          {inCall && (
            <div style={{ padding: '0 8px 8px', display: 'flex', justifyContent: 'center', gap: 8 }}>
              <button
                onClick={toggleListening}
                style={{
                  padding: '8px 20px', borderRadius: 20, border: 'none',
                  background: isListening ? '#e91e63' : '#4caf50',
                  color: '#fff', fontSize: 14, cursor: 'pointer', fontWeight: 600,
                }}
              >
                {isListening ? '⏹ 停止语音' : '🎤 语音识别'}
              </button>
              <span style={{ fontSize: 12, color: '#999', alignSelf: 'center' }}>
                {isListening ? '正在听您说话...' : '点击开启语音'}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="action-bar">
        {!inCall ? (
          <button className="btn-call" onClick={handleCall}>联系客服</button>
        ) : (
          <>
            <button className="btn-transfer" onClick={handleTransfer} disabled={status !== 'AI_ANSWERING'}>转人工</button>
            <button className="btn-end" onClick={handleEnd}>结束通话</button>
          </>
        )}
      </div>
    </div>
  );
}
