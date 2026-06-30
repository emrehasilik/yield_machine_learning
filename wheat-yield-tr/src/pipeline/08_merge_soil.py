# src/08_merge_soil.py
# Mevcut dataset_model.csv'ye toprak verilerini ekler.
# Toprak statik oldugu icin il adi uzerinden left join yapilir.

import pandas as pd
from pathlib import Path
from utils.names import normalize_province_name

BASE_DIR   = Path(__file__).resolve().parents[2]
DATASET_IN = BASE_DIR / "result" / "datasets" / "dataset_model_v1.csv"
SOIL_IN    = BASE_DIR / "result" / "features" / "soil_features.csv"
OUT_PATH   = BASE_DIR / "result" / "datasets" / "dataset_model_v2.csv"

def main():
    df   = pd.read_csv(DATASET_IN)
    soil = pd.read_csv(SOIL_IN)

    # normalize
    df["province_norm"]   = df["province_norm"].apply(normalize_province_name)
    soil["province_norm"] = soil["province_norm"].apply(normalize_province_name)

    soil_cols = [c for c in soil.columns if c.startswith("soil_")]
    soil_slim = soil[["province_norm"] + soil_cols]

    merged = df.merge(soil_slim, on="province_norm", how="left")

    missing = merged[soil_cols].isna().sum()
    print("Eksik toprak verisi (il eslesemedi):")
    print(missing[missing > 0] if missing.any() else "  Hepsi eslesti!")

    print(f"\nOrijinal: {len(df)} satir, {len(df.columns)} sutun")
    print(f"Yeni    : {len(merged)} satir, {len(merged.columns)} sutun")
    print(f"Eklenen : {soil_cols}")

    merged.to_csv(OUT_PATH, index=False, encoding="utf-8")
    print(f"\nKaydedildi: {OUT_PATH}")

if __name__ == "__main__":
    main()
