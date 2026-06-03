import { useState, useCallback, useRef, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useWebRTC } from '../hooks/useWebRTC';
import { VideoPlayer } from '../components/VideoPlayer';
import { ChatPanel } from '../components/ChatPanel';
import { StatusBar } from '../components/StatusBar';
import './AgentPage.css';

interface ChatMessage {
  sender: 'customer' | 'ai' | 'agent' | 'system';
  text: string;
  time: number;
}

export function AgentPage() {
  const agentId = useRef(`agent-${Date.now()}`).current!;
  const agentName = useRef(`客服-${agentId.substring(6, 10)}`).current!;
  const [status, setStatus] = useState('IDLE');
  const [sid, setSid] = useState('');
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [incomingCall, setIncomingCall] = useState(false);
  const [inCall, setInCall] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { sender: 'system', text: `坐席 ${agentName} 已就绪，等待客户呼叫...`, time: Date.now() },
  ]);

  const { startPush, peerRef } = useWebRTC('push');

  const handleMessage = useCallback(
    (msg: any) => {
      console.log('[Agent] Received:', msg);
      switch (msg.type) {
        case 'login-ok':
          setStatus('ONLINE');
          break;
        case 'incoming-call':
          setIncomingCall(true);
          setSid(msg.sid);
          setMessages((prev) => [
            ...prev,
            { sender: 'system', text: `客户来电 — 会话: ${msg.sid}`, time: Date.now() },
          ]);
          break;
        case 'stream-ready':
          setStatus('BUSY');
          setInCall(true);
          break;
      }
    },
    []
  );

  const { send } = useWebSocket(agentId, 'agent', handleMessage);

  const hasLoggedIn = useRef(false);
  useEffect(() => {
    if (!hasLoggedIn.current) {
      hasLoggedIn.current = true;
      send({ type: 'agent-login', agentId, agentName });
    }
  }, [send, agentId, agentName]);

  const handleAccept = async () => {
    setIncomingCall(false);
    try {
      const stream = await startPush();
      setLocalStream(stream);
      send({ type: 'agent-accept', sid, agentId });
      setInCall(true);
      setMessages((prev) => [
        ...prev,
        { sender: 'system', text: '已接听，视频通话中', time: Date.now() },
      ]);
    } catch (err) {
      console.error('Failed to get media:', err);
    }
  };

  const handleReject = () => {
    setIncomingCall(false);
    send({ type: 'agent-hangup', agentId });
    setMessages((prev) => [
      ...prev,
      { sender: 'system', text: '已拒绝来电', time: Date.now() },
    ]);
  };

  const handleHangup = () => {
    send({ type: 'agent-hangup', agentId });
    setInCall(false);
    setStatus('ONLINE');
    localStream?.getTracks().forEach((t) => t.stop());
    peerRef.current?.close();
    setMessages((prev) => [
      ...prev,
      { sender: 'system', text: '通话已结束', time: Date.now() },
    ]);
  };

  const handleSendText = (text: string) => {
    setMessages((prev) => [...prev, { sender: 'agent', text, time: Date.now() }]);
  };

  return (
    <div className="agent-page">
      <StatusBar sid={sid} status={status} />

      <div className="agent-body">
        <div className="video-area">
          <VideoPlayer title={agentName} localStream={localStream} muted mirror />
          <VideoPlayer title="客户画面" style={{ background: '#333' }} />
        </div>

        <div className="chat-area">
          <ChatPanel messages={messages} onSendText={handleSendText} placeholder="输入消息..." />
        </div>
      </div>

      <div className="action-bar">
        {incomingCall ? (
          <>
            <button className="btn-accept" onClick={handleAccept}>
              接听
            </button>
            <button className="btn-reject" onClick={handleReject}>
              拒绝
            </button>
          </>
        ) : inCall ? (
          <button className="btn-end" onClick={handleHangup}>
            挂断
          </button>
        ) : (
          <span style={{ color: '#999', fontSize: 14 }}>等待客户来电...</span>
        )}
      </div>
    </div>
  );
}
