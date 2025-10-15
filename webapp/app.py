# webapp/app.py
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
import io
import time
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# Agents & utils
from agents.coordinator import run_multi_agent_inference_async
from utils.run_groq_inference import run_groq_inference
from utils.mcp_adapter import fetch_external_context
from utils.specialist_recommender import recommend_specialist
from utils.pdf_report import ReportPDF
from utils.reasoning_trace import generate_reasoning_trace

# visualization libs
import pandas as pd
from statistics import mean, median

st.set_page_config(page_title="Groq Medical AI - Enhanced (Reports & Trace)", layout="centered")
st.title("🩺 Groq Medical AI — Diagnosis Assistant (Enhanced)")

# --- Patient Info ---
st.header("Patient Info")
name = st.text_input("Name", key="patient_name")
age = st.number_input("Age", min_value=0, max_value=120, value=30, key="patient_age")
gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="patient_gender")

# --- Symptoms ---
st.header("Symptoms")
symptoms = st.text_area("Describe your symptoms here", height=140, key="symptoms_input")

# Voice upload
st.markdown("Optional: upload voice (wav/mp3)")
voice_file = st.file_uploader("Voice file", type=["wav", "mp3"], key="voice_upload")
if voice_file:
    try:
        audio_bytes = voice_file.read()
        from utils.voice_utils import transcribe_audio_file
        voice_text = transcribe_audio_file(io.BytesIO(audio_bytes))
        st.text_area("Transcribed voice", value=voice_text, height=120, key=f"transcribed_{int(time.time())}")
        if voice_text:
            symptoms = (symptoms + "\n" + voice_text).strip()
    except Exception as e:
        st.error(f"Voice transcription failed: {e}")

# External provider selection
st.header("External Context (MCP)")
provider = st.selectbox("Provider", ["mock", "pubmed", "openfda", "wikipedia"], key="provider_choice")

# Model selection & image
st.header("Model & Image")
model_choice = st.selectbox("Model", [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant",
    "qwen/qwen3-32b"
], index=0, key="model_choice")

modality = st.selectbox("Modality", ["X-ray", "CT Scan", "MRI", "Blood Report", "Vision"], key="modality_choice")
img = st.file_uploader(f"Upload {modality} (optional)", type=["jpg", "jpeg", "png"], key="image_upload")

# Feature toggles
st.markdown("---")
st.header("Result Options")
col_a, col_b = st.columns(2)
with col_a:
    include_trace = st.checkbox("Include Reasoning Trace (explainable steps)", value=True, key="include_trace")
with col_b:
    include_report = st.checkbox("Include Specialist Recommendation & PDF report", value=True, key="include_report")

st.markdown("---")

# Analyze action
if st.button("Analyze & Generate Results", key="analyze_button"):
    if not symptoms.strip():
        st.error("Please enter symptoms or upload voice.")
    else:
        with st.spinner("Running multi-agent inference..."):
            try:
                orchestration_result = asyncio.run(
                    run_multi_agent_inference_async(
                        symptoms_text=symptoms,
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

        if not orchestration_result:
            st.error("No result. Check logs.")
        else:
            st.success("Analysis completed ✅")
            per_agent = orchestration_result.get("per_agent", {})
            combined = orchestration_result.get("combined_response", "")
            total_latency = orchestration_result.get("total_latency_seconds")

            # Show per-agent outputs
            st.subheader("Per-Agent Outputs")
            for agent in ("tool", "symptom", "image"):
                info = per_agent.get(agent)
                if not info:
                    continue
                st.markdown(f"**{agent.capitalize()} agent** — status: **{info.get('status')}**")
                st.write(f"Latency (approx): {info.get('agent_latency_seconds')}")
                st.text_area(f"{agent} output", value=info.get("full_response", ""), height=180, key=f"{agent}_out_{int(time.time()*1000)}")

            # Combined
            st.subheader("Combined Result")
            st.text_area("Combined", value=combined, height=300, key=f"combined_{int(time.time()*1000)}")
            st.write(f"⏱ Total orchestration latency: {total_latency} seconds")

            # ---- Telemetry visualization ----
            try:
                rows = []
                for agent_name in ("tool", "symptom", "image"):
                    info = per_agent.get(agent_name, {})
                    latency = info.get("agent_latency_seconds")
                    latency_val = float(latency) if (latency is not None and isinstance(latency, (int, float))) else float("nan")
                    status = info.get("status", "missing")
                    rows.append({"agent": agent_name, "latency_s": latency_val, "status": status})
                df = pd.DataFrame(rows)
                st.subheader("Telemetry & Performance")
                col_t1, col_t2 = st.columns([2, 1])
                with col_t1:
                    st.markdown("**Agent latency (seconds)**")
                    st.bar_chart(data=df.set_index("agent")["latency_s"])
                    st.markdown("**Per-agent metrics**")
                    st.table(df)
                with col_t2:
                    st.markdown("**Summary stats**")
                    numeric_latencies = [r for r in df["latency_s"].tolist() if not pd.isna(r)]
                    if numeric_latencies:
                        st.metric("Total orchestration (s)", value=f"{total_latency}")
                        st.metric("Mean agent latency (s)", value=f"{mean(numeric_latencies):.3f}")
                        st.metric("Median agent latency (s)", value=f"{median(numeric_latencies):.3f}")
                        st.write("Statuses:")
                        st.write({r["agent"]: r["status"] for r in rows})
                    else:
                        st.write("No numeric latencies available yet.")
            except Exception as e:
                st.warning(f"Telemetry rendering error: {e}")

            # 1) Reasoning trace (optional)
            if include_trace:
                st.markdown("## Reasoning Trace / Explainability")
                try:
                    trace_results = generate_reasoning_trace(per_agent=per_agent, combined_text=combined, prefer_model=True, model=model_choice)
                except Exception:
                    trace_results = generate_reasoning_trace(per_agent=per_agent, combined_text=combined, prefer_model=False, model=None)

                for ag, t in trace_results.get("agent_traces", {}).items():
                    st.markdown(f"### {ag.capitalize()} agent trace (method: {t.get('method')})")
                    trace = t.get("trace", [])
                    if not trace:
                        st.write("No trace available.")
                    else:
                        for block in trace:
                            if isinstance(block, dict):
                                btype = block.get("type", "item")
                                st.markdown(f"**{btype.capitalize()}:**")
                                for it in block.get("items", []):
                                    st.markdown(f"- {it}")
                            elif isinstance(block, str):
                                st.markdown(f"- {block}")
                            elif isinstance(block, list):
                                for it in block:
                                    st.markdown(f"- {it}")
                st.markdown("**Combined trace summary:**")
                st.write(trace_results.get("combined_trace", ""))

            # 2) Specialist recommendation + PDF (optional)
            if include_report:
                st.markdown("## Specialist Recommendation & PDF Report")
                try:
                    image_findings = per_agent.get("image", {}).get("full_response", "")
                    spec = recommend_specialist(symptoms_text=symptoms, image_findings=image_findings, vitals=None)
                except Exception as e:
                    spec = {"specialist":"General Physician", "confidence_score":0, "rationale":f"Error recommending: {e}"}

                st.write(f"**Recommended Specialist:** {spec.get('specialist')} (score: {spec.get('confidence_score')})")
                st.write(spec.get("rationale"))

                # PDF generation
                try:
                    patient_info = {"name": name, "age": age, "gender": gender}
                    pdf_maker = ReportPDF(title="Groq Medical AI - Diagnostic Report")
                    pdf_bytes = pdf_maker.generate(patient_info=patient_info, combined_text=combined, per_agent=per_agent, specialist=spec)
                    st.download_button("Download Report (PDF)", data=pdf_bytes, file_name=f"groq_report_{int(time.time())}.pdf", mime="application/pdf", key=f"pdf_{int(time.time()*1000)}")
                except Exception as e:
                    st.error(f"PDF generation error: {e}")

            st.markdown("---")
            st.info("Note: This assistant is for demo/educational use only and is not a substitute for professional medical advice.")
