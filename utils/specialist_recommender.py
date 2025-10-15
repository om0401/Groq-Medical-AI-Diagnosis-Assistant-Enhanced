# utils/specialist_recommender.py
import re
from typing import Optional, Dict

_SPECIALIST_KEYWORDS = {
    "Pulmonologist": ["cough", "shortness of breath", "dyspnea", "wheezing", "respiratory", "lung", "pneumonia", "opacity", "pleural", "spO2", "spo2"],
    "Cardiologist": ["chest pain", "palpitation", "palpitations", "arrhythmia", "tachycardia", "bradycardia", "heart", "cardiac", "ischemia"],
    "Neurologist": ["headache", "seizure", "dizziness", "weakness", "neurologic", "numbness", "stroke", "syncope"],
    "Gastroenterologist": ["abdominal", "nausea", "vomit", "diarrhea", "abdomen", "liver", "hepatitis", "jaundice"],
    "Orthopedician": ["fracture", "bone", "joint", "sprain", "back pain", "hip", "knee", "arthritis"],
    "ENT": ["ear", "nose", "throat", "hoarseness", "sinus", "otitis"],
    "Dermatologist": ["rash", "itch", "skin", "dermato", "lesion", "erythema"],
    "Oncologist": ["mass", "tumor", "metastasis", "neoplasm", "cancer"],
    "Infectious Disease": ["fever", "sepsis", "bacteremia", "viral", "infection", "abscess"],
    "Pulmonary / Critical Care": ["respiratory failure", "intubation", "ARDS", "ICU", "mechanical ventilation"]
}

def _normalize_text(text: str) -> str:
    return (text or "").lower()

def recommend_specialist(symptoms_text: str, image_findings: Optional[str] = "", vitals: Optional[Dict] = None) -> Dict:
    """
    Returns a recommended specialist, confidence score and rationale.
    Deterministic rule-based keyword matching + simple vitals heuristics.
    """
    text = _normalize_text(symptoms_text) + " " + _normalize_text(image_findings or "")
    scores = {k: 0 for k in _SPECIALIST_KEYWORDS.keys()}

    for specialist, keywords in _SPECIALIST_KEYWORDS.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", text):
                scores[specialist] += 1

    # Vitals heuristics
    vitals_notes = []
    if vitals:
        try:
            hr = vitals.get("heart_rate")
            spo2 = vitals.get("spo2") or vitals.get("spO2")
            temp = vitals.get("temperature")
            if temp and isinstance(temp, (int, float)) and temp >= 38:
                vitals_notes.append(f"Fever {temp}°C")
                scores["Infectious Disease"] += 1
            if spo2 and isinstance(spo2, (int, float)) and spo2 < 92:
                vitals_notes.append(f"Low SpO₂ {spo2}%")
                scores["Pulmonary / Critical Care"] += 1
            if hr and isinstance(hr, (int, float)) and hr > 120:
                vitals_notes.append(f"Tachycardia {hr} bpm")
                scores["Cardiologist"] += 1
        except Exception:
            pass

    best = max(scores.items(), key=lambda kv: kv[1])
    if best[1] == 0:
        return {
            "specialist": "General Physician",
            "confidence_score": 0,
            "rationale": "No strong keyword match found; recommend general practitioner for initial evaluation."
        }

    specialist = best[0]
    matched = []
    for kw in _SPECIALIST_KEYWORDS[specialist]:
        if re.search(r"\b" + re.escape(kw.lower()) + r"\b", text):
            matched.append(kw)
    rationale = ""
    if matched:
        rationale = f"Matched keywords: {', '.join(matched)}."
    if vitals_notes:
        rationale = (rationale + " " if rationale else "") + "Vitals: " + "; ".join(vitals_notes)

    return {
        "specialist": specialist,
        "confidence_score": int(best[1]),
        "rationale": rationale or "Matched specialist based on keywords."
    }
