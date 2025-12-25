import math
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error


BASE_DIR = Path(__file__).resolve().parents[1]
IN_PATH = BASE_DIR / "result" / "dataset_model.csv"
OUT_REPORT = BASE_DIR / "result" / "model_report.txt"
OUT_PRED = BASE_DIR / "result" / "predictions_holdout.csv"

TARGET = "yield_kg_dekar"
KEY_COLS = ["province_norm", "harvest_year"]


def rmse(y_true, y_pred):
    return math.sqrt(mean_squared_error(y_true, y_pred))


def evaluate(name, y_true, y_pred):
    return {
        "model": name,
        "R2": float(r2_score(y_true, y_pred)),
        "RMSE": float(rmse(y_true, y_pred)),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
    }


def build_preprocess(feature_cols):
    # Sayısal özelliklere imputing + scaling
    num_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    pre = ColumnTransformer(
        transformers=[
            ("num", num_pipe, feature_cols),
        ],
        remainder="drop",
    )
    return pre


def main():
    df = pd.read_csv(IN_PATH)

    # --- basic checks ---
    df = df.dropna(subset=[TARGET]).copy()
    df["harvest_year"] = pd.to_numeric(df["harvest_year"], errors="coerce").astype("Int64")
    df = df[df["harvest_year"].notna()].copy()
    df["harvest_year"] = df["harvest_year"].astype(int)

    # -------------------------
    # Feature selection FIX ✅
    # -------------------------
    drop_cols = set(KEY_COLS + [TARGET])

    # Sadece sayısal kolonları feature olarak al
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [c for c in numeric_cols if c not in drop_cols]

    # Bilgilendirici debug: hangi non-numeric kolonlar görmezden gelindi?
    non_numeric = [c for c in df.columns if c not in drop_cols and c not in feature_cols]
    print("Dataset rows:", len(df))
    print("Years:", df["harvest_year"].min(), "-", df["harvest_year"].max())
    print("Provinces:", df["province_norm"].nunique())
    print("Numeric feature count:", len(feature_cols))
    if non_numeric:
        print("Non-numeric columns ignored:", non_numeric)

    # -------------------------
    # 1) HOLDOUT (time-based)
    # -------------------------
    test_years = [2020, 2021, 2022, 2023, 2024]
    train = df[~df["harvest_year"].isin(test_years)].copy()
    test = df[df["harvest_year"].isin(test_years)].copy()

    X_train = train[feature_cols]
    y_train = train[TARGET].values
    X_test = test[feature_cols]
    y_test = test[TARGET].values

    # baseline: train mean
    base_pred = np.full_like(y_test, y_train.mean(), dtype=float)

    models = {
        "BaselineMean": None,
        "Ridge": Ridge(alpha=1.0, random_state=42),
        "RandomForest": RandomForestRegressor(
            n_estimators=600, random_state=42, n_jobs=-1, max_depth=None
        ),
        "GradientBoosting": GradientBoostingRegressor(random_state=42),
    }

    results = []
    preds_out = test[KEY_COLS + [TARGET]].copy()

    # preprocess only for models that need it (Ridge)
    pre = build_preprocess(feature_cols)

    for name, model in models.items():
        if name == "BaselineMean":
            y_pred = base_pred
            results.append(evaluate(name, y_test, y_pred))
            preds_out[name] = y_pred
            continue

        if name == "Ridge":
            pipe = Pipeline([("pre", pre), ("model", model)])
        else:
            # tree models: impute only (scale gerekmez)
            pipe = Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("model", model),
                ]
            )

        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)

        results.append(evaluate(name, y_test, y_pred))
        preds_out[name] = y_pred

    # -------------------------
    # 2) YEAR-FOLD CV (5 folds)
    # -------------------------
    years = sorted(df["harvest_year"].unique().tolist())
    folds = np.array_split(years, 5)

    cv_rows = []
    for fold_i, test_yrs in enumerate(folds, start=1):
        test_yrs = list(map(int, test_yrs))

        tr = df[~df["harvest_year"].isin(test_yrs)].copy()
        te = df[df["harvest_year"].isin(test_yrs)].copy()

        X_tr = tr[feature_cols]
        y_tr = tr[TARGET].values
        X_te = te[feature_cols]
        y_te = te[TARGET].values

        # baseline
        cv_rows.append(
            {
                "fold": fold_i,
                "test_years": ",".join(map(str, test_yrs)),
                **evaluate("BaselineMean", y_te, np.full_like(y_te, y_tr.mean(), dtype=float)),
            }
        )

        # Ridge
        ridge_pipe = Pipeline([("pre", pre), ("model", Ridge(alpha=1.0, random_state=42))])
        ridge_pipe.fit(X_tr, y_tr)
        cv_rows.append(
            {
                "fold": fold_i,
                "test_years": ",".join(map(str, test_yrs)),
                **evaluate("Ridge", y_te, ridge_pipe.predict(X_te)),
            }
        )

        # RF
        rf_pipe = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", RandomForestRegressor(n_estimators=400, random_state=42, n_jobs=-1)),
            ]
        )
        rf_pipe.fit(X_tr, y_tr)
        cv_rows.append(
            {
                "fold": fold_i,
                "test_years": ",".join(map(str, test_yrs)),
                **evaluate("RandomForest", y_te, rf_pipe.predict(X_te)),
            }
        )

        # GB
        gb_pipe = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", GradientBoostingRegressor(random_state=42)),
            ]
        )
        gb_pipe.fit(X_tr, y_tr)
        cv_rows.append(
            {
                "fold": fold_i,
                "test_years": ",".join(map(str, test_yrs)),
                **evaluate("GradientBoosting", y_te, gb_pipe.predict(X_te)),
            }
        )

    cv_df = pd.DataFrame(cv_rows)

    cv_summary = (
        cv_df.groupby("model")[["R2", "RMSE", "MAE"]]
        .mean()
        .sort_values("RMSE")
        .reset_index()
    )

    # --- Save outputs ---
    preds_out.to_csv(OUT_PRED, index=False, encoding="utf-8")

    # report text
    lines = []
    lines.append("DATASET")
    lines.append(
        f"Rows: {len(df)} | Provinces: {df['province_norm'].nunique()} | Years: {df['harvest_year'].min()}-{df['harvest_year'].max()}"
    )
    lines.append(f"Numeric features ({len(feature_cols)}): {feature_cols}")
    if non_numeric:
        lines.append(f"Ignored non-numeric columns: {non_numeric}")
    lines.append("")
    lines.append("HOLDOUT TEST (years 2020-2024)")
    hold_df = pd.DataFrame(results).sort_values("RMSE")
    lines.append(hold_df.to_string(index=False))
    lines.append("")
    lines.append("YEAR-FOLD CV (5 folds) - mean over folds")
    lines.append(cv_summary.to_string(index=False))
    lines.append("")
    lines.append("Per-fold details:")
    lines.append(cv_df.to_string(index=False))

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    print("DONE ✅")
    print(f"- Saved report: {OUT_REPORT}")
    print(f"- Saved predictions: {OUT_PRED}")


if __name__ == "__main__":
    main()
