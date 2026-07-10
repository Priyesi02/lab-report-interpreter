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

    llm = get_llm()

    try:
        analysis = analyse_abnormal_values(llm, abnormal_tests)
        if not analysis or "explanations" not in analysis:
            analysis = _fallback_analysis(abnormal_tests)
    except Exception as e:
        print(f"Analysis LLM failed: {e}")
        analysis = _fallback_analysis(abnormal_tests)

    knowledge = []
    for test in abnormal_tests:
        knowledge.extend(_safe_knowledge_search(test))

    try:
        specialist = recommend_specialist(llm, analysis, knowledge, abnormal_tests)
    except Exception as e:
        print(f"Specialist LLM failed: {e}")
        primary = _rule_based_specialist(abnormal_tests)
        specialist = {
            "primary_specialist": primary,
            "urgency": "Within 1 week",
            "reason": "Based on the abnormal test categories detected in the report.",
            "booking_message": f"I want to book an appointment with a {primary} to review my lab report.",
            "secondary_specialists": ["General Physician"]
        }

    try:
        questions = generate_questions(llm, analysis, specialist)
        if not questions or "questions" not in questions:
            questions = _fallback_questions(abnormal_tests, specialist)
    except Exception as e:
        print(f"Questions LLM failed: {e}")
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


def analyse_abnormal_values(llm, abnormal_tests):
    prompt = PromptTemplate(
        input_variables=["abnormal_tests"],
        template="""
You are a medical assistant explaining lab results in simple language.

Only explain the tests already marked abnormal.
Do NOT change their HIGH/LOW/NORMAL status.

Abnormal tests:
{abnormal_tests}

Return ONLY valid JSON:
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
    ]
}}
"""
    )

    chain = prompt | llm
    result = chain.invoke({"abnormal_tests": json.dumps(abnormal_tests, indent=2)})
    return _parse_json(result.content)


def recommend_specialist(llm, analysis, knowledge, abnormal_tests):
    rule_specialist = _rule_based_specialist(abnormal_tests)

    prompt = PromptTemplate(
        input_variables=["analysis", "knowledge", "rule_specialist"],
        template="""
You are a medical assistant. Output ONLY a JSON object.

Patient analysis:
{analysis}

Medical knowledge:
{knowledge}

Rule-based specialist suggestion:
{rule_specialist}

Use the rule-based suggestion unless the analysis strongly suggests a better specialist.

Output this exact JSON structure:
{{
    "primary_specialist": "specialist type here",
    "urgency": "Routine / Within 1 week / Soon / Emergency",
    "reason": "one sentence reason here",
    "booking_message": "what to say when booking",
    "secondary_specialists": ["specialist if needed"]
}}
"""
    )

    knowledge_text = "\n".join([k.get("text", "") for k in knowledge[:3]]) if knowledge else "No extra knowledge found."

    chain = prompt | llm
    result = chain.invoke({
        "analysis": json.dumps(analysis, indent=2),
        "knowledge": knowledge_text,
        "rule_specialist": rule_specialist
    })

    specialist = _parse_json(result.content)

    if not specialist or "primary_specialist" not in specialist:
        specialist = {}

    specialist.setdefault("primary_specialist", rule_specialist)
    specialist.setdefault("urgency", "Within 1 week")
    specialist.setdefault("reason", "Based on the abnormal tests detected.")
    specialist.setdefault(
        "booking_message",
        f"I want to book an appointment with a {specialist['primary_specialist']} to review my lab report."
    )
    specialist.setdefault("secondary_specialists", ["General Physician"])

    return specialist


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


def generate_questions(llm, analysis, specialist):
    prompt = PromptTemplate(
        input_variables=["analysis", "specialist"],
        template="""
Help a patient prepare for their doctor appointment.

Their abnormal results:
{analysis}

They are visiting:
{specialist}

Generate 6 specific questions to ask the doctor.
Reference their ACTUAL values where possible.
Use simple first-person language.

Return ONLY valid JSON:
{{
    "questions": ["Question 1?", "Question 2?"]
}}
"""
    )

    chain = prompt | llm
    result = chain.invoke({
        "analysis": json.dumps(analysis, indent=2),
        "specialist": json.dumps(specialist, indent=2)
    })

    return _parse_json(result.content)


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