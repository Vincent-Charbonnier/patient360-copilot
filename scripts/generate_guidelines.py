"""Generate fictional clinical guideline PDF documents."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

OUTPUT_DIR = Path("data/guidelines")
GUIDELINES = [
    "Chronic Disease Management Guideline",
    "Medication Safety Guideline",
    "Preventive Screening Guideline",
    "Care Coordination Guideline",
    "Clinical Escalation Guideline",
    "Privacy and Clinical Use Guideline",
]


def write_pdf(name: str) -> None:
    """Write one fictional guideline PDF."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT_DIR / f"{name.replace(' ', '_').lower()}.pdf"), pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = [Paragraph(name, styles["Title"]), Spacer(1, 12)]
    sections = {
        "Purpose": "This fictional guideline supports safe, evidence-aware clinical workflow demonstrations.",
        "Assessment requirements": "Review patient context, recent encounters, medications, allergies, lab indicators, and open care gaps.",
        "Documentation guidance": "Record the rationale, source evidence, patient preferences, and clinician review requirements.",
        "Escalation rules": "Escalate urgent symptoms, abnormal trends, medication safety concerns, and unresolved high-risk care gaps.",
        "Compliance guidance": "Use minimum necessary patient information and avoid exposing sensitive data outside approved private systems.",
    }
    for heading, text in sections.items():
        story.append(Paragraph(heading, styles["Heading2"]))
        story.append(Paragraph(text, styles["BodyText"]))
        story.append(Spacer(1, 10))
    doc.build(story)


def generate_guidelines() -> int:
    """Generate all guideline PDFs."""
    for name in GUIDELINES:
        write_pdf(name)
    return len(GUIDELINES)


if __name__ == "__main__":
    print(f"Generated {generate_guidelines()} guideline documents")
