MEDICAL_KNOWLEDGE = [
    # DIABETES
    {
        "id": "hba1c_high",
        "text": "HbA1c above 6.5% confirms diabetes mellitus. Values 5.7-6.4% indicate prediabetes. Consult Endocrinologist urgently. Indicates poor blood sugar control over 3 months.",
        "parameter": "HbA1c", "condition": "Diabetes",
        "specialist": "Endocrinologist", "urgency": "Within 1 week"
    },
    {
        "id": "fasting_glucose_high",
        "text": "Fasting glucose above 126 mg/dL on two occasions confirms diabetes. Values 100-125 indicate prediabetes. Consult Endocrinologist or General Physician.",
        "parameter": "Fasting Glucose", "condition": "Diabetes",
        "specialist": "Endocrinologist", "urgency": "Within 1 week"
    },
    # THYROID
    {
        "id": "tsh_high",
        "text": "TSH above 4.0 mIU/L indicates hypothyroidism. Symptoms: fatigue, weight gain, cold sensitivity, depression. Consult Endocrinologist. Usually requires thyroid hormone replacement.",
        "parameter": "TSH", "condition": "Hypothyroidism",
        "specialist": "Endocrinologist", "urgency": "Within 1 week"
    },
    {
        "id": "tsh_low",
        "text": "TSH below 0.4 mIU/L indicates hyperthyroidism. Symptoms: weight loss, rapid heartbeat, anxiety, sweating. Consult Endocrinologist immediately. Can affect heart.",
        "parameter": "TSH", "condition": "Hyperthyroidism",
        "specialist": "Endocrinologist", "urgency": "Within 3 days"
    },
    # BLOOD / ANEMIA
    {
        "id": "hemoglobin_low_male",
        "text": "Hemoglobin below 13 g/dL in men indicates anemia. Causes: iron deficiency, B12 deficiency, or chronic disease. Consult General Physician or Hematologist.",
        "parameter": "Hemoglobin", "condition": "Anemia",
        "specialist": "General Physician", "urgency": "Within 2 weeks"
    },
    {
        "id": "hemoglobin_low_female",
        "text": "Hemoglobin below 12 g/dL in women indicates anemia. Very common in Indian women. Consult General Physician. Iron supplements and dietary changes needed.",
        "parameter": "Hemoglobin", "condition": "Anemia",
        "specialist": "General Physician", "urgency": "Within 2 weeks"
    },
    {
        "id": "hemoglobin_critical",
        "text": "Hemoglobin below 8 g/dL is severe anemia requiring immediate attention. May need blood transfusion. Go to hospital immediately.",
        "parameter": "Hemoglobin", "condition": "Severe Anemia",
        "specialist": "Emergency/Hematologist", "urgency": "Immediately"
    },
    # KIDNEY
    {
        "id": "creatinine_high",
        "text": "Creatinine above 1.2 mg/dL in women or 1.4 mg/dL in men indicates impaired kidney function. Could be chronic kidney disease. Consult Nephrologist. Stay hydrated, avoid NSAIDs.",
        "parameter": "Creatinine", "condition": "Kidney Disease",
        "specialist": "Nephrologist", "urgency": "Within 1 week"
    },
    {
        "id": "urea_high",
        "text": "Blood urea above 20 mg/dL may indicate kidney dysfunction or dehydration. Consult Nephrologist if consistently high. Increase water intake.",
        "parameter": "Blood Urea", "condition": "Kidney Dysfunction",
        "specialist": "Nephrologist", "urgency": "Within 2 weeks"
    },
    # LIVER
    {
        "id": "sgpt_high",
        "text": "SGPT/ALT above 40 U/L indicates liver cell damage. Could be fatty liver, hepatitis, or medication side effects. Consult Gastroenterologist. Avoid alcohol completely.",
        "parameter": "SGPT", "condition": "Liver Disease",
        "specialist": "Gastroenterologist", "urgency": "Within 1 week"
    },
    {
        "id": "sgot_high",
        "text": "SGOT/AST above 40 U/L indicates liver or muscle damage. Can indicate heart problems if very high. Consult Gastroenterologist. Avoid alcohol and hepatotoxic medications.",
        "parameter": "SGOT", "condition": "Liver/Heart Issue",
        "specialist": "Gastroenterologist", "urgency": "Within 1 week"
    },
    # CHOLESTEROL
    {
        "id": "cholesterol_high",
        "text": "Total cholesterol above 200 mg/dL increases cardiovascular risk. Above 240 is high risk. Consult Cardiologist. Lifestyle changes and statins may be needed.",
        "parameter": "Total Cholesterol", "condition": "Hypercholesterolemia",
        "specialist": "Cardiologist", "urgency": "Within 2 weeks"
    },
    {
        "id": "ldl_high",
        "text": "LDL above 130 mg/dL increases heart disease risk. Above 160 is high risk. Consult Cardiologist. Diet low in saturated fat and regular exercise essential.",
        "parameter": "LDL", "condition": "High Bad Cholesterol",
        "specialist": "Cardiologist", "urgency": "Within 2 weeks"
    },
    # VITAMINS
    {
        "id": "vitamin_d_low",
        "text": "Vitamin D below 20 ng/mL indicates deficiency. Very common in India. Causes bone weakness, fatigue, depression. Consult General Physician. Sunlight + supplements needed.",
        "parameter": "Vitamin D", "condition": "Vitamin D Deficiency",
        "specialist": "General Physician", "urgency": "Within 1 month"
    },
    {
        "id": "vitamin_b12_low",
        "text": "Vitamin B12 below 200 pg/mL indicates deficiency. Common in vegetarians. Causes nerve damage, anemia, fatigue. Consult General Physician. B12 injections or supplements needed.",
        "parameter": "Vitamin B12", "condition": "B12 Deficiency",
        "specialist": "General Physician", "urgency": "Within 2 weeks"
    },
    # URIC ACID
    {
        "id": "uric_acid_high",
        "text": "Uric acid above 7 mg/dL in men or 6 mg/dL in women causes hyperuricemia and gout. Consult Rheumatologist. Avoid red meat, alcohol, and high-purine foods.",
        "parameter": "Uric Acid", "condition": "Hyperuricemia/Gout",
        "specialist": "Rheumatologist", "urgency": "Within 2 weeks"
    },
    # WBC + PLATELETS
    {
        "id": "wbc_high",
        "text": "WBC above 11000 cells/mcL indicates infection, inflammation, or rarely blood disorders. Body is fighting an infection. Consult General Physician. Further tests to identify cause.",
        "parameter": "WBC", "condition": "Infection/Inflammation",
        "specialist": "General Physician", "urgency": "Within 1 week"
    },
    {
        "id": "platelets_low",
        "text": "Platelets below 150000/mcL (thrombocytopenia) increases bleeding risk. Could be viral infection, medications, or bone marrow issues. Consult Hematologist. Avoid blood thinners.",
        "parameter": "Platelets", "condition": "Thrombocytopenia",
        "specialist": "Hematologist", "urgency": "Within 3 days"
    },
    # IRON
    {
        "id": "ferritin_low",
        "text": "Ferritin below 12 ng/mL indicates iron deficiency even if hemoglobin normal. Early stage anemia. Consult General Physician. Iron-rich diet and supplements needed.",
        "parameter": "Ferritin", "condition": "Iron Deficiency",
        "specialist": "General Physician", "urgency": "Within 2 weeks"
    },
]