import json
from langchain_core.prompts import PromptTemplate
from config import get_llm
from backend.knowledge_base import search_medical_knowledge


def _parse_json(text):
    try:
        text = text.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        try:
            return json.loads(text)
        except Exception:
            pass

        start = text.find("{")
        if start == -1:
            start = text.find("[")

        if start != -1:
            end = max(text.rfind("}"), text.rfind("]"))
            if end != -1:
                return json.loads(text[start:end + 1])

        return {"raw": text}

    except Exception:
        return {"raw": text}


def _safe_knowledge_search(test):
    try:
        query = f"{test.get('name')} {test.get('status')} {test.get('value')} {test.get('unit')}"
        return search_medical_knowledge(query)
    except Exception as e:
        print(f"Knowledge search failed for {test.get('name')}: {e}")
        return []


def _rule_based_specialist(abnormal_tests):
    names = " ".join([t.get("name", "").lower() for t in abnormal_tests])
    statuses = " ".join([t.get("status", "").lower() for t in abnormal_tests])

    if any(x in names for x in ["hba1c", "glucose", "sugar", "insulin"]):
        return "Endocrinologist"

    if any(x in names for x in ["tsh", "t3", "t4", "thyroid"]):
        return "Endocrinologist"

    if any(x in names for x in ["hemoglobin", "hb", "rbc", "wbc", "platelet", "mcv", "mch"]):
        return "Hematologist"

    if any(x in names for x in ["cholesterol", "ldl", "hdl", "triglycerides"]):
        return "Cardiologist"

    if any(x in names for x in ["creatinine", "urea", "uric acid", "egfr"]):
        return "Nephrologist"

    if any(x in names for x in ["sgpt", "sgot", "alt", "ast", "bilirubin", "liver"]):
        return "Gastroenterologist"

    if any(x in names for x in ["vitamin d", "vitamin b12", "calcium"]):
        return "General Physician"

    if "critical" in statuses:
        return "General Physician"

    return "General Physician"


def _fallback_analysis(abnormal_tests):
    explanations = []

    for test in abnormal_tests:
        name = test.get("name", "This test")
        value = test.get("value", "")
        unit = test.get("unit", "")
        normal_range = test.get("normal_range", "Not specified")
        status = test.get("status", "UNKNOWN")

        explanations.append({
            "test_name": name,
            "your_value": f"{value} {unit}".strip(),
            "normal_range": normal_range,
            "status": status,
            "what_it_means": f"{name} is marked {status} compared with the given normal range.",
            "severity": "needs doctor review",
            "possible_condition": "Requires clinical correlation"
        })

    return {"explanations": explanations}


def _fallback_specialist(abnormal_tests):
    primary = _rule_based_specialist(abnormal_tests)
    return {
        "primary_specialist": primary,
        "urgency": "Within 1 week",
        "reason": "Based on the abnormal test categories detected in the report.",
        "booking_message": f"I want to book an appointment with a {primary} to review my lab report.",
        "secondary_specialists": ["General Physician"]
    }


def _fallback_questions(abnormal_tests, specialist):
    primary = specialist.get("primary_specialist", "doctor") if isinstance(specialist, dict) else "doctor"

    questions = [
        "Can you explain what my abnormal values mean?",
        f"Should I consult a {primary} for these results?",
        "Do I need any follow-up tests?",
        "Are medicines needed or should I first try lifestyle changes?",
        "When should I repeat this lab test?"
    ]

    for test in abnormal_tests[:2]:
        test_name = test.get("name", "test")
        questions.append(f"What could be the reason for my abnormal {test_name} value?")

    return {"questions": questions}


def _build_summary(abnormal_tests):
    if not abnormal_tests:
        return "All extracted values are within the provided normal ranges."

    parts = []
    for test in abnormal_tests[:4]:
        parts.append(
            f"{test.get('name', 'A test')} is {test.get('status')} "
            f"at {test.get('value')} {test.get('unit', '')}, "
            f"with normal range {test.get('normal_range', 'Not specified')}"
        )

    return "Abnormal findings: " + "; ".join(parts) + "."


def _validate_explanations(explanations):
    if not isinstance(explanations, list) or len(explanations) == 0:
        return None
    if not all(isinstance(item, dict) and "test_name" in item for item in explanations):
        return None
    return explanations


def _validate_specialist(specialist):
    if not isinstance(specialist, dict) or "primary_specialist" not in specialist:
        return None
    specialist.setdefault("urgency", "Within 1 week")
    specialist.setdefault("reason", "Based on the abnormal tests detected.")
    specialist.setdefault(
        "booking_message",
        f"I want to book an appointment with a {specialist['primary_specialist']} to review my lab report."
    )
    specialist.setdefault("secondary_specialists", ["General Physician"])
    return specialist


def _validate_questions(questions):
    if not isinstance(questions, list) or len(questions) == 0:
        return None
    if not all(isinstance(q, str) for q in questions):
        return None
    return questions


def analyze_report_combined(llm, abnormal_tests, knowledge):
    """
    Single LLM call that returns explanations, specialist recommendation,
    and doctor-prep questions together. Replaces 3 sequential calls with 1
    to cut round-trip latency.

    Falls back per-section: if only one part of the JSON is malformed,
    the other two parsed sections are still used instead of discarding
    everything.
    """
    rule_specialist = _rule_based_specialist(abnormal_tests)
    knowledge_text = (
        "\n".join([k.get("text", "") for k in knowledge[:3]])
        if knowledge else "No extra knowledge found."
    )

    prompt = PromptTemplate(
        input_variables=["abnormal_tests", "knowledge", "rule_specialist"],
        template="""
You are a medical assistant helping a patient understand their lab report
and prepare for a doctor visit. Do this in ONE response covering three
tasks below. Do NOT change any HIGH/LOW/CRITICAL status you are given.

Abnormal tests:
{abnormal_tests}

Relevant medical knowledge:
{knowledge}

Rule-based specialist suggestion (use this unless the tests strongly
suggest a better fit):
{rule_specialist}

Return ONLY one valid JSON object with this exact structure, no markdown,
no explanation outside the JSON:

{{
    "explanations": [
        {{
            "test_name": "name",
            "your_value": "value with unit",
            "normal_range": "range",
            "status": "HIGH/LOW/CRITICAL",
            "what_it_means": "simple explanation",
            "severity": "mild/moderate/severe/needs doctor review",
            "possible_condition": "condition name"
        }}
    ],
    "specialist": {{
        "primary_specialist": "specialist type here",
        "urgency": "Routine / Within 1 week / Soon / Emergency",
        "reason": "one sentence reason here",
        "booking_message": "what to say when booking",
        "secondary_specialists": ["specialist if needed"]
    }},
    "questions": [
        "Question 1 referencing an actual value?",
        "Question 2?",
        "Question 3?",
        "Question 4?",
        "Question 5?",
        "Question 6?"
    ]
}}

Include one "explanations" entry per abnormal test above.
Generate exactly 6 "questions", written in simple first-person language,
referencing the patient's actual values where possible.
"""
    )

    chain = prompt | llm
    result = chain.invoke({
        "abnormal_tests": json.dumps(abnormal_tests, indent=2),
        "knowledge": knowledge_text,
        "rule_specialist": rule_specialist
    })

    parsed = _parse_json(result.content)
    if not isinstance(parsed, dict):
        parsed = {}

    explanations = _validate_explanations(parsed.get("explanations")) \
        or _fallback_analysis(abnormal_tests)["explanations"]

    specialist = _validate_specialist(parsed.get("specialist")) \
        or _fallback_specialist(abnormal_tests)

    questions = _validate_questions(parsed.get("questions")) \
        or _fallback_questions(abnormal_tests, specialist)["questions"]

    return (
        {"explanations": explanations},
        specialist,
        {"questions": questions},
    )


def run_analysis_pipeline(parsed_report):
    tests = parsed_report.get("tests", [])

    abnormal_tests = [
        t for t in tests
        if str(t.get("status", "")).upper() in ["HIGH", "LOW", "CRITICAL"]
    ]

    if not abnormal_tests:
        return {
            "status": "all_normal",
            "message": "All values are within the provided normal range.",
            "summary": "All extracted values are within the provided normal ranges.",
            "patient_name": parsed_report.get("patient_name", "Unknown"),
            "report_date": parsed_report.get("report_date", "Unknown"),
            "total_tests": len(tests),
            "normal_count": len(tests),
            "abnormal_count": 0,
            "abnormal_values": [],
            "analysis": {"explanations": []},
            "specialist": {
                "primary_specialist": "General Physician",
                "urgency": "Routine check-up",
                "reason": "No abnormal values were detected from the provided ranges.",
                "booking_message": "I want to discuss my routine lab report.",
                "secondary_specialists": []
            },
            "questions": {"questions": []}
        }

    knowledge = []
    for test in abnormal_tests:
        knowledge.extend(_safe_knowledge_search(test))

    try:
        llm = get_llm()
        analysis, specialist, questions = analyze_report_combined(
            llm, abnormal_tests, knowledge
        )
    except Exception as e:
        print(f"[Pipeline] Combined LLM call failed, using full fallback: {e}")
        analysis = _fallback_analysis(abnormal_tests)
        specialist = _fallback_specialist(abnormal_tests)
        questions = _fallback_questions(abnormal_tests, specialist)

    return {
        "status": "analysis_complete",
        "summary": _build_summary(abnormal_tests),
        "patient_name": parsed_report.get("patient_name", "Unknown"),
        "report_date": parsed_report.get("report_date", "Unknown"),
        "total_tests": len(tests),
        "normal_count": len(tests) - len(abnormal_tests),
        "abnormal_count": len(abnormal_tests),
        "abnormal_values": abnormal_tests,
        "analysis": analysis,
        "specialist": specialist,
        "questions": questions
    }


if __name__ == "__main__":
    sample = {
        "patient_name": "Rahul Sharma",
        "report_date": "15/06/2024",
        "tests": [
            {
                "name": "HbA1c",
                "value": "7.8",
                "unit": "%",
                "normal_range": "Below 5.7%",
                "status": "HIGH"
            },
            {
                "name": "TSH",
                "value": "8.2",
                "unit": "mIU/L",
                "normal_range": "0.4-4.0",
                "status": "HIGH"
            },
            {
                "name": "Hemoglobin",
                "value": "11.2",
                "unit": "g/dL",
                "normal_range": "13.0-17.0",
                "status": "LOW"
            }
        ]
    }

    print("Running pipeline test...")
    result = run_analysis_pipeline(sample)
    print(json.dumps(result, indent=2))