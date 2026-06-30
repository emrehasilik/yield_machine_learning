# src/01_prepare_modis.py
from pathlib import Path
import pandas as pd

from utils.names import normalize_province_name

BASE_DIR = Path(__file__).resolve().parents[2]

IN_FILES = [
    BASE_DIR / "data" / "raw" / "TR_Wheat_MODIS_2005_2009.csv",
    BASE_DIR / "data" / "raw" / "TR_Wheat_MODIS_2010_2014.csv",
    BASE_DIR / "data" / "raw" / "TR_Wheat_MODIS_2015_2019.csv",
    BASE_DIR / "data" / "raw" / "TR_Wheat_MODIS_2020_2024.csv",
]

OUT_PATH = BASE_DIR / "result" / "features" / "modis_features.csv"

def detect_cols(df: pd.DataFrame):
    # province column
    prov_candidates = ["province", "il", "adm1_name", "name", "province_name", "ADM1_NAME"]
    prov_col = next((c for c in df.columns if c in prov_candidates), None)
    if prov_col is None:
        # fallback contains
        for c in df.columns:
            cl = c.lower()
            if "adm1" in cl and "name" in cl:
                prov_col = c
                break
    if prov_col is None:
        raise RuntimeError(f"Province kolonu bulunamadı. Kolonlar: {list(df.columns)[:50]}")

    # year column
    year_col = None
    for c in df.columns:
        if c.lower() in ["harvest_year", "year"]:
            year_col = c
            break
    if year_col is None:
        raise RuntimeError("MODIS csv içinde harvest_year/year kolonu yok.")

    # ndvi/evi columns
    cols_lower = {c: c.lower() for c in df.columns}
    ndvi_cols = [c for c, cl in cols_lower.items() if "ndvi" in cl]
    evi_cols = [c for c, cl in cols_lower.items() if "evi" in cl]
    if not ndvi_cols and not evi_cols:
        raise RuntimeError("NDVI/EVI kolonu bulunamadı.")

    # ağırlık varsa (alan)
    area_col = None
    for c in df.columns:
        if c.lower() in ["shape_area", "area", "Shape_Area".lower()]:
            area_col = c
            break
    return prov_col, year_col, ndvi_cols, evi_cols, area_col

def weighted_mean(group: pd.DataFrame, value_cols: list[str], wcol: str):
    w = pd.to_numeric(group[wcol], errors="coerce").fillna(0)
    out = {}
    wsum = float(w.sum())
    for c in value_cols:
        x = pd.to_numeric(group[c], errors="coerce")
        if wsum > 0:
            out[c] = float((x * w).sum() / wsum)
        else:
            out[c] = float(x.mean())
    return pd.Series(out)

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

    prov_col, year_col, ndvi_cols, evi_cols, area_col = detect_cols(df)

    df["province"] = df[prov_col].astype(str)
    df["province_norm"] = df["province"].apply(normalize_province_name)

    df["harvest_year"] = pd.to_numeric(df[year_col], errors="coerce").astype("Int64")
    df = df[df["harvest_year"].notna()].copy()
    df["harvest_year"] = df["harvest_year"].astype(int)

    feat_cols = ndvi_cols + evi_cols
    for c in feat_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    key = ["province_norm", "harvest_year"]

    if area_col and area_col in df.columns:
        out = (
            df.groupby(key, as_index=False)
              .apply(lambda g: weighted_mean(g, feat_cols, area_col))
              .reset_index()
        )
        # groupby apply sonrası kolonlar: key + index vs; düzelt
        out = out.rename(columns={"level_0": "province_norm", "level_1": "harvest_year"})
        # bazı pandas sürümlerinde farklı gelebilir, garantiye al:
        if "province_norm" not in out.columns:
            out["province_norm"] = out[key[0]]
        if "harvest_year" not in out.columns:
            out["harvest_year"] = out[key[1]]
        out = out[key + feat_cols]
    else:
        out = df.groupby(key, as_index=False)[feat_cols].mean()

    # kolon isimlerini standardize et
    rename = {}
    for c in out.columns:
        if c in key:
            continue
        rename[c] = c.lower().replace(" ", "_")
    out = out.rename(columns=rename)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False, encoding="utf-8")

    print("MODIS rows:", len(out))
    print("Years:", out["harvest_year"].min(), "-", out["harvest_year"].max())
    print("Provinces:", out["province_norm"].nunique())
    print("Saved:", OUT_PATH)

if __name__ == "__main__":
    main()
