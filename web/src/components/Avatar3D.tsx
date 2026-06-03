import { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';

interface Word { text: string; pinyin: string; startMs: number; durationMs: number; viseme: string; }
interface Props {
  audioBase64?: string; words?: Word[]; trigger?: number;
  emotion?: 'neutral' | 'happy' | 'surprised' | 'thinking';
  width?: number; height?: number;
}

const visemeShapes: Record<string, { h: number; w: number }> = {
  wide: { h: 1.0, w: 1.0 }, round: { h: 0.55, w: 0.65 },
  spread: { h: 0.3, w: 1.2 }, neutral: { h: 0.4, w: 0.85 },
  tight: { h: 0.25, w: 0.5 }, closed: { h: 0.0, w: 0.7 },
};

export function Avatar3D({ audioBase64, words = [], trigger = 0, emotion = 'neutral', width = 320, height = 480 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const animRef = useRef<number>(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const visemeRef = useRef('closed');
  const speakingRef = useRef(false);
  const mouthHRef = useRef(0);
  const mouthWRef = useRef(0.7);
  const facePlaneRef = useRef<THREE.Mesh | null>(null);
  const mouthGroupRef = useRef<THREE.Group | null>(null);
  const eyeLRef = useRef<THREE.Group | null>(null);
  const eyeRRef = useRef<THREE.Group | null>(null);
  const browLRef = useRef<THREE.Mesh | null>(null);
  const browRRef = useRef<THREE.Mesh | null>(null);
  const lastTriggerRef = useRef(0);
  const faceTextureRef = useRef<THREE.Texture | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [texReady, setTexReady] = useState(false);

  // Load face texture
  useEffect(() => {
    const loader = new THREE.TextureLoader();
    loader.load('/portrait.jpg', (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      faceTextureRef.current = tex;
      setTexReady(true);
    }, undefined, () => { setTexReady(true); });
  }, []);

  // Audio + viseme
  useEffect(() => {
    if (!audioBase64 || words.length === 0 || trigger === 0 || trigger === lastTriggerRef.current) return;
    lastTriggerRef.current = trigger;
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ''; audioRef.current = null; }
    visemeRef.current = 'closed';
    speakingRef.current = true;
    const audio = new Audio('data:audio/mp3;base64,' + audioBase64);
    audioRef.current = audio;
    const timers: number[] = [];
    for (const w of words) {
      timers.push(window.setTimeout(() => { visemeRef.current = w.viseme; }, w.startMs));
      timers.push(window.setTimeout(() => { visemeRef.current = 'closed'; }, w.startMs + w.durationMs));
    }
    audio.onended = () => { speakingRef.current = false; visemeRef.current = 'closed'; };
    audio.onerror = () => { speakingRef.current = false; };
    audio.play().catch(() => {});
    return () => { timers.forEach(clearTimeout); audio.pause(); audio.src = ''; speakingRef.current = false; visemeRef.current = 'closed'; };
  }, [audioBase64, words, trigger]);

  // Three.js scene with photo-textured face
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    if (!texReady) return;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    const w = container.clientWidth || width;
    const h = container.clientHeight || height;
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.domElement.style.display = 'block';
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#0d0d20');
    const camera = new THREE.PerspectiveCamera(35, w / Math.max(h, 1), 0.1, 20);
    camera.position.set(0, 0.05, 3.5);
    camera.lookAt(0, -0.02, 0);

    // Lighting
    scene.add(new THREE.AmbientLight('#ccccee', 1.5));
    const kl = new THREE.DirectionalLight('#fff5ee', 3.0); kl.position.set(1.2, 1.5, 2); scene.add(kl);
    const fl = new THREE.DirectionalLight('#aaccff', 0.8); fl.position.set(-1, 0.3, 0.5); scene.add(fl);
    const rl = new THREE.DirectionalLight('#ffffff', 1.0); rl.position.set(0, 0.8, -1.5); scene.add(rl);

    // === Face plane with photo texture ===
    // Create an oval face shape (like a portrait)
    const shape = new THREE.Shape();
    const rx = 0.38, ry = 0.52;
    shape.moveTo(0, -ry);
    shape.bezierCurveTo(rx + 0.03, -ry, rx + 0.08, -ry * 0.45, rx, 0);
    shape.bezierCurveTo(rx + 0.08, ry * 0.45, rx + 0.03, ry, 0, ry + 0.02);
    shape.bezierCurveTo(-rx - 0.03, ry, -rx - 0.08, ry * 0.45, -rx, 0);
    shape.bezierCurveTo(-rx - 0.08, -ry * 0.45, -rx - 0.03, -ry, 0, -ry);

    let faceGeo: THREE.BufferGeometry;
    if (faceTextureRef.current) {
      // Use a regular PlaneGeometry and curve it slightly for 3D effect
      const planeGeo = new THREE.PlaneGeometry(0.78, 1.08, 32, 32);
      const pos = planeGeo.attributes.position.array as Float32Array;
      for (let i = 0; i < pos.length; i += 3) {
        const x = pos[i], y = pos[i + 1];
        // Bend the plane backwards at edges (subtle 3D curvature)
        pos[i + 2] = -(x * x + y * y) * 0.3;
      }
      planeGeo.computeVertexNormals();
      faceGeo = planeGeo;
    } else {
      faceGeo = new THREE.ShapeGeometry(shape, 32);
    }

    const faceTex = faceTextureRef.current || null;
    const faceMat = new THREE.MeshStandardMaterial({
      map: faceTex,
      roughness: 0.5,
      metalness: 0.03,
      color: faceTex ? '#ffffff' : '#f0c8a0',
    });
    if (!faceTex) faceMat.color.set('#f0c8a0');

    const facePlane = new THREE.Mesh(faceGeo, faceMat);
    scene.add(facePlane);
    facePlaneRef.current = facePlane;

    // === Eyes (3D, on top of face) ===
    function createEye(x: number) {
      const g = new THREE.Group();
      const s = new THREE.Mesh(new THREE.SphereGeometry(0.055, 16, 16), new THREE.MeshStandardMaterial({ color: '#faf8f5', roughness: 0.15 }));
      g.add(s);
      const ir = new THREE.Mesh(new THREE.CircleGeometry(0.025, 16), new THREE.MeshStandardMaterial({ color: '#3a1808', roughness: 0.3, side: THREE.DoubleSide }));
      ir.position.z = 0.05; g.add(ir);
      const pu = new THREE.Mesh(new THREE.CircleGeometry(0.012, 16), new THREE.MeshStandardMaterial({ color: '#050200', roughness: 0.1, side: THREE.DoubleSide }));
      pu.position.z = 0.051; g.add(pu);
      const cl = new THREE.Mesh(new THREE.CircleGeometry(0.005, 8), new THREE.MeshBasicMaterial({ color: '#fff', side: THREE.DoubleSide }));
      cl.position.set(-0.008, 0.007, 0.052); g.add(cl);
      g.position.set(x, 0.18, 0.08);
      scene.add(g);
      return g;
    }
    eyeLRef.current = createEye(-0.08);
    eyeRRef.current = createEye(0.08);

    // Eyebrows
    function createBrow(x: number) {
      const geo = new THREE.CylinderGeometry(0.005, 0.005, 0.07, 8);
      geo.rotateZ(Math.PI / 2);
      const b = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: '#2a1508', roughness: 0.5 }));
      b.position.set(x, 0.24, 0.08); b.rotation.z = 0.04 * Math.sign(x);
      scene.add(b); return b;
    }
    browLRef.current = createBrow(-0.08);
    browRRef.current = createBrow(0.08);

    // === Mouth group ===
    const mouthGrp = new THREE.Group();
    mouthGrp.position.set(0, -0.05, 0.06);
    // Dark inner mouth (hidden when closed)
    const innerMouth = new THREE.Mesh(
      new THREE.PlaneGeometry(0.1, 0.04),
      new THREE.MeshBasicMaterial({ color: '#1a0606', side: THREE.DoubleSide, transparent: true, opacity: 0 })
    );
    mouthGrp.add(innerMouth);
    // Upper lip
    const upperLip = new THREE.Mesh(
      new THREE.CylinderGeometry(0.003, 0.003, 0.12, 16),
      new THREE.MeshStandardMaterial({ color: '#b87050', roughness: 0.4 })
    );
    upperLip.rotation.z = Math.PI / 2;
    upperLip.position.y = 0.008;
    mouthGrp.add(upperLip);
    // Lower lip
    const lowerLip = new THREE.Mesh(
      new THREE.CylinderGeometry(0.004, 0.004, 0.12, 16),
      new THREE.MeshStandardMaterial({ color: '#c06040', roughness: 0.4 })
    );
    lowerLip.rotation.z = Math.PI / 2;
    lowerLip.position.y = -0.012;
    mouthGrp.add(lowerLip);

    scene.add(mouthGrp);
    mouthGroupRef.current = mouthGrp;

    // === Shoulders (curved plane with texture) ===
    const shoulderGeo = new THREE.PlaneGeometry(1.2, 0.55, 16, 8);
    const sp = shoulderGeo.attributes.position.array as Float32Array;
    for (let i = 0; i < sp.length; i += 3) {
      sp[i + 2] = -(sp[i] * sp[i]) * 0.5 - 0.1;
    }
    shoulderGeo.computeVertexNormals();
    const shoulder = new THREE.Mesh(shoulderGeo, new THREE.MeshStandardMaterial({ color: '#1a1a3e', roughness: 0.45, metalness: 0.1 }));
    shoulder.position.y = -0.55;
    scene.add(shoulder);

    function animate() {
      animRef.current = requestAnimationFrame(animate);
      const t = performance.now() / 1000;
      const s = speakingRef.current;

      // Face plane subtle movement
      if (facePlaneRef.current) {
        facePlaneRef.current.rotation.y = Math.sin(t * 0.4) * 0.04 + (s ? Math.sin(t * 2.2) * 0.03 : 0);
        facePlaneRef.current.rotation.z = Math.sin(t * 0.55) * 0.02;
        facePlaneRef.current.position.y = Math.sin(t * 0.6) * 0.008;
      }

      // Blink
      if (eyeLRef.current && eyeRRef.current) {
        const blinkCycle = t % 4;
        const blink = blinkCycle > 3.8 && blinkCycle < 4.0 ? Math.sin((blinkCycle - 3.8) / 0.2 * Math.PI) : 1;
        const es = blink < 0.1 ? 0.1 : 1;
        (eyeLRef.current.children[0] as THREE.Mesh).scale.y = es;
        (eyeRRef.current.children[0] as THREE.Mesh).scale.y = es;
      }

      // Viseme mouth
      const viseme = visemeRef.current;
      const shape = visemeShapes[viseme] || visemeShapes.closed;
      mouthHRef.current += (shape.h - mouthHRef.current) * 0.25;
      mouthWRef.current += (shape.w - mouthWRef.current) * 0.25;

      if (mouthGroupRef.current) {
        const mh = mouthHRef.current;
        const mw = mouthWRef.current;
        const grp = mouthGroupRef.current;
        // Inner mouth
        const inner = grp.children[0] as THREE.Mesh;
        (inner.material as THREE.MeshBasicMaterial).opacity = mh > 0.02 ? 1 : 0;
        inner.scale.set(mw, 1 + mh * 8, 1);
        // Upper lip
        (grp.children[1] as THREE.Mesh).position.y = 0.008 + mh * 0.02;
        // Lower lip
        (grp.children[2] as THREE.Mesh).position.y = -0.012 - mh * 0.03;
      }

      // Eyebrows (expression)
      if (browLRef.current && browRRef.current) {
        const by: Record<string, number> = { surprised: 0.26, happy: 0.23, thinking: 0.22, neutral: 0.24 };
        const bt: Record<string, number> = { thinking: -0.15, surprised: 0.08, happy: 0, neutral: 0 };
        browLRef.current.position.y = by[emotion] ?? 0.24;
        browRRef.current.position.y = by[emotion] ?? 0.24;
        browLRef.current.rotation.z = bt[emotion] ?? 0;
        browRRef.current.rotation.z = -(bt[emotion] ?? 0);
      }

      renderer.render(scene, camera);
    }
    animate();
    setLoaded(true);

    return () => {
      cancelAnimationFrame(animRef.current);
      renderer.dispose();
      container.removeChild(renderer.domElement);
    };
  }, [texReady, width, height, emotion]);

  useEffect(() => { return () => { if (audioRef.current) audioRef.current.pause(); }; }, []);

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', background: '#0d0d20' }}>
      {!texReady && <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#999', fontSize: 13 }}>Loading...</div>}
    </div>
  );
}
