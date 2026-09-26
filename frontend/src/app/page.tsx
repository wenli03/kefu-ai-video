'use client';

import { useState, useRef, useEffect } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  agent?: string;
  latency?: number;
}

interface Metrics {
  counters: Record<string, number>;
  gauges: Record<string, number>;
  histograms: Record<string, { count: number; mean: number }>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: '您好！我是AI购物助手小智，很高兴为您服务。请问有什么可以帮助您的吗？' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => Math.random().toString(36).slice(2, 10));
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [showMetrics, setShowMetrics] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input, session_id: sessionId }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        intent: data.intent,
        agent: data.agent,
        latency: data.latency_ms,
      }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: '服务暂时不可用，请稍后重试。' }]);
    }
    setLoading(false);
  };

  const loadMetrics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/metrics`);
      setMetrics(await res.json());
      setShowMetrics(true);
    } catch { /* ignore */ }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', borderBottom: '1px solid #2a3550', background: '#111827' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: 'linear-gradient(135deg, #6366f1, #a855f7)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700 }}>S</div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 15 }}>ShopMind AI</div>
            <div style={{ fontSize: 11, color: '#64748b' }}>v2.0 · LangGraph + Multi-Agent + LangSmith</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <span style={{ fontSize: 11, color: '#64748b', fontFamily: 'monospace' }}>Session: {sessionId}</span>
          <button onClick={loadMetrics} style={{ padding: '4px 12px', background: '#1a2236', border: '1px solid #2a3550', borderRadius: 6, color: '#94a3b8', fontSize: 12, cursor: 'pointer' }}>Metrics</button>
        </div>
      </header>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', gap: 12, flexDirection: msg.role === 'user' ? 'row-reverse' : 'row', maxWidth: '85%', alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, flexShrink: 0, background: msg.role === 'assistant' ? 'linear-gradient(135deg, #6366f1, #a855f7)' : '#1a2236', border: msg.role === 'user' ? '1px solid #2a3550' : 'none' }}>
              {msg.role === 'assistant' ? '🤖' : '👤'}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <div style={{ padding: '10px 14px', borderRadius: 16, fontSize: 14, lineHeight: 1.6, background: msg.role === 'assistant' ? '#1a2236' : '#6366f1', border: msg.role === 'assistant' ? '1px solid #2a3550' : 'none', borderBottomLeftRadius: msg.role === 'assistant' ? 4 : 16, borderBottomRightRadius: msg.role === 'user' ? 4 : 16 }}>
                {msg.content}
              </div>
              {msg.agent && (
                <div style={{ fontSize: 10, color: '#64748b', fontFamily: 'monospace' }}>
                  [{msg.agent.toUpperCase()}] intent={msg.intent} · {msg.latency}ms
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && <div style={{ color: '#64748b', fontSize: 13, padding: '0 44px' }}>小智正在思考...</div>}
        <div ref={messagesEndRef} />
      </div>

      {/* Metrics Panel */}
      {showMetrics && metrics && (
        <div style={{ padding: '12px 20px', borderTop: '1px solid #2a3550', background: '#111827', fontSize: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8, color: '#94a3b8' }}>System Metrics</div>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            {Object.entries(metrics.counters || {}).map(([k, v]) => (
              <div key={k}><span style={{ color: '#64748b' }}>{k}:</span> <span style={{ fontFamily: 'monospace', color: '#f1f5f9' }}>{v}</span></div>
            ))}
            {Object.entries(metrics.gauges || {}).map(([k, v]) => (
              <div key={k}><span style={{ color: '#64748b' }}>{k}:</span> <span style={{ fontFamily: 'monospace', color: '#10b981' }}>{v}</span></div>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div style={{ padding: '12px 20px', borderTop: '1px solid #2a3550', background: '#111827', display: 'flex', gap: 10 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
          placeholder="输入消息..."
          style={{ flex: 1, padding: '10px 16px', background: '#0f1629', border: '1px solid #2a3550', borderRadius: 8, color: '#f1f5f9', fontSize: 14, outline: 'none' }}
        />
        <button onClick={sendMessage} disabled={loading} style={{ padding: '10px 20px', background: '#6366f1', color: 'white', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: loading ? 'default' : 'pointer', opacity: loading ? 0.6 : 1 }}>
          发送
        </button>
      </div>
    </div>
  );
}
