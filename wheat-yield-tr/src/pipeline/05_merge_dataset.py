import pandas as pd
from pathlib import Path
from utils.names import normalize_province_name

BASE_DIR = Path(__file__).resolve().parents[2]

TUIK_PATH  = BASE_DIR / "result" / "features" / "tuik_yield_long.csv"
METEO_PATH = BASE_DIR / "result" / "features" / "meteo_harvest_il.csv"
MODIS_PATH = BASE_DIR / "result" / "features" / "modis_features.csv"

OUT_PATH   = BASE_DIR / "result" / "datasets" / "dataset_model_v1.csv"
COV_PATH   = BASE_DIR / "result" / "coverage_report.csv"

KEY = ["province_norm", "harvest_year"]

def prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "province_norm" not in df.columns and "province" in df.columns:
        df["province_norm"] = df["province"]
    df["province_norm"] = df["province_norm"].apply(normalize_province_name)

    df["harvest_year"] = pd.to_numeric(df["harvest_year"], errors="coerce")
    df = df.dropna(subset=["harvest_year"]).copy()
    df["harvest_year"] = df["harvest_year"].astype(int)

    # ortak yıl aralığı (senin hedefin)
    df = df[df["harvest_year"].between(2005, 2024)].copy()
    return df

def keyset(df: pd.DataFrame) -> set[tuple]:
    return set(zip(df["province_norm"], df["harvest_year"]))

def main():
    tuik  = prep(pd.read_csv(TUIK_PATH))
    meteo = prep(pd.read_csv(METEO_PATH))
    modis = prep(pd.read_csv(MODIS_PATH))

    # sadece hedef + gerekli kolonlar
    if "yield_kg_dekar" not in tuik.columns:
        raise RuntimeError("TUIK dosyasında yield_kg_dekar yok.")
    tuik = tuik[KEY + ["yield_kg_dekar"]].copy()

    # INNER MERGE = Strateji A
    df = (
        tuik.merge(meteo, on=KEY, how="inner")
            .merge(modis, on=KEY, how="inner")
            .sort_values(KEY)
            .reset_index(drop=True)
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8")

    # Coverage raporu (debug için çok işe yarar)
    ks_t, ks_m, ks_v = keyset(tuik), keyset(meteo), keyset(modis)
    all_keys = sorted(ks_t | ks_m | ks_v)
    cov = pd.DataFrame([{
        "province_norm": prov,
        "harvest_year": y,
        "in_tuik":  (prov, y) in ks_t,
        "in_meteo": (prov, y) in ks_m,
        "in_modis": (prov, y) in ks_v,
    } for prov, y in all_keys])
    cov["in_all"] = cov["in_tuik"] & cov["in_meteo"] & cov["in_modis"]
    cov.to_csv(COV_PATH, index=False, encoding="utf-8")

    print("✅ TRAIN dataset:", OUT_PATH, "| rows:", len(df))
    print("✅ Coverage:", COV_PATH)
    print("Years:", df["harvest_year"].min(), "-", df["harvest_year"].max())
    print("Provinces:", df["province_norm"].nunique())

if __name__ == "__main__":
    main()
