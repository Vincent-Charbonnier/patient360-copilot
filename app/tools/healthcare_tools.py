"""Deterministic local tools used by the Patient360 agent."""

from __future__ import annotations

import logging
from typing import Any

from app.models.schemas import RiskAssessmentResult
from app.rag.vector_store import VectorStore
from app.services.patient_service import PatientService

logger = logging.getLogger(__name__)


class HealthcareTools:
    """Tool implementations for patient context, RAG, care messaging, and risk scoring."""

    def __init__(self) -> None:
        self.patients = PatientService()
        self._vector_store: VectorStore | None = None

    @property
    def vector_store(self) -> VectorStore:
        """Create the ChromaDB client only when a RAG tool is used."""
        if self._vector_store is None:
            self._vector_store = VectorStore()
        return self._vector_store

    def get_patient(self, patient_id: str) -> dict[str, Any]:
        """Return a patient profile as a JSON-serializable dictionary."""
        return self.patients.get_patient(patient_id).model_dump()

    def get_patient_encounters(self, patient_id: str) -> list[dict[str, Any]]:
        """Return recent patient encounters."""
        return [item.model_dump() for item in self.patients.get_encounters(patient_id)]

    def search_care_programs(self, query: str) -> list[dict[str, Any]]:
        """Search generated care program documents."""
        return [item.model_dump() for item in self.vector_store.search("care_programs", query)]

    def search_guidelines(self, query: str) -> list[dict[str, Any]]:
        """Search generated clinical guideline documents."""
        return [item.model_dump() for item in self.vector_store.search("guidelines", query)]

    def draft_care_message(self, patient_name: str, care_plan: str) -> str:
        """Draft a professional patient follow-up message."""
        return (
            "Subject: Follow-up on your care plan\n\n"
            f"Dear {patient_name},\n\n"
            "Thank you for meeting with the care team. Based on the information reviewed, "
            f"{care_plan}\n\n"
            "Please contact the clinic if symptoms worsen, if you have medication concerns, "
            "or if you need help scheduling the recommended follow-up.\n\n"
            "Kind regards,\n"
            "Patient Care Team"
        )

    def calculate_patient_risk(
        self,
        age: int,
        conditions: list[str],
        recent_ed_visits: int = 0,
        medication_count: int = 0,
        care_gap_count: int = 0,
    ) -> dict[str, Any]:
        """Return deterministic patient risk using simple care-management rules."""
        score = 20
        if age >= 75:
            score += 18
        elif age >= 60:
            score += 10
        score += min(len(conditions) * 8, 32)
        score += min(recent_ed_visits * 12, 24)
        if medication_count >= 8:
            score += 16
        elif medication_count >= 5:
            score += 8
        score += min(care_gap_count * 6, 18)
        score = max(0, min(100, score))

        if score >= 70:
            status = "urgent_review"
        elif score >= 45:
            status = "care_management"
        else:
            status = "routine"

        result = RiskAssessmentResult(
            status=status,
            score=score,
            explanation=(
                f"Risk score {score}/100 based on age, {len(conditions)} active conditions, "
                f"{recent_ed_visits} recent emergency visits, {medication_count} medications, "
                f"and {care_gap_count} open care gaps."
            ),
        )
        return result.model_dump()

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute a named tool."""
        tool = getattr(self, name, None)
        if tool is None or not callable(tool):
            raise ValueError(f"Unknown tool: {name}")
        logger.info("Executing tool %s with arguments %s", name, arguments)
        return tool(**arguments)


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_patient",
            "description": "Return a fictional patient profile.",
            "parameters": {
                "type": "object",
                "properties": {"patient_id": {"type": "string"}},
                "required": ["patient_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_encounters",
            "description": "Return recent patient encounters.",
            "parameters": {
                "type": "object",
                "properties": {"patient_id": {"type": "string"}},
                "required": ["patient_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_care_programs",
            "description": "Search care program documents using RAG.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_guidelines",
            "description": "Search clinical guideline documents using RAG.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_care_message",
            "description": "Draft a professional patient follow-up message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string"},
                    "care_plan": {"type": "string"},
                },
                "required": ["patient_name", "care_plan"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_patient_risk",
            "description": "Calculate deterministic patient risk and care-management status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "age": {"type": "integer"},
                    "conditions": {"type": "array", "items": {"type": "string"}},
                    "recent_ed_visits": {"type": "integer"},
                    "medication_count": {"type": "integer"},
                    "care_gap_count": {"type": "integer"},
                },
                "required": ["age", "conditions"],
            },
        },
    },
]
