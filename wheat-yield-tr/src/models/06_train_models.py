import json
import math
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


BASE_DIR = Path(__file__).resolve().parents[2]
IN_PATH = BASE_DIR / "result" / "datasets" / "dataset_model_v1.csv"
OUT_REPORT = BASE_DIR / "result" / "models" / "model_report_v1.txt"
OUT_PRED = BASE_DIR / "result" / "predictions" / "predictions_v1.csv"
OUT_MODEL = BASE_DIR / "result" / "models" / "model_v1.joblib"
OUT_META = BASE_DIR / "result" / "models" / "model_meta_v1.json"

TARGET = "yield_kg_dekar"
KEY_COLS = ["province_norm", "harvest_year"]
CAT_FEATURES = ["province_norm"]
DROP_FEATURES = {"index"}


def rmse(y_true, y_pred):
    return math.sqrt(mean_squared_error(y_true, y_pred))


def evaluate(name, y_true, y_pred):
    return {
        "model": name,
        "R2": float(r2_score(y_true, y_pred)),
        "RMSE": float(rmse(y_true, y_pred)),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
    }


def build_preprocess(num_feature_cols, cat_feature_cols, scale_numeric):
    num_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        num_steps.append(("scaler", StandardScaler()))

    cat_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", Pipeline(steps=num_steps), num_feature_cols),
            ("cat", cat_pipe, cat_feature_cols),
        ],
        remainder="drop",
    )


def make_pipeline(name, num_feature_cols, cat_feature_cols):
    if name == "Ridge":
        return Pipeline(
            [
                ("pre", build_preprocess(num_feature_cols, cat_feature_cols, scale_numeric=True)),
                ("model", Ridge(alpha=3.0, random_state=42)),
            ]
        )

    if name == "RandomForest":
        return Pipeline(
            [
                ("pre", build_preprocess(num_feature_cols, cat_feature_cols, scale_numeric=False)),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=600,
                        random_state=42,
                        n_jobs=1,
                        max_depth=None,
                    ),
                ),
            ]
        )

    if name == "GradientBoosting":
        return Pipeline(
            [
                ("pre", build_preprocess(num_feature_cols, cat_feature_cols, scale_numeric=False)),
                ("model", GradientBoostingRegressor(random_state=42)),
            ]
        )

    raise ValueError(f"Unknown model: {name}")


def main():
    df = pd.read_csv(IN_PATH)

    df = df.dropna(subset=[TARGET]).copy()
    df["harvest_year"] = pd.to_numeric(df["harvest_year"], errors="coerce").astype("Int64")
    df = df[df["harvest_year"].notna()].copy()
    df["harvest_year"] = df["harvest_year"].astype(int)

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    num_feature_cols = [c for c in numeric_cols if c not in {TARGET, *DROP_FEATURES}]
    cat_feature_cols = [c for c in CAT_FEATURES if c in df.columns]
    feature_cols = num_feature_cols + cat_feature_cols

    ignored_cols = [c for c in df.columns if c not in feature_cols and c != TARGET]

    print("Dataset rows:", len(df))
    print("Years:", df["harvest_year"].min(), "-", df["harvest_year"].max())
    print("Provinces:", df["province_norm"].nunique())
    print("Numeric feature count:", len(num_feature_cols))
    print("Categorical feature count:", len(cat_feature_cols))
    print("Holdout years will be used as test: 2020-2024")
    if ignored_cols:
        print("Ignored columns:", ignored_cols)

    test_years = [2020, 2021, 2022, 2023, 2024]
    train = df[~df["harvest_year"].isin(test_years)].copy()
    test = df[df["harvest_year"].isin(test_years)].copy()

    if test.empty:
        raise RuntimeError(
            "Holdout (2020-2024) is empty. Check dataset_model.csv coverage for those years."
        )

    print("Holdout rows:", len(test))
    print("Years in holdout:", sorted(test["harvest_year"].unique().tolist()))

    X_train = train[feature_cols]
    y_train = train[TARGET].values
    X_test = test[feature_cols]
    y_test = test[TARGET].values

    base_pred = np.full_like(y_test, y_train.mean(), dtype=float)
    model_names = ["BaselineMean", "Ridge", "RandomForest", "GradientBoosting"]

    results = []
    preds_out = test[KEY_COLS + [TARGET]].copy()

    for name in model_names:
        if name == "BaselineMean":
            y_pred = base_pred
        else:
            pipe = make_pipeline(name, num_feature_cols, cat_feature_cols)
            pipe.fit(X_train, y_train)
            y_pred = pipe.predict(X_test)

        results.append(evaluate(name, y_test, y_pred))
        preds_out[name] = y_pred

    hold_df = pd.DataFrame(results).sort_values("RMSE").reset_index(drop=True)

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

        cv_rows.append(
            {
                "fold": fold_i,
                "test_years": ",".join(map(str, test_yrs)),
                **evaluate("BaselineMean", y_te, np.full_like(y_te, y_tr.mean(), dtype=float)),
            }
        )

        for name in ["Ridge", "RandomForest", "GradientBoosting"]:
            pipe = make_pipeline(name, num_feature_cols, cat_feature_cols)
            pipe.fit(X_tr, y_tr)
            cv_rows.append(
                {
                    "fold": fold_i,
                    "test_years": ",".join(map(str, test_yrs)),
                    **evaluate(name, y_te, pipe.predict(X_te)),
                }
            )

    cv_df = pd.DataFrame(cv_rows)
    cv_summary = (
        cv_df.groupby("model")[["R2", "RMSE", "MAE"]]
        .mean()
        .sort_values("RMSE")
        .reset_index()
    )

    best_cv_model = cv_summary.iloc[0]["model"]
    if best_cv_model == "BaselineMean":
        best_cv_model = cv_summary[cv_summary["model"] != "BaselineMean"].iloc[0]["model"]

    print("Best model by CV RMSE:", best_cv_model)

    final_train = df[~df["harvest_year"].isin(test_years)].copy()
    X_final = final_train[feature_cols]
    y_final = final_train[TARGET].values

    final_pipe = make_pipeline(best_cv_model, num_feature_cols, cat_feature_cols)
    final_pipe.fit(X_final, y_final)

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_pipe, OUT_MODEL)

    meta = {
        "target": TARGET,
        "key_cols": KEY_COLS,
        "numeric_feature_cols": num_feature_cols,
        "categorical_feature_cols": cat_feature_cols,
        "feature_cols": feature_cols,
        "dropped_feature_cols": sorted(DROP_FEATURES),
        "best_model": best_cv_model,
        "train_years_min": int(final_train["harvest_year"].min()),
        "train_years_max": int(final_train["harvest_year"].max()),
        "holdout_years": test_years,
        "rows_total": int(len(df)),
        "rows_train_final": int(len(final_train)),
        "rows_holdout": int(len(test)),
    }
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    preds_out.to_csv(OUT_PRED, index=False, encoding="utf-8")

    lines = []
    lines.append("DATASET")
    lines.append(
        f"Rows: {len(df)} | Provinces: {df['province_norm'].nunique()} | Years: "
        f"{df['harvest_year'].min()}-{df['harvest_year'].max()}"
    )
    lines.append(f"Numeric features ({len(num_feature_cols)}): {num_feature_cols}")
    lines.append(f"Categorical features ({len(cat_feature_cols)}): {cat_feature_cols}")
    if ignored_cols:
        lines.append(f"Ignored columns: {ignored_cols}")
    lines.append("")
    lines.append("HOLDOUT TEST (years 2020-2024)")
    lines.append(hold_df.to_string(index=False))
    lines.append("")
    lines.append("YEAR-FOLD CV (5 folds) - mean over folds")
    lines.append(cv_summary.to_string(index=False))
    lines.append("")
    lines.append("Per-fold details:")
    lines.append(cv_df.to_string(index=False))
    lines.append("")
    lines.append("FINAL MODEL SAVED")
    lines.append(f"Best model: {best_cv_model}")
    lines.append(f"Model file: {OUT_MODEL}")
    lines.append(f"Meta file:  {OUT_META}")

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    print("DONE")
    print(f"- Saved report: {OUT_REPORT}")
    print(f"- Saved predictions: {OUT_PRED}")
    print(f"- Saved model: {OUT_MODEL}")
    print(f"- Saved meta: {OUT_META}")


if __name__ == "__main__":
    main()
