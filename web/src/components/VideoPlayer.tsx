import { useRef, useEffect } from 'react';

interface Props {
  title: string;
  localStream?: MediaStream | null;
  remoteSrc?: string;
  muted?: boolean;
  mirror?: boolean;
  style?: React.CSSProperties;
}

export function VideoPlayer({ title, localStream, remoteSrc, muted = false, mirror = false, style }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current && localStream) {
      videoRef.current.srcObject = localStream;
    }
  }, [localStream]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !remoteSrc) return;
    // React already set src attribute - just call play
    video.play().catch(() => {});
  }, [remoteSrc]);

  return (
    <div style={{ ...styles.container, ...style }}>
      <div style={styles.label}>{title}</div>
      <video
        ref={videoRef}
        src={remoteSrc || undefined}
        autoPlay
        playsInline
        muted={muted}
        loop
        style={{ ...styles.video, transform: mirror ? 'scaleX(-1)' : 'none' }}
      />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { background: '#1a1a2e', borderRadius: 8, overflow: 'hidden', position: 'relative' },
  label: { position: 'absolute', top: 8, left: 8, zIndex: 2, background: 'rgba(0,0,0,0.6)', color: '#fff', padding: '2px 10px', borderRadius: 4, fontSize: 12 },
  video: { width: '100%', height: '100%', objectFit: 'cover', background: '#1a1a2e' },
};
