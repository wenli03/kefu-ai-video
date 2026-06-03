import express from 'express';
import cors from 'cors';
import pipelineRoutes from './routes/pipeline';

const app = express();
const PORT = 3002;

app.use(cors());
app.use(express.json({ limit: '10mb' }));

app.get('/api/pipeline/health', (_req, res) => {
  res.json({ service: 'ai-pipeline', status: 'ok' });
});

app.use('/api/pipeline', pipelineRoutes);

app.listen(PORT, () => {
  console.log(`[AI Pipeline] running on http://localhost:${PORT}`);
});
