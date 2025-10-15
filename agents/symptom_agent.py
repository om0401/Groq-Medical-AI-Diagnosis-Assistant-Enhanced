# agents/symptom_agent.py
import asyncio
from typing import Optional, Dict, Any
from utils.run_groq_inference import run_groq_inference

async def analyze_symptoms_async(symptoms_text: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Async wrapper for symptom (text) analysis.
    """
    # run synchronous inference in a thread
    return await asyncio.to_thread(run_groq_inference, symptoms_text, None, "text", model, False)
