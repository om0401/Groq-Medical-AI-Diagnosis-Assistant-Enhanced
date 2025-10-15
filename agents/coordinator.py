# agents/coordinator.py
import asyncio
import time
from typing import Optional, Dict, Any

from agents.symptom_agent import analyze_symptoms_async
from agents.image_agent import analyze_image_async
from agents.tool_agent import fetch_external_data_async

AGENT_TIMEOUT = 25

async def run_multi_agent_inference_async(
    symptoms_text: str,
    image_file=None,
    modality: str = "X-ray",
    external_provider: str = "mock",
    symptom_model: Optional[str] = None,
    image_model: Optional[str] = None,
    timeout_per_agent: int = AGENT_TIMEOUT
) -> Dict[str, Any]:
    """
    Orchestrate agents in parallel:
      - symptom agent
      - image agent (optional)
      - external tool (MCP)
    Returns a dict with per-agent responses and overall telemetry.
    """
    start_all = time.time()

    tasks = {
        "tool": asyncio.create_task(
            asyncio.wait_for(fetch_external_data_async(symptoms_text, provider=external_provider), timeout=timeout_per_agent)
        ),
        "symptom": asyncio.create_task(
            asyncio.wait_for(analyze_symptoms_async(symptoms_text, model=symptom_model), timeout=timeout_per_agent)
        )
    }

    if image_file:
        tasks["image"] = asyncio.create_task(
            asyncio.wait_for(analyze_image_async(image_file, modality=modality, model=image_model), timeout=timeout_per_agent)
        )

    results: Dict[str, Any] = {}
    for name, task in tasks.items():
        t_start = time.time()
        try:
            res = await task
            elapsed = round(time.time() - t_start, 3)
            if isinstance(res, dict):
                results[name] = {
                    "status": "ok",
                    "full_response": res.get("full_response", ""),
                    "agent_latency_seconds": res.get("latency_seconds", elapsed)
                }
            else:
                results[name] = {"status": "ok", "full_response": str(res), "agent_latency_seconds": elapsed}
        except asyncio.TimeoutError:
            results[name] = {"status": "timeout", "full_response": "", "agent_latency_seconds": None}
        except Exception as e:
            results[name] = {"status": "error", "full_response": f"{e}", "agent_latency_seconds": None}

    total_latency = round(time.time() - start_all, 3)
    combined_text = ""
    if "tool" in results and results["tool"].get("full_response"):
        combined_text += f"External Context (tool):\n{results['tool']['full_response']}\n\n"
    if "symptom" in results and results["symptom"].get("full_response"):
        combined_text += f"Symptoms Analysis:\n{results['symptom']['full_response']}\n\n"
    if "image" in results and results["image"].get("full_response"):
        combined_text += f"Image Analysis ({modality}):\n{results['image']['full_response']}\n\n"

    return {
        "per_agent": results,
        "combined_response": combined_text.strip(),
        "total_latency_seconds": total_latency
    }
