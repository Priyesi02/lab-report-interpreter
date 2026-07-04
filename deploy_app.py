import streamlit as st
import tempfile
import os
import pdfplumber
from dotenv import load_dotenv

from backend.parser import parse_lab_values
from backend.pipeline import run_analysis_pipeline
from backend.doctor_search import search_nearby_doctors

load_dotenv()

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="AI Lab Report Interpreter",
    page_icon="🔬",
    layout="wide"
)

# =========================
# GLOBAL STYLE (FULL UI RESET)
# =========================
st.markdown("""
<style>

/* Hide Streamlit UI */
#MainMenu, footer, header {visibility: hidden;}

/* App background */
.stApp {
    background: #f4f6f8;
    font-family: Inter, system-ui, sans-serif;
}

/* Container */
.block-container {
    padding: 1.5rem 2rem;
    max-width: 1200px;
}

/* Smooth UI feel */
::-webkit-scrollbar {
    width: 6px;
}
::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)

# =========================
# TOP NAV
# =========================
def top_nav():
    st.markdown("""
    <div style="
        background:white;
        padding:16px 22px;
        border-radius:18px;
        display:flex;
        justify-content:space-between;
        align-items:center;
        box-shadow:0 8px 30px rgba(0,0,0,0.06);
        margin-bottom:20px;
    ">
        <div style="font-size:18px; font-weight:800; color:#111827;">
            🔬 AI Lab Report Interpreter
        </div>

        <div style="font-size:13px; color:#6b7280;">
            Medical AI Dashboard
        </div>
    </div>
    """, unsafe_allow_html=True)


# =========================
# KPI ROW
# =========================
def kpi_row(health, total, normal, abnormal):

    st.markdown(f"""
    <div style="display:flex; gap:14px; margin-bottom:20px;">

        <div style="flex:1; background:white; padding:18px; border-radius:18px;
            box-shadow:0 8px 25px rgba(0,0,0,0.06);">
            <div style="color:#6b7280; font-size:13px;">❤️ Health Score</div>
            <div style="font-size:26px; font-weight:800; color:#56d9d6;">
                {health}/100
            </div>
        </div>

        <div style="flex:1; background:white; padding:18px; border-radius:18px;">
            <div style="color:#6b7280;">🧪 Total Tests</div>
            <div style="font-size:22px; font-weight:700;">{total}</div>
        </div>

        <div style="flex:1; background:white; padding:18px; border-radius:18px;">
            <div style="color:#6b7280;">✅ Normal</div>
            <div style="font-size:22px; font-weight:700; color:#16a34a;">{normal}</div>
        </div>

        <div style="flex:1; background:white; padding:18px; border-radius:18px;">
            <div style="color:#6b7280;">⚠️ Abnormal</div>
            <div style="font-size:22px; font-weight:700; color:#dc2626;">{abnormal}</div>
        </div>

    </div>
    """, unsafe_allow_html=True)


# =========================
# UPLOAD UI (CUSTOM CARD)
# =========================
def upload_ui():
    st.markdown("""
    <div style="
        background:white;
        padding:24px;
        border-radius:20px;
        box-shadow:0 10px 30px rgba(0,0,0,0.06);
        margin-bottom:20px;
    ">
        <h3 style="margin:0;">Upload Medical Report</h3>
        <p style="color:#6b7280;">PDF format supported</p>
    </div>
    """, unsafe_allow_html=True)

    return st.file_uploader("Drop your file here", type=["pdf"])


# =========================
# PROCESS FILE
# =========================
def process(uploaded):

    with st.spinner("Analyzing report..."):

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded.read())
            path = tmp.name

        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                if page.extract_text():
                    text += page.extract_text()

        parsed = parse_lab_values(text)
        analysis = run_analysis_pipeline(parsed)

        st.session_state.analysis = analysis

        os.unlink(path)

    st.success("Analysis complete!")
    st.rerun()


# =========================
# DASHBOARD VIEW
# =========================
def dashboard():

    a = st.session_state.analysis

    if not a:
        st.error("No analysis found")
        return

    total = a.get("total_tests", 0)
    normal = a.get("normal_count", 0)
    abnormal = a.get("abnormal_count", 0)

    health = max(40, 100 - abnormal * 10)

    # NAV
    top_nav()

    # KPIs
    kpi_row(health, total, normal, abnormal)

    # SUMMARY CARD
    st.markdown(f"""
    <div style="
        background:white;
        padding:20px;
        border-radius:20px;
        box-shadow:0 8px 25px rgba(0,0,0,0.06);
        margin-bottom:20px;
    ">
        <h3>Patient Summary</h3>
        <p><b>Name:</b> {a.get("patient_name","")}</p>
        <p><b>Date:</b> {a.get("report_date","")}</p>
    </div>
    """, unsafe_allow_html=True)

    # ABNORMAL SECTION
    st.markdown("""
    <h3 style="margin-top:10px;">⚠️ Abnormal Findings</h3>
    """, unsafe_allow_html=True)

    for item in a.get("analysis", {}).get("explanations", []):
        status = item.get("status", "NORMAL").upper()
        color = {
            "HIGH": "#dc2626",
            "LOW": "#ea580c",
            "CRITICAL": "#991b1b",
            "NORMAL": "#16a34a"
        }.get(status, "#16a34a")

        st.markdown(f"""
        <div style="
            background:white;
            border-left:6px solid {color};
            padding:16px;
            border-radius:18px;
            margin-bottom:12px;
            box-shadow:0 8px 25px rgba(0,0,0,0.06);
        ">
            <div style="display:flex; justify-content:space-between;">
                <b>{item.get("test_name","Test")}</b>
                <span style="color:{color}; font-weight:700;">{status}</span>
            </div>

            <div style="color:#6b7280; margin-top:8px;">
                <b>Your Value:</b> {item.get("your_value","")}
            </div>

            <div style="color:#6b7280;">
                <b>Normal Range:</b> {item.get("normal_range","")}
            </div>

            <div style="margin-top:8px; color:#111827;">
                {item.get("what_it_means","")}
            </div>
        </div>
        """, unsafe_allow_html=True)


# =========================
# APP ROUTER
# =========================
if "analysis" not in st.session_state:
    st.session_state.analysis = None

if st.session_state.analysis is None:
    top_nav()
    uploaded = upload_ui()

    if uploaded and st.button("Analyze Report 🚀"):
        process(uploaded)

else:
    dashboard()