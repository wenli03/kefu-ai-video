import { Router, Request, Response } from 'express';
import { getStreamManager } from '../services/stream-manager';

const router = Router();
const streamManager = getStreamManager();

router.post('/', async (req: Request, res: Response) => {
  try {
    const { sid } = req.body;
    if (!sid) {
      return res.status(400).json({ error: 'sid is required' });
    }
    const room = await streamManager.createRoom(sid);
    return res.json(room);
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

router.get('/:rid', async (req: Request, res: Response) => {
  try {
    const room = await streamManager.getRoom(req.params.rid);
    if (!room) {
      return res.status(404).json({ error: 'Room not found' });
    }
    return res.json(room);
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

router.get('/:rid/streams', async (req: Request, res: Response) => {
  try {
    const room = await streamManager.getRoom(req.params.rid);
    if (!room) {
      return res.status(404).json({ error: 'Room not found' });
    }
    return res.json({
      roomId: room.roomId,
      pushUrl: room.pushUrl,
      pullUrl: room.pullUrl,
      pullFlvUrl: room.pullFlvUrl,
    });
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

router.delete('/:rid', async (req: Request, res: Response) => {
  try {
    await streamManager.deleteRoom(req.params.rid);
    return res.json({ status: 'ok' });
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

export default router;
