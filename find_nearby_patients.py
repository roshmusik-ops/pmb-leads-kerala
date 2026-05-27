"""
Find local patients by scraping Google Maps reviewers of nearby hospitals.
People who review hospitals near Velupadam are clearly local patients.

Requires: GOOGLE_PLACES_API_KEY in environment.

Usage:
    set GOOGLE_PLACES_API_KEY=AIza...
    python find_nearby_patients.py
    python find_nearby_patients.py --radius-km 10
    python find_nearby_patients.py --keyword "hospital Thrissur"
"""
from __future__ import annotations
import argparse, csv, json, os, sys, time
from pathlib import Path
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Centre: Velupadam, Thrissur
LAT, LON = 10.5276, 76.2144

PLACES_NEARBY = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACES_DETAILS = "https://maps.googleapis.com/maps/api/place/details/json"
PLACES_SEARCH  = "https://maps.googleapis.com/maps/api/place/textsearch/json"

NEARBY_TYPES = ["hospital", "doctor", "pharmacy", "health"]


def nearby_places(lat: float, lon: float, radius_m: int, ptype: str, key: str) -> list[dict]:
    results = []
    params = {"location": f"{lat},{lon}", "radius": radius_m,
              "type": ptype, "key": key}
    while True:
        r = requests.get(PLACES_NEARBY, params=params, timeout=15)
        data = r.json()
        results.extend(data.get("results", []))
        token = data.get("next_page_token")
        if not token:
            break
        time.sleep(2)
        params = {"pagetoken": token, "key": key}
    return results


def place_details(place_id: str, key: str) -> dict:
    r = requests.get(PLACES_DETAILS, params={
        "place_id": place_id,
        "fields": "name,formatted_address,formatted_phone_number,reviews,rating,user_ratings_total",
        "key": key,
    }, timeout=15)
    return r.json().get("result", {})


def extract_reviewers(place: dict, details: dict) -> list[dict]:
    rows = []
    place_name = details.get("name") or place.get("name", "")
    address    = details.get("formatted_address", "")
    phone      = details.get("formatted_phone_number", "")
    reviews    = details.get("reviews") or []
    for rev in reviews:
        author = rev.get("author_name", "")
        profile = rev.get("author_url", "")
        text    = rev.get("text", "")
        rating  = rev.get("rating", "")
        rows.append({
            "reviewer_name": author,
            "reviewer_profile": profile,
            "reviewed_place": place_name,
            "place_address": address,
            "place_phone": phone,
            "review_text": text[:200],
            "review_rating": rating,
            "source": "Google Maps",
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radius-km", type=float, default=15,
                    help="Search radius in km from Velupadam (default 15)")
    ap.add_argument("--out", default="local_patients_maps.csv")
    args = ap.parse_args()

    key = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
    if not key:
        print("ERROR: set GOOGLE_PLACES_API_KEY environment variable.")
        sys.exit(1)

    radius_m = int(args.radius_km * 1000)
    print(f"Searching within {args.radius_km} km of Velupadam, Thrissur")

    all_places: dict[str, dict] = {}
    for ptype in NEARBY_TYPES:
        print(f"  -> {ptype} ...")
        places = nearby_places(LAT, LON, radius_m, ptype, key)
        for p in places:
            all_places[p["place_id"]] = p
        time.sleep(0.5)

    print(f"Found {len(all_places)} unique places. Fetching reviews...")

    all_rows = []
    for i, (pid, place) in enumerate(all_places.items(), 1):
        try:
            details = place_details(pid, key)
            rows = extract_reviewers(place, details)
            all_rows.extend(rows)
            total = details.get("user_ratings_total", 0)
            print(f"  [{i}/{len(all_places)}] {place.get('name','?')[:40]:40s} "
                  f"-> {len(rows)} reviewers ({total} total ratings)")
            time.sleep(0.15)
        except Exception as e:
            print(f"  [{i}] error: {e}")

    # dedupe by reviewer name + place
    seen = set()
    deduped = []
    for r in all_rows:
        key2 = f"{r['reviewer_name']}|{r['reviewed_place']}"
        if key2 not in seen:
            seen.add(key2)
            deduped.append(r)

    fields = ["reviewer_name","reviewer_profile","reviewed_place","place_address",
              "place_phone","review_text","review_rating","source"]
    out = Path(args.out)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(deduped)

    print(f"\nDone. {len(deduped)} local reviewers -> {out}")
    print("NOTE: These are people who visited nearby hospitals/clinics.")
    print("You can reach them via Google Maps message or recognise them as local patients.")


if __name__ == "__main__":
    main()
