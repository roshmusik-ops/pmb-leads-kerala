"""
PMB Jan Aushadhi — Patient Lead Capture Form
=============================================
A simple Streamlit form for patients to register for medicine price updates.
Share the URL or QR code at your counter / WhatsApp groups.

Run:
    streamlit run patient_form.py --server.port 8522
"""
from __future__ import annotations
import csv, io, json
from datetime import datetime
from pathlib import Path
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_OK = True
except ImportError:
    GSPREAD_OK = False

LEADS_FILE = Path(__file__).with_name("local_patients.csv")
FIELDS = ["name", "phone", "registered_at"]
SHEET_NAME = "PMB Patient Leads"


def get_sheet():
    if not GSPREAD_OK:
        return None
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive"]
        )
        gc = gspread.authorize(creds)
        try:
            sh = gc.open(SHEET_NAME)
        except gspread.exceptions.SpreadsheetNotFound:
            sh = gc.create(SHEET_NAME)
            sh.share(None, perm_type="anyone", role="reader")
        ws = sh.sheet1
        if ws.row_count < 2 or ws.cell(1,1).value != "name":
            ws.insert_row(FIELDS, 1)
        return ws
    except Exception:
        return None


def save_lead(row: dict):
    ws = get_sheet()
    if ws:
        ws.append_row([row.get(f, "") for f in FIELDS])
    exists = LEADS_FILE.exists()
    with open(LEADS_FILE, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)

st.set_page_config(
    page_title="PMB Jan Aushadhi — Free Price List",
    page_icon="💊",
    layout="centered",
)

st.markdown("""
<style>
.block-container { max-width: 520px; padding-top: 2rem; }
h1 { color: #16a34a; }
</style>
""", unsafe_allow_html=True)

# ── Logo / header ──
st.markdown("""
<div style='text-align:center;padding:1rem 0'>
  <div style='font-size:3rem'>💊</div>
  <h1 style='margin:0.3rem 0'>PMB Jan Aushadhi Chelakottukara</h1>
  <p style='color:#64748b;margin:0'>Chelakottukara, Thrissur &nbsp;·&nbsp; +91 73569 85202</p>
  <div style='background:#f0fdf4;border:1px solid #86efac;border-radius:12px;padding:0.7rem;margin-top:1rem'>
    <b style='color:#15803d'>Save 50–90%</b> on your medicines with government-approved generics
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.subheader("📋 Get Free Medicine Price List")

with st.form("patient_form", clear_on_submit=True):
    name  = st.text_input("Your name *")
    phone = st.text_input("WhatsApp number *", placeholder="10-digit mobile number")
    submitted = st.form_submit_button("✅ Send me the price list", type="primary")

if submitted:
    if not name.strip():
        st.error("Please enter your name.")
    elif len("".join(c for c in phone if c.isdigit())[-10:]) < 10:
        st.error("Please enter a valid 10-digit mobile number.")
    else:
        save_lead({
            "name": name.strip(),
            "phone": phone.strip(),
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        st.balloons()
        st.success(f"✅ Thank you, {name.split()[0]}! We'll WhatsApp you shortly.")
        st.info("📞 Call us: **+91 73569 85202**")

st.markdown("---")
st.markdown("""
<div style='text-align:center;font-size:0.85rem;color:#64748b'>
  PMB Jan Aushadhi Chelakottukara, Chelakottukara, Thrissur<br>
  <a href='tel:+917356985202'>+91 73569 85202</a> &nbsp;·&nbsp;
  <a href='mailto:pmbjanaushadhi680006@gmail.com'>pmbjanaushadhi680006@gmail.com</a>
</div>
""", unsafe_allow_html=True)
