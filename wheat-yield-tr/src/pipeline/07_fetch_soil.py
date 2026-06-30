# src/07_fetch_soil.py
# SoilGrids WCS endpoint'inden il bazinda toprak ozellikleri ceker.
# Toprak statik oldugu icin her il icin bir kez cekilir, yila gore degismez.
# NASA POWER ile ayni nokta ornekleme mantigini kullanir (5 nokta, seed=42).
# WCS 1.0.0 + rasterio kullanilir (REST API bozuk, WCS stabil).

import json
import time
import random
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import rasterio
from shapely.geometry import shape, Point

from utils.names import normalize_province_name

BASE_DIR     = Path(__file__).resolve().parents[2]
GEOJSON_PATH = BASE_DIR / "data" / "raw" / "provinces.geojson"
OUT_PATH     = BASE_DIR / "result" / "features" / "soil_features.csv"
CACHE_DIR    = BASE_DIR / "cache" / "soil_cache_points"

N_POINTS  = 5
SEED      = 42
SLEEP_SEC = 0.3
TIMEOUT   = 25
MAX_RETRY = 4
BBOX_DEG  = 0.05   # nokta etrafinda +/- 0.05 derece (~5km)

WCS_BASE = "https://maps.isric.org/mapserv"

# (map_dosyasi, coverage_adi, olcek_bolu)
# SoilGrids WCS degerleri scaled: clay/sand/silt/bdod g/kg*10, soc dg/kg, phh2o pH*10, cec mmol/kg*10
SOIL_LAYERS = [
    ("clay",  "clay_0-5cm_mean",   10.0),   # -> g/kg (= %)
    ("sand",  "sand_0-5cm_mean",   10.0),
    ("silt",  "silt_0-5cm_mean",   10.0),
    ("soc",   "soc_0-5cm_mean",    10.0),   # -> dg/kg
    ("phh2o", "phh2o_0-5cm_mean",  10.0),   # -> pH
    ("bdod",  "bdod_0-5cm_mean",   100.0),  # -> cg/cm3 -> /100 = g/cm3
    ("cec",   "cec_0-5cm_mean",    10.0),   # -> mmol/kg
]


def load_provinces(path: Path):
    with path.open("r", encoding="utf-8") as f:
        gj = json.load(f)
    result = []
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        geom  = feat.get("geometry")
        if not geom:
            continue
        name = props.get("ADM1_NAME") or props.get("name") or props.get("province")
        if not name:
            continue
        result.append({
            "province":      name,
            "province_norm": normalize_province_name(name),
            "geometry":      shape(geom),
        })
    return result


def sample_points(geom, n: int, rng: random.Random):
    minx, miny, maxx, maxy = geom.bounds
    pts, attempts = [], 0
    while len(pts) < n and attempts < 50000:
        attempts += 1
        p = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
        if geom.covers(p):
            pts.append(p)
    if len(pts) < n:
        raise RuntimeError(f"Yeterli nokta uretilmedi: {len(pts)}/{n}")
    return pts


def wcs_fetch_value(map_name: str, coverage: str, lon: float, lat: float, scale: float) -> float | None:
    params = {
        "map":      f"/map/{map_name}.map",
        "SERVICE":  "WCS",
        "VERSION":  "1.0.0",
        "REQUEST":  "GetCoverage",
        "COVERAGE": coverage,
        "CRS":      "EPSG:4326",
        "BBOX":     f"{lon-BBOX_DEG},{lat-BBOX_DEG},{lon+BBOX_DEG},{lat+BBOX_DEG}",
        "WIDTH":    "5",
        "HEIGHT":   "5",
        "FORMAT":   "GEOTIFF_INT16",
    }
    last_err = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            r = requests.get(WCS_BASE, params=params, timeout=TIMEOUT)
            ct = r.headers.get("content-type", "")
            if not ct.startswith("image"):
                raise RuntimeError(f"Beklenmis image degil: {ct} | {r.text[:200]}")
            with rasterio.open(BytesIO(r.content)) as ds:
                arr = ds.read(1).astype(float)
                nd  = ds.nodata
                if nd is not None:
                    arr[arr == nd] = np.nan
                mean_val = float(np.nanmean(arr))
            return mean_val / scale if not np.isnan(mean_val) else None
        except Exception as e:
            last_err = e
            time.sleep(min(6, 0.8 * (2 ** (attempt - 1))))
    print(f"    WARN: {coverage} basarisiz ({last_err})")
    return None


def cache_path(prov_norm: str, prop: str) -> Path:
    safe = "".join(c if c.isalnum() else "_" for c in prov_norm)
    return CACHE_DIR / f"{safe}_{prop}.json"


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    provinces = load_provinces(GEOJSON_PATH)
    print(f"Toplam il: {len(provinces)}")

    rng = random.Random(SEED)
    rows = []

    for i, prov in enumerate(provinces, 1):
        name = prov["province"]
        norm = prov["province_norm"]
        geom = prov["geometry"]
        print(f"\n[{i}/{len(provinces)}] {name}")

        points = sample_points(geom, N_POINTS, rng)
        row = {"province_norm": norm, "province": name}

        for map_name, coverage, scale in SOIL_LAYERS:
            prop_key = f"soil_{map_name}"
            cp = cache_path(norm, map_name)

            if cp.exists():
                with cp.open("r") as f:
                    cached = json.load(f)
                row[prop_key] = cached.get("value")
                print(f"  {map_name}: cache OK -> {row[prop_key]}")
                continue

            vals = []
            for j, pt in enumerate(points, 1):
                val = wcs_fetch_value(map_name, coverage, pt.x, pt.y, scale)
                if val is not None:
                    vals.append(val)
                time.sleep(SLEEP_SEC)

            mean = float(np.mean(vals)) if vals else None
            row[prop_key] = mean

            with cp.open("w") as f:
                json.dump({"value": mean, "n_pts": len(vals)}, f)

            print(f"  {map_name}: {mean:.3f} ({len(vals)}/{N_POINTS} nokta)" if mean is not None else f"  {map_name}: veri yok")

        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8")
    print(f"\nKaydedildi: {OUT_PATH}  ({len(df)} il)")
    soil_cols = [f"soil_{m}" for m, _, _ in SOIL_LAYERS]
    print(df[["province_norm"] + soil_cols].describe())


if __name__ == "__main__":
    main()
