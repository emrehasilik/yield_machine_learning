import re
import unicodedata
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

# Senin mevcut dosya adların (data/raw içinde)
IN_FILES = [
    BASE_DIR / "data" / "raw" / "TR_Wheat_MODIS_2005_2009.csv",
    BASE_DIR / "data" / "raw" / "TR_Wheat_MODIS_2010_2014.csv",
    BASE_DIR / "data" / "raw" / "TR_Wheat_MODIS_2015_2019.csv",
    BASE_DIR / "data" / "raw" / "TR_Wheat_MODIS_2020_2024.csv",
]

OUT_PATH = BASE_DIR / "result" / "modis_features.csv"

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

def detect_cols(df: pd.DataFrame):
    # province kolonu
    prov_col = None
    for c in df.columns:
        cl = c.lower()
        if cl in ["province", "il", "adm1_name", "name", "province_name"]:
            prov_col = c
            break
    if prov_col is None:
        # bazı exportlarda "ADM1_NAME" olur
        for c in df.columns:
            if "adm1" in c.lower() and "name" in c.lower():
                prov_col = c
                break
    if prov_col is None:
        raise RuntimeError(f"Province kolonu bulunamadı. Kolonlar: {list(df.columns)[:40]}")

    # year kolonu
    year_col = None
    for c in df.columns:
        if c.lower() in ["harvest_year", "year"]:
            year_col = c
            break
    if year_col is None:
        raise RuntimeError("MODIS csv içinde year/harvest_year kolonu yok.")

    # NDVI/EVI kolonları
    cols_lower = {c: c.lower() for c in df.columns}
    ndvi_cols = [c for c, cl in cols_lower.items() if "ndvi" in cl]
    evi_cols  = [c for c, cl in cols_lower.items() if "evi" in cl]
    if not ndvi_cols and not evi_cols:
        raise RuntimeError("NDVI/EVI kolonu bulunamadı.")
    return prov_col, year_col, ndvi_cols, evi_cols

def main():
    missing = [str(p) for p in IN_FILES if not p.exists()]
    if missing:
        raise FileNotFoundError("Eksik MODIS dosyaları:\n" + "\n".join(missing))

    dfs = []
    for fp in IN_FILES:
        df = pd.read_csv(fp)
        df["__file"] = fp.name
        dfs.append(df)

    df = pd.concat(dfs, ignore_index=True)

    prov_col, year_col, ndvi_cols, evi_cols = detect_cols(df)

    # normalize
    df["province"] = df[prov_col].astype(str)
    df["province_norm"] = df["province"].apply(normalize_name)

    df["harvest_year"] = pd.to_numeric(df[year_col], errors="coerce").astype("Int64")
    df = df[df["harvest_year"].notna()].copy()
    df["harvest_year"] = df["harvest_year"].astype(int)

    # NDVI/EVI sayısal
    for c in ndvi_cols + evi_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    feat_cols = ndvi_cols + evi_cols

    # aynı il-yıl birden çok satır varsa ortalama al
    out = df.groupby(["province_norm", "harvest_year"], as_index=False)[feat_cols].mean()

    # isimleri standardize et
    rename = {}
    for c in out.columns:
        if c in ["province_norm", "harvest_year"]:
            continue
        cl = c.lower().replace(" ", "_")
        rename[c] = cl
    out = out.rename(columns=rename)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False, encoding="utf-8")

    print("Input files:", len(IN_FILES))
    print("NDVI cols:", ndvi_cols)
    print("EVI cols:", evi_cols)
    print("Output rows:", len(out))
    print("Years:", out["harvest_year"].min(), "-", out["harvest_year"].max())
    print("Provinces:", out["province_norm"].nunique())
    print(f"DONE ✅ Saved: {OUT_PATH}")

if __name__ == "__main__":
    main()
