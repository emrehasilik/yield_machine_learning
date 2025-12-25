import re
import unicodedata
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

TUIK_PATH  = BASE_DIR / "result" / "tuik_yield_long_fixed.csv"
METEO_PATH = BASE_DIR / "result" / "meteo_harvest_il.csv"
MODIS_PATH = BASE_DIR / "result" / "modis_features.csv"
OUT_PATH   = BASE_DIR / "result" / "dataset_model.csv"

ALIASES = {
    "AFYON": "AFYONKARAHISAR",
    "ICEL": "MERSIN",
    "K MARAS": "KAHRAMANMARAS",
    "K.MARAS": "KAHRAMANMARAS",
}

def normalize_name(s: str) -> str:
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper().replace("İ", "I")
    s = re.sub(r"[^A-Z ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIASES.get(s, s)

def main():
    tuik  = pd.read_csv(TUIK_PATH)
    meteo = pd.read_csv(METEO_PATH)
    modis = pd.read_csv(MODIS_PATH)

    # --- year aralığı aynı olsun (2005-2024) ---
    for df in (tuik, meteo, modis):
        df["harvest_year"] = pd.to_numeric(df["harvest_year"], errors="coerce").astype("Int64")
    tuik  = tuik[tuik["harvest_year"].between(2005, 2024)].copy()
    meteo = meteo[meteo["harvest_year"].between(2005, 2024)].copy()
    modis = modis[modis["harvest_year"].between(2005, 2024)].copy()

    tuik["harvest_year"]  = tuik["harvest_year"].astype(int)
    meteo["harvest_year"] = meteo["harvest_year"].astype(int)
    modis["harvest_year"] = modis["harvest_year"].astype(int)

    # --- province_norm üret / normalize ---
    tuik["province_norm"] = tuik["province_norm"].apply(normalize_name)

    # METEO'da 'province' var (Adana, Afyon...), bunu normalize ederek province_norm yap
    if "province" not in meteo.columns and "province_norm" not in meteo.columns:
        raise RuntimeError("METEO dosyasında ne 'province' ne de 'province_norm' var.")
    if "province_norm" not in meteo.columns:
        meteo["province_norm"] = meteo["province"].apply(normalize_name)
    else:
        meteo["province_norm"] = meteo["province_norm"].apply(normalize_name)

    # MODIS zaten province_norm ile geliyor ama garanti
    if "province_norm" not in modis.columns:
        raise RuntimeError("MODIS dosyasında province_norm yok.")
    modis["province_norm"] = modis["province_norm"].apply(normalize_name)

    key = ["province_norm", "harvest_year"]

    # --- sadece gerekli hedef kolonunu tut ---
    tuik = tuik[key + ["yield_kg_dekar"]].copy()

    # --- Merge ---
    df = tuik.merge(meteo, on=key, how="inner").merge(modis, on=key, how="inner")
    df = df.sort_values(key).reset_index(drop=True)

    print("TUIK:", len(tuik), "rows | provinces:", tuik["province_norm"].nunique(),
          "| years:", tuik["harvest_year"].min(), "-", tuik["harvest_year"].max())
    print("METEO:", len(meteo), "rows | provinces:", meteo["province_norm"].nunique(),
          "| years:", meteo["harvest_year"].min(), "-", meteo["harvest_year"].max())
    print("MODIS:", len(modis), "rows | provinces:", modis["province_norm"].nunique(),
          "| years:", modis["harvest_year"].min(), "-", modis["harvest_year"].max())

    print("\nMERGED:")
    print("Rows:", len(df))
    print("Provinces:", df["province_norm"].nunique())
    print("Years:", df["harvest_year"].min(), "-", df["harvest_year"].max())
    print("RIZE rows:", (df["province_norm"] == "RIZE").sum())
    print("TRABZON rows:", (df["province_norm"] == "TRABZON").sum())

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8")
    print(f"\nDONE ✅ Saved: {OUT_PATH}")

if __name__ == "__main__":
    main()
