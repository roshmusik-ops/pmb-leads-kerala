"""
Fill `district` column by point-in-polygon against Kerala district boundaries.
Single Overpass call to fetch all 14 districts, then offline lookup. ~5 sec total.

Usage:
    python fill_districts.py leads_kerala_health.csv
"""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

POLY_CACHE = Path(__file__).with_name(".kerala_districts.geojson")
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
HEADERS = {"User-Agent": "kerala-health-leads/1.0 (janaushadhipound8873@gmail.com)"}

QUERY = """[out:json][timeout:180];
area["ISO3166-2"="IN-KL"]->.kl;
relation["admin_level"="5"]["boundary"="administrative"](area.kl);
out geom;
"""


def fetch_districts() -> list[dict]:
    """Returns [{name, polygons:[[(lon,lat),...]]}]"""
    if POLY_CACHE.exists():
        try:
            return json.loads(POLY_CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass

    print("Fetching Kerala district polygons from Overpass...")
    last_err = None
    for url in OVERPASS_ENDPOINTS:
        try:
            print(f"  -> {url}")
            r = requests.post(url, data={"data": QUERY}, headers=HEADERS, timeout=200)
            if r.status_code == 200:
                data = r.json()
                break
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
            time.sleep(2)
    else:
        raise RuntimeError(f"Overpass failed: {last_err}")

    districts = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = (tags.get("name:en") or tags.get("name") or "").replace(" District", "").strip()
        # Build outer-ring polygons by stitching `outer` member ways
        rings: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] = []
        for m in el.get("members", []):
            if m.get("role") != "outer":
                continue
            geom = m.get("geometry") or []
            if not geom:
                continue
            seg = [(p["lon"], p["lat"]) for p in geom]
            if not current:
                current = seg[:]
            elif current[-1] == seg[0]:
                current.extend(seg[1:])
            elif current[-1] == seg[-1]:
                current.extend(reversed(seg[:-1]))
            elif current[0] == seg[0]:
                current = list(reversed(seg)) + current[1:]
            elif current[0] == seg[-1]:
                current = seg + current[1:]
            else:
                # disjoint — close current ring and start new
                if len(current) >= 3:
                    rings.append(current)
                current = seg[:]
            # ring closed?
            if current and current[0] == current[-1] and len(current) >= 4:
                rings.append(current)
                current = []
        if current and len(current) >= 3:
            rings.append(current)
        if name and rings:
            districts.append({"name": name, "polygons": rings})
            print(f"   ✓ {name}: {sum(len(r) for r in rings)} pts in {len(rings)} ring(s)")

    POLY_CACHE.write_text(json.dumps(districts, ensure_ascii=False), encoding="utf-8")
    return districts


def point_in_ring(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def bbox(ring: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def build_index(districts: list[dict]):
    """Pre-compute bboxes for fast rejection."""
    indexed = []
    for d in districts:
        for ring in d["polygons"]:
            indexed.append((d["name"], bbox(ring), ring))
    return indexed


def find_district(lat: float, lon: float, idx) -> str:
    for name, (xmin, ymin, xmax, ymax), ring in idx:
        if xmin <= lon <= xmax and ymin <= lat <= ymax:
            if point_in_ring(lon, lat, ring):
                return name
    return ""


def main():
    if len(sys.argv) < 2:
        print("Usage: python fill_districts.py <csv_path>")
        sys.exit(1)
    path = Path(sys.argv[1])
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    if not rows:
        print("Empty CSV"); return

    districts = fetch_districts()
    if not districts:
        print("No district polygons fetched.")
        return
    idx = build_index(districts)
    print(f"Indexed {len(idx)} polygon ring(s) across {len(districts)} districts.")
    print()

    fields = list(rows[0].keys())
    filled = 0
    already = 0
    no_coords = 0
    not_found = 0
    valid_names = {d["name"] for d in districts}

    for r in rows:
        cur = (r.get("district") or "").strip().title()
        # normalize lowercase variants
        if cur and cur in valid_names:
            r["district"] = cur
            already += 1
            continue
        try:
            lat = float(r.get("lat") or "")
            lon = float(r.get("lon") or "")
        except ValueError:
            no_coords += 1
            continue
        d = find_district(lat, lon, idx)
        if d:
            r["district"] = d
            filled += 1
        else:
            not_found += 1

    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    by_d = Counter(r["district"] or "(unknown)" for r in rows)
    print(f"Done.  filled={filled}  already_set={already}  no_coords={no_coords}  not_found={not_found}")
    print(f"Saved -> {path}")
    print()
    print("Final district breakdown:")
    for d, n in sorted(by_d.items(), key=lambda x: -x[1]):
        print(f"  {n:5d}  {d}")


if __name__ == "__main__":
    main()
