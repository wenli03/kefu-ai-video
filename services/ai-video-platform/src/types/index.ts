export interface RoomInfo {
  roomId: string;
  sid: string;
  pushUrl: string;
  pullUrl: string;
  pullFlvUrl: string;
  createdAt: number;
}

export interface SrsStream {
  id: string;
  name: string;
  vhost: string;
  app: string;
  tcUrl: string;
  url: string;
  live_ms: number;
  clients: number;
  frames: number;
  send_bytes: number;
  recv_bytes: number;
  publish?: {
    active: boolean;
    cid: string;
  };
}

export interface StreamUrls {
  pushRtmp: string;
  pullWebrtc: string;
  pullFlv: string;
  pullHls: string;
}
