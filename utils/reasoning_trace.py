# utils/reasoning_trace.py
from typing import Dict, Optional
from utils.run_groq_inference import run_groq_inference
import re
import time
import json

def _heuristic_trace_from_text(text: str) -> Dict:
    """
    Heuristic extraction of findings, evidence and recommendations from agent output.
    """
    if not text:
        return {"trace": [], "summary": ""}

    sents = re.split(r'(?<=[.!?])\s+', text.strip())
    findings = []
    evidence = []
    recommendations = []

    for s in sents:
        low = s.lower()
        if any(k in low for k in ["opacit", "infiltrat", "consolid", "nodule", "mass", "lesion", "fracture", "effusion"]):
            findings.append(s.strip())
        elif any(k in low for k in ["because", "due to", "suggest", "likely", "consistent with", "may be", "consider"]):
            evidence.append(s.strip())
        elif any(k in low for k in ["recommend", "refer", "follow", "advise", "start", "consider"]):
            recommendations.append(s.strip())

    trace = []
    if findings:
        trace.append({"type":"findings", "items": findings})
    if evidence:
        trace.append({"type":"evidence", "items": evidence})
    if recommendations:
        trace.append({"type":"recommendations", "items": recommendations})

    summary = " ".join(sents[:2]) if sents else ""
    return {"trace": trace, "summary": summary}

def generate_reasoning_trace(per_agent: Dict, combined_text: str, prefer_model: bool = True, model: str = None) -> Dict:
    """
    Generate reasoning trace for each agent. If 'model' is provided and Groq key is configured,
    tries to ask the model to produce a concise JSON reasoning trace. Otherwise fall back to heuristics.
    Returns: {"agent_traces": {agent: {...}}, "combined_trace": "..."}
    """
    results = {"agent_traces": {}, "combined_trace": ""}

    for agent_name, info in (per_agent or {}).items():
        text = info.get("full_response", "")
        if not text:
            results["agent_traces"][agent_name] = {"method":"none", "trace": [], "summary": ""}
            continue

        if prefer_model and model:
            prompt = (
                "You are a medical reasoning assistant. Given the agent output below, produce a short, "
                "step-by-step numbered reasoning trace (3-6 steps) that shows how the agent arrived at the conclusion, "
                "list key evidences from the text, and end with a 1-line confidence estimate.\n\n"
                f"Agent output:\n'''{text}'''\n\nRespond in JSON with keys: steps (list), evidence (list), confidence (string)."
            )
            try:
                resp = run_groq_inference(symptoms_text=prompt, image_file=None, modality="text", model=model)
                content = resp.get("full_response", "")
                # attempt JSON parse
                parsed = None
                try:
                    parsed = json.loads(content)
                except Exception:
                    parsed = None
                if isinstance(parsed, dict):
                    steps = parsed.get("steps", []) or []
                    evidence = parsed.get("evidence", []) or []
                    confidence = parsed.get("confidence", "")
                    results["agent_traces"][agent_name] = {"method":"model", "trace": steps, "evidence": evidence, "confidence": confidence, "raw": content}
                else:
                    # model returned text — split into lines as steps
                    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
                    results["agent_traces"][agent_name] = {"method":"model", "trace": lines[:6], "evidence": [], "confidence": ""}
                continue
            except Exception:
                pass

        # fallback heuristic
        h = _heuristic_trace_from_text(text)
        results["agent_traces"][agent_name] = {"method":"heuristic", "trace": h.get("trace", []), "summary": h.get("summary", "")}

    # build combined trace summary
    combined_steps = []
    for agent, t in results["agent_traces"].items():
        if t.get("trace"):
            combined_steps.append(f"{agent}: {len(t.get('trace',[]))} blocks")
    results["combined_trace"] = "; ".join(combined_steps)
    return results
