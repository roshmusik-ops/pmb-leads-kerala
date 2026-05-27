"""
Kerala Govt Health Centres — Lead Finder
=========================================
Pulls every government-operated health facility in Kerala from OpenStreetMap
(via the Overpass API) and writes a clean leads CSV ready for outreach.

Output: leads_kerala_health.csv
Columns: name, type, district, sub_district, address, phone, email, website,
         operator, lat, lon, osm_id, source

Usage:
    python find_health_centres.py                  # all of Kerala
    python find_health_centres.py --district Thrissur
    python find_health_centres.py --out my.csv
    python find_health_centres.py --include-private  # also list private hospitals

No API key required. Run-time: ~30-90 seconds depending on Overpass load.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import requests

# Force UTF-8 output on Windows consoles (cp1252 default chokes on arrows/check-marks)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]

# Tags that mark a feature as government-operated
GOVT_OPERATOR_REGEX = (
    r"government|govt|public|state|kerala|gok|ministry|nhm|"
    r"directorate|dhs|esi|railway|defence|military|central|"
    r"municipal|panchayat|corporation|district"
)

HEALTH_AMENITIES = ["hospital", "clinic", "doctors", "pharmacy"]
HEALTHCARE_TAGS = ["hospital", "clinic", "doctor", "centre", "health_post", "dispensary"]


def build_query(district: str | None, include_private: bool) -> str:
    area = (
        f'area["name"="{district}"]["admin_level"~"5|6"]["ISO3166-2"!~".*"]->.area;\n'
        f'area["ISO3166-2"="IN-KL"]->.kerala;\n'
        if district
        else 'area["ISO3166-2"="IN-KL"]->.area;\n'
    )

    if include_private:
        # No operator filter — every health facility in the area
        body = """(
  nwr["amenity"~"^(hospital|clinic|doctors|pharmacy)$"](area.area);
  nwr["healthcare"](area.area);
);"""
    else:
        body = f"""(
  nwr["amenity"~"^(hospital|clinic|doctors|pharmacy)$"]["operator:type"~"government|public"](area.area);
  nwr["amenity"~"^(hospital|clinic|doctors|pharmacy)$"]["operator"~"{GOVT_OPERATOR_REGEX}",i](area.area);
  nwr["healthcare"]["operator:type"~"government|public"](area.area);
  nwr["healthcare"]["operator"~"{GOVT_OPERATOR_REGEX}",i](area.area);
  nwr["amenity"~"^(hospital|clinic|doctors)$"]["name"~"government|govt|district|taluk|general|primary health|community health|family health|PHC|CHC|FHC|govt\\.|medical college",i](area.area);
);"""

    return f"""[out:json][timeout:180];
{area}
{body}
out center tags;
"""


def call_overpass(query: str) -> dict:
    headers = {
        "User-Agent": "kerala-health-leads/1.0 (contact: janaushadhipound8873@gmail.com)",
        "Accept": "application/json",
    }
    last_err = None
    for url in OVERPASS_ENDPOINTS:
        try:
            print(f"  -> querying {url} ...", flush=True)
            r = requests.post(url, data={"data": query}, headers=headers, timeout=300)
            if r.status_code == 200:
                return r.json()
            print(f"    HTTP {r.status_code}: {r.text[:200]}", flush=True)
            last_err = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:
            print(f"    error: {e}", flush=True)
            last_err = str(e)
        time.sleep(3)
    raise RuntimeError(f"All Overpass endpoints failed: {last_err}")


def classify(tags: dict) -> str:
    """Best-guess facility type from name + tags."""
    name = (tags.get("name") or "").lower()
    amenity = tags.get("amenity", "")
    healthcare = tags.get("healthcare", "")

    if "medical college" in name:
        return "Medical College"
    if "district hospital" in name or " dh " in f" {name} ":
        return "District Hospital"
    if "taluk" in name or "taluq" in name:
        return "Taluk Hospital"
    if "general hospital" in name:
        return "General Hospital"
    if "women" in name or "w&c" in name or "maternity" in name:
        return "Women & Children Hospital"
    if "community health" in name or "chc" in name:
        return "Community Health Centre (CHC)"
    if "family health" in name or "fhc" in name:
        return "Family Health Centre (FHC)"
    if "primary health" in name or "phc" in name:
        return "Primary Health Centre (PHC)"
    if "ayurveda" in name or "ayurvedic" in name:
        return "Ayurveda Hospital/Dispensary"
    if "homoeo" in name or "homeo" in name:
        return "Homoeopathy Hospital/Dispensary"
    if "siddha" in name:
        return "Siddha Centre"
    if "unani" in name:
        return "Unani Centre"
    if "veterinary" in name:
        return "Veterinary Hospital"
    if "dispensary" in name:
        return "Govt Dispensary"
    if amenity == "pharmacy" or "jan aushadhi" in name or "janaushadhi" in name:
        return "Pharmacy / Jan Aushadhi"
    if amenity == "hospital" or healthcare == "hospital":
        return "Hospital"
    if amenity == "clinic" or healthcare == "clinic":
        return "Clinic"
    if amenity == "doctors":
        return "Doctor's Office"
    return (healthcare or amenity or "Health Facility").title()


def best_address(tags: dict) -> str:
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:village") or tags.get("addr:hamlet"),
        tags.get("addr:city") or tags.get("addr:town"),
        tags.get("addr:district"),
        tags.get("addr:state"),
        tags.get("addr:postcode"),
    ]
    return ", ".join(p for p in parts if p)


def best_district(tags: dict) -> str:
    return (
        tags.get("addr:district")
        or tags.get("is_in:district")
        or ""
    )


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


def best_website(tags: dict) -> str:
    for k in ("website", "contact:website", "url"):
        if tags.get(k):
            return tags[k].strip()
    return ""


def element_to_row(el: dict) -> dict:
    tags = el.get("tags", {})
    lat = el.get("lat") or el.get("center", {}).get("lat")
    lon = el.get("lon") or el.get("center", {}).get("lon")
    return {
        "name": tags.get("name") or tags.get("official_name") or "(unnamed facility)",
        "type": classify(tags),
        "district": best_district(tags),
        "sub_district": tags.get("addr:subdistrict") or tags.get("is_in:subdistrict") or "",
        "address": best_address(tags),
        "phone": best_phone(tags),
        "email": best_email(tags),
        "website": best_website(tags),
        "operator": tags.get("operator") or tags.get("operator:type") or "",
        "lat": lat,
        "lon": lon,
        "osm_id": f"{el.get('type')}/{el.get('id')}",
        "source": "OpenStreetMap",
    }


def dedupe(rows: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for r in rows:
        # key by name + ~100m grid
        try:
            grid = f"{round(float(r['lat']), 3)},{round(float(r['lon']), 3)}"
        except (TypeError, ValueError):
            grid = ""
        key = f"{(r['name'] or '').lower().strip()}|{grid}"
        if key in seen:
            # prefer the row with more populated fields
            existing = seen[key]
            existing_score = sum(1 for v in existing.values() if v)
            new_score = sum(1 for v in r.values() if v)
            if new_score > existing_score:
                seen[key] = r
        else:
            seen[key] = r
    return list(seen.values())


def main():
    ap = argparse.ArgumentParser(description="Find Kerala govt health centre leads")
    ap.add_argument("--district", help="Restrict to one district (e.g. Thrissur)")
    ap.add_argument("--out", default="leads_kerala_health.csv", help="Output CSV path")
    ap.add_argument("--include-private", action="store_true",
                    help="Also include private hospitals/clinics")
    ap.add_argument("--include-ayush", action="store_true",
                    help="Include Ayurveda / Homoeopathy / Siddha / Unani / Veterinary "
                         "(default: allopathic only)")
    ap.add_argument("--raw", help="Also save raw Overpass JSON to this path")
    args = ap.parse_args()

    print("Kerala Govt Health Centres — Lead Finder")
    print("=" * 50)
    print(f"District filter : {args.district or 'ALL Kerala'}")
    print(f"Include private : {args.include_private}")
    print(f"Output CSV      : {args.out}")
    print()

    query = build_query(args.district, args.include_private)
    print("Overpass query:")
    print(query)
    print()

    t0 = time.time()
    data = call_overpass(query)
    elements = data.get("elements", [])
    print(f"  ✓ {len(elements)} raw elements in {time.time()-t0:.1f}s")

    if args.raw:
        Path(args.raw).write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"  ✓ raw JSON saved to {args.raw}")

    rows = [element_to_row(el) for el in elements]
    rows = dedupe(rows)

    if not args.include_ayush:
        excluded = ("Ayurveda", "Homoeopathy", "Siddha", "Unani", "Veterinary")
        before = len(rows)
        rows = [
            r for r in rows
            if not any(x in r["type"] for x in excluded)
            and not any(x.lower() in (r["name"] or "").lower() for x in excluded + ("homeo",))
        ]
        print(f"  filtered out {before - len(rows)} AYUSH/Veterinary facilities "
              f"(use --include-ayush to keep them)")
    # sort: named first, then by district then name
    rows.sort(key=lambda r: (
        0 if r["name"] != "(unnamed facility)" else 1,
        r["district"] or "zzz",
        r["name"].lower(),
    ))

    fields = ["name", "type", "district", "sub_district", "address",
              "phone", "email", "website", "operator", "lat", "lon",
              "osm_id", "source"]

    out_path = Path(args.out)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # quick stats
    by_type: dict[str, int] = {}
    by_district: dict[str, int] = {}
    with_phone = 0
    with_email = 0
    for r in rows:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
        d = r["district"] or "(unknown)"
        by_district[d] = by_district.get(d, 0) + 1
        if r["phone"]:
            with_phone += 1
        if r["email"]:
            with_email += 1

    print()
    print(f"✅ wrote {len(rows)} leads → {out_path.resolve()}")
    print(f"   {with_phone} with phone, {with_email} with email")
    print()
    print("Breakdown by type:")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {n:5d}  {t}")
    print()
    print("Breakdown by district:")
    for d, n in sorted(by_district.items(), key=lambda x: -x[1])[:20]:
        print(f"  {n:5d}  {d}")

    print()
    print("Next:")
    print(f"  → Enrich phones via Google Places:  python enrich_phones.py {out_path.name}")
    print(f"  → Or open the CSV in Excel and start calling.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
