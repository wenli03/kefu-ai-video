interface Props {
  sid?: string;
  status: string;
  queueDepth?: number;
  elapsed?: number;
}

export function StatusBar({ sid, status, queueDepth, elapsed }: Props) {
  const statusMap: Record<string, { text: string; color: string }> = {
    QUEUING: { text: '排队中', color: '#ff9800' },
    AI_ANSWERING: { text: 'AI客服中', color: '#2196f3' },
    TRANSFERRING: { text: '转接中', color: '#9c27b0' },
    HUMAN_SERVING: { text: '人工服务中', color: '#4caf50' },
    ENDED: { text: '已结束', color: '#f44336' },
    IDLE: { text: '空闲', color: '#4caf50' },
    BUSY: { text: '忙碌', color: '#ff9800' },
    ONLINE: { text: '在线', color: '#4caf50' },
  };

  const info = statusMap[status] || { text: status, color: '#999' };

  return (
    <div style={styles.bar}>
      {sid && <span style={styles.item}>会话: {sid}</span>}
      <span style={{ ...styles.badge, background: info.color }}>{info.text}</span>
      {queueDepth !== undefined && <span style={styles.item}>队列: {queueDepth}人</span>}
      {elapsed !== undefined && <span style={styles.item}>耗时: {elapsed}ms</span>}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: { display: 'flex', alignItems: 'center', gap: 12, padding: '8px 16px', background: '#fff', borderBottom: '1px solid #e0e0e0', fontSize: 13 },
  item: { color: '#666' },
  badge: { padding: '2px 10px', borderRadius: 12, color: '#fff', fontSize: 12, fontWeight: 500 },
};
