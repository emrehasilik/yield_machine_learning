# src/02_prepare_tuik.py
import re
from pathlib import Path
import pandas as pd

from utils.names import normalize_province_name

BASE_DIR = Path(__file__).resolve().parents[2]

TUIK_PATH = BASE_DIR / "data" / "raw" / "tuik_wheat_yield.csv"
OUT_PATH  = BASE_DIR / "result" / "features" / "tuik_yield_long.csv"

def find_header_line(lines: list[str]):
    for i, line in enumerate(lines[:2000]):
        if "Adana-1" in line and "Ankara-6" in line:
            return i, line
    return None, None

def main():
    lines = TUIK_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    header_idx, header = find_header_line(lines)
    if header is None:
        raise RuntimeError("TÜİK header satırı bulunamadı (Adana-1/Ankara-6 arandı).")

    # Header'daki kolonları çıkar (boşları tamamen atmak yerine olduğu gibi tutmak daha güvenli;
    # ama burada iller zaten isimle yakalandığı için pratikte sorun olmaz.)
    raw_cols = [c.strip() for c in header.split("|")]
    # illerin başladığı index
    start_idx = None
    for i, c in enumerate(raw_cols):
        if c and c.strip().startswith("Adana-1"):
            start_idx = i
            break
    if start_idx is None:
        raise RuntimeError("Header içinde 'Adana-1' bulunamadı.")

    city_cols = [c.strip() for c in raw_cols[start_idx:] if c and c.strip()]

    # Yıllık veri satırları
    data_lines = []
    year_pat = re.compile(r"\b(19|20)\d{2}\b")
    for line in lines[header_idx+1:]:
        # satırda yıl geçiyorsa aday
        if year_pat.search(line):
            # ve pipe formatı varsa
            if "|" in line:
                data_lines.append(line)

    records = []
    for line in data_lines:
        parts = [p.strip() for p in line.split("|")]

        # satırdaki yılı bul
        year = None
        year_idx = None
        for idx, p in enumerate(parts[:50]):
            if re.fullmatch(r"(19|20)\d{2}", p):
                year = int(p)
                year_idx = idx
                break
        if year is None:
            continue

        vals = parts[year_idx+1: year_idx+1+len(city_cols)]
        if len(vals) < len(city_cols):
            vals += [None] * (len(city_cols) - len(vals))

        for c, v in zip(city_cols, vals):
            city = re.sub(r"-\d{1,2}$", "", c).strip()
            city_norm = normalize_province_name(city)

            yld = None
            if v is not None and str(v).strip() != "":
                try:
                    yld = float(str(v).replace(",", "."))
                except Exception:
                    yld = None

            if yld is None:
                continue

            records.append({
                "province": city,
                "province_norm": city_norm,
                "harvest_year": year,
                "yield_kg_dekar": yld
            })

    df = pd.DataFrame(records)
    if df.empty:
        raise RuntimeError("TÜİK long tablo boş çıktı. Dosya formatı farklı olabilir.")

    # İstersen GeoJSON 80 il ile kesişim yapacağız; burada Düzce hardcode yok.
    df["harvest_year"] = df["harvest_year"].astype(int)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8")

    print("Rows:", len(df))
    print("Years:", df["harvest_year"].min(), "-", df["harvest_year"].max())
    print("Provinces:", df["province_norm"].nunique())
    print("Saved:", OUT_PATH)

if __name__ == "__main__":
    main()
