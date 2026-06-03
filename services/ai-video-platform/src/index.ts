import express from 'express';
import cors from 'cors';
import path from 'path';
import roomRoutes from './routes/room';

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());

// Serve static avatar videos for the frontend
app.use('/avatar-videos', express.static(path.join(__dirname, '..', '..', '..', 'assets', 'avatar-videos')));

app.get('/api/video/health', (_req, res) => {
  res.json({ service: 'ai-video-platform', status: 'ok' });
});

app.use('/api/rooms', roomRoutes);

app.listen(PORT, () => {
  console.log(`[AI Video Platform] running on http://localhost:${PORT}`);
});
