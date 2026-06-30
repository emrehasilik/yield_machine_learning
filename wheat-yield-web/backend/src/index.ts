import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import provincesRouter from './routes/provinces';
import modelRouter from './routes/model';
import mapRouter from './routes/map';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors({ origin: 'http://localhost:5173' }));
app.use(express.json());

app.use('/api/provinces', provincesRouter);
app.use('/api/model', modelRouter);
app.use('/api/map', mapRouter);

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(`Backend http://localhost:${PORT} adresinde çalışıyor`);
}).on('error', (err) => {
  console.error('Sunucu hatası:', err);
});
