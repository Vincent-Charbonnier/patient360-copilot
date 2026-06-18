"""Generate reproducible fictional patient profiles."""

from __future__ import annotations

import random
from pathlib import Path

from faker import Faker

from app.services.patient_service import PatientService

SEED = 8128
OUTPUT_DIR = Path("data/patients")


def generate_patients(count: int = 50) -> list[dict[str, object]]:
    """Generate fictional patient records."""
    random.seed(SEED)
    Faker.seed(SEED)
    service = PatientService(data_path=Path("data"))
    patients: list[dict[str, object]] = []
    for index in range(1, count + 1):
        patient = service.generate_demo_patient().model_copy(update={"patient_id": f"{index:03d}"})
        patients.append(patient.model_dump())
    return patients


def write_patients(patients: list[dict[str, object]], output_dir: Path = OUTPUT_DIR) -> int:
    """Write one JSON file per patient."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for patient in patients:
        path = output_dir / f"patient_{patient['patient_id']}.json"
        path.write_text(__import__('json').dumps(patient, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(patients)


if __name__ == "__main__":
    written = write_patients(generate_patients())
    print(f"Generated {written} patients")
