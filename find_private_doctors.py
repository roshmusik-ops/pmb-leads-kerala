"""
Kerala Private Doctors & Clinics — Lead Finder
================================================
Finds private doctors, GPs, specialist clinics, nursing homes and
pharmacies in Kerala via OpenStreetMap Overpass API.

These are high-value Jan Aushadhi leads — doctors who can:
  - Prescribe generic medicines to their patients
  - Refer patients to Jan Aushadhi Kendra
  - Stock generic medicines (for nursing homes)

Output: leads_private_doctors.csv

Usage:
    python find_private_doctors.py                     # all Kerala
    python find_private_doctors.py --district Thrissur # one district
    python find_private_doctors.py --radius-km 20      # ~20km around Velupadam
"""
from __future__ import annotations
import argparse, csv, json, sys, time
from pathlib import Path
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
HEADERS = {"User-Agent": "kerala-health-leads/1.0 (janaushadhipound8873@gmail.com)",
           "Accept": "application/json"}

# Velupadam, Thrissur (approx centre)
VELUPADAM_LAT = 10.5276
VELUPADAM_LON = 76.2144


def build_query_kerala(district: str | None) -> str:
    if district:
        area = f'area["name"="{district}"]["admin_level"~"5|6"]->.area;'
    else:
        area = 'area["ISO3166-2"="IN-KL"]->.area;'
    return f"""[out:json][timeout:180];
{area}
(
  nwr["amenity"~"^(hospital|clinic|doctors|dentist|pharmacy)$"](area.area);
  nwr["healthcare"](area.area);
  nwr["amenity"="nursing_home"](area.area);
);
out center tags;
"""


def build_query_radius(lat: float, lon: float, km: float) -> str:
    r = int(km * 1000)
    return f"""[out:json][timeout:120];
(
  nwr["amenity"~"^(hospital|clinic|doctors|dentist|pharmacy)$"](around:{r},{lat},{lon});
  nwr["healthcare"](around:{r},{lat},{lon});
  nwr["amenity"="nursing_home"](around:{r},{lat},{lon});
);
out center tags;
"""


def call_overpass(query: str) -> dict:
    last_err = None
    for url in OVERPASS_ENDPOINTS:
        try:
            print(f"  -> {url}", flush=True)
            r = requests.post(url, data={"data": query}, headers=HEADERS, timeout=300)
            if r.status_code == 200:
                return r.json()
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
        time.sleep(3)
    raise RuntimeError(f"Overpass failed: {last_err}")


GOVT_KEYWORDS = (
    "government", "govt", "public", "nhm", "dhs", "esi", "taluk",
    "district hospital", "general hospital", "primary health", "community health",
    "family health", "medical college", "panchayat",
)

def is_govt(tags: dict) -> bool:
    op = (tags.get("operator") or "").lower()
    op_type = (tags.get("operator:type") or "").lower()
    name = (tags.get("name") or "").lower()
    if op_type in ("government", "public"):
        return True
    for kw in GOVT_KEYWORDS:
        if kw in op or kw in name:
            return True
    return False


def classify(tags: dict) -> str:
    name = (tags.get("name") or "").lower()
    amenity = tags.get("amenity", "")
    healthcare = tags.get("healthcare", "")
    spec = (tags.get("healthcare:speciality") or tags.get("speciality") or "").lower()

    if "nursing home" in name or amenity == "nursing_home":
        return "Nursing Home"
    if "dental" in name or "dentist" in name or amenity == "dentist":
        return "Dental Clinic"
    if "eye" in name or "ophthal" in name or "vision" in name:
        return "Eye Clinic"
    if "ortho" in name:
        return "Orthopaedic Clinic"
    if "cardio" in name or "heart" in name:
        return "Cardiology Clinic"
    if "diabeto" in name or "diabetes" in name or "endocrin" in name:
        return "Diabetes/Endocrinology Clinic"
    if "skin" in name or "derma" in name:
        return "Dermatology Clinic"
    if "children" in name or "paediat" in name or "pediatr" in name:
        return "Paediatric Clinic"
    if "maternity" in name or "gynaec" in name or "gynec" in name or "obstet" in name:
        return "Maternity/Gynaecology Clinic"
    if "ent" in name or "ear" in name or "nose" in name:
        return "ENT Clinic"
    if "neuro" in name:
        return "Neurology Clinic"
    if "cancer" in name or "oncol" in name:
        return "Cancer/Oncology Centre"
    if "pharmacy" in name or amenity == "pharmacy":
        return "Pharmacy"
    if spec:
        return f"Specialist Clinic ({spec.title()})"
    if amenity == "hospital":
        return "Private Hospital"
    if amenity in ("clinic", "doctors"):
        return "GP / Clinic"
    if healthcare:
        return healthcare.replace("_", " ").title()
    return "Clinic / Doctor"


def best_phone(tags: dict) -> str:
    for k in ("phone", "contact:phone", "contact:mobile", "mobile"):
        if tags.get(k):
            return tags[k].split(";")[0].strip()
    return ""


def best_email(tags: dict) -> str:
    for k in ("email", "contact:email"):
        if tags.get(k):
            return tags[k].split(";")[0].strip()
    return ""


def best_address(tags: dict) -> str:
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:village") or tags.get("addr:hamlet"),
        tags.get("addr:city") or tags.get("addr:town"),
        tags.get("addr:postcode"),
    ]
    return ", ".join(p for p in parts if p)


def element_to_row(el: dict) -> dict | None:
    tags = el.get("tags", {})
    if is_govt(tags):
        return None   # skip govt — already in the other CSV
    name = tags.get("name") or tags.get("official_name") or ""
    if not name:
        return None   # skip unnamed
    lat = el.get("lat") or el.get("center", {}).get("lat")
    lon = el.get("lon") or el.get("center", {}).get("lon")
    return {
        "name": name,
        "type": classify(tags),
        "district": tags.get("addr:district") or tags.get("is_in:district") or "",
        "address": best_address(tags),
        "phone": best_phone(tags),
        "email": best_email(tags),
        "website": tags.get("website") or tags.get("contact:website") or "",
        "operator": tags.get("operator") or "",
        "opening_hours": tags.get("opening_hours") or "",
        "speciality": tags.get("healthcare:speciality") or tags.get("speciality") or "",
        "lat": lat,
        "lon": lon,
        "osm_id": f"{el.get('type')}/{el.get('id')}",
        "source": "OpenStreetMap",
    }


def dedupe(rows: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for r in rows:
        try:
            grid = f"{round(float(r['lat']), 3)},{round(float(r['lon']), 3)}"
        except (TypeError, ValueError):
            grid = ""
        key = f"{r['name'].lower().strip()}|{grid}"
        if key not in seen or sum(1 for v in r.values() if v) > sum(1 for v in seen[key].values() if v):
            seen[key] = r
    return list(seen.values())


FIELDS = ["name", "type", "district", "address", "phone", "email",
          "website", "operator", "opening_hours", "speciality",
          "lat", "lon", "osm_id", "source"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--district", help="Kerala district name e.g. Thrissur")
    ap.add_argument("--radius-km", type=float, default=0,
                    help="Search within this km radius of Velupadam (overrides --district)")
    ap.add_argument("--out", default="leads_private_doctors.csv")
    args = ap.parse_args()

    print("Kerala Private Doctors & Clinics — Lead Finder")
    print("=" * 50)

    if args.radius_km > 0:
        print(f"Radius: {args.radius_km} km around Velupadam, Thrissur")
        query = build_query_radius(VELUPADAM_LAT, VELUPADAM_LON, args.radius_km)
    else:
        print(f"District: {args.district or 'ALL Kerala'}")
        query = build_query_kerala(args.district)

    print()
    t0 = time.time()
    data = call_overpass(query)
    elements = data.get("elements", [])
    print(f"  raw elements: {len(elements)} in {time.time()-t0:.1f}s")

    rows = [r for el in elements if (r := element_to_row(el)) is not None]
    rows = dedupe(rows)
    rows.sort(key=lambda r: (r["district"] or "zzz", r["name"].lower()))

    out = Path(args.out)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    with_phone = sum(1 for r in rows if r["phone"])
    with_email = sum(1 for r in rows if r["email"])
    from collections import Counter
    by_type = Counter(r["type"] for r in rows)

    print(f"\nDone. {len(rows)} private doctors/clinics -> {out}")
    print(f"  {with_phone} with phone, {with_email} with email")
    print("\nBreakdown by type:")
    for t, n in by_type.most_common(20):
        print(f"  {n:5d}  {t}")

    print(f"\nNext: python enrich_phones.py {out.name}")


if __name__ == "__main__":
    main()
