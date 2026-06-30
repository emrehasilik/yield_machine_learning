import json
import re
import unicodedata
from pathlib import Path

geo_path = Path("data/raw/provinces.geojson")
tuik_path = Path("data/raw/tuik_wheat_yield.csv")

GEO_NAME_KEY = "ADM1_NAME"

# GAUL -> TÜİK isim eşleştirme düzeltmeleri (en kritik 2 tane)
ALIASES = {
    "ICEL": "MERSIN",
    "K MARAS": "KAHRAMANMARAS",
    "K MARAS ": "KAHRAMANMARAS",
    "K.MARAS": "KAHRAMANMARAS",
    "K.MARAS ": "KAHRAMANMARAS",
}

def normalize_name(s: str) -> str:
    """
    İstanbul -> ISTANBUL, Şanlıurfa -> SANLIURFA
    Nokta, tire, boşluk farklarını temizler.
    """
    s = str(s).strip()

    # İl kolonlarında Adana-1 gibi plaka varsa at
    s = re.sub(r"-\d{1,2}$", "", s).strip()

    # Türkçe karakterleri sadeleştir
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    # Büyük harf, noktalama sadeleştirme
    s = s.upper()
    s = s.replace("İ", "I")  # bazen normalize sonrası kalabiliyor
    s = re.sub(r"[^A-Z ]+", " ", s)  # nokta, virgül vs -> boşluk
    s = re.sub(r"\s+", " ", s).strip()

    # GAUL kısaltmalarını düzelt
    s = ALIASES.get(s, s)

    return s

# --- GeoJSON illeri ---
with geo_path.open("r", encoding="utf-8") as f:
    d = json.load(f)

features = d.get("features", [])
if not features:
    raise RuntimeError("GeoJSON boş.")

geo_raw = [fea["properties"].get(GEO_NAME_KEY) for fea in features]
geo = {normalize_name(x) for x in geo_raw if x}

# --- TÜİK header satırından illeri çek ---
raw_lines = tuik_path.read_text(encoding="utf-8", errors="ignore").splitlines()

header = None
for line in raw_lines[:500]:
    if "Adana-1" in line and "Ankara-6" in line:
        header = line
        break
if header is None:
    raise RuntimeError("TÜİK header satırı bulunamadı. Dosyanın başını kontrol et.")

cols = [c.strip() for c in header.split("|") if c.strip()]

# Gereksiz kolonları at
cols = [c for c in cols if not c.startswith("Unnamed") and c not in {"Satırlar", "Sütunlar"}]

tuik = {normalize_name(c) for c in cols}

only_geo = sorted(geo - tuik)
only_tuik = sorted(tuik - geo)

print("GeoJSON il sayısı (norm):", len(geo))
print("TÜİK il sayısı (norm):", len(tuik))

print("\nGeoJSON'da var, TÜİK'te yok (isim):", only_geo)
print("\nTÜİK'te var, GeoJSON'da yok (isim):", only_tuik)

Path("result").mkdir(parents=True, exist_ok=True)
Path("result/diff_geo_vs_tuik_names.txt").write_text(
    "GeoJSON'da var, TÜİK'te yok:\n" + "\n".join(only_geo) +
    "\n\nTÜİK'te var, GeoJSON'da yok:\n" + "\n".join(only_tuik),
    encoding="utf-8"
)
print("\nKaydedildi: result/diff_geo_vs_tuik_names.txt")
