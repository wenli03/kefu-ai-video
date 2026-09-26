import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'ShopMind AI — 智能视频客服',
  description: '基于 LiveKit + LangChain + LangGraph 的电商AI客服系统',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body style={{ margin: 0, background: '#0a0e1a', color: '#f1f5f9', fontFamily: 'Inter, sans-serif' }}>
        {children}
      </body>
    </html>
  );
}
