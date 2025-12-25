import pandas as pd
from pathlib import Path

IN_PATH = Path("wheat-yield-tr/result/nasa_power_daily_province.csv")
OUT_PATH = Path("wheat-yield-tr/result/meteo_harvest_il.csv")

# Sezon penceresi: 1 Oct (y-1) -> 31 Jul (y)
# Burada günlük veriden hasat yılı (harvest_year) üretiyoruz:
# Oct-Dec => year+1, Jan-Jul => year
def harvest_year_from_date(dt: pd.Timestamp) -> int | None:
    m = dt.month
    y = dt.year
    if m in (10, 11, 12):
        return y + 1
    if m in (1, 2, 3, 4, 5, 6, 7):
        return y
    # Ağustos-Eylül sezon dışı (bizim tanımda yok)
    return None

def main():
    df = pd.read_csv(IN_PATH)
    df["date"] = pd.to_datetime(df["date"])
    df["harvest_year"] = df["date"].apply(harvest_year_from_date)
    df = df[df["harvest_year"].notna()].copy()
    df["harvest_year"] = df["harvest_year"].astype(int)

    # Sezonda kullanacağımız meteorolojik kolonlar
    # (POWER_PARAMS ile uyumlu)
    met_cols = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN"]

    # --- Sezon özetleri (Oct-Jul) ---
    agg = {
        "T2M": "mean",
        "T2M_MAX": "mean",
        "T2M_MIN": "mean",
        "PRECTOTCORR": "sum",          # yağış: sezon toplamı
        "ALLSKY_SFC_SW_DWN": "mean",   # radyasyon: ortalama
    }

    season = df.groupby(["province", "harvest_year"], as_index=False)[met_cols].agg(agg)
    season = season.rename(columns={
        "T2M": "tmean_season",
        "T2M_MAX": "tmax_season",
        "T2M_MIN": "tmin_season",
        "PRECTOTCORR": "rain_season_sum",
        "ALLSKY_SFC_SW_DWN": "rad_season_mean",
    })

    # --- Kritik dönem özetleri (ör: Mar-May) ---
    df["month"] = df["date"].dt.month
    spring = df[df["month"].isin([3, 4, 5])].groupby(["province", "harvest_year"], as_index=False)[met_cols].agg(agg)
    spring = spring.rename(columns={
        "T2M": "tmean_mam",
        "T2M_MAX": "tmax_mam",
        "T2M_MIN": "tmin_mam",
        "PRECTOTCORR": "rain_mam_sum",
        "ALLSKY_SFC_SW_DWN": "rad_mam_mean",
    })

    out = season.merge(spring, on=["province", "harvest_year"], how="left")

    # Hızlı sanity check
    print("Rows (province x harvest_year):", len(out))
    print("Years:", out["harvest_year"].min(), "-", out["harvest_year"].max())
    print("Provinces:", out["province"].nunique())

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False, encoding="utf-8")
    print(f"DONE ✅ Saved: {OUT_PATH}")

if __name__ == "__main__":
    main()
