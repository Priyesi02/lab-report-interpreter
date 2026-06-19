import boto3
import pdfplumber
import os
from dotenv import load_dotenv
load_dotenv()

def extract_text_local(file_path):
    """
    Fallback: local extraction using pdfplumber.
    Use ONLY if Textract fails or for offline testing.
    """
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        print(f"[Extractor] Local: extracted {len(text)} chars")
        return text
    except Exception as e:
        print(f"[Extractor] Local failed: {e}")
        return None

def extract_text_textract(file_path):
    """
    PRIMARY: AWS Textract extraction.
    Use this from Day 1 — it's your AWS feature.
    Handles PDFs, images, even handwritten text better than pdfplumber.
    """
    region = os.getenv('AWS_REGION', 'ap-south-1')
    bucket = os.getenv('S3_BUCKET_NAME')

    s3 = boto3.client('s3', region_name=region)
    textract = boto3.client('textract', region_name=region)

    # Step 1: Upload to S3
    file_name = f"reports/{os.path.basename(file_path)}"
    s3.upload_file(file_path, bucket, file_name)
    print(f"[Extractor] Uploaded to S3: s3://{bucket}/{file_name}")

    # Step 2: Run Textract
    response = textract.detect_document_text(
        Document={
            'S3Object': {
                'Bucket': bucket,
                'Name': file_name
            }
        }
    )

    # Step 3: Parse response blocks
    text = ""
    for block in response['Blocks']:
        if block['BlockType'] == 'LINE':
            text += block['Text'] + "\n"

    print(f"[Extractor] Textract: extracted {len(text)} chars")
    return text

def extract_text(file_path):
    """
    Main entry point.
    Always tries Textract first (AWS hackathon = use AWS!).
    Falls back to local if Textract fails.
    """
    from config import USE_AWS_TEXTRACT

    if USE_AWS_TEXTRACT:
        try:
            return extract_text_textract(file_path)
        except Exception as e:
            print(f"[Extractor] Textract failed, falling back to local: {e}")
            return extract_text_local(file_path)
    else:
        return extract_text_local(file_path)


# Test
if __name__ == "__main__":
    # Download any sample blood test PDF from internet
    result = extract_text("report.pdf")
    print(result[:500])