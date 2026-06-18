"""Generate fictional patient encounter history."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 8128
PATIENT_DIR = Path("data/patients")
OUTPUT_DIR = Path("data/encounters")
SETTINGS = ["primary care", "specialist", "emergency", "telehealth", "inpatient"]
SUMMARIES = [
    "Reviewed chronic condition management and medication adherence.",
    "Patient reported improved symptoms but needs follow-up labs.",
    "Care team discussed prevention screening and vaccination status.",
    "Medication reconciliation identified an opportunity to simplify regimen.",
    "Patient asked about remote monitoring and care-management support.",
    "Emergency visit for acute symptoms; discharged with follow-up instructions.",
    "Specialist recommended additional monitoring and primary care coordination.",
]


def generate_encounters() -> int:
    """Generate encounters for every patient JSON file."""
    random.seed(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for path in sorted(PATIENT_DIR.glob("patient_*.json")):
        patient_id = path.stem.split("_")[-1]
        count = random.randint(3, 15)
        encounters = []
        for _ in range(count):
            encounter_date = date.today() - timedelta(days=random.randint(3, 720))
            encounters.append(
                {
                    "patient_id": patient_id,
                    "date": encounter_date.isoformat(),
                    "setting": random.choice(SETTINGS),
                    "summary": random.choice(SUMMARIES),
                }
            )
        encounters.sort(key=lambda item: item["date"], reverse=True)
        (OUTPUT_DIR / f"encounters_{patient_id}.json").write_text(json.dumps(encounters, indent=2), encoding="utf-8")
        total += len(encounters)
    return total


if __name__ == "__main__":
    print(f"Generated {generate_encounters()} encounters")
