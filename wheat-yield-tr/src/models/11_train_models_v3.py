# src/11_train_models_v3.py
# dataset_model_v3.csv (toprak + GDD + lagged yield) ile model egitir.
# V1 ve V2 ile karsilastirir.

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
IN_PATH    = BASE_DIR / "result" / "datasets" / "dataset_model_v3.csv"
OUT_REPORT = BASE_DIR / "result" / "models" / "model_report_v3.txt"
OUT_PRED   = BASE_DIR / "result" / "predictions" / "predictions_v3.csv"
OUT_MODEL  = BASE_DIR / "result" / "models" / "model_v3.joblib"

TARGET       = "yield_kg_dekar"
KEY_COLS     = ["province_norm", "harvest_year"]
CAT_FEATURES = ["province_norm"]
DROP_COLS    = {"index"}
TEST_YEARS   = [2020, 2021, 2022, 2023, 2024]

# V1 ve V2 karsilastirma icin sabit degerler
V1 = {"R2": 0.538, "RMSE": 59.5, "MAE": 46.3}
V2 = {"R2": 0.5517, "RMSE": 58.60, "MAE": 45.47}


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

    new_cols = [c for c in num_cols if c in ("gdd_season","gdd_mam","gdd_mean_day","yield_lag1")]

    train = df[~df["harvest_year"].isin(TEST_YEARS)].copy()
    test  = df[ df["harvest_year"].isin(TEST_YEARS)].copy()
    X_tr, y_tr = train[feat_cols], train[TARGET].values
    X_te, y_te = test[feat_cols],  test[TARGET].values

    print(f"Dataset: {len(df)} satir | {len(num_cols)} numerik ozellik")
    print(f"Yeni eklenen: {new_cols}")
    print(f"Train: {len(train)} | Holdout: {len(test)}\n")

    # --- HOLDOUT ---
    hold_rows = []
    preds_out = test[KEY_COLS + [TARGET]].copy()

    base = np.full_like(y_te, y_tr.mean(), dtype=float)
    hold_rows.append(evaluate("BaselineMean", y_te, base))

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

    # --- FINAL MODEL ---
    final_pipe = make_pipe(best, num_cols, cat_cols)
    final_pipe.fit(X_tr, y_tr)
    joblib.dump(final_pipe, OUT_MODEL)
    preds_out.to_csv(OUT_PRED, index=False, encoding="utf-8")

    # --- RAPOR ---
    ridge_v3 = hold_df[hold_df["model"] == "Ridge"].iloc[0]

    lines = []
    lines.append("=" * 65)
    lines.append("MODEL V3 — TOPRAK + GDD + LAGGED YIELD")
    lines.append("=" * 65)
    lines.append(f"Toplam satir   : {len(df)}")
    lines.append(f"Numerik ozellik: {len(num_cols)}")
    lines.append(f"Yeni ozellikler: {new_cols}")
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
    lines.append("=" * 65)
    lines.append("VERSIYON KARSILASTIRMASI (Ridge, Holdout)")
    lines.append("=" * 65)
    lines.append(f"V1 (Hava+NDVI)          R2={V1['R2']}  RMSE={V1['RMSE']}  MAE={V1['MAE']}")
    lines.append(f"V2 (+Toprak)             R2={V2['R2']}  RMSE={V2['RMSE']}  MAE={V2['MAE']}")
    lines.append(f"V3 (+GDD+LaggedYield)    R2={ridge_v3['R2']}  RMSE={ridge_v3['RMSE']}  MAE={ridge_v3['MAE']}")

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    # --- EKRANA YAZDIR ---
    print("--- HOLDOUT SONUCLARI ---")
    print(hold_df.to_string(index=False))
    print("\n--- CV OZETI ---")
    print(cv_summary.to_string(index=False))
    print("\n" + "=" * 55)
    print("VERSIYON KARSILASTIRMASI (Ridge, Holdout)")
    print("=" * 55)
    print(f"V1 (Hava+NDVI)        R2={V1['R2']}  RMSE={V1['RMSE']}  MAE={V1['MAE']}")
    print(f"V2 (+Toprak)          R2={V2['R2']}  RMSE={V2['RMSE']}  MAE={V2['MAE']}")
    print(f"V3 (+GDD+Lagged)      R2={ridge_v3['R2']}  RMSE={ridge_v3['RMSE']}  MAE={ridge_v3['MAE']}")
    print(f"\nEn iyi model (CV): {best}")
    print(f"Rapor: {OUT_REPORT}")


if __name__ == "__main__":
    main()
