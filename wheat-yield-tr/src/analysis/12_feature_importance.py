# src/12_feature_importance.py
# V3 modeli icin feature importance analizi.
# Ridge -> Permutation Importance
# RandomForest -> Built-in importance
# GradientBoosting -> Built-in importance
# Sonuclar CSV + konsol tablosu olarak kaydedilir.

import numpy as np
import pandas as pd
import math
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE_DIR  = Path(__file__).resolve().parents[2]
IN_PATH   = BASE_DIR / "result" / "datasets" / "dataset_model_v3.csv"
OUT_PATH  = BASE_DIR / "result" / "analysis" / "feature_importance_v3.csv"

TARGET       = "yield_kg_dekar"
CAT_FEATURES = ["province_norm"]
DROP_COLS    = {"index"}
TEST_YEARS   = [2020, 2021, 2022, 2023, 2024]


def build_pre(num_cols, cat_cols, scale):
    num_steps = [("imp", SimpleImputer(strategy="median"))]
    if scale:
        num_steps.append(("sc", StandardScaler()))
    return ColumnTransformer([
        ("num", Pipeline(num_steps), num_cols),
        ("cat", Pipeline([
            ("imp", SimpleImputer(strategy="most_frequent")),
            ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), cat_cols),
    ], remainder="drop")


def make_pipe(name, num_cols, cat_cols):
    if name == "Ridge":
        return Pipeline([("pre", build_pre(num_cols, cat_cols, True)),
                         ("m", Ridge(alpha=3.0, random_state=42))])
    if name == "RandomForest":
        return Pipeline([("pre", build_pre(num_cols, cat_cols, False)),
                         ("m", RandomForestRegressor(n_estimators=600, random_state=42, n_jobs=-1))])
    if name == "GradientBoosting":
        return Pipeline([("pre", build_pre(num_cols, cat_cols, False)),
                         ("m", GradientBoostingRegressor(random_state=42))])


def get_feature_names(pipe, num_cols, cat_cols):
    """Pipeline'dan gercek ozellik isimlerini cikarir."""
    pre = pipe.named_steps["pre"]
    ohe = pre.named_transformers_["cat"].named_steps["ohe"]
    cat_names = list(ohe.get_feature_names_out(cat_cols))
    return num_cols + cat_names


def permutation_imp(pipe, X, y, num_cols, cat_cols, n_repeats=20):
    """Ridge icin permutation importance (test seti uzerinde)."""
    result = permutation_importance(
        pipe, X, y,
        n_repeats=n_repeats,
        random_state=42,
        n_jobs=-1,
        scoring="r2"
    )
    feat_names = get_feature_names(pipe, num_cols, cat_cols)
    # sadece numerik (il one-hot kolonlarini atla)
    rows = []
    for i, name in enumerate(feat_names):
        if any(name.startswith(f"province_norm_") for _ in [1]):
            continue
        rows.append({
            "feature":    name,
            "importance": round(result.importances_mean[i], 5),
            "std":        round(result.importances_std[i], 5),
        })
    df = pd.DataFrame(rows).sort_values("importance", ascending=False)
    return df


def tree_imp(pipe, num_cols, cat_cols):
    """RF / GBM icin dahili feature importance."""
    feat_names = get_feature_names(pipe, num_cols, cat_cols)
    imps = pipe.named_steps["m"].feature_importances_
    rows = []
    for name, imp in zip(feat_names, imps):
        if name.startswith("province_norm_"):
            continue
        rows.append({"feature": name, "importance": round(float(imp), 5), "std": None})
    df = pd.DataFrame(rows).sort_values("importance", ascending=False)
    return df


def print_top(df, model_name, n=15):
    total = df["importance"].clip(lower=0).sum()
    print(f"\n{'='*55}")
    print(f"  {model_name} — Top {n} Feature")
    print(f"{'='*55}")
    print(f"{'Ozellik':<28} {'Onemi':>9}  {'Bar'}")
    print("-" * 55)
    for _, row in df.head(n).iterrows():
        imp   = row["importance"]
        pct   = imp / total * 100 if total > 0 else 0
        bar   = "#" * int(pct / 2)
        print(f"{row['feature']:<28} {pct:>8.1f}%  {bar}")


def main():
    df = pd.read_csv(IN_PATH)
    df = df.dropna(subset=[TARGET]).copy()
    df["harvest_year"] = pd.to_numeric(df["harvest_year"], errors="coerce").astype(int)

    num_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                if c not in {TARGET, *DROP_COLS}]
    cat_cols = [c for c in CAT_FEATURES if c in df.columns]
    feat_cols = num_cols + cat_cols

    train = df[~df["harvest_year"].isin(TEST_YEARS)]
    test  = df[ df["harvest_year"].isin(TEST_YEARS)]
    X_tr, y_tr = train[feat_cols], train[TARGET].values
    X_te, y_te = test[feat_cols],  test[TARGET].values

    results = {}

    # --- Ridge: Permutation Importance ---
    print("\nRidge egitiliyor + permutation importance hesaplaniyor...")
    ridge_pipe = make_pipe("Ridge", num_cols, cat_cols)
    ridge_pipe.fit(X_tr, y_tr)
    ridge_imp = permutation_imp(ridge_pipe, X_te, y_te, num_cols, cat_cols, n_repeats=30)
    results["Ridge_perm"] = ridge_imp
    print_top(ridge_imp, "Ridge (Permutation Importance)")

    # --- Random Forest: Built-in ---
    print("\nRandomForest egitiliyor...")
    rf_pipe = make_pipe("RandomForest", num_cols, cat_cols)
    rf_pipe.fit(X_tr, y_tr)
    rf_imp = tree_imp(rf_pipe, num_cols, cat_cols)
    results["RandomForest"] = rf_imp
    print_top(rf_imp, "Random Forest (Built-in Importance)")

    # --- GradientBoosting: Built-in ---
    print("\nGradientBoosting egitiliyor...")
    gb_pipe = make_pipe("GradientBoosting", num_cols, cat_cols)
    gb_pipe.fit(X_tr, y_tr)
    gb_imp = tree_imp(gb_pipe, num_cols, cat_cols)
    results["GradientBoosting"] = gb_imp
    print_top(gb_imp, "Gradient Boosting (Built-in Importance)")

    # --- Uzlasma: 3 modelin ortalamasi ---
    print("\n\nUzlasma tablosu hesaplaniyor (3 model ortalamasi)...")

    # normalize et (0-1)
    def norm(s):
        s = s.clip(lower=0)
        return s / s.sum() if s.sum() > 0 else s

    r = ridge_imp.set_index("feature")["importance"].pipe(norm)
    rf = rf_imp.set_index("feature")["importance"].pipe(norm)
    gb = gb_imp.set_index("feature")["importance"].pipe(norm)

    consensus = pd.concat([r, rf, gb], axis=1)
    consensus.columns = ["Ridge", "RF", "GB"]
    consensus = consensus.fillna(0)
    consensus["Ortalama"] = consensus.mean(axis=1)
    consensus = consensus.sort_values("Ortalama", ascending=False).reset_index()
    consensus.rename(columns={"index": "feature"}, inplace=True)

    print(f"\n{'='*65}")
    print("  UZLASMA — 3 Model Ortalamasi (il one-hot haric)")
    print(f"{'='*65}")
    print(f"{'Ozellik':<28} {'Ridge':>7} {'RF':>7} {'GB':>7} {'Ort':>7}  Bar")
    print("-" * 65)
    for _, row in consensus.head(20).iterrows():
        bar = "#" * int(row["Ortalama"] * 200)
        print(f"{row['feature']:<28} {row['Ridge']:>7.3f} {row['RF']:>7.3f} {row['GB']:>7.3f} {row['Ortalama']:>7.3f}  {bar}")

    # Kaydet
    consensus.to_csv(OUT_PATH, index=False, encoding="utf-8")
    print(f"\nKaydedildi: {OUT_PATH}")

    # Gruplu ozet
    groups = {
        "Lagged Yield":   ["yield_lag1"],
        "GDD":            ["gdd_season", "gdd_mam", "gdd_mean_day"],
        "NDVI/EVI":       ["ndvi_max", "ndvi_mean", "ndvi_auc", "evi_max", "evi_mean"],
        "Meteo (Sezon)":  ["tmean","tmax_mean","tmin_mean","rain_sum","rad_mean",
                           "tmean_std","tmax_p95","tmin_p05","hot_days_30","frost_days_0","dry_days_lt1mm"],
        "Meteo (MAM)":    [c for c in num_cols if c.startswith("mam_")],
        "Toprak":         [c for c in num_cols if c.startswith("soil_")],
        "Zaman":          ["harvest_year"],
    }

    print(f"\n{'='*45}")
    print("  GRUP BAZINDA KATKI (Ortalama, normalize)")
    print(f"{'='*45}")
    grp_rows = []
    for grp, cols in groups.items():
        ort = consensus[consensus["feature"].isin(cols)]["Ortalama"].sum()
        grp_rows.append({"Grup": grp, "Katki": round(ort, 4)})
    grp_df = pd.DataFrame(grp_rows).sort_values("Katki", ascending=False)
    total_grp = grp_df["Katki"].sum()
    for _, r in grp_df.iterrows():
        pct = r["Katki"] / total_grp * 100
        bar = "#" * int(pct / 2)
        print(f"{r['Grup']:<18} {pct:>6.1f}%  {bar}")


if __name__ == "__main__":
    main()
