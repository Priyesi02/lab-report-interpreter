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
        return json.loads(text)
    except Exception:
        return {"raw": text}


def run_analysis_pipeline(parsed_report):
    llm = get_llm()
    abnormal_tests = [
        t for t in parsed_report["tests"]
        if t["status"] in ["HIGH", "LOW", "CRITICAL"]
    ]
    if not abnormal_tests:
        return {
            "status": "all_normal",
            "message": "All values are within normal range!",
            "patient_name": parsed_report.get("patient_name", "Unknown"),
            "report_date": parsed_report.get("report_date", "Unknown"),
            "total_tests": len(parsed_report["tests"]),
            "normal_count": len(parsed_report["tests"]),
            "abnormal_count": 0,
            "analysis": {"explanations": []},
            "specialist": {},
            "questions": {"questions": []}
        }
    analysis = analyse_abnormal_values(llm, abnormal_tests)
    knowledge = []
    for test in abnormal_tests:
        query = f"{test['name']} is {test['value']} {test['unit']} which is {test['status']}"
        knowledge.extend(search_medical_knowledge(query))
    specialist = recommend_specialist(llm, analysis, knowledge)
    questions = generate_questions(llm, analysis, specialist)
    return {
        "status": "analysis_complete",
        "patient_name": parsed_report.get("patient_name", "Unknown"),
        "report_date": parsed_report.get("report_date", "Unknown"),
        "total_tests": len(parsed_report["tests"]),
        "normal_count": len(parsed_report["tests"]) - len(abnormal_tests),
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
You are a medical expert explaining lab results in simple language.
These lab values are abnormal:
{abnormal_tests}
For each explain:
1. What this test measures
2. What it means when high/low
3. Severity: mild/moderate/severe
4. What condition it might indicate
Use simple language. No jargon.
Return ONLY valid JSON:
{{
    "explanations": [
        {{
            "test_name": "name",
            "your_value": "value with unit",
            "normal_range": "range",
            "status": "HIGH/LOW/CRITICAL",
            "what_it_means": "simple explanation",
            "severity": "mild/moderate/severe",
            "possible_condition": "condition name"
        }}
    ]
}}
"""
    )
    chain = prompt | llm
    result = chain.invoke({"abnormal_tests": json.dumps(abnormal_tests, indent=2)})
    return _parse_json(result.content)


def recommend_specialist(llm, analysis, knowledge):
    prompt = PromptTemplate(
        input_variables=["analysis", "knowledge"],
        template="""
Help a patient find the right doctor based on abnormal lab results.
Patient analysis: {analysis}
Medical knowledge: {knowledge}
Return ONLY valid JSON:
{{
    "primary_specialist": "specialist type",
    "urgency": "Immediately / Within 3 days / Within 1 week / Within 1 month",
    "reason": "why this specialist",
    "booking_message": "what to say when booking",
    "secondary_specialists": ["if needed"]
}}
"""
    )
    knowledge_text = "\n".join([k["text"] for k in knowledge[:5]])
    chain = prompt | llm
    result = chain.invoke({
        "analysis": json.dumps(analysis, indent=2),
        "knowledge": knowledge_text
    })
    return _parse_json(result.content)


def generate_questions(llm, analysis, specialist):
    prompt = PromptTemplate(
        input_variables=["analysis", "specialist"],
        template="""
Help a patient prepare for their doctor appointment.
Their abnormal results: {analysis}
They are visiting: {specialist}
Generate 6-8 specific questions to ask the doctor.
Reference their ACTUAL values. Simple first-person language.
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
