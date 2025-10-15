# utils/run_groq_inference.py
import os
import time
import base64
import requests
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1").rstrip("/")
CHAT_URL = GROQ_API_BASE + "/chat/completions"

# mapping defaults (based on your account's available models)
DEFAULT_TEXT_MODEL = "openai/gpt-oss-20b"
DEFAULT_IMAGE_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

def _extract_text(resp_json):
    try:
        return resp_json["choices"][0]["message"]["content"]
    except Exception:
        try:
            return resp_json["choices"][0]["text"]
        except Exception:
            return str(resp_json)

def _build_prompt(symptoms_text="", modality="text", image_file=None, include_image=False):
    prompt = f"[Modality: {modality}]\n" + (symptoms_text or "")
    if include_image and image_file:
        try:
            image_file.seek(0)
            img_bytes = image_file.read()
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            prompt += "\n\n[Attached image omitted in logs. Model should analyze embedded image if supported.]"
            # If you choose to embed image data, uncomment:
            # prompt += f'\n[Image:data:image/jpeg;base64,{b64}]'
        except Exception:
            prompt += "\n\n[Warning: could not attach image]"
    return prompt

def run_groq_inference(symptoms_text="", image_file=None, modality="text", model=None, include_image=False, timeout=30):
    """
    Generic Groq REST inference call.
    - model: use exact model id available on your account
    - include_image: True to include base64 image in prompt (beware size)
    """
    start = time.time()
    if not GROQ_API_KEY:
        # Simulated response for offline development
        simulated = "SIMULATED MODEL RESPONSE (no GROQ_API_KEY). Provide GROQ_API_KEY in .env to call Groq."
        return {"full_response": simulated, "latency_seconds": round(time.time() - start, 3)}

    model = model or (DEFAULT_IMAGE_MODEL if modality.lower() != "text" else DEFAULT_TEXT_MODEL)
    prompt = _build_prompt(symptoms_text=symptoms_text, modality=modality, image_file=image_file, include_image=include_image)

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}

    try:
        r = requests.post(CHAT_URL, headers=headers, json=payload, timeout=timeout)
    except Exception as e:
        return {"full_response": f"Network/error calling Groq: {e}", "latency_seconds": round(time.time() - start, 3)}

    try:
        if r.status_code != 200:
            # return body for debugging
            body_text = ""
            try:
                body_text = r.json()
            except Exception:
                body_text = r.text
            return {"full_response": f"Groq HTTP {r.status_code}: {body_text}", "latency_seconds": round(time.time() - start, 3)}
        body = r.json()
    except Exception:
        return {"full_response": f"Invalid JSON response from Groq: {r.text}", "latency_seconds": round(time.time() - start, 3)}

    text = _extract_text(body)
    return {"full_response": text, "latency_seconds": round(time.time() - start, 3)}
