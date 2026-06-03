// Mock CC System Server
const http = require('http');
const crypto = require('crypto');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');

const WS_MAGIC = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11';
const PORT = 8080;
const WS_TEXT = 0x01;

// ===== In-memory state =====
const sessions = new Map();
const agents = new Map();
const customers = new Map();

function createSession(customerId) {
  const sid = 'sid-' + uuidv4().substring(0, 8);
  sessions.set(sid, { sid, customerId, status: 'QUEUING', roomId: null, pushUrl: null, pullUrl: null, createdAt: Date.now() });
  return sessions.get(sid);
}

function getInstantAnswer(text) {
  const q = text || '';
  if (q.includes('理赔') || q.includes('报案') || q.includes('索赔')) return '理赔流程：1.拨打95511报案 2.准备身份证/保单/医疗记录 3.提交审核（3-5个工作日）4.赔付到账。';
  if (q.includes('退保') || q.includes('退款')) return '退保规则：投保后10天犹豫期内可全额退款。超过犹豫期按现金价值返还。需准备保单、身份证、银行卡办理。';
  if (q.includes('续保') || q.includes('续费')) return '续保政策：保障到期前30天可办理续保，无需重新核保，按原费率或调整后费率计算。';
  if (q.includes('投保') || q.includes('购买') || q.includes('保险')) return '投保流程：1.选择产品（寿险/健康险/意外险/车险）2.填写信息 3.健康告知 4.支付保费 5.生效。24小时在线投保。';
  return '您好！我可以解答：投保流程、理赔流程、退保规则、续保政策。请问您想了解哪方面？';
}

function isGoodbye(text) {
  const q = text || '';
  return q.includes('再见') || q.includes('拜拜') || q.includes('拜') || q.includes('88') ||
         q.includes('bye') || q.includes('挂了') || q.includes('挂断') || q.includes('结束') ||
         q.includes('先这样') || q.includes('回头') || q.includes('下次') || q.includes('就这样');
}

function getGoodbyeAnswer() {
  return '再见！感谢您的咨询，如有需要随时联系我，祝您生活愉快！';
}

function getVideo(text) {
  if (text.includes('理赔') || text.includes('报案')) return '/avatar-videos/claim-guide.webm';
  if (text.includes('退保') || text.includes('退款')) return '/avatar-videos/refund-info.webm';
  if (text.includes('续保') || text.includes('续费')) return '/avatar-videos/renewal-info.webm';
  if (text.includes('投保') || text.includes('保险') || text.includes('产品')) return '/avatar-videos/insurance-intro.webm';
  return '/avatar-videos/greeting.webm';
}

// ===== Static TTS audio cache (no edge_tts/Python needed) =====
const answerToAudio = {
  '您好！我可以解答：投保流程、理赔流程、退保规则、续保政策。请问您想了解哪方面？': 'greeting.mp3',
  '理赔流程：1.拨打95511报案 2.准备身份证/保单/医疗记录 3.提交审核（3-5个工作日）4.赔付到账。': 'claim.mp3',
  '退保规则：投保后10天犹豫期内可全额退款。超过犹豫期按现金价值返还。需准备保单、身份证、银行卡办理。': 'refund.mp3',
  '续保政策：保障到期前30天可办理续保，无需重新核保，按原费率或调整后费率计算。': 'renewal.mp3',
  '投保流程：1.选择产品（寿险/健康险/意外险/车险）2.填写信息 3.健康告知 4.支付保费 5.生效。24小时在线投保。': 'insurance.mp3',
  '再见！感谢您的咨询，如有需要随时联系我，祝您生活愉快！': 'goodbye.mp3',
};

const ttsCache = new Map();

function loadAudioCache() {
  const AUDIO_DIR = path.join(__dirname, '..', '..', 'web', 'public', 'audio');
  let count = 0;
  for (const [answerText, audioFile] of Object.entries(answerToAudio)) {
    const audioPath = path.join(AUDIO_DIR, audioFile);
    try {
      const audioData = fs.readFileSync(audioPath);
      ttsCache.set(answerText, { audio: audioData.toString('base64'), words: [], format: 'mp3' });
      count++;
    } catch(e) { console.log(`[CC] Audio missing: ${audioFile}`); }
  }
  console.log(`[CC] Static TTS cache: ${count}/${Object.keys(answerToAudio).length} entries`);
}

function parseWSUrl(url) {
  const p = {};
  (url||'').split('?')[1]?.split('&').forEach(kv => { const [k,v] = kv.split('='); if(k) p[k]=decodeURIComponent(v||''); });
  return p;
}

function acceptWebSocket(req, socket) {
  const key = req.headers['sec-websocket-key'];
  socket.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+crypto.createHash('sha1').update(key+WS_MAGIC).digest('base64')+'\r\n\r\n');
}

function sendWS(ws, data) {
  try {
    const payload = Buffer.from(JSON.stringify(data), 'utf-8');
    const len = payload.length;
    let header;
    if (len < 126) { header = Buffer.alloc(2); header[0] = 0x80|WS_TEXT; header[1] = len; }
    else if (len < 65536) { header = Buffer.alloc(4); header[0] = 0x80|WS_TEXT; header[1] = 126; header.writeUInt16BE(len, 2); }
    else { header = Buffer.alloc(10); header[0] = 0x80|WS_TEXT; header[1] = 127; header.writeBigUInt64BE(BigInt(len), 2); }
    ws.write(Buffer.concat([header, payload]));
  } catch(e) { console.error('sendWS:', e.message); }
}

function handleWSFrame(ws, buffer) {
  if (buffer.length < 2) return null;
  const opcode = buffer[0] & 0x0f;
  if (opcode === 0x08) { ws.end(); return null; }
  if (opcode !== WS_TEXT) return null;
  let len = buffer[1] & 0x7f, off = 2;
  if (len === 126) { len = buffer.readUInt16BE(2); off = 4; }
  else if (len === 127) { len = Number(buffer.readBigUInt64BE(2)); off = 10; }
  const masked = (buffer[1] & 0x80) !== 0;
  const mask = masked ? buffer.slice(off, off + 4) : null;
  off += masked ? 4 : 0;
  const payload = buffer.slice(off, off + len);
  if (masked) for (let i = 0; i < payload.length; i++) payload[i] ^= mask[i % 4];
  return payload.toString('utf-8');
}

async function handleMessage(ws, rawMsg, role) {
  let msg;
  try { msg = JSON.parse(rawMsg); } catch(e) { return; }
  const log = (t) => console.log(`[CC] ${t}`);

  switch (msg.type) {
    case 'call': {
      const session = createSession(msg.payload?.customerId || 'anon');
      try {
        const res = await fetch('http://localhost:3001/api/rooms', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({sid:session.sid}) });
        const room = await res.json();
        session.roomId = room.roomId; session.pushUrl = room.pushUrl; session.pullUrl = room.pullUrl; session.status = 'AI_ANSWERING';
        sendWS(ws, {type:'room-ready', sid:session.sid, roomId:room.roomId, pushUrl:room.pushUrl, pullUrl:room.pullUrl});
      } catch(e) {
        const rid = 'room-mock-'+Date.now();
        session.roomId = rid; session.pushUrl = 'rtmp://localhost:1935/live/'+rid; session.pullUrl = 'webrtc://localhost:1985/live/'+rid; session.status = 'AI_ANSWERING';
        sendWS(ws, {type:'room-ready', sid:session.sid, roomId:rid, pushUrl:session.pushUrl, pullUrl:session.pullUrl});
      }
      break;
    }

    case 'audio': {
      const session = sessions.get(msg.sid);
      if (!session) break;
      const text = msg.text || '';
      
      // Goodbye detection → auto end session
      if (isGoodbye(text)) {
        const goodbye = getGoodbyeAnswer();
        sendWS(ws, {type:'ai-answer', text:goodbye, sid:msg.sid});
        const cached = server._ttsCache?.get(goodbye);
        if (cached) sendWS(ws, {type:'tts-audio', audio:cached.audio, words:cached.words||[], format:'mp3', sid:msg.sid});
        session.status = 'ENDED';
        // Session-ended with delay so customer hears the goodbye
        setTimeout(() => { sendWS(ws, {type:'session-ended', text:'会话已结束', sid:msg.sid}); }, 3000);
        break;
      }
      
      const answer = getInstantAnswer(text);
      const video = getVideo(text); // Match on user QUESTION, not the answer
      sendWS(ws, {type:'ai-answer', text:answer, sid:msg.sid});
      // TTS from pre-generated cache (instant) or generate on-demand
      const cached = server._ttsCache?.get(answer);
      if (cached) {
        sendWS(ws, {type:'tts-audio', audio:cached.audio, words:cached.words||[], format:'mp3', sid:msg.sid});
      } else {
        // Fallback: just send answer text without audio
        console.log('[CC] No cached audio for answer');
      }
      sendWS(ws, {type:'video-play', videoPath:video, sid:msg.sid});
      break;
    }

    case 'transfer': {
      const session = sessions.get(msg.sid);
      if (!session) break;
      let foundAgent = null;
      for (const [id, a] of agents) { if (a.status === 'ONLINE') { foundAgent = a; a.status = 'BUSY'; break; } }
      if (foundAgent) { session.status = 'HUMAN_SERVING'; sendWS(foundAgent.ws, {type:'incoming-call', sid:session.sid, roomId:session.roomId, text:'客户请求人工服务'}); sendWS(ws, {type:'transfer-accepted', text:'已接通人工客服'}); }
      else { sendWS(ws, {type:'queue-wait', text:'无空闲坐席，请稍候...'}); }
      break;
    }

    case 'agent-login': {
      agents.set(msg.agentId, {ws, status:'ONLINE', name:msg.agentName||msg.agentId});
      sendWS(ws, {type:'login-ok', text:'登录成功'});
      break;
    }

    case 'agent-accept': {
      const agent = agents.get(msg.agentId);
      if (agent) { agent.status = 'BUSY'; sendWS(ws, {type:'stream-ready', sid:msg.sid}); }
      break;
    }

    case 'agent-hangup': {
      const agent = agents.get(msg.agentId);
      if (agent) agent.status = 'ONLINE';
      break;
    }

    case 'end': {
      const session = sessions.get(msg.sid);
      if (session) session.status = 'ENDED';
      break;
    }
  }
}

// ===== HTTP Server =====
const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
  const url = new URL(req.url, `http://localhost:${PORT}`);

  if (url.pathname.startsWith('/api/cc/sessions/')) {
    const session = sessions.get(url.pathname.split('/').pop());
    res.writeHead(session?200:404, {'Content-Type':'application/json'});
    res.end(JSON.stringify(session||{error:'Not found'}));
    return;
  }
  if (url.pathname === '/api/cc/admin/stats') {
    res.writeHead(200, {'Content-Type':'application/json'});
    res.end(JSON.stringify({queueDepth:0,activeSessions:sessions.size,onlineAgents:[...agents.values()].filter(a=>a.status==='ONLINE').length,busyAgents:[...agents.values()].filter(a=>a.status==='BUSY').length,service:'cc-system (mock)',uptime:Date.now()}));
    return;
  }
  if (url.pathname === '/api/cc/admin/agents') {
    res.writeHead(200, {'Content-Type':'application/json'});
    res.end(JSON.stringify([...agents.entries()].map(([id,a])=>({agentId:id,name:a.name,status:a.status}))));
    return;
  }
  res.writeHead(404); res.end('Not found');
});

// ===== WebSocket upgrade =====
server.on('upgrade', (req, socket) => {
  if (req.headers.upgrade?.toLowerCase() !== 'websocket') { socket.destroy(); return; }
  const p = parseWSUrl(req.url);
  const userId = p.userId || 'unknown';
  const role = p.role || 'customer';
  acceptWebSocket(req, socket);
  if (role === 'agent') agents.set(userId, {ws:socket, status:'ONLINE', name:'客服-'+userId.substring(0,4)});
  else customers.set(userId, socket);
  console.log(`[CC] ${role} connected: ${userId}`);
  socket.on('data', buf => { const m = handleWSFrame(socket, buf); if (m) handleMessage(socket, m, role); });
  socket.on('close', () => { if (role==='agent') agents.delete(userId); else customers.delete(userId); console.log(`[CC] ${role} disconnected: ${userId}`); });
  socket.on('error', e => {});
});

server.listen(PORT, () => {
  console.log(`[Mock CC System] ws://localhost:${PORT}/ws/cc`);
  console.log(`[Mock CC System] http://localhost:${PORT}/api/cc`);
  
  // Load static TTS audio cache (instant, no edge_tts/Python needed)
  loadAudioCache();
  server._ttsCache = ttsCache;
});
