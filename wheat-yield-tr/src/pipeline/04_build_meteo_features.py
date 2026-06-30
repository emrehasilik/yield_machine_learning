# src/04_build_meteo_features.py
import pandas as pd
from pathlib import Path

from utils.names import normalize_province_name

BASE_DIR = Path(__file__).resolve().parents[2]

IN_PATH  = BASE_DIR / "result" / "features" / "nasa_power_daily_province.csv"
OUT_PATH = BASE_DIR / "result" / "features" / "meteo_harvest_il.csv"

POWER_PARAMS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN"]

def harvest_year_from_date(dt: pd.Timestamp) -> int | None:
    m = dt.month
    y = dt.year
    if m in (10, 11, 12):
        return y + 1
    if m in (1, 2, 3, 4, 5, 6, 7):
        return y
    return None  # Aug-Sep out

def meteo_agg(df: pd.DataFrame):
    # basit + güçlü birkaç ek özet
    out = {}
    out["tmean"] = df["T2M"].mean()
    out["tmax_mean"] = df["T2M_MAX"].mean()
    out["tmin_mean"] = df["T2M_MIN"].mean()
    out["rain_sum"] = df["PRECTOTCORR"].sum()
    out["rad_mean"] = df["ALLSKY_SFC_SW_DWN"].mean()

    # varyans / uçlar
    out["tmean_std"] = df["T2M"].std()
    out["tmax_p95"] = df["T2M_MAX"].quantile(0.95)
    out["tmin_p05"] = df["T2M_MIN"].quantile(0.05)

    # stres günleri örnekleri
    out["hot_days_30"] = (df["T2M_MAX"] > 30).sum()
    out["frost_days_0"] = (df["T2M_MIN"] < 0).sum()
    out["dry_days_lt1mm"] = (df["PRECTOTCORR"] < 1).sum()
    return pd.Series(out)

def main():
    df = pd.read_csv(IN_PATH)
    df["date"] = pd.to_datetime(df["date"])

    # normalize
    if "province_norm" not in df.columns:
        df["province_norm"] = df["province"].apply(normalize_province_name)
    else:
        df["province_norm"] = df["province_norm"].apply(normalize_province_name)

    df["harvest_year"] = df["date"].apply(harvest_year_from_date)
    df = df[df["harvest_year"].notna()].copy()
    df["harvest_year"] = df["harvest_year"].astype(int)

    # numeric
    for c in POWER_PARAMS:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # sezon: Oct-Jul
    season = (
        df.groupby(["province_norm", "harvest_year"], as_index=False)
          .apply(meteo_agg)
          .reset_index()
    )
    season = season.rename(columns={"level_0": "province_norm", "level_1": "harvest_year"})
    season = season[["province_norm", "harvest_year"] + [c for c in season.columns if c not in ("province_norm","harvest_year","index")]]

    # kritik dönem: Mar-May
    df["month"] = df["date"].dt.month
    spring_df = df[df["month"].isin([3,4,5])].copy()
    spring = (
        spring_df.groupby(["province_norm", "harvest_year"], as_index=False)
                 .apply(meteo_agg)
                 .reset_index()
    )
    spring = spring.rename(columns={"level_0": "province_norm", "level_1": "harvest_year"})
    # prefix
    spring_cols = {c: f"mam_{c}" for c in spring.columns if c not in ("province_norm","harvest_year","index")}
    spring = spring.rename(columns=spring_cols)

    out = season.merge(spring, on=["province_norm", "harvest_year"], how="left")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False, encoding="utf-8")

    print("Rows:", len(out))
    print("Years:", out["harvest_year"].min(), "-", out["harvest_year"].max())
    print("Provinces:", out["province_norm"].nunique())
    print("Saved:", OUT_PATH)

if __name__ == "__main__":
    main()
