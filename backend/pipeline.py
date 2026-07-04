import json
from langchain_core.prompts import PromptTemplate
from config import get_llm
from backend.knowledge_base import search_medical_knowledge


def _parse_json(text):
    try:
        text = text.strip()
        
        # Clean markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        # Try direct parse first
        try:
            return json.loads(text)
        except:
            pass
        
        # Find JSON by looking for { or [
        start = text.find('{')
        if start == -1:
            start = text.find('[')
        
        if start != -1:
            # Find the last } or ]
            end = max(text.rfind('}'), text.rfind(']'))
            if end != -1:
                json_str = text[start:end+1]
                return json.loads(json_str)
        
        return {"raw": text}
        
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
You are a medical assistant. Output ONLY a JSON object. No explanation. No markdown. No text before or after.

Patient analysis:
{analysis}

Medical knowledge:
{knowledge}

Output this exact JSON structure:
{{
    "primary_specialist": "specialist type here",
    "urgency": "Within 1 week",
    "reason": "one sentence reason here",
    "booking_message": "what to say when booking",
    "secondary_specialists": ["specialist if needed"]
}}

IMPORTANT: Output ONLY the JSON. Nothing else. No notes. No explanation.
"""
    )
    knowledge_text = "\n".join([k["text"] for k in knowledge[:3]])
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
    import json
    print(json.dumps(result, indent=2))
