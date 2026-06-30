# src/db/03_import_data.py
# CSV dosyalarindan SQL Server'a veri yukler.
# Once 01_create_db.sql ve 02_create_tables.sql'i SSMS'de calistir.

import sys
from pathlib import Path
import pandas as pd
import pyodbc

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / "src"))
from utils.names import normalize_province_name

# --- BAGLANTI ---
# SSMS'de sunucu adini kontrol et: Genellikle bilgisayar_adi\SQLEXPRESS veya sadece .
CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"          # veya BILGISAYAR_ADI\SQLEXPRESS
    "DATABASE=wheat_yield_tr;"
    "Trusted_Connection=yes;"   # Windows kimlik dogrulamasi (sifre gerekmez)
)

REGION_MAP = {
    "ADANA":"Akdeniz","ADIYAMAN":"Guneydogu Anadolu","AFYONKARAHISAR":"Ege",
    "AGRI":"Dogu Anadolu","AKSARAY":"Ic Anadolu","AMASYA":"Karadeniz",
    "ANKARA":"Ic Anadolu","ANTALYA":"Akdeniz","ARDAHAN":"Dogu Anadolu",
    "ARTVIN":"Karadeniz","AYDIN":"Ege","BALIKESIR":"Ege","BARTIN":"Karadeniz",
    "BATMAN":"Guneydogu Anadolu","BAYBURT":"Karadeniz","BILECIK":"Marmara",
    "BINGOL":"Dogu Anadolu","BITLIS":"Dogu Anadolu","BOLU":"Bati Karadeniz",
    "BURDUR":"Akdeniz","BURSA":"Marmara","CANAKKALE":"Ege","CANKIRI":"Ic Anadolu",
    "CORUM":"Karadeniz","DENIZLI":"Ege","DIYARBAKIR":"Guneydogu Anadolu",
    "EDIRNE":"Marmara","ELAZIG":"Dogu Anadolu","ERZINCAN":"Dogu Anadolu",
    "ERZURUM":"Dogu Anadolu","ESKISEHIR":"Ic Anadolu","GAZIANTEP":"Guneydogu Anadolu",
    "GIRESUN":"Karadeniz","GUMUSHANE":"Karadeniz","HAKKARI":"Dogu Anadolu",
    "HATAY":"Akdeniz","IGDIR":"Dogu Anadolu","ISPARTA":"Akdeniz",
    "ISTANBUL":"Marmara","IZMIR":"Ege","KAHRAMANMARAS":"Akdeniz",
    "KARABUK":"Karadeniz","KARAMAN":"Ic Anadolu","KARS":"Dogu Anadolu",
    "KASTAMONU":"Karadeniz","KAYSERI":"Ic Anadolu","KILIS":"Guneydogu Anadolu",
    "KIRIKKALE":"Ic Anadolu","KIRKLARELI":"Marmara","KIRSEHIR":"Ic Anadolu",
    "KOCAELI":"Marmara","KONYA":"Ic Anadolu","KUTAHYA":"Ege","MALATYA":"Dogu Anadolu",
    "MANISA":"Ege","MARDIN":"Guneydogu Anadolu","MERSIN":"Akdeniz","MUGLA":"Ege",
    "MUS":"Dogu Anadolu","NEVSEHIR":"Ic Anadolu","NIGDE":"Ic Anadolu",
    "ORDU":"Karadeniz","OSMANIYE":"Akdeniz","RIZE":"Karadeniz","SAKARYA":"Marmara",
    "SAMSUN":"Karadeniz","SANLIURFA":"Guneydogu Anadolu","SIIRT":"Guneydogu Anadolu",
    "SINOP":"Karadeniz","SIRNAK":"Guneydogu Anadolu","SIVAS":"Ic Anadolu",
    "TEKIRDAG":"Marmara","TOKAT":"Karadeniz","TRABZON":"Karadeniz",
    "TUNCELI":"Dogu Anadolu","USAK":"Ege","VAN":"Dogu Anadolu",
    "YALOVA":"Marmara","YOZGAT":"Ic Anadolu","ZONGULDAK":"Karadeniz",
}


def get_conn():
    return pyodbc.connect(CONN_STR)


def bulk_insert(cur, table, columns, rows):
    """Satir satir INSERT - SQL Server'da execute_values yok."""
    placeholders = ", ".join(["?"] * len(columns))
    col_str = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})"
    cur.executemany(sql, rows)


def import_provinces(conn, df):
    cur = conn.cursor()
    iller = df["province_norm"].unique()
    rows = []
    for norm in sorted(iller):
        pretty = norm.title()
        rows.append((pretty, norm, REGION_MAP.get(norm)))

    for row in rows:
        cur.execute("""
            IF NOT EXISTS (SELECT 1 FROM provinces WHERE name_norm = ?)
            INSERT INTO provinces (name, name_norm, region) VALUES (?, ?, ?)
        """, row[1], row[0], row[1], row[2])
    conn.commit()

    cur.execute("SELECT id, name_norm FROM provinces")
    prov_map = {row[1]: row[0] for row in cur.fetchall()}
    cur.close()
    print(f"  provinces: {len(prov_map)} il")
    return prov_map


def import_yield(conn, df, prov_map):
    cur = conn.cursor()
    for _, r in df.iterrows():
        pid = prov_map.get(r["province_norm"])
        if not pid or pd.isna(r.get("yield_kg_dekar")):
            continue
        cur.execute("""
            IF EXISTS (SELECT 1 FROM yield_observations WHERE province_id=? AND harvest_year=?)
                UPDATE yield_observations SET yield_kg_dekar=? WHERE province_id=? AND harvest_year=?
            ELSE
                INSERT INTO yield_observations (province_id, harvest_year, yield_kg_dekar)
                VALUES (?, ?, ?)
        """, pid, int(r["harvest_year"]),
             float(r["yield_kg_dekar"]), pid, int(r["harvest_year"]),
             pid, int(r["harvest_year"]), float(r["yield_kg_dekar"]))
    conn.commit()
    cur.close()
    print(f"  yield_observations: yuklendi")


def import_meteo(conn, df, prov_map):
    cur = conn.cursor()
    meteo_cols = [
        "tmean","tmax_mean","tmin_mean","rain_sum","rad_mean","tmean_std",
        "tmax_p95","tmin_p05","hot_days_30","frost_days_0","dry_days_lt1mm",
        "mam_tmean","mam_tmax_mean","mam_tmin_mean","mam_rain_sum","mam_rad_mean",
        "mam_tmean_std","mam_tmax_p95","mam_tmin_p05","mam_hot_days_30",
        "mam_frost_days_0","mam_dry_days_lt1mm","gdd_season","gdd_mam","gdd_mean_day"
    ]
    count = 0
    for _, r in df.iterrows():
        pid = prov_map.get(r["province_norm"])
        if not pid:
            continue
        yr = int(r["harvest_year"])
        vals = [float(r[c]) if pd.notna(r.get(c)) else None for c in meteo_cols]
        set_str = ", ".join(f"{c}=?" for c in meteo_cols)
        col_str = ", ".join(meteo_cols)
        ph = ", ".join(["?"] * len(meteo_cols))
        cur.execute(f"""
            IF EXISTS (SELECT 1 FROM meteo_features WHERE province_id=? AND harvest_year=?)
                UPDATE meteo_features SET {set_str} WHERE province_id=? AND harvest_year=?
            ELSE
                INSERT INTO meteo_features (province_id, harvest_year, {col_str})
                VALUES (?, ?, {ph})
        """, pid, yr, *vals, pid, yr, pid, yr, *vals)
        count += 1
    conn.commit()
    cur.close()
    print(f"  meteo_features: {count} kayit")


def import_modis(conn, df, prov_map):
    cur = conn.cursor()
    modis_cols = ["ndvi_auc","ndvi_max","ndvi_mean","evi_max","evi_mean"]
    count = 0
    for _, r in df.iterrows():
        pid = prov_map.get(r["province_norm"])
        if not pid:
            continue
        yr = int(r["harvest_year"])
        vals = [float(r[c]) if pd.notna(r.get(c)) else None for c in modis_cols]
        set_str = ", ".join(f"{c}=?" for c in modis_cols)
        col_str = ", ".join(modis_cols)
        ph = ", ".join(["?"] * len(modis_cols))
        cur.execute(f"""
            IF EXISTS (SELECT 1 FROM modis_features WHERE province_id=? AND harvest_year=?)
                UPDATE modis_features SET {set_str} WHERE province_id=? AND harvest_year=?
            ELSE
                INSERT INTO modis_features (province_id, harvest_year, {col_str})
                VALUES (?, ?, {ph})
        """, pid, yr, *vals, pid, yr, pid, yr, *vals)
        count += 1
    conn.commit()
    cur.close()
    print(f"  modis_features: {count} kayit")


def import_soil(conn, df_soil, prov_map):
    cur = conn.cursor()
    soil_cols = ["soil_clay","soil_sand","soil_silt","soil_soc","soil_phh2o","soil_bdod","soil_cec"]
    count = 0
    for _, r in df_soil.iterrows():
        pid = prov_map.get(r["province_norm"])
        if not pid:
            continue
        vals = [float(r[c]) if pd.notna(r.get(c)) else None for c in soil_cols]
        set_str = ", ".join(f"{c}=?" for c in soil_cols)
        col_str = ", ".join(soil_cols)
        ph = ", ".join(["?"] * len(soil_cols))
        cur.execute(f"""
            IF EXISTS (SELECT 1 FROM soil_features WHERE province_id=?)
                UPDATE soil_features SET {set_str} WHERE province_id=?
            ELSE
                INSERT INTO soil_features (province_id, {col_str})
                VALUES (?, {ph})
        """, pid, *vals, pid, pid, *vals)
        count += 1
    conn.commit()
    cur.close()
    print(f"  soil_features: {count} kayit")


def import_model_versions(conn):
    cur = conn.cursor()
    versions = [
        ("v1", "Hava + NDVI",           0.538, 59.5, 46.3, 0.679, 45.8, 36.1, 27, "Ridge", "2005-2019", "2020-2024"),
        ("v2", "Hava + NDVI + Toprak",  0.552, 58.6, 45.5, 0.705, 43.8, 34.3, 34, "Ridge", "2005-2019", "2020-2024"),
        ("v3", "Hava + NDVI + Toprak + GDD + LaggedYield", 0.608, 54.8, 41.9, 0.732, 41.6, 32.2, 39, "Ridge", "2005-2019", "2020-2024"),
    ]
    for v in versions:
        cur.execute("""
            IF NOT EXISTS (SELECT 1 FROM model_versions WHERE version_name=?)
            INSERT INTO model_versions
              (version_name, description, r2_holdout, rmse_holdout, mae_holdout,
               r2_cv, rmse_cv, mae_cv, feature_count, algorithm, train_years, holdout_years)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, v[0], *v)
    conn.commit()
    cur.close()
    print(f"  model_versions: {len(versions)} versiyon")


def import_predictions(conn, df, prov_map):
    cur = conn.cursor()
    cur.execute("SELECT MAX(id) FROM model_versions")
    mv_id = cur.fetchone()[0]

    target_col = "GradientBoosting" if "GradientBoosting" in df.columns else "Ridge"
    count = 0
    for _, r in df.iterrows():
        pid = prov_map.get(r["province_norm"])
        if not pid or pd.isna(r.get(target_col)):
            continue
        yr = int(r["harvest_year"])
        actual = float(r["yield_kg_dekar"]) if pd.notna(r.get("yield_kg_dekar")) else None
        pred   = float(r[target_col])
        err    = round(actual - pred, 2) if actual else None
        errpct = round((err / actual) * 100, 2) if actual and actual != 0 else None
        cur.execute("""
            IF EXISTS (SELECT 1 FROM model_predictions WHERE province_id=? AND harvest_year=? AND model_version_id=?)
                UPDATE model_predictions
                SET predicted_yield=?, actual_yield=?, error_kg=?, error_pct=?
                WHERE province_id=? AND harvest_year=? AND model_version_id=?
            ELSE
                INSERT INTO model_predictions
                  (province_id, harvest_year, model_version_id, predicted_yield, actual_yield, error_kg, error_pct)
                VALUES (?,?,?,?,?,?,?)
        """, pid, yr, mv_id, pred, actual, err, errpct, pid, yr, mv_id,
             pid, yr, mv_id, pred, actual, err, errpct)
        count += 1
    conn.commit()
    cur.close()
    print(f"  model_predictions: {count} kayit")


def main():
    print("CSV dosyalari yukleniyor...")
    df_v3   = pd.read_csv(BASE_DIR / "result/datasets/dataset_model_v3.csv")
    df_soil = pd.read_csv(BASE_DIR / "result/features/soil_features.csv")
    df_pred = pd.read_csv(BASE_DIR / "result/predictions/predictions_v3.csv")

    for d in [df_v3, df_soil, df_pred]:
        if "province_norm" in d.columns:
            d["province_norm"] = d["province_norm"].apply(normalize_province_name)

    print("\nSQL Server'a baglaniliyor...")
    conn = get_conn()
    print("Baglanti OK\n")

    print("Veri yukleniyor:")
    prov_map = import_provinces(conn, df_v3)
    import_yield(conn, df_v3, prov_map)
    import_meteo(conn, df_v3, prov_map)
    import_modis(conn, df_v3, prov_map)
    import_soil(conn, df_soil, prov_map)
    import_model_versions(conn)
    import_predictions(conn, df_pred, prov_map)

    conn.close()
    print("\nTum veriler yuklendi!")

    # Dogrulama
    conn2 = get_conn()
    cur = conn2.cursor()
    for tablo in ["provinces","yield_observations","meteo_features",
                  "modis_features","soil_features","model_versions","model_predictions"]:
        cur.execute(f"SELECT COUNT(*) FROM {tablo}")
        print(f"  {tablo}: {cur.fetchone()[0]} kayit")
    cur.close()
    conn2.close()


if __name__ == "__main__":
    main()
