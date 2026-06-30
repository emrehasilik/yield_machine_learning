# src/09_train_models_v2.py
# dataset_model_v2.csv (toprak ozellikleri ekli) ile model egitir.
# Sonuclari v1 ile karsilastirir.

import json, math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE_DIR   = Path(__file__).resolve().parents[2]
IN_PATH    = BASE_DIR / "result" / "datasets" / "dataset_model_v2.csv"
OUT_REPORT = BASE_DIR / "result" / "models" / "model_report_v2.txt"
OUT_PRED   = BASE_DIR / "result" / "predictions" / "predictions_v2.csv"
OUT_MODEL  = BASE_DIR / "result" / "models" / "model_v2.joblib"
OUT_META   = BASE_DIR / "result" / "model_meta_v2.json"
V1_REPORT  = BASE_DIR / "result" / "models" / "model_report_v1.txt"

TARGET       = "yield_kg_dekar"
KEY_COLS     = ["province_norm", "harvest_year"]
CAT_FEATURES = ["province_norm"]
DROP_COLS    = {"index"}
TEST_YEARS   = [2020, 2021, 2022, 2023, 2024]


def rmse(y_true, y_pred):
    return math.sqrt(mean_squared_error(y_true, y_pred))

def evaluate(name, y_true, y_pred):
    return {
        "model": name,
        "R2":   round(float(r2_score(y_true, y_pred)), 4),
        "RMSE": round(float(rmse(y_true, y_pred)), 2),
        "MAE":  round(float(mean_absolute_error(y_true, y_pred)), 2),
    }

def build_pre(num_cols, cat_cols, scale):
    num_steps = [("imp", SimpleImputer(strategy="median"))]
    if scale:
        num_steps.append(("sc", StandardScaler()))
    return ColumnTransformer([
        ("num", Pipeline(num_steps), num_cols),
        ("cat", Pipeline([
            ("imp", SimpleImputer(strategy="most_frequent")),
            ("ohe", OneHotEncoder(handle_unknown="ignore")),
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
    raise ValueError(name)


def main():
    df = pd.read_csv(IN_PATH)
    df = df.dropna(subset=[TARGET]).copy()
    df["harvest_year"] = pd.to_numeric(df["harvest_year"], errors="coerce").astype("Int64")
    df = df[df["harvest_year"].notna()].copy()
    df["harvest_year"] = df["harvest_year"].astype(int)

    num_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                if c not in {TARGET, *DROP_COLS}]
    cat_cols = [c for c in CAT_FEATURES if c in df.columns]
    feat_cols = num_cols + cat_cols

    soil_cols = [c for c in num_cols if c.startswith("soil_")]

    train = df[~df["harvest_year"].isin(TEST_YEARS)].copy()
    test  = df[ df["harvest_year"].isin(TEST_YEARS)].copy()

    X_tr, y_tr = train[feat_cols], train[TARGET].values
    X_te, y_te = test[feat_cols],  test[TARGET].values

    print(f"Dataset: {len(df)} satir | {len(num_cols)} numerik + {len(cat_cols)} kategorik ozellik")
    print(f"Toprak ozellikleri ({len(soil_cols)}): {soil_cols}")
    print(f"Train: {len(train)} | Holdout: {len(test)}\n")

    # --- HOLDOUT ---
    hold_rows = []
    preds_out = test[KEY_COLS + [TARGET]].copy()

    base = np.full_like(y_te, y_tr.mean(), dtype=float)
    hold_rows.append(evaluate("BaselineMean", y_te, base))
    preds_out["BaselineMean"] = base

    for name in ["Ridge", "RandomForest", "GradientBoosting"]:
        pipe = make_pipe(name, num_cols, cat_cols)
        pipe.fit(X_tr, y_tr)
        pred = pipe.predict(X_te)
        hold_rows.append(evaluate(name, y_te, pred))
        preds_out[name] = pred

    hold_df = pd.DataFrame(hold_rows).sort_values("RMSE").reset_index(drop=True)

    # --- 5-FOLD CV ---
    years = sorted(df["harvest_year"].unique().tolist())
    folds = np.array_split(years, 5)
    cv_rows = []

    for fi, test_yrs in enumerate(folds, 1):
        test_yrs = list(map(int, test_yrs))
        tr = df[~df["harvest_year"].isin(test_yrs)]
        te = df[ df["harvest_year"].isin(test_yrs)]
        Xtr, ytr = tr[feat_cols], tr[TARGET].values
        Xte, yte = te[feat_cols], te[TARGET].values

        cv_rows.append({"fold": fi, "test_years": ",".join(map(str, test_yrs)),
                        **evaluate("BaselineMean", yte, np.full_like(yte, ytr.mean(), dtype=float))})
        for name in ["Ridge", "RandomForest", "GradientBoosting"]:
            p = make_pipe(name, num_cols, cat_cols)
            p.fit(Xtr, ytr)
            cv_rows.append({"fold": fi, "test_years": ",".join(map(str, test_yrs)),
                            **evaluate(name, yte, p.predict(Xte))})

    cv_df = pd.DataFrame(cv_rows)
    cv_summary = (cv_df.groupby("model")[["R2","RMSE","MAE"]]
                  .mean().sort_values("RMSE").reset_index())

    best = cv_summary[cv_summary["model"] != "BaselineMean"].iloc[0]["model"]
    print("En iyi model (CV):", best)

    # --- FINAL MODEL ---
    final_pipe = make_pipe(best, num_cols, cat_cols)
    final_pipe.fit(X_tr, y_tr)
    joblib.dump(final_pipe, OUT_MODEL)

    meta = {
        "version": "v2_with_soil",
        "target": TARGET,
        "numeric_feature_cols": num_cols,
        "categorical_feature_cols": cat_cols,
        "soil_feature_cols": soil_cols,
        "best_model": best,
        "rows_total": int(len(df)),
        "rows_train": int(len(train)),
        "rows_holdout": int(len(test)),
    }
    OUT_META.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    preds_out.to_csv(OUT_PRED, index=False, encoding="utf-8")

    # --- KARSILASTIRMA RAPORU ---
    lines = []
    lines.append("=" * 60)
    lines.append("MODEL V2 — TOPRAK VERISi EKLI")
    lines.append("=" * 60)
    lines.append(f"Toplam satir   : {len(df)}")
    lines.append(f"Numerik ozellik: {len(num_cols)}  (v1: 27, yeni: +{len(soil_cols)} toprak)")
    lines.append(f"Toprak cols    : {soil_cols}")
    lines.append("")
    lines.append("--- HOLDOUT TEST (2020-2024) ---")
    lines.append(hold_df.to_string(index=False))
    lines.append("")
    lines.append("--- 5-FOLD CV OZETI ---")
    lines.append(cv_summary.to_string(index=False))
    lines.append("")
    lines.append("--- CV FOLD DETAYI ---")
    lines.append(cv_df.to_string(index=False))
    lines.append("")

    # V1 karsilastirmasi
    if V1_REPORT.exists():
        v1_text = V1_REPORT.read_text(encoding="utf-8")
        # v1 holdout Ridge satirini bul
        lines.append("=" * 60)
        lines.append("V1 vs V2 KARSILASTIRMA (Ridge, Holdout)")
        lines.append("=" * 60)
        for line in v1_text.splitlines():
            if "Ridge" in line and any(c.isdigit() for c in line):
                lines.append(f"V1: {line.strip()}")
                break
        ridge_v2 = hold_df[hold_df["model"] == "Ridge"].iloc[0]
        lines.append(f"V2: Ridge  R2={ridge_v2['R2']}  RMSE={ridge_v2['RMSE']}  MAE={ridge_v2['MAE']}")

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    print("\n--- HOLDOUT SONUCLARI ---")
    print(hold_df.to_string(index=False))
    print("\n--- CV OZETI ---")
    print(cv_summary.to_string(index=False))
    print(f"\nRapor: {OUT_REPORT}")


if __name__ == "__main__":
    main()
