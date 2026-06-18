"""Generate all fictional Patient360 demo data."""

from __future__ import annotations

from pathlib import Path

from generate_encounters import generate_encounters
from generate_guidelines import generate_guidelines
from generate_patients import generate_patients, write_patients
from generate_programs import generate_programs


def ensure_directories() -> None:
    """Create required data directories."""
    for directory in ["data/patients", "data/care_programs", "data/guidelines", "data/encounters", "data/config"]:
        Path(directory).mkdir(parents=True, exist_ok=True)


def main() -> None:
    """Generate all demo content."""
    ensure_directories()
    patients = write_patients(generate_patients(50))
    programs = generate_programs()
    guidelines = generate_guidelines()
    encounters = generate_encounters()
    print("Generated:")
    print(f"- {patients} patients")
    print(f"- {programs} care program documents")
    print(f"- {guidelines} guideline documents")
    print(f"- {encounters} encounters")


if __name__ == "__main__":
    main()
