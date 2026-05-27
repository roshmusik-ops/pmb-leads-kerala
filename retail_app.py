"""
Kerala Retail Leads — Private Doctors, Clinics & Pharmacies
PMB Jan Aushadhi Chelakottukara

Run:
    streamlit run retail_app.py
"""
from __future__ import annotations
import csv, io, smtplib, subprocess, sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

CSV_PATH   = Path(__file__).with_name("leads_private_doctors.csv")
SENT_LOG   = Path(__file__).with_name("sent_retail_log.csv")
SCRIPT_DIR = Path(__file__).parent

st.set_page_config(
    page_title="Kerala Retail Leads",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container { padding-top: 1.5rem; }
[data-testid="stMetricValue"] { font-size: 1.6rem; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_data(_mtime: float) -> pd.DataFrame:
    if not CSV_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(CSV_PATH)
    for c in ("phone","email","website","name","type","district","address","operator","speciality"):
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str)
    df["has_phone"]   = df["phone"].str.strip().ne("")
    df["has_email"]   = df["email"].str.strip().ne("")
    df["has_website"] = df["website"].str.strip().ne("")
    return df


def whatsapp_url(phone: str, name: str) -> str:
    p = "".join(c for c in phone if c.isdigit())
    if not p: return ""
    if len(p) == 10: p = "91" + p
    msg = (f"Namaste Doctor/Sir, I'm from PMB Jan Aushadhi Chelakottukara. "
           f"We supply 2,000+ PMBJP generic medicines at 50-90% less than branded prices. "
           f"Could we discuss how we can support {name} with affordable generic medicines for your patients?")
    return f"https://wa.me/{p}?text={quote(msg)}"


def maps_url(lat, lon, name) -> str:
    try:
        return f"https://www.google.com/maps/?q={float(lat)},{float(lon)}"
    except Exception:
        return f"https://www.google.com/maps/search/{quote(str(name))}"


def type_color(t: str) -> str:
    t = t.lower()
    if "hospital" in t:   return "🔴"
    if "pharmacy" in t:   return "🟢"
    if "dental" in t:     return "🔵"
    if "eye" in t:        return "🟡"
    if "nursing" in t:    return "🟠"
    if "gp" in t or "clinic" in t: return "⚪"
    return "⚫"


# ---------- header ----------
st.title("🏪 Kerala Retail Leads")
st.caption("Private doctors, clinics & pharmacies · "
           "**PMB Jan Aushadhi Chelakottukara**")

if not CSV_PATH.exists():
    st.warning("No retail leads CSV found.")
    if st.button("Scrape now (all Kerala, ~30s)"):
        with st.spinner("Finding private doctors & clinics..."):
            r = subprocess.run([sys.executable, "find_private_doctors.py"],
                               cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=300)
            st.code(r.stdout)
        st.cache_data.clear()
        st.rerun()
    st.stop()

df = load_data(CSV_PATH.stat().st_mtime)

# ---------- sidebar ----------
st.sidebar.header("🔎 Filters")

districts = sorted([d for d in df["district"].dropna().unique() if d])
sel_districts = st.sidebar.multiselect("District", districts)

types = sorted(df["type"].dropna().unique().tolist())
TYPE_PRESETS = {
    "All": types,
    "Doctors & GPs": [t for t in types if any(x in t.lower() for x in ("gp","clinic","doctor","specialist","physician"))],
    "Hospitals": [t for t in types if "hospital" in t.lower() or "nursing" in t.lower()],
    "Pharmacies": [t for t in types if "pharmacy" in t.lower()],
    "Dental":  [t for t in types if "dental" in t.lower()],
    "Eye":     [t for t in types if "eye" in t.lower()],
}
preset = st.sidebar.radio("Type preset", list(TYPE_PRESETS.keys()), index=0)
if preset == "All":
    sel_types = st.sidebar.multiselect("Facility type", types, default=types)
else:
    sel_types = st.sidebar.multiselect("Facility type", types, default=TYPE_PRESETS[preset])

st.sidebar.markdown("---")
only_phone   = st.sidebar.checkbox("Has phone")
only_email   = st.sidebar.checkbox("Has email")
only_website = st.sidebar.checkbox("Has website")
q = st.sidebar.text_input("Search").strip().lower()

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Tools")
if st.sidebar.button("🔄 Re-scrape"):
    with st.spinner("Scraping..."):
        r = subprocess.run([sys.executable, "find_private_doctors.py"],
                           cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=300)
        st.sidebar.code(r.stdout[-1000:])
    st.cache_data.clear()
    st.rerun()
if st.sidebar.button("🔄 Thrissur only"):
    with st.spinner("Scraping Thrissur..."):
        r = subprocess.run([sys.executable, "find_private_doctors.py","--district","Thrissur"],
                           cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=120)
        st.sidebar.code(r.stdout[-1000:])
    st.cache_data.clear()
    st.rerun()

# ---------- filter ----------
fdf = df.copy()
if sel_districts: fdf = fdf[fdf["district"].isin(sel_districts)]
if sel_types:     fdf = fdf[fdf["type"].isin(sel_types)]
if only_phone:    fdf = fdf[fdf["has_phone"]]
if only_email:    fdf = fdf[fdf["has_email"]]
if only_website:  fdf = fdf[fdf["has_website"]]
if q:
    mask = (fdf["name"].str.lower().str.contains(q, na=False)
          | fdf["address"].str.lower().str.contains(q, na=False)
          | fdf["type"].str.lower().str.contains(q, na=False)
          | fdf["speciality"].str.lower().str.contains(q, na=False))
    fdf = fdf[mask]

# ---------- KPIs ----------
k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Leads", f"{len(fdf):,}", f"of {len(df):,}")
k2.metric("With phone", f"{int(fdf['has_phone'].sum()):,}")
k3.metric("With email", f"{int(fdf['has_email'].sum()):,}")
k4.metric("Districts",  fdf["district"].nunique())
k5.metric("Types",      fdf["type"].nunique())
st.markdown("---")

# ---------- tabs ----------
tab_table, tab_map, tab_breakdown, tab_call, tab_email = st.tabs(
    ["📋 Table", "🗺️ Map", "📊 Breakdown", "📞 Call list", "✉️ Email"])

with tab_table:
    cols = ["name","type","district","phone","email","website","address","speciality","opening_hours"]
    cols = [c for c in cols if c in fdf.columns]
    st.dataframe(fdf[cols], use_container_width=True, hide_index=True, height=560,
                 column_config={"website": st.column_config.LinkColumn("website")})
    buf = io.StringIO()
    fdf.drop(columns=["has_phone","has_email","has_website"], errors="ignore").to_csv(buf, index=False)
    st.download_button("⬇️ Download CSV", buf.getvalue(),
                       f"retail_leads_{len(fdf)}.csv", "text/csv")

with tab_map:
    mdf = fdf.dropna(subset=["lat","lon"]).copy()
    mdf["lat"] = pd.to_numeric(mdf["lat"], errors="coerce")
    mdf["lon"] = pd.to_numeric(mdf["lon"], errors="coerce")
    mdf = mdf.dropna(subset=["lat","lon"])
    if len(mdf):
        st.caption(f"{len(mdf):,} pinned")
        st.map(mdf.rename(columns={"lat":"latitude","lon":"longitude"}), size=20, zoom=7)
    else:
        st.info("No coordinates in current filter.")

with tab_breakdown:
    a, b = st.columns(2)
    with a:
        st.subheader("By district")
        st.bar_chart(fdf["district"].replace("","(unknown)").value_counts())
    with b:
        st.subheader("By type")
        st.bar_chart(fdf["type"].value_counts().head(15))

with tab_call:
    callable_df = fdf[fdf["has_phone"]].head(200)
    if not len(callable_df):
        st.info("No phone numbers in current filter.")
    else:
        for _, r in callable_df.iterrows():
            with st.container(border=True):
                c1,c2,c3,c4 = st.columns([4,2,2,2])
                c1.markdown(f"{type_color(r['type'])} **{r['name']}**  \n"
                            f"*{r['type']} · {r['district']}*  \n{r['address']}")
                c2.markdown(f"📞 `{r['phone']}`")
                wa = whatsapp_url(r["phone"], r["name"])
                if wa: c3.link_button("💬 WhatsApp", wa)
                c4.link_button("📍 Maps", maps_url(r.get("lat"), r.get("lon"), r["name"]))
        if int(fdf["has_phone"].sum()) > 200:
            st.caption(f"Showing 200 of {int(fdf['has_phone'].sum())}")

with tab_email:
    st.subheader("✉️ Email outreach")
    try:
        gmail_user = st.secrets["GMAIL_USER"]
        gmail_pass = st.secrets["GMAIL_APP_PASSWORD"]
        from_name  = st.secrets.get("FROM_NAME","PMB Jan Aushadhi Kendra")
        st.success(f"Gmail: **{gmail_user}**")
    except Exception:
        st.info("Add Gmail credentials to Streamlit secrets.")
        gmail_user = st.text_input("Gmail", value="pmbjanaushadhi680006@gmail.com")
        gmail_pass = st.text_input("App Password", type="password")
        from_name  = st.text_input("Sender name", value="PMB Jan Aushadhi Kendra, Velupadam")

    def load_sent():
        if not SENT_LOG.exists(): return set()
        try: return {r["email"] for r in csv.DictReader(open(SENT_LOG,encoding="utf-8"))}
        except Exception: return set()

    def log_sent(email, name):
        exists = SENT_LOG.exists()
        with open(SENT_LOG,"a",encoding="utf-8",newline="") as f:
            w = csv.writer(f)
            if not exists: w.writerow(["email","name","sent_at"])
            w.writerow([email, name, datetime.now().strftime("%Y-%m-%d %H:%M")])

    def build_email(name, district, ftype):
        subject = "Generic Medicines Supply — PMB Jan Aushadhi Chelakottukara"
        body = f"""Dear Doctor / Proprietor,

Greetings from PMB Jan Aushadhi Chelakottukara.

We are Kerala's leading supplier of PMBJP government-approved generic medicines, supplying 2,000+ medicines at 50-90% less than branded prices.

We would like to partner with {name}{(', ' + district) if district else ''} to:
- Supply generic medicines for your patients at affordable prices
- Provide quick delivery and reliable stock
- Help your patients save on long-term medicines (diabetes, BP, thyroid, etc.)

Contact: +91 73569 85202
Email: pmbjanaushadhi680006@gmail.com

Warm regards,
{from_name}"""
        return subject, body

    def send_email(to, name, district, ftype):
        try:
            subject, body = build_email(name, district, ftype)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{gmail_user}>"
            msg["To"] = to
            msg.attach(MIMEText(body, "plain"))
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
                s.login(gmail_user, gmail_pass)
                s.sendmail(gmail_user, to, msg.as_string())
            return True
        except Exception as e:
            st.error(f"Failed: {e}")
            return False

    sent_set = load_sent()
    email_leads = fdf[fdf["email"].str.strip().ne("")]
    unsent      = email_leads[~email_leads["email"].isin(sent_set)]
    sent_count  = email_leads[email_leads["email"].isin(sent_set)]

    c1,c2,c3 = st.columns(3)
    c1.metric("With email", len(email_leads))
    c2.metric("Not sent",   len(unsent))
    c3.metric("Sent",       len(sent_count))

    if not gmail_pass:
        st.warning("Enter App Password to enable sending.")
    elif not len(unsent):
        st.success("All email leads in filter already sent!")
    else:
        with st.expander("Preview email"):
            r = unsent.iloc[0]
            subj, body = build_email(r["name"], r["district"], r["type"])
            st.markdown(f"**Subject:** {subj}")
            st.text(body)

        max_send = st.slider("Send how many?", 1, min(50, len(unsent)), min(10, len(unsent)))
        if st.button(f"🚀 Send {max_send} emails", type="primary"):
            prog = st.progress(0)
            ok = 0
            for i, (_, r) in enumerate(unsent.head(max_send).iterrows()):
                if send_email(r["email"], r["name"], r["district"], r["type"]):
                    log_sent(r["email"], r["name"]); ok += 1
                prog.progress((i+1)/max_send)
            st.success(f"Sent {ok}/{max_send}")
            st.rerun()

        st.divider()
        st.markdown("**Send one at a time:**")
        for _, r in unsent.head(20).iterrows():
            with st.container(border=True):
                c1,c2,c3 = st.columns([4,2,1])
                c1.markdown(f"**{r['name']}** · *{r['type']}*")
                c2.markdown(f"📧 `{r['email']}`")
                if c3.button("Send", key=f"rs_{r['email']}"):
                    if send_email(r["email"], r["name"], r["district"], r["type"]):
                        log_sent(r["email"], r["name"])
                        st.success(f"Sent to {r['email']}")
                        st.rerun()

st.markdown("---")
st.caption(f"Source: OpenStreetMap · {len(df):,} retail leads · "
           f"[Govt Health Leads →](app)")
