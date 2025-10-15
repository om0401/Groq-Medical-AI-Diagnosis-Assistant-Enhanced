# utils/pdf_report.py
from fpdf import FPDF
from typing import Dict, Optional
import io
import datetime

class ReportPDF:
    def __init__(self, title="Groq Medical AI Report"):
        self.title = title

    def _header(self, pdf: FPDF, patient_name: str):
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, self.title, ln=True, align="C")
        pdf.ln(2)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, f"Generated: {datetime.datetime.now().isoformat()}", ln=True)
        if patient_name:
            pdf.cell(0, 6, f"Patient: {patient_name}", ln=True)
        pdf.ln(4)

    def generate(self, patient_info: Dict, combined_text: str, per_agent: Dict, specialist: Dict) -> bytes:
        """
        Create PDF bytes for the report.
        """
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        self._header(pdf, patient_info.get("name", ""))

        # Patient details
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Patient Details", ln=True)
        pdf.set_font("Arial", size=10)
        patient_block = f"Name: {patient_info.get('name','-')}\nAge: {patient_info.get('age','-')}\nGender: {patient_info.get('gender','-')}"
        pdf.multi_cell(0, 6, patient_block)
        pdf.ln(4)

        # Specialist
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Recommended Specialist", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, f"{specialist.get('specialist')}\nConfidence: {specialist.get('confidence_score')}\nRationale: {specialist.get('rationale')}")
        pdf.ln(4)

        # Per-agent outputs
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Agent Outputs", ln=True)
        pdf.ln(1)
        pdf.set_font("Arial", size=10)
        for agent_name, info in (per_agent or {}).items():
            pdf.set_font("Arial", "B", 11)
            pdf.multi_cell(0, 6, f"{agent_name.capitalize()} Agent:")
            pdf.set_font("Arial", size=10)
            text = info.get("full_response", "") or "-"
            pdf.multi_cell(0, 6, text)
            pdf.ln(2)

        # Combined
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Combined Summary", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, combined_text or "-")

        out = io.BytesIO()
        out.write(pdf.output(dest='S').encode('latin-1'))
        return out.getvalue()
