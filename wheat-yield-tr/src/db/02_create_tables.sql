-- ============================================================
-- TABLO TANIMLARI (SQL Server)
-- wheat_yield_tr veritabanina baglandiktan sonra calistir
-- ============================================================

USE wheat_yield_tr;
GO

-- 1. ILLER
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'provinces')
CREATE TABLE provinces (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    name        NVARCHAR(100) NOT NULL,
    name_norm   NVARCHAR(100) NOT NULL UNIQUE,
    region      NVARCHAR(100),
    area_km2    DECIMAL(10,2),
    latitude    DECIMAL(9,6),
    longitude   DECIMAL(9,6),
    created_at  DATETIME2 DEFAULT GETDATE()
);
GO

-- 2. TUIK GERCEK VERIM VERILERI
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'yield_observations')
CREATE TABLE yield_observations (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    province_id     INT NOT NULL REFERENCES provinces(id),
    harvest_year    SMALLINT NOT NULL,
    yield_kg_dekar  DECIMAL(8,2) NOT NULL,
    source          NVARCHAR(50) DEFAULT 'TUIK',
    created_at      DATETIME2 DEFAULT GETDATE(),
    UNIQUE (province_id, harvest_year)
);
GO

-- 3. METEOROLOJI OZELLIKLERI (Sezon + MAM + GDD)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'meteo_features')
CREATE TABLE meteo_features (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    province_id         INT NOT NULL REFERENCES provinces(id),
    harvest_year        SMALLINT NOT NULL,
    -- Sezon geneli (Ekim-Temmuz)
    tmean               DECIMAL(6,3),
    tmax_mean           DECIMAL(6,3),
    tmin_mean           DECIMAL(6,3),
    rain_sum            DECIMAL(8,2),
    rad_mean            DECIMAL(6,3),
    tmean_std           DECIMAL(6,3),
    tmax_p95            DECIMAL(6,3),
    tmin_p05            DECIMAL(6,3),
    hot_days_30         SMALLINT,
    frost_days_0        SMALLINT,
    dry_days_lt1mm      SMALLINT,
    -- Mart-Mayis (kritik donem)
    mam_tmean           DECIMAL(6,3),
    mam_tmax_mean       DECIMAL(6,3),
    mam_tmin_mean       DECIMAL(6,3),
    mam_rain_sum        DECIMAL(8,2),
    mam_rad_mean        DECIMAL(6,3),
    mam_tmean_std       DECIMAL(6,3),
    mam_tmax_p95        DECIMAL(6,3),
    mam_tmin_p05        DECIMAL(6,3),
    mam_hot_days_30     SMALLINT,
    mam_frost_days_0    SMALLINT,
    mam_dry_days_lt1mm  SMALLINT,
    -- Buyume Derece Gunu
    gdd_season          DECIMAL(8,2),
    gdd_mam             DECIMAL(8,2),
    gdd_mean_day        DECIMAL(6,3),
    created_at          DATETIME2 DEFAULT GETDATE(),
    UNIQUE (province_id, harvest_year)
);
GO

-- 4. MODIS VEJETASYON INDISLERI
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'modis_features')
CREATE TABLE modis_features (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    province_id     INT NOT NULL REFERENCES provinces(id),
    harvest_year    SMALLINT NOT NULL,
    ndvi_auc        DECIMAL(8,3),
    ndvi_max        DECIMAL(6,4),
    ndvi_mean       DECIMAL(6,4),
    evi_max         DECIMAL(6,4),
    evi_mean        DECIMAL(6,4),
    created_at      DATETIME2 DEFAULT GETDATE(),
    UNIQUE (province_id, harvest_year)
);
GO

-- 5. TOPRAK OZELLIKLERI (Statik - il basina tek kayit)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'soil_features')
CREATE TABLE soil_features (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    province_id     INT NOT NULL REFERENCES provinces(id) UNIQUE,
    soil_clay       DECIMAL(6,3),
    soil_sand       DECIMAL(6,3),
    soil_silt       DECIMAL(6,3),
    soil_soc        DECIMAL(8,3),
    soil_phh2o      DECIMAL(5,3),
    soil_bdod       DECIMAL(6,4),
    soil_cec        DECIMAL(7,3),
    created_at      DATETIME2 DEFAULT GETDATE()
);
GO

-- 6. MODEL VERSIYONLARI
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'model_versions')
CREATE TABLE model_versions (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    version_name    NVARCHAR(20) NOT NULL UNIQUE,
    description     NVARCHAR(MAX),
    r2_holdout      DECIMAL(6,4),
    rmse_holdout    DECIMAL(8,3),
    mae_holdout     DECIMAL(8,3),
    r2_cv           DECIMAL(6,4),
    rmse_cv         DECIMAL(8,3),
    mae_cv          DECIMAL(8,3),
    feature_count   SMALLINT,
    algorithm       NVARCHAR(50),
    train_years     NVARCHAR(20),
    holdout_years   NVARCHAR(20),
    model_path      NVARCHAR(MAX),
    trained_at      DATETIME2 DEFAULT GETDATE(),
    notes           NVARCHAR(MAX)
);
GO

-- 7. MODEL TAHMINLERI
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'model_predictions')
CREATE TABLE model_predictions (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    province_id         INT NOT NULL REFERENCES provinces(id),
    harvest_year        SMALLINT NOT NULL,
    model_version_id    INT NOT NULL REFERENCES model_versions(id),
    predicted_yield     DECIMAL(8,2),
    actual_yield        DECIMAL(8,2),
    error_kg            DECIMAL(8,2),
    error_pct           DECIMAL(6,2),
    created_at          DATETIME2 DEFAULT GETDATE(),
    UNIQUE (province_id, harvest_year, model_version_id)
);
GO

-- ============================================================
-- INDEKSLER
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_yield_province_year')
    CREATE INDEX idx_yield_province_year ON yield_observations(province_id, harvest_year);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_meteo_province_year')
    CREATE INDEX idx_meteo_province_year ON meteo_features(province_id, harvest_year);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_modis_province_year')
    CREATE INDEX idx_modis_province_year ON modis_features(province_id, harvest_year);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pred_province_year')
    CREATE INDEX idx_pred_province_year ON model_predictions(province_id, harvest_year);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pred_model')
    CREATE INDEX idx_pred_model ON model_predictions(model_version_id);
GO

-- ============================================================
-- GORUNUMLER (VIEW)
-- ============================================================

-- Il + yil bazinda tam ozet (uygulama icin)
CREATE OR ALTER VIEW v_province_year_summary AS
SELECT
    p.name                          AS province,
    p.name_norm,
    p.region,
    yo.harvest_year,
    yo.yield_kg_dekar               AS actual_yield,
    mp.predicted_yield,
    mp.error_kg,
    mp.error_pct,
    mf.tmean, mf.rain_sum, mf.hot_days_30, mf.frost_days_0,
    mf.mam_tmean, mf.mam_rain_sum,
    mf.gdd_season,
    mo.ndvi_max, mo.evi_mean,
    sf.soil_clay, sf.soil_soc, sf.soil_phh2o
FROM provinces p
LEFT JOIN yield_observations yo  ON yo.province_id = p.id
LEFT JOIN meteo_features mf      ON mf.province_id = p.id AND mf.harvest_year = yo.harvest_year
LEFT JOIN modis_features mo      ON mo.province_id = p.id AND mo.harvest_year = yo.harvest_year
LEFT JOIN soil_features sf       ON sf.province_id = p.id
LEFT JOIN model_predictions mp   ON mp.province_id = p.id
                                 AND mp.harvest_year = yo.harvest_year
                                 AND mp.model_version_id = (SELECT MAX(id) FROM model_versions);
GO

-- Il ozeti - tum yillarin ortalamasi (mobil uygulama icin)
CREATE OR ALTER VIEW v_province_overview AS
SELECT
    p.name,
    p.name_norm,
    p.region,
    p.latitude,
    p.longitude,
    AVG(yo.yield_kg_dekar)  AS avg_yield_alltime,
    MAX(yo.yield_kg_dekar)  AS max_yield,
    MIN(yo.yield_kg_dekar)  AS min_yield,
    COUNT(yo.id)            AS data_years
FROM provinces p
LEFT JOIN yield_observations yo ON yo.province_id = p.id
GROUP BY p.id, p.name, p.name_norm, p.region, p.latitude, p.longitude;
GO
