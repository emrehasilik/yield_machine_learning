import re
import unicodedata
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

TUIK_PATH = BASE_DIR / "data" / "raw" / "tuik_wheat_yield.csv"
OUT_PATH = BASE_DIR / "result" / "tuik_yield_long.csv"

# GeoJSON(GAUL) tarafındaki isimleri TÜİK ile aynı anahtara getiren alias'lar
ALIASES = {
    # Mersin
    "ICEL": "MERSIN",
    "MERSIN": "MERSIN",

    # Afyon
    "AFYON": "AFYONKARAHISAR",
    "AFYONKARAHISAR": "AFYONKARAHISAR",

    # Kahramanmaraş
    "K MARAS": "KAHRAMANMARAS",
    "K.MARAS": "KAHRAMANMARAS",
    "KAHRAMANMARAS": "KAHRAMANMARAS",
}

def normalize_name(s: str) -> str:
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper().replace("İ", "I")
    s = re.sub(r"[^A-Z ]+", " ", s)   # nokta, tire, vs temizle
    s = re.sub(r"\s+", " ", s).strip()
    s = ALIASES.get(s, s)
    return s

def find_header_line(lines):
    # TÜİK exportlarında illerin geçtiği satır
    for i, line in enumerate(lines[:1200]):
        if "Adana-1" in line and "Ankara-6" in line:
            return i, line
    return None, None

def main():
    lines = TUIK_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()

    header_idx, header = find_header_line(lines)
    if header is None:
        raise RuntimeError("TÜİK header satırı bulunamadı (Adana-1/Ankara-6 arandı).")

    cols = [c.strip() for c in header.split("|") if c.strip()]
    # Gereksiz kolonları at
    cols = [c for c in cols if c not in {"Satırlar", "Sütunlar"} and not c.startswith("Unnamed")]

    # İl kolonlarının başladığı yeri bul
    start_idx = None
    for i, c in enumerate(cols):
        if c.startswith("Adana-1"):
            start_idx = i
            break
    if start_idx is None:
        raise RuntimeError("Header içinde 'Adana-1' bulunamadı.")

    city_cols = cols[start_idx:]

    # Veri satırları: içinde |YYYY| geçen satırlar
    data_lines = []
    for line in lines[header_idx+1:]:
        if re.search(r"\|\s*(19|20)\d{2}\s*\|", line):
            data_lines.append(line)

    if not data_lines:
        raise RuntimeError("Yıllık veri satırları bulunamadı. Dosya formatı farklı olabilir.")

    records = []

    for line in data_lines:
        parts = [p.strip() for p in line.split("|")]

        # satırdaki yılı bul
        year = None
        year_idx = None
        for idx, p in enumerate(parts[:25]):
            if re.fullmatch(r"(19|20)\d{2}", p):
                year = int(p)
                year_idx = idx
                break
        if year is None:
            continue

        vals = parts[year_idx+1 : year_idx+1+len(city_cols)]

        # 🔥 kritik: kısa geldiyse satırı atlama, pad yap
        if len(vals) < len(city_cols):
            vals = vals + [None] * (len(city_cols) - len(vals))

        for c, v in zip(city_cols, vals):
            # "Kahramanmaraş-46" -> "Kahramanmaraş"
            city = re.sub(r"-\d{1,2}$", "", c).strip()
            city_norm = normalize_name(city)

            # Sayısal parse
            yld = None
            if v is not None and v != "":
                try:
                    yld = float(str(v).replace(",", "."))
                except:
                    yld = None

            records.append({
                "province": city,
                "province_norm": city_norm,
                "harvest_year": year,
                "yield_kg_dekar": yld
            })

    df = pd.DataFrame(records)

    # boş yield satırlarını at
    df = df.dropna(subset=["yield_kg_dekar"]).copy()
    df["harvest_year"] = df["harvest_year"].astype(int)

    # GeoJSON 80 il setiyle hizalama için Düzce'yi çıkar
    df = df[df["province_norm"] != "DUZCE"].copy()

    print("Rows:", len(df))
    print("Years:", df["harvest_year"].min(), "-", df["harvest_year"].max())
    print("Provinces:", df["province_norm"].nunique())

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8")
    print(f"DONE ✅ Saved: {OUT_PATH}")

if __name__ == "__main__":
    main()
