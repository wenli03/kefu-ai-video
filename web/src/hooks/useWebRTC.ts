import { useRef, useCallback, useEffect } from 'react';

export function useWebRTC(_streamType: 'push' | 'pull') {
  const peerRef = useRef<RTCPeerConnection | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const createPeer = useCallback(() => {
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    });
    peerRef.current = pc;
    return pc;
  }, []);

  const startPush = useCallback(async (): Promise<MediaStream> => {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true,
    });
    streamRef.current = stream;

    const pc = createPeer();
    stream.getTracks().forEach((track) => pc.addTrack(track, stream));
    return stream;
  }, [createPeer]);

  const startPull = useCallback(
    (remoteVideo: HTMLVideoElement) => {
      const pc = createPeer();
      pc.ontrack = (event) => {
        remoteVideo.srcObject = event.streams[0];
      };
      return pc;
    },
    [createPeer]
  );

  useEffect(() => {
    return () => {
      peerRef.current?.close();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return { peerRef, streamRef, startPush, startPull, createPeer };
}
