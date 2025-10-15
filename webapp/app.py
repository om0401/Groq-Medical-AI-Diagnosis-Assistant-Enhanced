# webapp/app.py
import sys, os
# ensure project root on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
import io
from dotenv import load_dotenv
import streamlit as st
import speech_recognition as sr

from agents.coordinator import run_multi_agent_inference_async
from agents.tool_agent import fetch_external_data
from utils.run_groq_inference import run_groq_inference

load_dotenv()

st.set_page_config(page_title="Groq Medical AI - Enhanced", layout="centered")
st.title("🩺 Groq Medical AI - Diagnosis Assistant (Enhanced)")

# Patient info
st.header("Patient Info")
name = st.text_input("Name")
age = st.number_input("Age", min_value=0, max_value=120, value=30)
gender = st.selectbox("Gender", ["Male", "Female", "Other"])

# Symptoms
st.header("Symptoms")
symptoms = st.text_area("Describe your symptoms here", height=140)

# Voice input
st.markdown("**Optional voice input** — upload a short WAV/MP3 file and we will transcribe and append it to symptoms.")
voice_file = st.file_uploader("Upload voice file (wav/mp3)", type=["wav", "mp3"])

if voice_file is not None:
    try:
        # Streamlit's UploadedFile supports .read()
        audio_bytes = voice_file.read()
        st.info("Transcribing audio (uses Google Web Speech API via SpeechRecognition).")
        from utils.voice_utils import transcribe_audio_file
        voice_text = transcribe_audio_file(io.BytesIO(audio_bytes))
        st.text_area("Transcribed voice text (read-only)", value=voice_text, height=120)
        if voice_text and voice_text.strip():
            symptoms = (symptoms + "\n" + voice_text).strip()
    except Exception as e:
        st.error(f"Audio handling/transcription error: {e}")

# External context
st.header("External Context (MCP)")
provider = st.selectbox("Choose provider for external context", ["mock", "pubmed", "openfda", "wikipedia"])
if st.button("Fetch External Context"):
    if not symptoms.strip():
        st.warning("Please add symptoms (or voice input) to fetch relevant external context.")
    else:
        with st.spinner(f"Fetching external context from {provider}..."):
            ext = fetch_external_data(symptoms, provider=provider)
            st.success(f"Loaded external context from {provider}")
            st.text_area("External Context (short)", value=ext, height=160)

# Model & Image
st.header("Model & Image")
model_choice = st.selectbox(
    "Choose model (pick model listed in your Groq account)",
    [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "llama-3.1-8b-instant",
        "qwen/qwen3-32b",
    ],
    index=0
)

modality = st.selectbox("Select Modality", ["X-ray", "CT Scan", "MRI", "Blood Report", "Vision"])
img = st.file_uploader(f"Upload {modality} image (optional)", type=["jpg", "jpeg", "png"])

st.markdown("---")
st.markdown("### Run analysis")

if st.button("Analyze (Run Agents Async)"):
    if not symptoms.strip():
        st.error("Please provide symptoms or voice input to continue.")
    else:
        prompt_text = f"Patient: {name or '(unknown)'}\nAge: {age}\nGender: {gender}\n\nSymptoms:\n{symptoms}"
        with st.spinner("Running agents in parallel..."):
            try:
                orchestration_result = asyncio.run(
                    run_multi_agent_inference_async(
                        symptoms_text=prompt_text,
                        image_file=img,
                        modality=modality,
                        external_provider=provider,
                        symptom_model=model_choice,
                        image_model=model_choice,
                        timeout_per_agent=25
                    )
                )
            except Exception as e:
                st.error(f"Orchestration error: {e}")
                orchestration_result = None

        if orchestration_result:
            st.success("Agents finished ✅")
            st.subheader("Per-Agent Results")
            per_agent = orchestration_result.get("per_agent", {})
            order = ["tool", "symptom", "image"]
            for agent_name in order:
                info = per_agent.get(agent_name)
                if not info:
                    continue
                st.markdown(f"#### {agent_name.capitalize()} agent — status: **{info.get('status', 'unknown')}**")
                latency = info.get("agent_latency_seconds")
                if latency is not None:
                    st.write(f"Latency (agent best-effort): {latency} seconds")
                else:
                    st.write("Latency: N/A")
                st.text_area(f"{agent_name} output", value=info.get("full_response", ""), height=200)

            st.subheader("Combined Response")
            combined = orchestration_result.get("combined_response", "")
            st.text_area("Combined", value=combined, height=320)
            st.write(f"⏱ Total orchestration latency: {orchestration_result.get('total_latency_seconds')} seconds")
        else:
            st.error("No orchestration results available. Check logs.")

st.markdown("---")
st.markdown("### Quick single-model test (direct call)")
if st.button("Run quick direct Groq test (simulated if no key)"):
    with st.spinner("Calling run_groq_inference directly..."):
        try:
            test_prompt = f"Quick test: summarize: {symptoms[:300] or 'Hello Groq'}"
            res = run_groq_inference(symptoms_text=test_prompt, image_file=img, modality=modality, model=model_choice)
            st.success("Direct call complete")
            st.text_area("Direct model response", value=res.get("full_response", ""), height=300)
            st.write(f"⏱ Latency: {res.get('latency_seconds', 0)} seconds")
        except Exception as e:
            st.error(f"Direct run error: {e}")

st.markdown("---")
st.info("⚠️ This assistant is for demo/educational purposes only. Not a medical professional. Always consult a licensed physician for diagnosis or treatment.")
