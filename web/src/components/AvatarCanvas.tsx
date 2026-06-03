import { useRef, useEffect, useCallback, useState } from 'react';

interface Word { text: string; pinyin: string; startMs: number; durationMs: number; viseme: string; }
interface Props { audioBase64?: string; words?: Word[]; trigger?: number; width?: number; height?: number; }

const visemeShapes: Record<string, { h: number; w: number; round: number }> = {
  wide: { h: 1.0, w: 1.0, round: 0.1 },
  round: { h: 0.6, w: 0.65, round: 0.8 },
  spread: { h: 0.35, w: 1.2, round: 0.0 },
  neutral: { h: 0.45, w: 0.85, round: 0.3 },
  tight: { h: 0.25, w: 0.5, round: 0.9 },
  closed: { h: 0.0, w: 0.7, round: 0.2 },
};

export function AvatarCanvas({ audioBase64, words, trigger = 0, width = 320, height = 480 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const photoRef = useRef<HTMLImageElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const visemeRef = useRef('closed');
  const speakingRef = useRef(false);
  const blinkRef = useRef(0);
  const lastBlinkRef = useRef(0);
  const lastTriggerRef = useRef(0);
  const [ready, setReady] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [interrupted, setInterrupted] = useState(false);
  const lipColor = useRef({ r: 210, g: 100, b: 80, a: 1 });
  const skinColor = useRef({ r: 210, g: 160, b: 120 });

  // Load photo and sample colors from original mouth/lip area
  useEffect(() => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const oc = document.createElement('canvas');
      oc.width = width; oc.height = height;
      const ctx = oc.getContext('2d');
      if (!ctx) return;
      const scale = Math.max(width / img.width, height / img.height);
      ctx.drawImage(img, (width - img.width * scale) / 2, (height - img.height * scale) / 2, img.width * scale, img.height * scale);

      // Sample lip color from original mouth area
      const lipX = Math.round(width * 0.5);
      const lipY = Math.round(height * 0.70);
      const lipSample = ctx.getImageData(lipX - 8, lipY - 3, 16, 3);
      let lr = 0, lg = 0, lb = 0, ln = 0;
      for (let i = 0; i < lipSample.data.length; i += 4) {
        lr += lipSample.data[i]; lg += lipSample.data[i + 1]; lb += lipSample.data[i + 2]; ln++;
      }
      lipColor.current = { r: Math.round(lr / ln), g: Math.round(lg / ln), b: Math.round(lb / ln), a: 1 };

      // Sample skin from cheek area
      const skinX = Math.round(width * 0.5);
      const skinY = Math.round(height * 0.35);
      const skinSample = ctx.getImageData(skinX - 10, skinY, 20, 4);
      let sr = 0, sg = 0, sb = 0, sn = 0;
      for (let i = 0; i < skinSample.data.length; i += 4) {
        sr += skinSample.data[i]; sg += skinSample.data[i + 1]; sb += skinSample.data[i + 2]; sn++;
      }
      skinColor.current = { r: Math.round(sr / sn), g: Math.round(sg / sn), b: Math.round(sb / sn) };

      photoRef.current = img;
      setReady(true);
    };
    img.src = '/portrait.jpg';
  }, [width, height]);

  useEffect(() => {
    if (!audioBase64 || !words || words.length === 0 || trigger === 0 || trigger === lastTriggerRef.current) return;
    if (speakingRef.current) { setInterrupted(true); setTimeout(() => setInterrupted(false), 800); }
    lastTriggerRef.current = trigger;
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ''; audioRef.current = null; }
    visemeRef.current = 'closed';
    speakingRef.current = true;
    setSpeaking(true);
    const audio = new Audio('data:audio/mp3;base64,' + audioBase64);
    audioRef.current = audio;
    const timers: number[] = [];
    for (const w of words) {
      timers.push(window.setTimeout(() => { visemeRef.current = w.viseme; }, w.startMs));
      timers.push(window.setTimeout(() => { visemeRef.current = 'closed'; }, w.startMs + w.durationMs));
    }
    audio.onended = () => { speakingRef.current = false; setSpeaking(false); visemeRef.current = 'closed'; };
    audio.onerror = () => { speakingRef.current = false; setSpeaking(false); };
    audio.play().catch(() => {});
    return () => { timers.forEach(clearTimeout); audio.pause(); audio.src = ''; speakingRef.current = false; setSpeaking(false); visemeRef.current = 'closed'; };
  }, [audioBase64, words, trigger]);

  const renderFrame = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) { animRef.current = requestAnimationFrame(renderFrame); return; }
    const ctx = canvas.getContext('2d');
    if (!ctx) { animRef.current = requestAnimationFrame(renderFrame); return; }
    const w = canvas.width, h = canvas.height;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#0a0a1a';
    ctx.fillRect(0, 0, w, h);

    if (!ready || !photoRef.current) {
      ctx.fillStyle = '#fff'; ctx.font = '14px sans-serif'; ctx.textAlign = 'center'; ctx.fillText('Loading...', w / 2, h / 2);
      animRef.current = requestAnimationFrame(renderFrame); return;
    }

    // Blink
    const now = performance.now();
    let blink = 0;
    if (now - lastBlinkRef.current > 2400 + Math.random() * 2600) blinkRef.current = 1;
    if (blinkRef.current > 0) { blinkRef.current += 0.08; blink = Math.sin(blinkRef.current * Math.PI); if (blinkRef.current > 1) { blink = 0; blinkRef.current = 0; lastBlinkRef.current = now; } }
    blink = Math.max(0, Math.min(1, blink));

    // Natural head movement
    const t = performance.now() / 1000;
    const s = speakingRef.current;
    const headX = s ? Math.sin(t * 2.1) * 1.8 + Math.sin(t * 5.7) * 0.5 : Math.sin(t * 0.6) * 1.0;
    const headY = s ? Math.sin(t * 2.5) * 2.2 + Math.cos(t * 4.1) * 0.8 : Math.sin(t * 0.7) * 1.2;
    const breath = 1 + Math.sin(t * 0.45 + 3) * 0.004 + (s ? Math.abs(Math.sin(t * 1.5)) * 0.005 : 0);

    ctx.save();
    ctx.translate(headX, headY);
    ctx.scale(breath, breath);

    // Draw original photo (no mouth erasure!)
    const scale = Math.max(w / photoRef.current.width, h / photoRef.current.height);
    const iw = photoRef.current.width * scale;
    const ih = photoRef.current.height * scale;
    ctx.drawImage(photoRef.current, (w - iw) / 2, (h - ih) / 2, iw, ih);

    const viseme = visemeRef.current;
    const shape = visemeShapes[viseme] || visemeShapes.closed;
    const mouthOpen = shape.h;
    const mX = w * 0.5;
    const mY = h * 0.70;
    const jawShift = mouthOpen * 5;

    if (mouthOpen > 0.02) {
      const lc = lipColor.current;
      const sc = skinColor.current;

      // Inner mouth dark fill (deep, natural)
      ctx.beginPath();
      ctx.ellipse(mX, mY + jawShift * 0.3, w * 0.055 + mouthOpen * 12, mouthOpen * 14, 0, 0, Math.PI * 2);
      const innerGrad = ctx.createRadialGradient(mX, mY, w * 0.01, mX, mY + 3, mouthOpen * 14);
      innerGrad.addColorStop(0, '#1a0606');
      innerGrad.addColorStop(0.7, '#301010');
      innerGrad.addColorStop(1, '#0a0202');
      ctx.fillStyle = innerGrad;
      ctx.fill();

      // Teeth (natural color, slight transparency)
      if (mouthOpen > 0.12) {
        ctx.beginPath();
        ctx.ellipse(mX, mY - mouthOpen * 3 + jawShift * 0.2, w * 0.04 + mouthOpen * 8, mouthOpen * 7, 0, 0, Math.PI * 2);
        ctx.fillStyle = '#f5f0e8';
        ctx.fill();
        // Tooth line
        ctx.beginPath();
        ctx.moveTo(mX, mY - mouthOpen * 6 + jawShift * 0.2);
        ctx.lineTo(mX, mY - mouthOpen * 0.5 + jawShift * 0.2);
        ctx.strokeStyle = '#d8d0c5'; ctx.lineWidth = 0.5; ctx.stroke();
      }

      // Tongue (for wide open)
      if (mouthOpen > 0.25 && viseme === 'wide') {
        ctx.beginPath();
        ctx.ellipse(mX, mY + jawShift * 0.3 + mouthOpen * 8, w * 0.03 + mouthOpen * 3, mouthOpen * 4, 0, 0, Math.PI * 2);
        ctx.fillStyle = '#c06050';
        ctx.fill();
      }

      // Upper lip — natural cupid's bow shape
      ctx.beginPath();
      ctx.moveTo(mX - w * 0.09 - mouthOpen * 4, mY + jawShift * 0.2);
      ctx.bezierCurveTo(mX - w * 0.06, mY - mouthOpen * 6 + jawShift * 0.1, mX - w * 0.015, mY - mouthOpen * 8 + jawShift * 0.1, mX, mY - mouthOpen * 6 + jawShift * 0.1);
      ctx.bezierCurveTo(mX + w * 0.015, mY - mouthOpen * 8 + jawShift * 0.1, mX + w * 0.06, mY - mouthOpen * 6 + jawShift * 0.1, mX + w * 0.09 + mouthOpen * 4, mY + jawShift * 0.2);
      ctx.strokeStyle = `rgb(${lc.r},${lc.g},${lc.b})`;
      ctx.lineWidth = mouthOpen > 0.3 ? 3.5 : 2.5;
      ctx.lineCap = 'round';
      ctx.stroke();

      // Lower lip
      ctx.beginPath();
      ctx.moveTo(mX - w * 0.09 - mouthOpen * 4, mY + jawShift * 0.2);
      ctx.bezierCurveTo(mX - w * 0.04, mY + mouthOpen * 5 + jawShift * 0.5, mX, mY + mouthOpen * 6 + jawShift * 0.4, mX + w * 0.09 + mouthOpen * 4, mY + jawShift * 0.2);
      ctx.strokeStyle = `rgb(${Math.min(255,lc.r+10)},${Math.min(255,lc.g+5)},${Math.min(255,lc.b+5)})`;
      ctx.lineWidth = mouthOpen > 0.3 ? 3 : 2;
      ctx.fillStyle = `rgba(${lc.r},${lc.g},${lc.b},0.5)`;
      ctx.fill();
      ctx.stroke();

      // Lip highlight (waxes when open)
      if (mouthOpen > 0.2) {
        ctx.beginPath();
        ctx.ellipse(mX - w * 0.025, mY + jawShift * 0.15 + mouthOpen * 1.5, w * 0.025 + mouthOpen * 3, 1.0, -0.1, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${Math.min(255,lc.r+50)},${Math.min(255,lc.g+40)},${Math.min(255,lc.b+30)},0.35)`;
        ctx.fill();
      }

      // Skin blend around lips (soft transition)
      const blendGrad = ctx.createRadialGradient(mX, mY, mouthOpen * 5, mX, mY, mouthOpen * 12 + 3);
      blendGrad.addColorStop(0, 'rgba(0,0,0,0)');
      blendGrad.addColorStop(0.7, `rgba(${sc.r},${sc.g},${sc.b},0.08)`);
      blendGrad.addColorStop(1, `rgba(${sc.r},${sc.g},${sc.b},0)`);
      ctx.fillStyle = blendGrad;
      ctx.beginPath(); ctx.ellipse(mX, mY + jawShift * 0.2, w * 0.12, mouthOpen * 16 + 4, 0, 0, Math.PI * 2); ctx.fill();
    }

    // Blink overlay
    if (blink > 0.01) {
      const eY = h * 0.42, eW = w * 0.06;
      function drawBlink(c2: CanvasRenderingContext2D, ecx: number) {
        c2.beginPath(); c2.moveTo(ecx - eW * 2, eY);
        c2.quadraticCurveTo(ecx, eY - 6 * blink, ecx + eW * 2, eY);
        c2.lineWidth = 2.5 * blink; c2.strokeStyle = '#3a2018'; c2.stroke();
      }
      drawBlink(ctx, w * 0.43); drawBlink(ctx, w * 0.57);
    }

    ctx.restore();

    // Viseme debug
    const dViseme = visemeRef.current;
    if (dViseme !== 'closed') {
      const lc = lipColor.current;
      ctx.fillStyle = 'rgba(0,0,0,0.5)';
      ctx.fillRect(w - 55, 4, 50, 18);
      ctx.fillStyle = `rgb(${lc.r},${lc.g},${lc.b})`; ctx.font = 'bold 10px monospace';
      ctx.textAlign = 'right'; ctx.fillText(dViseme, w - 6, 17);
    }

    if (interrupted) {
      ctx.fillStyle = 'rgba(255,150,50,0.6)'; ctx.font = `bold ${Math.round(w*0.04)}px sans-serif`;
      ctx.textAlign = 'center'; ctx.fillText('AI已打断', w/2, h-30);
    } else if (speaking) {
      ctx.fillStyle = 'rgba(0,255,140,0.35)'; ctx.font = `${Math.round(w*0.035)}px sans-serif`;
      ctx.textAlign = 'center'; ctx.fillText('Speaking...', w/2, h-30);
    } else if (!audioBase64) {
      ctx.fillStyle = 'rgba(255,255,255,0.18)'; ctx.font = `${Math.round(w*0.04)}px sans-serif`;
      ctx.textAlign = 'center'; ctx.fillText('AI客服', w/2, h-30);
    }

    animRef.current = requestAnimationFrame(renderFrame);
  }, [ready, speaking, interrupted, audioBase64]);

  useEffect(() => { animRef.current = requestAnimationFrame(renderFrame); return () => cancelAnimationFrame(animRef.current); }, [renderFrame]);
  useEffect(() => { return () => { if (audioRef.current) audioRef.current.pause(); }; }, []);
  return <canvas ref={canvasRef} width={width} height={height} style={{ width: '100%', height: '100%', display: 'block', background: '#0a0a1a' }} />;
}
