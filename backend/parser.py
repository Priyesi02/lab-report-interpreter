# backend/parser.py
import json
from config import get_llm
from langchain_core.prompts import PromptTemplate


def _parse_json(text):
    try:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)
    except Exception:
        return None


def parse_lab_values(raw_text):
    """
    Extracts all test values from raw text into structured JSON.
    """
    llm = get_llm()

    prompt = PromptTemplate(
        input_variables=["raw_text"],
        template="""
You are a medical data extraction assistant.
Extract ALL lab test values from this report text.
Return ONLY valid JSON, no explanation, no markdown:
{{
    "patient_name": "name or Unknown",
    "report_date": "date or Unknown",
    "tests": [
        {{
            "name": "test name",
            "value": "numeric value as string",
            "unit": "unit of measurement",
            "normal_range": "normal range as string",
            "status": "NORMAL or HIGH or LOW or CRITICAL"
        }}
    ]
}}

Rules:
- Do not return a list. Always return one JSON object with patient_name, report_date, and tests.
- Do not write comments, explanations, or trailing commas.
- Extract every single test mentioned
- If normal range not mentioned write "Not specified"
- NORMAL = value within range
- HIGH = value above range
- LOW = value below range
- CRITICAL = dangerously outside range

IMPORTANT:
- Output ONLY valid JSON.
- Do not wrap the JSON in markdown.
- Do not add any explanation before or after the JSON.

Report text:
{raw_text}
        """
    )

    chain = prompt | llm

    try:
        result = chain.invoke({"raw_text": raw_text})
        text = result.content.strip()

        # Clean markdown if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        print("RAW LLM OUTPUT:")
        print(text)

        parsed = json.loads(text)

        if isinstance(parsed, list):
            parsed = {
                "patient_name": "Unknown",
                "report_date": "Unknown",
                "tests": parsed
            }

        print(f"[Parser] Extracted {len(parsed.get('tests', []))} test values")
        return parsed

    except json.JSONDecodeError as e:
        print(f"[Parser] JSON error: {e}")
        return None
    except Exception as e:
        print(f"[Parser] Error: {e}")
        return None


# Test
if __name__ == "__main__":
    sample = """
    Patient: Rahul Sharma | Date: 15/06/2024
    HbA1c: 7.8% (Normal: Below 5.7%)
    TSH: 8.2 mIU/L (Normal: 0.4-4.0)
    Hemoglobin: 11.2 g/dL (Normal: 13.0-17.0)
    Vitamin D: 18 ng/mL (Normal: 20-50)
    WBC: 7500 cells/mcL (Normal: 4500-11000)
    """

    result = parse_lab_values(sample)
    print(json.dumps(result, indent=2))