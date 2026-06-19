# deploy_app.py — completely standalone version
import streamlit as st
import tempfile
import os
import boto3
import pdfplumber
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="AI Lab Report Interpreter", page_icon="🔬")
st.title("🔬 AI Lab Report Interpreter")
st.caption("Week 1 Build")
st.info("Week 1 — PDF extraction working.")

uploaded = st.file_uploader("Upload Lab Report PDF", type=["pdf"])

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    with st.spinner("Reading PDF..."):
        try:
            # Extract text locally
            text = ""
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"

            # Upload to S3
            s3 = boto3.client(
                's3',
                region_name=os.getenv('AWS_REGION'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            s3_key = f"reports/{uploaded.name}"
            s3.upload_file(tmp_path, os.getenv('S3_BUCKET_NAME'), s3_key)

            st.success("✅ PDF uploaded to AWS S3!")
            st.markdown(f"**Stored at:** `s3://{os.getenv('S3_BUCKET_NAME')}/{s3_key}`")

            with st.expander("📄 Extracted Text"):
                st.text(text[:1000])

        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            os.unlink(tmp_path)