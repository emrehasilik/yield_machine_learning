import { Router, Request, Response } from 'express';
import { getPool } from '../db';

const router = Router();

// Model versiyonları karşılaştırma
router.get('/versions', async (_req: Request, res: Response) => {
  try {
    const pool = await getPool();
    const result = await pool.request().query(`
      SELECT version_name, description, r2_holdout, rmse_holdout, mae_holdout,
             r2_cv, rmse_cv, mae_cv, feature_count, algorithm, train_years, holdout_years
      FROM model_versions
      ORDER BY id
    `);
    res.json(result.recordset);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

// Tahmin vs gerçek (scatter plot için) - tüm iller holdout dönemi
router.get('/predictions', async (_req: Request, res: Response) => {
  try {
    const pool = await getPool();
    const result = await pool.request().query(`
      SELECT
        p.name AS province, p.region,
        mp.harvest_year,
        mp.actual_yield,
        mp.predicted_yield,
        mp.error_kg,
        mp.error_pct
      FROM model_predictions mp
      JOIN provinces p ON p.id = mp.province_id
      WHERE mp.model_version_id = (SELECT MAX(id) FROM model_versions)
        AND mp.actual_yield IS NOT NULL
      ORDER BY mp.harvest_year, p.name
    `);
    res.json(result.recordset);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

// Bölgeye göre ortalama hata
router.get('/error-by-region', async (_req: Request, res: Response) => {
  try {
    const pool = await getPool();
    const result = await pool.request().query(`
      SELECT
        p.region,
        AVG(ABS(mp.error_pct))  AS avg_abs_error_pct,
        AVG(mp.error_kg)        AS avg_error_kg,
        COUNT(*)                AS n
      FROM model_predictions mp
      JOIN provinces p ON p.id = mp.province_id
      WHERE mp.model_version_id = (SELECT MAX(id) FROM model_versions)
        AND mp.actual_yield IS NOT NULL
      GROUP BY p.region
      ORDER BY avg_abs_error_pct
    `);
    res.json(result.recordset);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

// Yıla göre Türkiye toplam üretim trendi
router.get('/yearly-trend', async (_req: Request, res: Response) => {
  try {
    const pool = await getPool();
    const result = await pool.request().query(`
      SELECT
        yo.harvest_year,
        AVG(yo.yield_kg_dekar)  AS avg_yield,
        SUM(yo.yield_kg_dekar)  AS total_yield,
        COUNT(yo.id)            AS province_count
      FROM yield_observations yo
      GROUP BY yo.harvest_year
      ORDER BY yo.harvest_year
    `);
    res.json(result.recordset);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

export default router;
