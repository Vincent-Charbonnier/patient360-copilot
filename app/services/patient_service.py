"""Patient and encounter file access."""

from __future__ import annotations

import json
import logging
import random
from datetime import date
from pathlib import Path

from faker import Faker

from app.config.settings import settings
from app.models.schemas import Encounter, Patient

logger = logging.getLogger(__name__)

CONDITIONS = [
    "Type 2 Diabetes",
    "Hypertension",
    "Chronic Kidney Disease",
    "Asthma",
    "COPD",
    "Heart Failure",
    "Coronary Artery Disease",
    "Depression",
    "Hyperlipidemia",
]
MEDICATIONS = [
    "Metformin",
    "Lisinopril",
    "Atorvastatin",
    "Amlodipine",
    "Albuterol inhaler",
    "Sertraline",
    "Furosemide",
    "Aspirin",
]
CARE_GAPS = [
    "Annual wellness visit due",
    "Medication reconciliation needed",
    "A1c follow-up overdue",
    "Blood pressure recheck needed",
    "LDL monitoring due",
    "Vaccination review due",
    "Care plan review needed",
]


class PatientService:
    """Reads and writes fictional patient profiles and encounters from local JSON files."""

    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or settings.data_path
        self.patient_path = self.data_path / "patients"
        self.encounter_path = self.data_path / "encounters"

    def list_patients(self) -> list[Patient]:
        """Return all patient profiles sorted by patient ID."""
        patients: list[Patient] = []
        for path in sorted(self.patient_path.glob("patient_*.json")):
            try:
                patients.append(Patient.model_validate_json(path.read_text(encoding="utf-8")))
            except Exception as exc:
                logger.warning("Skipping invalid patient file %s: %s", path, exc)
        return patients

    def next_patient_id(self) -> str:
        """Return the next available three-digit patient ID."""
        max_id = 0
        for patient in self.list_patients():
            if patient.patient_id.isdigit():
                max_id = max(max_id, int(patient.patient_id))
        return f"{max_id + 1:03d}"

    def get_patient(self, patient_id: str) -> Patient:
        """Return one patient profile."""
        normalized_id = patient_id.zfill(3)
        path = self.patient_path / f"patient_{normalized_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Patient {normalized_id} was not found")
        return Patient.model_validate_json(path.read_text(encoding="utf-8"))

    def get_encounters(self, patient_id: str) -> list[Encounter]:
        """Return recent encounters for a patient, newest first."""
        normalized_id = patient_id.zfill(3)
        path = self.encounter_path / f"encounters_{normalized_id}.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        encounters = [Encounter.model_validate(item) for item in data]
        return sorted(encounters, key=lambda item: item.date, reverse=True)

    def create_patient(self, patient: Patient) -> Patient:
        """Persist a new patient JSON file and initialize empty encounters."""
        normalized_patient = patient.model_copy(update={"patient_id": patient.patient_id.zfill(3)})
        self.patient_path.mkdir(parents=True, exist_ok=True)
        self.encounter_path.mkdir(parents=True, exist_ok=True)
        path = self.patient_path / f"patient_{normalized_patient.patient_id}.json"
        if path.exists():
            raise FileExistsError(f"Patient {normalized_patient.patient_id} already exists")
        path.write_text(normalized_patient.model_dump_json(indent=2), encoding="utf-8")
        encounter_file = self.encounter_path / f"encounters_{normalized_patient.patient_id}.json"
        if not encounter_file.exists():
            encounter_file.write_text("[]", encoding="utf-8")
        logger.info("Created patient profile %s", path)
        return normalized_patient

    def generate_demo_patient(self) -> Patient:
        """Generate one fictional patient profile for form prefill."""
        fake = Faker(["en_US", "en_GB", "fr_FR", "de_DE", "nl_NL", "es_ES", "it_IT"])
        conditions = sorted(random.sample(CONDITIONS, random.randint(1, 4)))
        medications = sorted(random.sample(MEDICATIONS, random.randint(1, 5)))
        age = random.randint(18, 90)
        systolic = random.randint(112, 168)
        diastolic = random.randint(68, 96)
        hba1c = round(random.uniform(5.4, 9.8), 1) if "Type 2 Diabetes" in conditions else None
        ldl = random.randint(70, 178) if any(item in conditions for item in ["Hyperlipidemia", "Coronary Artery Disease"]) else None
        care_gaps = sorted(random.sample(CARE_GAPS, random.randint(1, 4)))
        risk_level = random.choices(["low", "medium", "high"], weights=[40, 42, 18], k=1)[0]
        return Patient(
            patient_id=self.next_patient_id(),
            name=fake.name(),
            age=age,
            sex=random.choice(["female", "male", "other"]),
            conditions=conditions,
            medications=medications,
            allergies=random.choice([[], ["Penicillin"], ["Sulfa"], ["Latex"]]),
            risk_level=risk_level,
            blood_pressure=f"{systolic}/{diastolic}",
            hba1c=hba1c,
            ldl=ldl,
            primary_provider=f"Dr. {fake.last_name()}",
            last_visit=fake.date_between_dates(date_start=date(2024, 1, 1), date_end=date.today()).isoformat(),
            care_gaps=care_gaps,
        )
