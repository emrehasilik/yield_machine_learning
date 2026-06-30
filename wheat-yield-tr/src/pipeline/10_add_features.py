# src/10_add_features.py
# dataset_model_v2.csv'ye iki yeni ozellik grubu ekler:
#
# 1. GDD (Growing Degree Days) — NASA POWER gunluk sicaklik verisinden
#    Base temp = 5C (bugday icin standart)
#    Sezon geneli (Oct-Jul) + ilkbahar donemi (MAM) ayri ayri hesaplanir
#
# 2. Lagged Yield — bir onceki yilin verimini feature olarak ekler
#    Her il icin: lag1 = t-1 yili verimi

import pandas as pd
import numpy as np
from pathlib import Path
from utils.names import normalize_province_name

BASE_DIR    = Path(__file__).resolve().parents[2]
DAILY_PATH  = BASE_DIR / "result" / "features" / "nasa_power_daily_province.csv"
DATASET_IN  = BASE_DIR / "result" / "datasets" / "dataset_model_v2.csv"
OUT_PATH    = BASE_DIR / "result" / "datasets" / "dataset_model_v3.csv"

BASE_TEMP   = 5.0   # bugday icin GDD baz sicakligi

# --- hasat yili mapping (04 scriptiyle ayni mantik) ---
def harvest_year_from_date(dt):
    m = dt.month
    if m in (10, 11, 12):
        return dt.year + 1
    if m in (1, 2, 3, 4, 5, 6, 7):
        return dt.year
    return None


def compute_gdd(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    NASA POWER gunluk verisinden il x hasat_yili bazinda GDD hesaplar.
    Dondurulan kolonlar:
      gdd_season  : Oct-Jul toplam GDD
      gdd_mam     : Mart-May toplam GDD (kritik donem)
      gdd_mean_day: Sezon gunluk ortalama GDD
    """
    df = daily_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["province_norm"] = df["province_norm"].apply(normalize_province_name)
    df["harvest_year"]  = df["date"].apply(harvest_year_from_date)
    df = df[df["harvest_year"].notna()].copy()
    df["harvest_year"] = df["harvest_year"].astype(int)

    # gunluk GDD
    df["T2M_MAX"] = pd.to_numeric(df["T2M_MAX"], errors="coerce")
    df["T2M_MIN"] = pd.to_numeric(df["T2M_MIN"], errors="coerce")
    df["tmean"]   = (df["T2M_MAX"] + df["T2M_MIN"]) / 2.0
    df["gdd_day"] = (df["tmean"] - BASE_TEMP).clip(lower=0)

    df["month"] = df["date"].dt.month

    # sezon geneli (Oct-Jul)
    season = (df.groupby(["province_norm", "harvest_year"])["gdd_day"]
                .agg(gdd_season="sum", gdd_mean_day="mean")
                .reset_index())

    # MAM (Mart-Mayis)
    mam = (df[df["month"].isin([3, 4, 5])]
             .groupby(["province_norm", "harvest_year"])["gdd_day"]
             .sum()
             .reset_index()
             .rename(columns={"gdd_day": "gdd_mam"}))

    out = season.merge(mam, on=["province_norm", "harvest_year"], how="left")
    return out


def compute_lagged_yield(dataset: pd.DataFrame) -> pd.DataFrame:
    """
    Her il icin bir onceki yilin verimini ekler (yield_lag1).
    Veri olmayan ilk yil NaN kalir — imputer halleder.
    """
    df = dataset.sort_values(["province_norm", "harvest_year"]).copy()
    df["yield_lag1"] = df.groupby("province_norm")["yield_kg_dekar"].shift(1)
    return df


def main():
    print("Gunluk NASA verisi yukleniyor...")
    daily = pd.read_csv(DAILY_PATH)

    print("GDD hesaplaniyor...")
    gdd_df = compute_gdd(daily)
    print(f"  GDD satirlari: {len(gdd_df)}")
    print(f"  GDD ornek (Ankara 2010): {gdd_df[(gdd_df.province_norm=='ANKARA') & (gdd_df.harvest_year==2010)][['gdd_season','gdd_mam','gdd_mean_day']].values}")

    print("\nDataset yukleniyor...")
    df = pd.read_csv(DATASET_IN)
    df["province_norm"] = df["province_norm"].apply(normalize_province_name)

    print("GDD merge ediliyor...")
    df = df.merge(gdd_df, on=["province_norm", "harvest_year"], how="left")
    missing_gdd = df["gdd_season"].isna().sum()
    print(f"  Eslesiemeyen: {missing_gdd} satir")

    print("Lagged yield hesaplaniyor...")
    df = compute_lagged_yield(df)
    lag_null = df["yield_lag1"].isna().sum()
    print(f"  NaN lag1 (beklenen = ilk yil her il): {lag_null}")

    print(f"\nOrijinal sutunlar: {len(pd.read_csv(DATASET_IN).columns)}")
    print(f"Yeni sutunlar    : {len(df.columns)}")
    print(f"Eklenen          : gdd_season, gdd_mam, gdd_mean_day, yield_lag1")

    df.to_csv(OUT_PATH, index=False, encoding="utf-8")
    print(f"\nKaydedildi: {OUT_PATH} ({len(df)} satir, {len(df.columns)} sutun)")

    # ozet istatistik
    print("\n--- Yeni ozellik istatistikleri ---")
    print(df[["gdd_season", "gdd_mam", "gdd_mean_day", "yield_lag1"]].describe().round(2))


if __name__ == "__main__":
    main()
