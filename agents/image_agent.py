# agents/image_agent.py
import asyncio
from typing import Optional, Dict, Any
from utils.run_groq_inference import run_groq_inference

async def analyze_image_async(image_file, modality: str = "X-ray", model: Optional[str] = None) -> Dict[str, Any]:
    """
    Async wrapper for image analysis. include_image=True to embed image (beware size).
    """
    return await asyncio.to_thread(run_groq_inference, "", image_file, modality, model, True)
