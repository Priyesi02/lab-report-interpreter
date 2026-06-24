import streamlit as st
import tempfile
import os
import boto3
import pdfplumber
from dotenv import load_dotenv

from backend.parser import parse_lab_values
from backend.pipeline import run_analysis_pipeline
from backend.doctor_search import search_nearby_doctors

load_dotenv()

st.set_page_config(
    page_title="AI Lab Report Interpreter",
    page_icon="🔬",
    layout="wide"
)


def status_style(status):
    status = str(status).upper()

    if status == "HIGH":
        return "#fee2e2", "#dc2626", "🔴"
    elif status == "LOW":
        return "#ffedd5", "#ea580c", "🟠"
    elif status == "CRITICAL":
        return "#fecaca", "#991b1b", "🚨"
    else:
        return "#dcfce7", "#16a34a", "🟢"


def test_card(item):
    bg, color, icon = status_style(item.get("status", "NORMAL"))

    st.markdown(
        f"""
        <div style="
            background:{bg};
            border-left:6px solid {color};
            padding:18px;
            border-radius:16px;
            margin-bottom:16px;
        ">
            <h4>{icon} {item.get("test_name", "Test")}</h4>
            <p><b>Your Value:</b> {item.get("your_value", "Not available")}</p>
            <p><b>Normal Range:</b> {item.get("normal_range", "Not specified")}</p>
            <p><b>Status:</b> <span style="color:{color};font-weight:bold;">{item.get("status", "")}</span></p>
            <p><b>Severity:</b> {item.get("severity", "Not specified")}</p>
            <p><b>Meaning:</b> {item.get("what_it_means", "")}</p>
            <p><b>Possible Condition:</b> {item.get("possible_condition", "")}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def doctor_card(specialist):
    st.markdown(
        f"""
        <div style="
            background:#e8f1ff;
            padding:22px;
            border-radius:18px;
            margin-bottom:18px;
            border:1px solid #bfdbfe;
        ">
            <h3>👨‍⚕️ Recommended Specialist</h3>
            <p><b>Doctor:</b> {specialist.get("primary_specialist", "General Physician")}</p>
            <p><b>Urgency:</b> {specialist.get("urgency", "Not specified")}</p>
            <p><b>Reason:</b> {specialist.get("reason", "")}</p>
            <p><b>Booking Message:</b> {specialist.get("booking_message", "")}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


st.title("🔬 AI Lab Report Interpreter")
st.caption("Upload your lab report and get simple AI-powered insights.")
st.info("Week 2 - PDF extraction + lab value parsing + AI analysis working.")

uploaded = st.file_uploader("Upload Lab Report PDF", type=["pdf"])

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    try:
        with st.spinner("Reading PDF..."):
            text = ""

            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"

        if not text.strip():
            st.error("Could not extract text from this PDF.")
            st.stop()

        with st.spinner("Uploading to AWS S3..."):
            s3 = boto3.client(
                "s3",
                region_name=os.getenv("AWS_REGION"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
            )

            s3_key = f"reports/{uploaded.name}"
            s3.upload_file(tmp_path, os.getenv("S3_BUCKET_NAME"), s3_key)

        st.success("✅ PDF uploaded to AWS S3!")
        st.markdown(f"**Stored at:** `s3://{os.getenv('S3_BUCKET_NAME')}/{s3_key}`")

        with st.spinner("Extracting lab values using AI..."):
            parsed = parse_lab_values(text)

        if not parsed:
            st.error("Could not parse lab values.")
            st.stop()

        with st.expander("🧾 Extracted Lab Values"):
            st.json(parsed)

        with st.spinner("Running AI analysis..."):
            analysis = run_analysis_pipeline(parsed)

        st.divider()
        st.subheader("📊 Health Summary")

        total = analysis.get("total_tests", 0)
        normal = analysis.get("normal_count", 0)
        abnormal = analysis.get("abnormal_count", 0)

        health_score = max(40, 100 - abnormal * 10)

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("❤️ Health Score", f"{health_score}/100")
        col2.metric("🧪 Total Tests", total)
        col3.metric("✅ Normal", normal)
        col4.metric("⚠️ Abnormal", abnormal)

        st.progress(health_score / 100)

        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "🧾 Summary",
                "⚠️ Abnormal Values",
                "👨‍⚕️ Doctor Prep",
                "📍 Nearby Doctors"
            ]
        )

        with tab1:
            st.subheader("Overall Summary")

            if abnormal > 0:
                st.warning(f"{abnormal} value(s) need attention.")
            else:
                st.success("All values look normal.")

            st.write(f"**Patient:** {analysis.get('patient_name', 'Unknown')}")
            st.write(f"**Report Date:** {analysis.get('report_date', 'Unknown')}")

            st.subheader("🗓️ Next Steps Timeline")
            st.write("✅ Report analysed")
            st.write("🧪 Abnormal values identified")
            st.write("👨‍⚕️ Specialist recommendation generated")
            st.write("📍 Nearby doctor search available")
            st.write("🔁 Follow up with a doctor if needed")

        with tab2:
            st.subheader("Test Result Cards")

            explanations = analysis.get("analysis", {}).get("explanations", [])

            if explanations:
                for item in explanations:
                    test_card(item)
            else:
                st.success("No abnormal values found.")

        with tab3:
            specialist = analysis.get("specialist", {})

            if specialist:
                doctor_card(specialist)

            st.subheader("❓ Questions to Ask Doctor")

            questions = analysis.get("questions", {}).get("questions", [])

            if questions:
                for q in questions:
                    st.checkbox(q)
            else:
                st.info("No questions generated.")

        with tab4:
            st.subheader("📍 Nearby Specialists")

            specialist = analysis.get("specialist", {})
            specialist_name = specialist.get("primary_specialist", "General Physician")

            city = st.text_input("Enter your city", value="Delhi")

            if st.button("Find Nearby Specialists"):
                with st.spinner("Searching nearby specialists..."):
                    doctors = search_nearby_doctors(specialist_name, city)

                if doctors:
                    for doc in doctors:
                        st.markdown(
                            f"""
                            <div style="
                                background:#f8fafc;
                                padding:18px;
                                border-radius:16px;
                                border:1px solid #e2e8f0;
                                margin-bottom:14px;
                            ">
                                <h4>🏥 {doc.get('name', 'Unknown')}</h4>
                                <p><b>Address:</b> {doc.get('address', 'Not available')}</p>
                                <p><b>Rating:</b> ⭐ {doc.get('rating', 'No rating')} ({doc.get('reviews', 0)} reviews)</p>
                                <p><b>Phone:</b> {doc.get('phone', 'Not available')}</p>
                                <p><b>Website:</b> {doc.get('website', 'Not available')}</p>
                                <p><b>Maps:</b> {doc.get('maps_link', 'Not available')}</p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.warning("No doctors found.")

    except Exception as e:
        st.error(f"Error: {e}")

    finally:
        os.unlink(tmp_path)