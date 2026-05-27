"""
Kerala Pharmacy — Patient Lead Capture Form
============================================
Run:
    streamlit run kerala_pharmacy_form.py --server.port 8523
"""
from __future__ import annotations
import csv, requests
from datetime import datetime
from pathlib import Path
import streamlit as st

TELEGRAM_TOKEN = "8957824877:AAEVNvB6LPRbtobSEwp_jRsHv0EgVHPtvsQ"
TELEGRAM_CHAT_ID = "1812502464"

LEADS_FILE = Path(__file__).with_name("kerala_pharmacy_leads.csv")
FIELDS = ["name", "phone", "medicine_enquiry", "registered_at"]

def telegram_notify(name: str, phone: str, medicine: str = ""):
    try:
        med_line = f"\n💊 Medicine: {medicine}" if medicine else ""
        msg = f"💊 *New Lead — Kerala Pharmacy*\n👤 {name}\n📞 {phone}{med_line}\n📍 Gandhi Nagar, Kodakara, Thrissur"
        requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            params={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=5,
        )
    except Exception:
        pass

def save_lead(row: dict):
    new = not LEADS_FILE.exists()
    with open(LEADS_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)

    # Google Sheets
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets",
                  "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes)
        gc = gspread.authorize(creds)
        try:
            sh = gc.open("Kerala Pharmacy Leads")
        except Exception:
            sh = gc.create("Kerala Pharmacy Leads")
            sh.share(None, perm_type="anyone", role="reader")
        ws = sh.sheet1
        if ws.row_count <= 1:
            ws.append_row(FIELDS)
        ws.append_row([row[f] for f in FIELDS])
    except Exception:
        pass

# ── PAGE CONFIG ──────────────────────────────────────────────
st.set_page_config(
    page_title="Kerala Pharmacy — Get Medicine Offers",
    page_icon="💊",
    layout="centered",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"]{background:linear-gradient(160deg,#0f172a,#1e293b);}
[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:1.5rem;}
div.stButton>button{
  background:linear-gradient(135deg,#d4a017,#f0c040);
  color:#0f172a;font-weight:700;font-size:1rem;
  border:none;border-radius:12px;padding:.7rem 2rem;width:100%;
}
div.stButton>button:hover{background:linear-gradient(135deg,#b8860b,#d4a017);}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:1.5rem 1rem 1rem'>
  <div style='font-size:3rem;margin-bottom:.5rem'>💊</div>
  <div style='font-size:1.6rem;font-weight:800;
    background:linear-gradient(135deg,#fff,#f0c040);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;'>Kerala Pharmacy</div>
  <div style='color:rgba(255,255,255,.7);font-size:.85rem;margin-top:.3rem'>
    Gandhi Nagar, Kodakara, Thrissur
  </div>
  <div style='margin-top:.75rem;background:rgba(212,160,23,.15);
    border:1px solid rgba(212,160,23,.4);border-radius:999px;
    padding:.35rem 1rem;display:inline-block;
    color:#f0c040;font-size:.82rem;font-style:italic'>
    ✨ Caring You Beyond Prescriptions
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style='background:rgba(255,255,255,.06);border:1px solid rgba(212,160,23,.3);
  border-radius:16px;padding:1rem 1.25rem;margin-bottom:1.5rem;text-align:center'>
  <div style='color:#f0c040;font-weight:700;font-size:1rem;margin-bottom:.4rem'>
    🎁 Register & Get Exclusive Offers
  </div>
  <div style='color:rgba(255,255,255,.8);font-size:.85rem;line-height:1.6'>
    ✅ <b>13% off</b> on all branded medicines<br>
    ✅ <b>Up to 80% off</b> on generic medicines<br>
    ✅ Free medicine price list on WhatsApp
  </div>
</div>
""", unsafe_allow_html=True)

# ── FORM ─────────────────────────────────────────────────────
with st.form("lead_form", clear_on_submit=True):
    st.markdown("<p style='color:#f0c040;font-weight:600;margin-bottom:.25rem'>👤 Your Name</p>", unsafe_allow_html=True)
    name = st.text_input("", placeholder="Enter your full name", label_visibility="collapsed")

    st.markdown("<p style='color:#f0c040;font-weight:600;margin-bottom:.25rem'>📱 WhatsApp Number</p>", unsafe_allow_html=True)
    phone = st.text_input("", placeholder="Enter your 10-digit mobile number", label_visibility="collapsed")

    st.markdown("<p style='color:#f0c040;font-weight:600;margin-bottom:.25rem'>💊 Medicine Enquiry (optional)</p>", unsafe_allow_html=True)
    medicine = st.text_input("", placeholder="e.g. Metformin 500mg, Amlodipine 5mg", label_visibility="collapsed", key="med")

    submitted = st.form_submit_button("💊 Get My Offers & Price List")

if submitted:
    if not name.strip():
        st.error("Please enter your name.")
    elif len("".join(c for c in phone if c.isdigit())[-10:]) < 10:
        st.error("Please enter a valid 10-digit mobile number.")
    else:
        save_lead({
            "name": name.strip(),
            "phone": phone.strip(),
            "medicine_enquiry": medicine.strip(),
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        telegram_notify(name.strip(), phone.strip(), medicine.strip())
        st.balloons()
        st.success(f"✅ Thank you, {name.split()[0]}! We'll WhatsApp you the price list shortly.")
        st.info("📞 Call us: **+91 80867 32560**")

# ── FOOTER ────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center;font-size:.82rem;color:rgba(255,255,255,.5)'>
  Kerala Pharmacy, Gandhi Nagar, Kodakara, Thrissur<br>
  <a href='tel:+918086732560' style='color:#f0c040'>+91 80867 32560</a>
  &nbsp;·&nbsp;
  <a href='mailto:keralapharmacy3@gmail.com' style='color:#f0c040'>keralapharmacy3@gmail.com</a><br>
  <span style='color:rgba(255,255,255,.4)'>✨ Caring You Beyond Prescriptions</span>
</div>
""", unsafe_allow_html=True)
