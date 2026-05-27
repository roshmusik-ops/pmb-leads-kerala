"""
Kerala Govt Health Centres — Lead Finder UI
Streamlit dashboard for browsing, filtering, mapping, and exporting leads.

Run:
    streamlit run app.py
"""
from __future__ import annotations
import io
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

CSV_PATH = Path(__file__).with_name("leads_kerala_health.csv")
SCRIPT_DIR = Path(__file__).parent

st.set_page_config(
    page_title="Kerala Govt Health Leads",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- styling ----------
st.markdown("""
<style>
.block-container { padding-top: 1.5rem; }
[data-testid="stMetricValue"] { font-size: 1.6rem; }
.stButton>button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ---------- data ----------
@st.cache_data(show_spinner=False)
def load_data(path: Path, _mtime: float) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    for c in ("phone", "email", "website", "name", "type", "district",
              "address", "operator"):
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str)
    df["has_phone"] = df["phone"].str.strip().ne("")
    df["has_email"] = df["email"].str.strip().ne("")
    df["has_website"] = df["website"].str.strip().ne("")
    return df


def whatsapp_url(phone: str, name: str) -> str:
    p = "".join(c for c in phone if c.isdigit())
    if not p:
        return ""
    if len(p) == 10:
        p = "91" + p
    msg = (
        f"Namaste, this is from PMB Jan Aushadhi Kendra, Pound Velupadam Thrissur "
        f"(No.1 Govt Health Centre dealer in Kerala). We supply 2,000+ generic medicines "
        f"at 50–90% lower than branded. Could we connect with the medical officer at "
        f"{name}?"
    )
    return f"https://wa.me/{p}?text={quote(msg)}"


def maps_url(lat, lon, name) -> str:
    if pd.notna(lat) and pd.notna(lon):
        return f"https://www.google.com/maps/?q={lat},{lon}"
    return f"https://www.google.com/maps/search/{quote(str(name))}"


# ---------- header ----------
st.title("🏥 Kerala Govt Health Centres — Lead Finder")
st.caption("Built for **PMB Jan Aushadhi Kendra, Pound Velupadam, Thrissur** · "
           "No.1 Govt Health Centre Dealer in Kerala")

if not CSV_PATH.exists():
    st.warning("No leads CSV found yet.")
    if st.button("🚀 Run scraper now (takes ~2 minutes)"):
        with st.spinner("Pulling Kerala govt health facilities from OpenStreetMap..."):
            r = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "find_health_centres.py")],
                cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=600,
            )
            st.code(r.stdout + "\n" + r.stderr)
        st.rerun()
    st.stop()

df = load_data(CSV_PATH, CSV_PATH.stat().st_mtime)

# ---------- sidebar filters ----------
st.sidebar.header("🔎 Filters")

districts = sorted(df["district"].dropna().unique().tolist())
districts = [d for d in districts if d]
sel_districts = st.sidebar.multiselect("District", districts, default=[])

types = sorted(df["type"].dropna().unique().tolist())
PRIORITY_TYPES = [
    "District Hospital", "General Hospital", "Taluk Hospital",
    "Medical College", "Community Health Centre (CHC)",
    "Family Health Centre (FHC)", "Primary Health Centre (PHC)",
    "Women & Children Hospital", "Govt Dispensary",
]
preset = st.sidebar.radio(
    "Type preset",
    ["All", "High-value buyers", "PHC/FHC/CHC", "Hospitals only", "Custom"],
    index=1,
)
if preset == "High-value buyers":
    default_types = [t for t in types if t in {
        "District Hospital", "General Hospital", "Taluk Hospital",
        "Medical College", "Community Health Centre (CHC)",
        "Women & Children Hospital",
    }]
elif preset == "PHC/FHC/CHC":
    default_types = [t for t in types if t in {
        "Primary Health Centre (PHC)", "Family Health Centre (FHC)",
        "Community Health Centre (CHC)",
    }]
elif preset == "Hospitals only":
    default_types = [t for t in types if "hospital" in t.lower() or "medical college" in t.lower()]
else:
    default_types = types

sel_types = st.sidebar.multiselect("Facility type", types, default=default_types)

st.sidebar.markdown("---")
only_phone = st.sidebar.checkbox("Has phone number", value=False)
only_email = st.sidebar.checkbox("Has email", value=False)
only_website = st.sidebar.checkbox("Has website", value=False)

q = st.sidebar.text_input("Search (name / address / operator)").strip().lower()

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Tools")
if st.sidebar.button("🔄 Re-scrape from OSM"):
    with st.spinner("Re-running scraper... ~2 min"):
        r = subprocess.run([sys.executable, "find_health_centres.py"],
                           cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=600)
        st.sidebar.code(r.stdout[-1500:])
    st.cache_data.clear()
    st.rerun()
if st.sidebar.button("📍 Re-fill districts"):
    with st.spinner("Point-in-polygon district lookup..."):
        r = subprocess.run([sys.executable, "fill_districts.py", "leads_kerala_health.csv"],
                           cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=300)
        st.sidebar.code(r.stdout[-1500:])
    st.cache_data.clear()
    st.rerun()

# ---------- apply filters ----------
fdf = df.copy()
if sel_districts:
    fdf = fdf[fdf["district"].isin(sel_districts)]
if sel_types:
    fdf = fdf[fdf["type"].isin(sel_types)]
if only_phone:
    fdf = fdf[fdf["has_phone"]]
if only_email:
    fdf = fdf[fdf["has_email"]]
if only_website:
    fdf = fdf[fdf["has_website"]]
if q:
    mask = (
        fdf["name"].str.lower().str.contains(q, na=False)
        | fdf["address"].str.lower().str.contains(q, na=False)
        | fdf["operator"].str.lower().str.contains(q, na=False)
    )
    fdf = fdf[mask]

# ---------- KPIs ----------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Leads (filtered)", f"{len(fdf):,}", f"of {len(df):,} total")
c2.metric("With phone", f"{int(fdf['has_phone'].sum()):,}")
c3.metric("With email", f"{int(fdf['has_email'].sum()):,}")
c4.metric("Districts", fdf["district"].nunique())
c5.metric("Types", fdf["type"].nunique())

st.markdown("---")

# ---------- tabs ----------
tab_table, tab_map, tab_breakdown, tab_call = st.tabs(
    ["📋 Table", "🗺️ Map", "📊 Breakdown", "📞 Call list"]
)

# ===== Table tab =====
with tab_table:
    show_cols = ["name", "type", "district", "phone", "email", "website",
                 "address", "operator"]
    show_cols = [c for c in show_cols if c in fdf.columns]
    st.dataframe(
        fdf[show_cols],
        use_container_width=True,
        hide_index=True,
        height=560,
        column_config={
            "website": st.column_config.LinkColumn("website"),
            "name": st.column_config.TextColumn("name", width="medium"),
            "address": st.column_config.TextColumn("address", width="large"),
        },
    )

    csv_buf = io.StringIO()
    fdf.drop(columns=["has_phone", "has_email", "has_website"], errors="ignore").to_csv(csv_buf, index=False)
    st.download_button(
        "⬇️ Download filtered CSV",
        csv_buf.getvalue(),
        file_name=f"kerala_leads_{len(fdf)}.csv",
        mime="text/csv",
    )

# ===== Map tab =====
with tab_map:
    map_df = fdf.dropna(subset=["lat", "lon"]).copy()
    map_df["lat"] = pd.to_numeric(map_df["lat"], errors="coerce")
    map_df["lon"] = pd.to_numeric(map_df["lon"], errors="coerce")
    map_df = map_df.dropna(subset=["lat", "lon"])
    if len(map_df):
        st.caption(f"Showing {len(map_df):,} pinned facilities")
        st.map(map_df.rename(columns={"lat": "latitude", "lon": "longitude"}),
               size=20, zoom=7)
    else:
        st.info("No coordinates in current filter.")

# ===== Breakdown tab =====
with tab_breakdown:
    a, b = st.columns(2)
    with a:
        st.subheader("By district")
        bd = fdf["district"].replace("", "(unknown)").value_counts()
        st.bar_chart(bd)
    with b:
        st.subheader("By facility type")
        bt = fdf["type"].value_counts().head(15)
        st.bar_chart(bt)

# ===== Call list tab =====
with tab_call:
    st.caption("WhatsApp + Maps deep-links for the rows in your current filter that have a phone number.")
    callable_df = fdf[fdf["has_phone"]].head(200)
    if not len(callable_df):
        st.info("No leads with phone numbers in current filter. Try removing the 'Has phone' filter "
                "or run phone enrichment via Google Places.")
    else:
        for _, r in callable_df.iterrows():
            with st.container(border=True):
                cols = st.columns([4, 2, 2, 2])
                cols[0].markdown(f"**{r['name']}**  \n*{r['type']} · {r['district']}*  \n{r['address']}")
                cols[1].markdown(f"📞 `{r['phone']}`")
                wa = whatsapp_url(r["phone"], r["name"])
                if wa:
                    cols[2].link_button("💬 WhatsApp", wa)
                cols[3].link_button("📍 Maps", maps_url(r.get("lat"), r.get("lon"), r["name"]))
        if len(fdf[fdf["has_phone"]]) > 200:
            st.caption(f"Showing first 200 of {int(fdf['has_phone'].sum())} — narrow filters to see more.")

st.markdown("---")
st.caption(f"Data source: OpenStreetMap · Last updated: "
           f"{pd.Timestamp(CSV_PATH.stat().st_mtime, unit='s').strftime('%d %b %Y %H:%M')}")
