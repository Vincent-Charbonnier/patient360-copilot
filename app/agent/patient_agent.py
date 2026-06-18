"""Lightweight tool-calling agent for Patient360 workflows."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agent.llm_client import LLMClient
from app.models.schemas import ChatMessage, ChatResponse, RetrievedDocument, ToolCallRecord
from app.tools.healthcare_tools import TOOL_DEFINITIONS, HealthcareTools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Patient360 Copilot, an enterprise healthcare assistant for clinicians and care teams.
Use tools for patient data, encounter history, clinical care program retrieval, guideline lookup, care-message drafting, and deterministic risk scoring.
Ground outputs in patient facts, retrieved sources, and deterministic tool results. Do not invent patient data.
This is a fictional demo and does not provide medical diagnosis. Advise clinician review for clinical decisions.
For patient summary requests, return a detailed clinical briefing with these Markdown sections:
Patient snapshot, Active conditions, Medications and allergies, Recent encounters, Risk and care gaps,
Relevant programs or guidelines, and Recommended next actions. Use clean bullets and avoid malformed tables."""


class PatientAgent:
    """Simple OpenAI-compatible tool-calling agent."""

    def __init__(self) -> None:
        self.tools = HealthcareTools()
        self.llm = LLMClient()

    def run(self, message: str, patient_id: str | None, history: list[ChatMessage]) -> ChatResponse:
        """Run the agent for one user message."""
        tool_records: list[ToolCallRecord] = []
        retrieved_documents: list[RetrievedDocument] = []
        try:
            llm_response = self._run_llm_tool_loop(message, patient_id, history, tool_records, retrieved_documents)
        except RuntimeError as exc:
            logger.warning("OpenAI tool-calling flow failed; using backend-planned tools with remote LLM: %s", exc)
            tool_records.clear()
            retrieved_documents.clear()
            llm_response = self._run_backend_planned_tool_flow(
                message, patient_id, history, tool_records, retrieved_documents, str(exc)
            )
        if not llm_response:
            raise RuntimeError("LLM returned an empty response.")
        return ChatResponse(
            answer=llm_response,
            tool_calls=tool_records,
            retrieved_documents=retrieved_documents,
            sources=self._sources_from_documents(retrieved_documents),
            suggested_questions=self._suggest_questions(message, patient_id, tool_records, retrieved_documents),
        )

    def _run_llm_tool_loop(
        self,
        message: str,
        patient_id: str | None,
        history: list[ChatMessage],
        tool_records: list[ToolCallRecord],
        retrieved_documents: list[RetrievedDocument],
    ) -> str | None:
        """Run a bounded OpenAI-compatible tool loop."""
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if patient_id:
            messages.append({"role": "system", "content": f"Selected patient_id: {patient_id}"})
        messages.extend(item.model_dump() for item in history[-8:])
        messages.append({"role": "user", "content": message})

        for _ in range(6):
            response = self.llm.chat(messages, tools=TOOL_DEFINITIONS)
            choice = response.get("choices", [{}])[0].get("message", {})
            tool_calls = choice.get("tool_calls") or []
            if not tool_calls:
                return str(choice.get("content") or "").strip() or None
            messages.append(choice)
            for call in tool_calls[:8]:
                function = call.get("function", {})
                name = function.get("name")
                raw_arguments = function.get("arguments") or "{}"
                try:
                    arguments = json.loads(raw_arguments)
                    result = self.tools.execute(name, arguments)
                except Exception as exc:
                    logger.exception("Tool call failed: %s", name)
                    result = {"error": str(exc)}
                    arguments = {}
                self._collect_retrieved(result, retrieved_documents)
                tool_records.append(ToolCallRecord(name=name, arguments=arguments, result=result))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id"),
                        "name": name,
                        "content": json.dumps(result, default=str),
                    }
                )
        final = self.llm.chat(messages, tools=None)
        return str(final.get("choices", [{}])[0].get("message", {}).get("content") or "").strip() or None

    def _run_backend_planned_tool_flow(
        self,
        message: str,
        patient_id: str | None,
        history: list[ChatMessage],
        tool_records: list[ToolCallRecord],
        retrieved_documents: list[RetrievedDocument],
        tool_call_error: str,
    ) -> str | None:
        """Execute a deterministic tool plan, then ask the remote LLM to answer normally."""
        lower = message.lower()
        detected_patient_id = self._detect_patient_id(message) or patient_id
        context: dict[str, Any] = {"tool_call_note": f"OpenAI tool-calling request was not accepted: {tool_call_error}"}
        patient: dict[str, Any] | None = None
        encounters: list[dict[str, Any]] = []

        if detected_patient_id:
            patient_result = self._execute_tool("get_patient", {"patient_id": detected_patient_id}, tool_records)
            context["patient"] = patient_result
            if isinstance(patient_result, dict) and "error" not in patient_result:
                patient = patient_result
            encounters_result = self._execute_tool("get_patient_encounters", {"patient_id": detected_patient_id}, tool_records)
            if isinstance(encounters_result, list):
                encounters = encounters_result
            context["encounters"] = encounters_result

        needs_guideline = any(term in lower for term in ["guideline", "protocol", "policy", "screening", "medication safety"])
        needs_program = any(term in lower for term in ["program", "care plan", "recommend", "follow-up", "diabetes", "hypertension", "cardiology", "ckd"])
        needs_risk = any(term in lower for term in ["risk", "readmission", "urgent", "care management", "prioritize"])
        needs_message = any(term in lower for term in ["message", "email", "letter", "follow up", "follow-up"])

        if needs_program:
            docs = self._execute_tool("search_care_programs", {"query": message}, tool_records)
            self._collect_retrieved(docs, retrieved_documents)
            context["care_program_documents"] = docs
        if needs_guideline or needs_risk:
            docs = self._execute_tool("search_guidelines", {"query": message}, tool_records)
            self._collect_retrieved(docs, retrieved_documents)
            context["guideline_documents"] = docs
        if needs_risk and patient:
            recent_ed_visits = sum(1 for item in encounters if item.get("setting") == "emergency")
            context["risk_assessment"] = self._execute_tool(
                "calculate_patient_risk",
                {
                    "age": patient["age"],
                    "conditions": patient["conditions"],
                    "recent_ed_visits": recent_ed_visits,
                    "medication_count": len(patient.get("medications", [])),
                    "care_gap_count": len(patient.get("care_gaps", [])),
                },
                tool_records,
            )
        if needs_message and patient:
            context["care_message"] = self._execute_tool(
                "draft_care_message",
                {"patient_name": patient["name"], "care_plan": "the care team recommends completing the discussed follow-up steps and confirming medications."},
                tool_records,
            )

        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.append(
            {
                "role": "system",
                "content": (
                    "The backend has already executed available healthcare tools. Use the JSON context below as grounded evidence. "
                    "If any tool result contains an error, explain what configuration or indexing step is needed instead of inventing facts.\n\n"
                    f"{json.dumps(context, default=str)}"
                ),
            }
        )
        messages.extend(item.model_dump() for item in history[-8:])
        messages.append({"role": "user", "content": message})
        final = self.llm.chat(messages, tools=None)
        return str(final.get("choices", [{}])[0].get("message", {}).get("content") or "").strip() or None

    def _execute_tool(self, name: str, arguments: dict[str, Any], tool_records: list[ToolCallRecord]) -> Any:
        """Execute a backend-planned tool and record errors without aborting chat."""
        try:
            result = self.tools.execute(name, arguments)
        except Exception as exc:
            logger.warning("Backend-planned tool failed: %s %s", name, exc)
            result = {"error": str(exc)}
        tool_records.append(ToolCallRecord(name=name, arguments=arguments, result=result))
        return result

    @staticmethod
    def _detect_patient_id(message: str) -> str | None:
        """Extract a three-digit patient id from a user prompt."""
        match = re.search(r"\bpatient\s+(\d{1,3})\b|\b(\d{3})\b", message, re.IGNORECASE)
        if not match:
            return None
        return (match.group(1) or match.group(2)).zfill(3)

    @staticmethod
    def _collect_retrieved(result: Any, retrieved_documents: list[RetrievedDocument]) -> None:
        if not isinstance(result, list):
            return
        for item in result:
            if isinstance(item, dict) and {"document_type", "document_name", "chunk"}.issubset(item):
                retrieved_documents.append(RetrievedDocument.model_validate(item))

    def _suggest_questions(
        self,
        message: str,
        patient_id: str | None,
        tool_records: list[ToolCallRecord],
        retrieved_documents: list[RetrievedDocument],
    ) -> list[str]:
        """Suggest relevant next clinical workflow prompts."""
        detected_patient_id = self._detect_patient_id(message) or patient_id
        if not detected_patient_id:
            return ["Select a patient and summarize their record."]
        lower = message.lower()
        tool_names = {record.name for record in tool_records}
        document_types = {document.document_type for document in retrieved_documents}
        suggestions: list[str] = []

        def add(question: str) -> None:
            if question not in suggestions:
                suggestions.append(question)

        if not tool_names or "summar" in lower or tool_names.issubset({"get_patient", "get_patient_encounters"}):
            add(f"What care gaps should we prioritize for patient {detected_patient_id}?")
            add(f"Which care programs are relevant for patient {detected_patient_id}?")
            add(f"Calculate risk and care-management priority for patient {detected_patient_id}.")
            add(f"Draft a follow-up care message for patient {detected_patient_id}.")
        elif "draft_care_message" in tool_names:
            add(f"What follow-up tasks should the care team create for patient {detected_patient_id}?")
            add(f"Which guideline evidence supports this care plan for patient {detected_patient_id}?")
            add(f"Summarize recent encounters for patient {detected_patient_id}.")
        elif "calculate_patient_risk" in tool_names or "guideline" in document_types:
            add(f"Which care programs are relevant for patient {detected_patient_id}?")
            add(f"Draft a follow-up care message for patient {detected_patient_id}.")
            add(f"What guideline checks apply before closing gaps for patient {detected_patient_id}?")
        else:
            add(f"Summarize patient {detected_patient_id}")
            add(f"Calculate risk and care-management priority for patient {detected_patient_id}.")
            add(f"Draft a follow-up care message for patient {detected_patient_id}.")
        add(f"Summarize recent encounters for patient {detected_patient_id}.")
        return suggestions[:4]

    @staticmethod
    def _sources_from_documents(documents: list[RetrievedDocument]) -> list[str]:
        seen: set[str] = set()
        sources: list[str] = []
        for doc in documents:
            label = f"{doc.document_type}: {doc.document_name}"
            if label not in seen:
                seen.add(label)
                sources.append(label)
        return sources
