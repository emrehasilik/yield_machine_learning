import json
import random
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests
from shapely.geometry import shape, Point

# -----------------------------
# AYARLAR
# -----------------------------
GEOJSON_PATH = Path("data/raw/provinces.geojson")
OUT_DIR = Path("result")
CACHE_DIR = OUT_DIR / "nasa_cache_points"

# NASA POWER parametreleri (AG community tarım için uygun)
POWER_PARAMS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN"]
COMMUNITY = "AG"

# Tüm hasat sezonlarını kapsayacak tarih aralığı (2005-2024 hasat yılları için)
START_DATE = "20041001"  # 2005 hasat yılı sezonu: 2004-10-01 başlar
END_DATE   = "20240731"

N_POINTS_PER_PROVINCE = 5
RANDOM_SEED = 42

# Request davranışı
SLEEP_BETWEEN_CALLS_SEC = 0.35
TIMEOUT_SEC = 60
MAX_RETRIES = 5


# -----------------------------
# YARDIMCI: isim normalize (sonraki join için işine yarar)
# -----------------------------
def normalize_name(s: str) -> str:
    s = str(s).strip()
    s = s.replace("İ", "I").replace("ı", "i")
    # çok temel normalize; istersek sonra genişletiriz
    return s


# -----------------------------
# GeoJSON oku
# -----------------------------
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
        provinces.append({
            "name": props.get("ADM1_NAME"),
            "name_norm": normalize_name(props.get("ADM1_NAME")),
            "adm1_code": props.get("ADM1_CODE"),
            "geometry": shape(geom),
        })
    return provinces


# -----------------------------
# Poligon içinde rastgele nokta üret (seed'li)
# -----------------------------
def sample_points_in_geometry(geom, n: int, rng: random.Random):
    # geom: Polygon veya MultiPolygon olabilir
    minx, miny, maxx, maxy = geom.bounds
    points = []
    attempts = 0
    # çok karmaşık geometrilerde biraz deneme gerekir
    while len(points) < n and attempts < 20000:
        attempts += 1
        x = rng.uniform(minx, maxx)
        y = rng.uniform(miny, maxy)
        p = Point(x, y)
        if geom.contains(p):
            points.append(p)

    if len(points) < n:
        raise RuntimeError(f"Geometri içinde yeterli nokta üretilemedi. Üretilen={len(points)}/{n}")
    return points


# -----------------------------
# NASA POWER API çağrısı (tek nokta, daily)
# -----------------------------
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
            data = r.json()
            return data
        except Exception as e:
            last_err = e
            # exponential backoff
            sleep_s = min(8, 0.8 * (2 ** (attempt - 1)))
            time.sleep(sleep_s)

    raise RuntimeError(f"NASA POWER API başarısız. lat={lat}, lon={lon}. Son hata: {last_err}")


def power_json_to_df(power_json):
    """
    Çıktı:
    date (YYYY-MM-DD), T2M, T2M_MAX, ... sütunları
    """
    try:
        param_block = power_json["properties"]["parameter"]
    except KeyError:
        raise RuntimeError("Beklenen JSON yapısı yok. Yanıtı kontrol et.")

    # Her param için {YYYYMMDD: value} dict var
    # Tarihlerin kesişimini al
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


def cache_key(prov_name_norm: str, idx: int):
    safe = "".join(ch if ch.isalnum() else "_" for ch in prov_name_norm)
    return CACHE_DIR / f"{safe}_pt{idx}.csv"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    provinces = load_provinces(GEOJSON_PATH)
    print(f"Provinces loaded: {len(provinces)}")

    rng = random.Random(RANDOM_SEED)

    province_daily_frames = []

    for pi, prov in enumerate(provinces, start=1):
        prov_name = prov["name"]
        prov_name_norm = prov["name_norm"]
        geom = prov["geometry"]

        print(f"\n[{pi}/{len(provinces)}] Province: {prov_name}")

        # 5 nokta üret
        points = sample_points_in_geometry(geom, N_POINTS_PER_PROVINCE, rng)

        point_dfs = []
        for j, p in enumerate(points, start=1):
            lat, lon = p.y, p.x
            ck = cache_key(prov_name_norm, j)

            if ck.exists():
                df_pt = pd.read_csv(ck)
                print(f"  - pt{j}: cache OK ({lat:.4f},{lon:.4f})")
            else:
                print(f"  - pt{j}: fetching ({lat:.4f},{lon:.4f})")
                power_json = fetch_power_daily_point(lat, lon)
                df_pt = power_json_to_df(power_json)
                df_pt.to_csv(ck, index=False, encoding="utf-8")
                time.sleep(SLEEP_BETWEEN_CALLS_SEC)

            # point id ekle
            df_pt["point_id"] = j
            point_dfs.append(df_pt)

        # 5 noktanın günlük ortalaması (il günlük seri)
        all_pts = pd.concat(point_dfs, ignore_index=True)
        # sayısal kolonlar
        num_cols = [c for c in POWER_PARAMS]
        prov_daily = (
            all_pts.groupby("date", as_index=False)[num_cols]
            .mean()
        )
        prov_daily["province"] = prov_name
        prov_daily["province_norm"] = prov_name_norm

        province_daily_frames.append(prov_daily)

    # tüm illeri birleştir
    out = pd.concat(province_daily_frames, ignore_index=True)
    out_path = OUT_DIR / "nasa_power_daily_province.csv"
    out.to_csv(out_path, index=False, encoding="utf-8")
    print(f"\nDONE ✅ Saved: {out_path}  | rows={len(out):,}")


if __name__ == "__main__":
    main()
