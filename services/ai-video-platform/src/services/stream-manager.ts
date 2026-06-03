import type { RoomInfo, StreamUrls } from '../types';

// In-memory storage (works without Redis/Docker)
const rooms = new Map<string, RoomInfo>();
const sidToRoomId = new Map<string, string>();

// Try Redis, but gracefully fall back to in-memory
let redis: any = null;
try {
  const Redis = require('ioredis');
  const r = new Redis({ host: 'localhost', port: 6379, maxRetriesPerRequest: 1, lazyConnect: true });
  r.connect().then(() => { redis = r; console.log('[StreamManager] Redis connected'); }).catch(() => { console.log('[StreamManager] Redis unavailable, using in-memory storage'); });
} catch { console.log('[StreamManager] Redis not installed, using in-memory storage'); }

const SRS_RTC_PORT = 1985;
const SRS_PUBLIC_IP = 'localhost';

async function redisSet(key: string, value: string, ttl?: number) {
  if (redis && redis.status === 'ready') {
    if (ttl) await redis.set(key, value, 'EX', ttl);
    else await redis.set(key, value);
  }
}

async function redisGet(key: string): Promise<string | null> {
  if (redis && redis.status === 'ready') return await redis.get(key);
  return null;
}

async function redisDel(key: string) {
  if (redis && redis.status === 'ready') await redis.del(key);
}

export function getStreamManager() {
  return {
    generateStreamUrls(roomId: string): StreamUrls {
      return {
        pushRtmp: `rtmp://${SRS_PUBLIC_IP}:1935/live/${roomId}`,
        pullWebrtc: `webrtc://${SRS_PUBLIC_IP}:${SRS_RTC_PORT}/live/${roomId}`,
        pullFlv: `http://${SRS_PUBLIC_IP}:8088/live/${roomId}.flv`,
        pullHls: `http://${SRS_PUBLIC_IP}:8088/live/${roomId}.m3u8`,
      };
    },

    async createRoom(sid: string): Promise<RoomInfo> {
      const roomId = `room-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
      const urls = this.generateStreamUrls(roomId);

      const room: RoomInfo = {
        roomId,
        sid,
        pushUrl: urls.pushRtmp,
        pullUrl: urls.pullWebrtc,
        pullFlvUrl: urls.pullFlv,
        createdAt: Date.now(),
      };

      // In-memory (always works)
      rooms.set(roomId, room);
      sidToRoomId.set(sid, roomId);

      // Redis (optional)
      const json = JSON.stringify(room);
      await redisSet(`room:${roomId}`, json, 3600);
      await redisSet(`room:sid:${sid}`, roomId, 3600);

      return room;
    },

    async getRoom(roomId: string): Promise<RoomInfo | null> {
      if (rooms.has(roomId)) return rooms.get(roomId)!;
      const raw = await redisGet(`room:${roomId}`);
      return raw ? JSON.parse(raw) : null;
    },

    async getRoomBySid(sid: string): Promise<RoomInfo | null> {
      const roomId = sidToRoomId.get(sid);
      if (roomId && rooms.has(roomId)) return rooms.get(roomId)!;
      const rId = await redisGet(`room:sid:${sid}`);
      if (!rId) return null;
      return this.getRoom(rId);
    },

    async deleteRoom(roomId: string): Promise<void> {
      const room = rooms.get(roomId);
      if (room) {
        sidToRoomId.delete(room.sid);
        rooms.delete(roomId);
      }
      await redisDel(`room:sid:${room?.sid || ''}`);
      await redisDel(`room:${roomId}`);
    },
  };
}
