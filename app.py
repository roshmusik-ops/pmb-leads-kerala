"""
Kerala Govt Health Centres — Lead Finder UI
Streamlit dashboard for browsing, filtering, mapping, and exporting leads.

Run:
    streamlit run app.py
"""
from __future__ import annotations
import csv
import io
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

CSV_PATH = Path(__file__).with_name("leads_kerala_health.csv")
SENT_LOG = Path(__file__).with_name("sent_log.csv")
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
st.title("🏥 Kerala Govt Health Centres")
st.caption("Built for **PMB Jan Aushadhi Kendra, Pound Velupadam, Thrissur** · "
           "No.1 Govt Health Centre Dealer in Kerala")

if not CSV_PATH.exists():
    st.warning("No leads CSV found yet.")
    if st.button("Run scraper now"):
        with st.spinner("Pulling Kerala govt health facilities..."):
            r = subprocess.run([sys.executable, "find_health_centres.py"],
                               cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=600)
            st.code(r.stdout)
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
tab_table, tab_map, tab_breakdown, tab_call, tab_email = st.tabs(
    ["📋 Table", "🗺️ Map", "📊 Breakdown", "📞 Call list", "✉️ Email"]
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

# ===== Email tab =====
with tab_email:
    st.subheader("✉️ Send outreach emails")

    # Gmail credentials from Streamlit secrets or manual input
    try:
        gmail_user = st.secrets["GMAIL_USER"]
        gmail_pass = st.secrets["GMAIL_APP_PASSWORD"]
        from_name  = st.secrets.get("FROM_NAME", "PMB Jan Aushadhi Kendra")
        st.success(f"Using Gmail: **{gmail_user}**")
    except Exception:
        st.info("Enter Gmail credentials below (add to Streamlit secrets for permanent setup).")
        gmail_user = st.text_input("Gmail address", value="pmbjanaushadhi680006@gmail.com")
        gmail_pass = st.text_input("Gmail App Password", type="password",
                                   help="Generate at myaccount.google.com/apppasswords")
        from_name  = st.text_input("Sender name", value="PMB Jan Aushadhi Kendra, Velupadam")

    # Load sent log
    def load_sent() -> set:
        if not SENT_LOG.exists():
            return set()
        try:
            return {r["email"] for r in csv.DictReader(open(SENT_LOG, encoding="utf-8"))}
        except Exception:
            return set()

    def log_sent(email: str, name: str):
        exists = SENT_LOG.exists()
        with open(SENT_LOG, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["email", "name", "sent_at"])
            w.writerow([email, name, datetime.now().strftime("%Y-%m-%d %H:%M")])

    def build_email(name: str, district: str, ftype: str) -> tuple[str, str]:
        subject = f"Generic Medicines Supply — PMB Jan Aushadhi Kendra, Thrissur"
        body = f"""Dear Medical Officer / Store In-charge,

Greetings from **PMB Jan Aushadhi Kendra**, Pound Velupadam, Thrissur — Kerala's leading supplier of government-approved generic medicines.

We supply 2,000+ PMBJP generic medicines at **50–90% lower prices** than branded alternatives, directly beneficial for patients at {name}{(', ' + district) if district else ''}.

Key highlights:
- All medicines approved under Pradhan Mantri Bhartiya Janaushadhi Pariyojana (PMBJP)
- Direct supply to PHCs, CHCs, Taluk & District Hospitals
- Competitive rates, reliable stock, timely delivery
- Contact: +91 73569 85202

We would appreciate the opportunity to connect and discuss how we can support your facility's medicine requirements.

Warm regards,
{from_name}
Phone: +91 73569 85202
Email: pmbjanaushadhi680006@gmail.com
"""
        return subject, body

    def send_email(to: str, name: str, district: str, ftype: str) -> bool:
        try:
            subject, body = build_email(name, district, ftype)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = f"{from_name} <{gmail_user}>"
            msg["To"]      = to
            html = body.replace("\n", "<br>").replace("**", "<b>").replace("</b><b>", "")
            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(f"<html><body style='font-family:sans-serif'>{html}</body></html>", "html"))
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
                s.login(gmail_user, gmail_pass)
                s.sendmail(gmail_user, to, msg.as_string())
            return True
        except Exception as e:
            st.error(f"Failed to send to {to}: {e}")
            return False

    sent_set = load_sent()
    email_leads = fdf[fdf["email"].str.strip().ne("")].copy()
    unsent = email_leads[~email_leads["email"].isin(sent_set)]
    already_sent = email_leads[email_leads["email"].isin(sent_set)]

    col1, col2, col3 = st.columns(3)
    col1.metric("Leads with email (filtered)", len(email_leads))
    col2.metric("Not yet sent", len(unsent))
    col3.metric("Already sent", len(already_sent))

    if not gmail_pass:
        st.warning("Enter Gmail App Password above to enable sending.")
    elif len(unsent) == 0:
        st.success("All email leads in current filter already sent!")
    else:
        st.markdown(f"**{len(unsent)} leads** ready to email in current filter.")

        # Preview email
        with st.expander("Preview email template", expanded=False):
            if len(unsent):
                r = unsent.iloc[0]
                subj, body = build_email(r["name"], r["district"], r["type"])
                st.markdown(f"**Subject:** {subj}")
                st.text(body)

        # Bulk send
        max_send = st.slider("Max emails to send this run", 1, min(50, len(unsent)), min(10, len(unsent)))
        if st.button(f"🚀 Send {max_send} emails now", type="primary", disabled=not gmail_pass):
            to_send = unsent.head(max_send)
            progress = st.progress(0)
            ok = 0
            for i, (_, r) in enumerate(to_send.iterrows()):
                if send_email(r["email"], r["name"], r["district"], r["type"]):
                    log_sent(r["email"], r["name"])
                    ok += 1
                progress.progress((i + 1) / len(to_send))
            st.success(f"Sent {ok}/{len(to_send)} emails successfully!")
            st.cache_data.clear()
            st.rerun()

        st.divider()
        # Per-lead send
        st.markdown("**Or send one at a time:**")
        for _, r in unsent.head(20).iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 2, 1])
                c1.markdown(f"**{r['name']}**  \n*{r['type']} · {r['district']}*")
                c2.markdown(f"📧 `{r['email']}`")
                if c3.button("Send", key=f"send_{r['email']}"):
                    if send_email(r["email"], r["name"], r["district"], r["type"]):
                        log_sent(r["email"], r["name"])
                        st.success(f"Sent to {r['email']}")
                        st.rerun()

st.markdown("---")
st.caption(f"Data source: OpenStreetMap · Last updated: "
           f"{pd.Timestamp(CSV_PATH.stat().st_mtime, unit='s').strftime('%d %b %Y %H:%M')} · "
           "[Retail Finder →](retail_app)")
