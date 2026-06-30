import { Router, Request, Response } from 'express';
import { getPool, sql } from '../db';

const router = Router();

// Tüm iller - harita için (kayıtlı/kayıtsız bilgisi dahil)
router.get('/', async (_req: Request, res: Response) => {
  try {
    const pool = await getPool();
    const result = await pool.request().query(`
      SELECT
        p.id, p.name, p.name_norm, p.region, p.latitude, p.longitude,
        COUNT(yo.id) AS data_years,
        AVG(yo.yield_kg_dekar) AS avg_yield,
        MAX(yo.yield_kg_dekar) AS max_yield,
        MIN(yo.yield_kg_dekar) AS min_yield
      FROM provinces p
      LEFT JOIN yield_observations yo ON yo.province_id = p.id
      GROUP BY p.id, p.name, p.name_norm, p.region, p.latitude, p.longitude
      ORDER BY p.name
    `);
    res.json(result.recordset);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

// Tek il detayı - yıllık verim + tahmin + meteo
router.get('/:name/history', async (req: Request, res: Response) => {
  try {
    const pool = await getPool();
    const result = await pool.request()
      .input('name', sql.NVarChar, String(req.params.name).toUpperCase())
      .query(`
        SELECT
          yo.harvest_year,
          yo.yield_kg_dekar          AS actual_yield,
          mp.predicted_yield,
          mp.error_kg,
          mp.error_pct,
          mf.tmean, mf.rain_sum,
          mf.hot_days_30, mf.frost_days_0,
          mf.mam_tmean, mf.mam_rain_sum,
          mf.gdd_season, mf.gdd_mam,
          mo.ndvi_max, mo.ndvi_mean, mo.evi_mean,
          sf.soil_clay, sf.soil_sand, sf.soil_soc, sf.soil_phh2o
        FROM provinces p
        JOIN yield_observations yo    ON yo.province_id = p.id
        LEFT JOIN meteo_features mf   ON mf.province_id = p.id AND mf.harvest_year = yo.harvest_year
        LEFT JOIN modis_features mo   ON mo.province_id = p.id AND mo.harvest_year = yo.harvest_year
        LEFT JOIN soil_features sf    ON sf.province_id = p.id
        LEFT JOIN model_predictions mp ON mp.province_id = p.id
                                      AND mp.harvest_year = yo.harvest_year
                                      AND mp.model_version_id = (SELECT MAX(id) FROM model_versions)
        WHERE p.name_norm = @name
        ORDER BY yo.harvest_year
      `);
    if (result.recordset.length === 0) {
      res.status(404).json({ error: 'İl bulunamadı' });
      return;
    }
    res.json(result.recordset);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

// Tek il toprak verisi
router.get('/:name/soil', async (req: Request, res: Response) => {
  try {
    const pool = await getPool();
    const result = await pool.request()
      .input('name', sql.NVarChar, String(req.params.name).toUpperCase())
      .query(`
        SELECT sf.*
        FROM soil_features sf
        JOIN provinces p ON p.id = sf.province_id
        WHERE p.name_norm = @name
      `);
    res.json(result.recordset[0] || null);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

export default router;
