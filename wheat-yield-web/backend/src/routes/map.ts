import { Router, Request, Response } from 'express';
import { getPool, sql } from '../db';

const router = Router();

// Belirli bir yıl için tüm illerin metrik değerleri (harita renklendirme)
router.get('/:year', async (req: Request, res: Response) => {
  try {
    const pool = await getPool();
    const result = await pool.request()
      .input('year', sql.SmallInt, parseInt(req.params.year as string))
      .query(`
        SELECT
          p.name, p.name_norm, p.region,
          yo.yield_kg_dekar,
          mp.predicted_yield, mp.error_pct,
          mf.tmean, mf.rain_sum, mf.hot_days_30, mf.frost_days_0,
          mf.mam_tmean, mf.mam_rain_sum, mf.gdd_season,
          mo.ndvi_max, mo.ndvi_mean
        FROM provinces p
        LEFT JOIN yield_observations yo   ON yo.province_id = p.id AND yo.harvest_year = @year
        LEFT JOIN meteo_features mf       ON mf.province_id = p.id AND mf.harvest_year = @year
        LEFT JOIN modis_features mo       ON mo.province_id = p.id AND mo.harvest_year = @year
        LEFT JOIN model_predictions mp    ON mp.province_id = p.id
                                        AND mp.harvest_year = @year
                                        AND mp.model_version_id = (SELECT MAX(id) FROM model_versions)
        ORDER BY p.name
      `);
    res.json(result.recordset);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

export default router;
