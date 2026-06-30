export interface Province {
  id: number;
  name: string;
  name_norm: string;
  region: string;
  data_years: number;
  avg_yield: number | null;
  max_yield: number | null;
  min_yield: number | null;
}

export interface YearRecord {
  harvest_year: number;
  actual_yield: number;
  predicted_yield: number | null;
  error_pct: number | null;
  tmean: number | null;
  rain_sum: number | null;
  gdd_season: number | null;
  ndvi_max: number | null;
  mam_tmean: number | null;
  mam_rain_sum: number | null;
}

export interface ModelVersion {
  version_name: string;
  description: string;
  r2_holdout: number;
  rmse_holdout: number;
  mae_holdout: number;
  r2_cv: number;
  feature_count: number;
  algorithm: string;
}

export interface YearlyTrend {
  harvest_year: number;
  avg_yield: number;
}
