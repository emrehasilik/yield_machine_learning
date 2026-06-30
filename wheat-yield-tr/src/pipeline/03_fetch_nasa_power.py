# src/03_fetch_nasa_power.py
import json
import random
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests
from shapely.geometry import shape, Point

from utils.names import normalize_province_name

BASE_DIR = Path(__file__).resolve().parents[2]

GEOJSON_PATH = BASE_DIR / "data" / "raw" / "provinces.geojson"
OUT_DIR      = BASE_DIR / "result" / "features"
CACHE_DIR    = BASE_DIR / "cache" / "nasa_cache_points"
POINTS_PATH  = BASE_DIR / "result" / "features" / "nasa_points.csv"

POWER_PARAMS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN"]
COMMUNITY = "AG"

START_DATE = "20041001"
END_DATE   = "20240731"

N_POINTS_PER_PROVINCE = 5
RANDOM_SEED = 42

SLEEP_BETWEEN_CALLS_SEC = 0.35
TIMEOUT_SEC = 60
MAX_RETRIES = 5

def load_provinces(geojson_path: Path):
    with geojson_path.open("r", encoding="utf-8") as f:
        gj = json.load(f)
    feats = gj.get("features", [])
    if not feats:
        raise RuntimeError("GeoJSON içinde features yok/boş görünüyor.")

    provinces = []
    for fea in feats:
        props = fea.get("properties", {})
        geom = fea.get("geometry")
        if not geom:
            continue
        name = props.get("ADM1_NAME") or props.get("name") or props.get("province")
        if not name:
            continue
        provinces.append({
            "province": name,
            "province_norm": normalize_province_name(name),
            "adm1_code": props.get("ADM1_CODE"),
            "geometry": shape(geom),
        })
    return provinces

def sample_points_in_geometry(geom, n: int, rng: random.Random):
    minx, miny, maxx, maxy = geom.bounds
    pts = []
    attempts = 0
    while len(pts) < n and attempts < 50000:
        attempts += 1
        x = rng.uniform(minx, maxx)
        y = rng.uniform(miny, maxy)
        p = Point(x, y)
        # contains yerine covers: sınırdaki noktaları dışlamaz
        if geom.covers(p):
            pts.append(p)
    if len(pts) < n:
        raise RuntimeError(f"Geometri içinde yeterli nokta üretilemedi. Üretilen={len(pts)}/{n}")
    return pts

def fetch_power_daily_point(lat: float, lon: float):
    base = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": ",".join(POWER_PARAMS),
        "community": COMMUNITY,
        "longitude": f"{lon:.5f}",
        "latitude": f"{lat:.5f}",
        "start": START_DATE,
        "end": END_DATE,
        "format": "JSON",
    }

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(base, params=params, timeout=TIMEOUT_SEC)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            sleep_s = min(8, 0.8 * (2 ** (attempt - 1)))
            time.sleep(sleep_s)

    raise RuntimeError(f"NASA POWER API başarısız. lat={lat}, lon={lon}. Son hata: {last_err}")

def power_json_to_df(power_json):
    try:
        param_block = power_json["properties"]["parameter"]
    except KeyError:
        raise RuntimeError("Beklenen JSON yapısı yok. Yanıtı kontrol et.")

    date_keys = None
    for p in POWER_PARAMS:
        keys = set(param_block[p].keys())
        date_keys = keys if date_keys is None else date_keys.intersection(keys)

    dates = sorted(date_keys)
    rows = []
    for d in dates:
        row = {"date": datetime.strptime(d, "%Y%m%d").date().isoformat()}
        for p in POWER_PARAMS:
            row[p] = param_block[p].get(d)
        rows.append(row)
    return pd.DataFrame(rows)

def cache_key(prov_norm: str, point_id: int):
    safe = "".join(ch if ch.isalnum() else "_" for ch in prov_norm)
    return CACHE_DIR / f"{safe}_pt{point_id}.csv"

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    provinces = load_provinces(GEOJSON_PATH)
    print(f"Provinces loaded: {len(provinces)}")

    rng = random.Random(RANDOM_SEED)

    all_prov_frames = []
    points_rows = []

    for pi, prov in enumerate(provinces, start=1):
        prov_name = prov["province"]
        prov_norm = prov["province_norm"]
        geom = prov["geometry"]

        print(f"\n[{pi}/{len(provinces)}] Province: {prov_name}")

        points = sample_points_in_geometry(geom, N_POINTS_PER_PROVINCE, rng)

        point_dfs = []
        for j, p in enumerate(points, start=1):
            lat, lon = p.y, p.x
            ck = cache_key(prov_norm, j)

            points_rows.append({
                "province": prov_name,
                "province_norm": prov_norm,
                "point_id": j,
                "lat": lat,
                "lon": lon,
            })

            if ck.exists():
                df_pt = pd.read_csv(ck)
                print(f"  - pt{j}: cache OK ({lat:.4f},{lon:.4f})")
            else:
                print(f"  - pt{j}: fetching ({lat:.4f},{lon:.4f})")
                power_json = fetch_power_daily_point(lat, lon)
                df_pt = power_json_to_df(power_json)
                # metadata: lat/lon
                df_pt["lat"] = lat
                df_pt["lon"] = lon
                df_pt.to_csv(ck, index=False, encoding="utf-8")
                time.sleep(SLEEP_BETWEEN_CALLS_SEC)

            df_pt["point_id"] = j
            point_dfs.append(df_pt)

        all_pts = pd.concat(point_dfs, ignore_index=True)

        # numeric cols
        for c in POWER_PARAMS:
            all_pts[c] = pd.to_numeric(all_pts[c], errors="coerce")

        prov_daily = all_pts.groupby("date", as_index=False)[POWER_PARAMS].mean()
        prov_daily["province"] = prov_name
        prov_daily["province_norm"] = prov_norm
        all_prov_frames.append(prov_daily)

    out = pd.concat(all_prov_frames, ignore_index=True)
    out_path = BASE_DIR / "result" / "features" / "nasa_power_daily_province.csv"
    out.to_csv(out_path, index=False, encoding="utf-8")

    pd.DataFrame(points_rows).to_csv(POINTS_PATH, index=False, encoding="utf-8")

    print(f"\nDONE ✅ Saved: {out_path}  | rows={len(out):,}")
    print(f"Points saved ✅: {POINTS_PATH}")

if __name__ == "__main__":
    main()
