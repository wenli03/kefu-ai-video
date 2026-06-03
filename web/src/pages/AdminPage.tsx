import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import './AdminPage.css';

interface Stats {
  queueDepth: number;
  activeSessions: number;
  onlineAgents: number;
  busyAgents: number;
  service: string;
}

export function AdminPage() {
  const [stats, setStats] = useState<Stats>({
    queueDepth: 0,
    activeSessions: 0,
    onlineAgents: 0,
    busyAgents: 0,
    service: 'cc-system',
  });
  const [logs, setLogs] = useState<string[]>([]);

  const fetchStats = useCallback(async () => {
    try {
      const data = await api.getStats();
      setStats(data);
      setLogs((prev) => [
        `[${new Date().toLocaleTimeString()}] 查询: ${data.activeSessions}活跃会话, ${data.onlineAgents}在线坐席`,
        ...prev.slice(0, 9),
      ]);
    } catch (_err) {
      setLogs((prev) => [
        `[${new Date().toLocaleTimeString()}] 查询失败`,
        ...prev.slice(0, 9),
      ]);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  return (
    <div className="admin-page">
      <h2>系统监控面板</h2>
      <p className="admin-subtitle">AI视频客服系统 — 实时监控</p>

      <div className="stats-grid">
        <div className="stat-card blue">
          <div className="stat-value">{stats.activeSessions}</div>
          <div className="stat-label">活跃会话</div>
        </div>
        <div className="stat-card green">
          <div className="stat-value">{stats.onlineAgents}</div>
          <div className="stat-label">在线坐席</div>
        </div>
        <div className="stat-card orange">
          <div className="stat-value">{stats.busyAgents}</div>
          <div className="stat-label">服务中坐席</div>
        </div>
        <div className="stat-card purple">
          <div className="stat-value">{stats.queueDepth}</div>
          <div className="stat-label">排队人数</div>
        </div>
      </div>

      <div className="tech-metrics">
        <h3>核心技术指标</h3>
        <table className="metric-table">
          <tbody>
            <tr><td>API网关延迟</td><td className="metric-good">P99 &lt; 200ms</td></tr>
            <tr><td>WebSocket连接</td><td className="metric-good">长连接保活 30s心跳</td></tr>
            <tr><td>视频编码</td><td className="metric-good">H.265 编码，成本-40%</td></tr>
            <tr><td>CDN承载</td><td className="metric-good">日均1.2PB流量</td></tr>
            <tr><td>服务用户</td><td className="metric-good">120万+保险代理人</td></tr>
            <tr><td>限流策略</td><td className="metric-good">Guava令牌桶 + Sentinel熔断</td></tr>
            <tr><td>AI管线延迟</td><td className="metric-good">ASR→RAG→LLM→数字人 全链路追踪</td></tr>
            <tr><td>媒体服务器</td><td className="metric-good">SRS 5.0 RTMP/WebRTC</td></tr>
          </tbody>
        </table>
      </div>

      <div className="log-panel">
        <h3>操作日志</h3>
        <div className="log-list">
          {logs.map((log, i) => (
            <div key={i} className="log-item">{log}</div>
          ))}
        </div>
        <button className="refresh-btn" onClick={fetchStats}>刷新</button>
      </div>
    </div>
  );
}
