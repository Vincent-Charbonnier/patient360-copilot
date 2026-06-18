"""Generate fictional healthcare care-program PDF documents."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

OUTPUT_DIR = Path("data/care_programs")
PROGRAMS = {
    "Diabetes Care Pathway": ["A1c monitoring", "nutrition support", "renal screening", "retinopathy checks"],
    "Hypertension Management": ["home blood pressure monitoring", "medication titration", "lifestyle coaching"],
    "Cardiology Follow-up": ["symptom review", "LDL targets", "cardiac rehabilitation referral"],
    "Preventive Care Program": ["wellness visits", "vaccination review", "age-appropriate screening"],
    "Medication Therapy Management": ["polypharmacy review", "adherence support", "side-effect assessment"],
    "Behavioral Health Support": ["screening", "warm handoff", "follow-up outreach"],
    "Chronic Kidney Disease Monitoring": ["eGFR trend", "albuminuria checks", "nephrology escalation"],
    "Post-Discharge Follow-up": ["48-hour outreach", "medication reconciliation", "red flag review"],
}


def write_pdf(name: str, topics: list[str]) -> None:
    """Write one care-program brochure PDF."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT_DIR / f"{name.replace(' ', '_').lower()}.pdf"), pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = [Paragraph(name, styles["Title"]), Spacer(1, 12)]
    sections = {
        "Program overview": f"{name} is a fictional care program for coordinated patient support in a private healthcare environment.",
        "Eligibility": "Patients are considered based on active conditions, recent utilization, open care gaps, and clinician judgement.",
        "Care-team workflow": "Review patient context, confirm current medications, assess barriers, and document shared next steps.",
        "Core interventions": "; ".join(topics) + ".",
        "Escalation criteria": "Escalate to clinician review for worsening symptoms, high-risk findings, abnormal labs, or unsafe medication concerns.",
        "Example scenario": "A care manager reviews the Patient360 summary, identifies gaps, and coordinates follow-up with the primary provider.",
    }
    for heading, text in sections.items():
        story.append(Paragraph(heading, styles["Heading2"]))
        story.append(Paragraph(text, styles["BodyText"]))
        story.append(Spacer(1, 10))
    doc.build(story)


def generate_programs() -> int:
    """Generate all care-program PDFs."""
    for name, topics in PROGRAMS.items():
        write_pdf(name, topics)
    return len(PROGRAMS)


if __name__ == "__main__":
    print(f"Generated {generate_programs()} care program documents")
