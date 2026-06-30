export interface Province {
  id: number;
  name: string;
  name_norm: string;
  region: string;
  latitude: number | null;
  longitude: number | null;
  data_years: number;
  avg_yield: number | null;
  max_yield: number | null;
  min_yield: number | null;
}

export interface YearRecord {
  harvest_year: number;
  actual_yield: number;
  predicted_yield: number | null;
  error_kg: number | null;
  error_pct: number | null;
  tmean: number | null;
  rain_sum: number | null;
  hot_days_30: number | null;
  frost_days_0: number | null;
  mam_tmean: number | null;
  mam_rain_sum: number | null;
  gdd_season: number | null;
  gdd_mam: number | null;
  ndvi_max: number | null;
  ndvi_mean: number | null;
  evi_mean: number | null;
  soil_clay: number | null;
  soil_sand: number | null;
  soil_soc: number | null;
  soil_phh2o: number | null;
}

export interface ModelVersion {
  version_name: string;
  description: string;
  r2_holdout: number;
  rmse_holdout: number;
  mae_holdout: number;
  r2_cv: number;
  rmse_cv: number;
  mae_cv: number;
  feature_count: number;
  algorithm: string;
  train_years: string;
  holdout_years: string;
}

export interface Prediction {
  province: string;
  region: string;
  harvest_year: number;
  actual_yield: number;
  predicted_yield: number;
  error_kg: number;
  error_pct: number;
}

export interface YearlyTrend {
  harvest_year: number;
  avg_yield: number;
  total_yield: number;
  province_count: number;
}

export interface RegionError {
  region: string;
  avg_abs_error_pct: number;
  avg_error_kg: number;
  n: number;
}

export interface MapYearData {
  name: string;
  name_norm: string;
  region: string;
  yield_kg_dekar: number | null;
  predicted_yield: number | null;
  error_pct: number | null;
  tmean: number | null;
  rain_sum: number | null;
  hot_days_30: number | null;
  frost_days_0: number | null;
  mam_tmean: number | null;
  mam_rain_sum: number | null;
  gdd_season: number | null;
  ndvi_max: number | null;
  ndvi_mean: number | null;
}
