import sys

sys.path.append("..")

from knowledge_base.medical_data import MEDICAL_KNOWLEDGE
from config import TOP_K_RESULTS


def search_medical_knowledge(query, n_results=TOP_K_RESULTS):
    query_lower = query.lower()
    scored_results = []

    for item in MEDICAL_KNOWLEDGE:
        score = 0

        searchable_text = (
            item["text"] + " " +
            item["parameter"] + " " +
            item["condition"] + " " +
            item["specialist"] + " " +
            item["urgency"]
        ).lower()

        for word in query_lower.split():
            if word in searchable_text:
                score += 1

        if item["parameter"].lower() in query_lower:
            score += 5

        if item["condition"].lower() in query_lower:
            score += 3

        if score > 0:
            scored_results.append((score, item))

    scored_results.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "text": item["text"],
            "metadata": {
                "parameter": item["parameter"],
                "condition": item["condition"],
                "specialist": item["specialist"],
                "urgency": item["urgency"],
            },
        }
        for score, item in scored_results[:n_results]
    ]