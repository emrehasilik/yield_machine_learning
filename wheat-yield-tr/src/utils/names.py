import re
import unicodedata

ALIASES = {
    "AFYON": "AFYONKARAHISAR",
    "ICEL": "MERSIN",
    "K MARAS": "KAHRAMANMARAS",
    "K.MARAS": "KAHRAMANMARAS",
}

def normalize_province_name(s: str) -> str:
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper().replace("İ", "I")
    s = re.sub(r"[^A-Z ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIASES.get(s, s)
