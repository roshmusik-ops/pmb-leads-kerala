"""
PMB Jan Aushadhi Chelakottukara — Govt Centre Daily Email Outreach
===================================================================
Run:
    streamlit run pmb_outreach.py --server.port 8525
"""
from __future__ import annotations
import csv, smtplib, ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
import streamlit as st
import pandas as pd

CENTRES_FILE = Path(__file__).with_name("pmb_govt_centres.csv")
FIELDS = ["name", "type", "location", "email", "phone", "status", "last_sent"]

GMAIL_USER = "pmbjanaushadhi680006@gmail.com"
FROM_NAME  = "PMB Jan Aushadhi Chelakottukara"

def build_email(centre_name: str, location: str) -> tuple[str, str]:
    subject = "Jan Aushadhi Generic Medicines for Your Patients — PMB Jan Aushadhi, Chelakottukara"
    body = f"""Dear Medical Officer / Pharmacist In-Charge,
{centre_name}, {location}

Greetings from PMB Jan Aushadhi Kendra, Chelakottukara, Thrissur.

We are a Government of India approved Jan Aushadhi Kendra operating under the
Pradhan Mantri Bhartiya Janaushadhi Pariyojana (PMBJP) scheme.

We offer high-quality WHO-GMP certified generic medicines at significantly
lower prices than branded medicines — making healthcare truly affordable
for every patient.

Our medicines include:
• Diabetes medicines
• Blood pressure & cardiac medicines
• Thyroid medicines
• Antibiotics
• Vitamins & supplements
• Insulin & injectables
• Neurological medicines
• Gastro medicines
• Dermatology medicines
• Paediatric medicines
• Cancer & oncology medicines
• And 2000+ more medicines

✅ All medicines are WHO-GMP certified
✅ Same active ingredients as branded medicines
✅ Government approved — PMBJP scheme
✅ Quality tested by central laboratories

We kindly request you to:
• Recommend our Jan Aushadhi Kendra to your patients
• Display our information in your OPD / pharmacy
• Share our contact with patients who need affordable medicines

We would be happy to send you our complete medicine list or visit
your centre at your convenience.

📞 Phone / WhatsApp : +91 94473 36560
📧 Email            : pmbjanaushadhi680006@gmail.com
📍 Address          : PMB Jan Aushadhi Kendra, Chelakottukara, Thrissur, Kerala

"Quality Medicines for Every Indian"
— Pradhan Mantri Bhartiya Janaushadhi Pariyojana

Warm regards,
PMB Jan Aushadhi Chelakottukara
Thrissur, Kerala
+91 94473 36560
""".strip()
    return subject, body

def send_email(to_email: str, subject: str, body: str, app_password: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{FROM_NAME} <{GMAIL_USER}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(body, "plain"))
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
            s.login(GMAIL_USER, app_password)
            s.sendmail(GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Failed to send to {to_email}: {e}")
        return False

def load_centres() -> list[dict]:
    if not CENTRES_FILE.exists():
        seed_centres()
    with open(CENTRES_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def save_centres(rows: list[dict]):
    with open(CENTRES_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

def mark_sent(email: str):
    rows = load_centres()
    for r in rows:
        if r["email"] == email:
            r["status"] = "sent"
            r["last_sent"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_centres(rows)

def seed_centres():
    rows = [
        {"name":"Chelakottukara PHC","type":"PHC","location":"Chelakottukara","email":"chelakottukara.phc@kerala.gov.in","phone":"04802700111","status":"pending","last_sent":""},
        {"name":"Kodakara PHC","type":"PHC","location":"Kodakara","email":"kodakara.phc@kerala.gov.in","phone":"04802700100","status":"pending","last_sent":""},
        {"name":"Chalakudy Taluk Hospital","type":"Taluk Hospital","location":"Chalakudy","email":"dmochalakudy@gmail.com","phone":"04802700200","status":"pending","last_sent":""},
        {"name":"Irinjalakuda Taluk Hospital","type":"Taluk Hospital","location":"Irinjalakuda","email":"irinjalakuda.hospital@kerala.gov.in","phone":"04802825000","status":"pending","last_sent":""},
        {"name":"Mala PHC","type":"PHC","location":"Mala","email":"mala.phc@kerala.gov.in","phone":"04802895100","status":"pending","last_sent":""},
        {"name":"Mukundapuram PHC","type":"PHC","location":"Mukundapuram","email":"mukundapuram.phc@kerala.gov.in","phone":"04802700300","status":"pending","last_sent":""},
        {"name":"Peramangalam PHC","type":"PHC","location":"Peramangalam","email":"peramangalam.phc@kerala.gov.in","phone":"04802700400","status":"pending","last_sent":""},
        {"name":"Thrissur District Hospital","type":"District Hospital","location":"Thrissur","email":"dmo.thrissur@kerala.gov.in","phone":"04872360100","status":"pending","last_sent":""},
        {"name":"Ollur PHC","type":"PHC","location":"Ollur","email":"ollur.phc@kerala.gov.in","phone":"04872360200","status":"pending","last_sent":""},
        {"name":"Karuvannur PHC","type":"PHC","location":"Karuvannur","email":"karuvannur.phc@kerala.gov.in","phone":"04802700500","status":"pending","last_sent":""},
        {"name":"Thrissur General Hospital","type":"General Hospital","location":"Thrissur","email":"dmotsr@kerala.gov.in","phone":"04872333333","status":"pending","last_sent":""},
        {"name":"Annamanada PHC","type":"PHC","location":"Annamanada","email":"annamanada.phc@kerala.gov.in","phone":"04802700800","status":"pending","last_sent":""},
        {"name":"Arimpur PHC","type":"PHC","location":"Arimpur","email":"arimpur.phc@kerala.gov.in","phone":"04872360300","status":"pending","last_sent":""},
        {"name":"Velookkara PHC","type":"PHC","location":"Velookkara","email":"velookkara.phc@kerala.gov.in","phone":"04802700900","status":"pending","last_sent":""},
        {"name":"Pariyaram PHC","type":"PHC","location":"Pariyaram","email":"pariyaram.phc@kerala.gov.in","phone":"04802700700","status":"pending","last_sent":""},
    ]
    save_centres(rows)

# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(page_title="PMB Outreach — Govt Centres", page_icon="📧", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"]{background:#0f172a;}
[data-testid="stHeader"]{background:transparent;}
h1,h2,h3,.stMetric label{color:#d4a017!important;}
div.stButton>button{background:linear-gradient(135deg,#d4a017,#f0c040);color:#0f172a;font-weight:700;border:none;border-radius:10px;}
</style>
""", unsafe_allow_html=True)

st.title("📧 PMB Jan Aushadhi — Govt Centre Outreach")
st.caption("Sending from: pmbjanaushadhi680006@gmail.com · Chelakottukara, Thrissur")

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Gmail App Password")
    app_password = st.text_input("App Password", type="password",
        value=st.secrets.get("GMAIL_APP_PASSWORD", "") if hasattr(st, "secrets") else "",
        help="Gmail → Security → App Passwords → 16-char password")
    st.markdown("---")
    st.markdown("### ➕ Add New Centre")
    with st.form("add_form"):
        n = st.text_input("Centre Name")
        t = st.selectbox("Type", ["PHC","CHC","Taluk Hospital","District Hospital","General Hospital","Clinic","Private Hospital"])
        l = st.text_input("Location")
        e = st.text_input("Email")
        p = st.text_input("Phone")
        if st.form_submit_button("Add"):
            if n and e:
                rows = load_centres()
                rows.append({"name":n,"type":t,"location":l,"email":e,"phone":p,"status":"pending","last_sent":""})
                save_centres(rows)
                st.success("Added!")
                st.rerun()

# ── MAIN ──────────────────────────────────────────────────────
rows = load_centres()
pending = [r for r in rows if r["status"] == "pending"]
sent    = [r for r in rows if r["status"] == "sent"]

c1, c2, c3 = st.columns(3)
c1.metric("🏥 Total Centres", len(rows))
c2.metric("📬 Pending", len(pending))
c3.metric("✅ Sent", len(sent))

st.markdown("---")

tab1, tab2 = st.tabs(["📬 Pending", "✅ Sent"])

with tab1:
    if not pending:
        st.info("All centres have been emailed!")
    else:
        st.markdown(f"**{len(pending)} centres waiting to receive email**")

        col1, col2 = st.columns([1,4])
        with col1:
            if st.button("📤 Send All Pending", use_container_width=True):
                if not app_password:
                    st.error("Enter Gmail App Password in sidebar.")
                else:
                    prog = st.progress(0)
                    ok = 0
                    for i, centre in enumerate(pending):
                        subj, body = build_email(centre["name"], centre["location"])
                        if send_email(centre["email"], subj, body, app_password):
                            mark_sent(centre["email"])
                            ok += 1
                        prog.progress((i+1)/len(pending))
                    st.success(f"✅ Sent to {ok}/{len(pending)} centres!")
                    st.rerun()

        st.markdown("---")
        for centre in pending:
            with st.expander(f"🏥 {centre['name']} — {centre['location']}"):
                st.write(f"**Type:** {centre['type']}")
                st.write(f"**Email:** {centre['email']}")
                st.write(f"**Phone:** {centre['phone']}")
                subj, body = build_email(centre["name"], centre["location"])
                st.text_area("Preview Email", body, height=200, key=centre["email"])
                if st.button(f"Send to {centre['name']}", key=f"btn_{centre['email']}"):
                    if not app_password:
                        st.error("Enter App Password in sidebar.")
                    else:
                        if send_email(centre["email"], subj, body, app_password):
                            mark_sent(centre["email"])
                            st.success("Sent!")
                            st.rerun()

with tab2:
    if not sent:
        st.info("No emails sent yet.")
    else:
        df_sent = pd.DataFrame(sent)[["name","type","location","email","last_sent"]]
        st.dataframe(df_sent, use_container_width=True)
        if st.button("🔄 Reset All to Pending"):
            for r in rows:
                r["status"] = "pending"
                r["last_sent"] = ""
            save_centres(rows)
            st.success("Reset done!")
            st.rerun()
