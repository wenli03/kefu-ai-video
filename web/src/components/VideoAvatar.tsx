import { useRef, useEffect, useState } from 'react';

interface Props { videoSrc?: string; audioBase64?: string; trigger?: number; width?: number; height?: number; }

export function VideoAvatar({ videoSrc, audioBase64, trigger = 0, width = 320, height = 480 }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const idleRef = useRef(true);
  const lastTriggerRef = useRef(0);
  const [speaking, setSpeaking] = useState(false);

  // Play response video
  useEffect(() => {
    if (!videoSrc) return;
    if (idleRef.current) { idleRef.current = false; return; }
    const video = videoRef.current; if (!video) return;
    video.src = videoSrc; video.loop = false; video.muted = true; video.playsInline = true;
    video.currentTime = 0; video.play().catch(() => {});
  }, [videoSrc]);

  // Play TTS audio
  useEffect(() => {
    if (!audioBase64 || trigger === 0 || trigger === lastTriggerRef.current) return;
    lastTriggerRef.current = trigger;
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ''; audioRef.current = null; }
    const audio = new Audio('data:audio/mp3;base64,' + audioBase64);
    audioRef.current = audio;
    setSpeaking(true);
    audio.onended = () => {
      setSpeaking(false);
      // Return to idle
      const v = videoRef.current;
      if (v) { v.src = '/avatar-videos/greeting.webm'; v.loop = true; v.muted = true; v.playsInline = true; v.play().catch(() => {}); }
    };
    audio.onerror = () => { setSpeaking(false); };
    audio.play().catch(() => {});
    return () => { audio.pause(); audio.src = ''; setSpeaking(false); };
  }, [audioBase64, trigger]);

  // Idle greeting on mount
  useEffect(() => {
    const v = videoRef.current;
    if (v) { v.src = '/avatar-videos/greeting.webm'; v.loop = true; v.muted = true; v.playsInline = true; v.play().catch(() => {}); }
    return () => { idleRef.current = true; };
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', background: '#0a0a1a', overflow: 'hidden' }}>
      <video ref={videoRef} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
      {speaking && <div style={{ position: 'absolute', bottom: 12, right: 12, width: 14, height: 14, borderRadius: '50%', background: '#00ff88', boxShadow: '0 0 8px #00ff88', zIndex: 2 }} />}
      <div style={{ position: 'absolute', top: 8, left: 8, background: 'rgba(0,0,0,0.5)', color: '#fff', padding: '2px 10px', borderRadius: 4, fontSize: 12, zIndex: 2 }}>保险客服{speaking ? ' · Speaking' : ''}</div>
    </div>
  );
}
