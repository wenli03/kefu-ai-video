import { useState, useEffect } from 'react';

interface Message {
  sender: 'customer' | 'ai' | 'agent' | 'system';
  text: string;
  time: number;
}

interface Props {
  messages: Message[];
  onSendText: (text: string) => void;
  placeholder?: string;
  speechText?: string;
}

export function ChatPanel({ messages, onSendText, placeholder = '输入消息...', speechText }: Props) {
  const [input, setInput] = useState('');

  // Update input when speech recognition provides text
  useEffect(() => {
    if (speechText !== undefined) {
      setInput(speechText);
    }
  }, [speechText]);

  const handleSend = () => {
    if (input.trim()) {
      onSendText(input.trim());
      setInput('');
    }
  };

  return (
    <div style={styles.panel}>
      <div style={styles.title}>对话记录</div>
      <div style={styles.messages}>
        {messages.map((m, i) => (
          <div key={i} style={{ ...styles.msg, ...getSenderStyle(m.sender) }}>
            <div style={styles.msgSender}>{getSenderLabel(m.sender)}</div>
            <div style={styles.msgText}>{m.text}</div>
            <div style={styles.msgTime}>{new Date(m.time).toLocaleTimeString()}</div>
          </div>
        ))}
      </div>
      <div style={styles.inputRow}>
        <input
          style={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={placeholder}
        />
        <button style={styles.sendBtn} onClick={handleSend}>
          发送
        </button>
      </div>
    </div>
  );
}

function getSenderLabel(sender: string) {
  const map: Record<string, string> = {
    customer: '客户', ai: 'AI客服', agent: '人工客服', system: '系统',
  };
  return map[sender] || sender;
}

function getSenderStyle(sender: string): React.CSSProperties {
  const colors: Record<string, string> = {
    customer: '#e3f2fd', ai: '#e8f5e9', agent: '#fff3e0', system: '#f5f5f5',
  };
  return { background: colors[sender] || '#f5f5f5' };
}

const styles: Record<string, React.CSSProperties> = {
  panel: { display: 'flex', flexDirection: 'column', height: '100%', background: '#fff', borderRadius: 8, overflow: 'hidden' },
  title: { padding: '10px 16px', borderBottom: '1px solid #e0e0e0', fontWeight: 600, fontSize: 14 },
  messages: { flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 },
  msg: { padding: '8px 12px', borderRadius: 8, maxWidth: '80%' },
  msgSender: { fontSize: 11, fontWeight: 600, color: '#666', marginBottom: 2 },
  msgText: { fontSize: 13, lineHeight: 1.5 },
  msgTime: { fontSize: 10, color: '#999', marginTop: 4 },
  inputRow: { display: 'flex', padding: 8, borderTop: '1px solid #e0e0e0', gap: 8 },
  input: { flex: 1, padding: '8px 12px', border: '1px solid #ddd', borderRadius: 6, fontSize: 13, outline: 'none' },
  sendBtn: { padding: '8px 16px', background: '#1976d2', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 500 },
};
