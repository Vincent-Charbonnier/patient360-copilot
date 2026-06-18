"""FastAPI routes for the Patient360 Copilot."""

from __future__ import annotations

import logging
import os
import subprocess
import sys

from fastapi import APIRouter, HTTPException

from app.agent.llm_client import LLMClient
from app.agent.patient_agent import PatientAgent
from app.config.settings import settings
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ConnectionTestResponse,
    Encounter,
    HealthResponse,
    Patient,
    RuntimeSettings,
    RuntimeSettingsUpdate,
)
from app.rag.vector_store import VectorStore, embed_texts
from app.services.patient_service import PatientService
from app.services.settings_service import get_runtime_settings, update_runtime_settings

logger = logging.getLogger(__name__)

router = APIRouter()
patient_service = PatientService()
agent = PatientAgent()


def rebuild_agent() -> None:
    """Recreate the agent after runtime model or Chroma settings change."""
    global agent
    agent = PatientAgent()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Return application health status."""
    return HealthResponse(status="ok", app=settings.app_name)


@router.get("/patients", response_model=list[Patient], tags=["patients"])
def list_patients() -> list[Patient]:
    """List all fictional patients."""
    return patient_service.list_patients()


@router.post("/patients", response_model=Patient, tags=["patients"])
def create_patient(patient: Patient) -> Patient:
    """Create a new fictional patient profile."""
    try:
        return patient_service.create_patient(patient)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Patient creation failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/patients/demo-profile", response_model=Patient, tags=["patients"])
def generate_demo_patient() -> Patient:
    """Generate a fictional patient profile for form prefill."""
    return patient_service.generate_demo_patient()


@router.get("/patient/{patient_id}", response_model=Patient, tags=["patients"])
def get_patient(patient_id: str) -> Patient:
    """Get one fictional patient profile."""
    try:
        return patient_service.get_patient(patient_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/patient/{patient_id}/encounters", response_model=list[Encounter], tags=["patients"])
def get_patient_encounters(patient_id: str) -> list[Encounter]:
    """Get recent patient encounters."""
    return patient_service.get_encounters(patient_id)


@router.post("/chat", response_model=ChatResponse, tags=["agent"])
def chat(request: ChatRequest) -> ChatResponse:
    """Run the copilot for a chat message."""
    try:
        return agent.run(request.message, request.patient_id, request.history)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/settings", response_model=RuntimeSettings, tags=["settings"])
def read_settings() -> RuntimeSettings:
    """Return current runtime settings without exposing API keys."""
    return get_runtime_settings()


@router.put("/settings", response_model=RuntimeSettings, tags=["settings"])
def update_settings(update: RuntimeSettingsUpdate) -> RuntimeSettings:
    """Update runtime settings for the current backend process."""
    try:
        updated = update_runtime_settings(update)
        rebuild_agent()
        return updated
    except Exception as exc:
        logger.exception("Settings update failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/settings/test/{service}", response_model=ConnectionTestResponse, tags=["settings"])
def test_connection(service: str) -> ConnectionTestResponse:
    """Test one configured runtime dependency without changing settings."""
    try:
        if service == "llm":
            response = LLMClient().chat(
                [
                    {"role": "system", "content": "Reply with exactly: ok"},
                    {"role": "user", "content": "connection test"},
                ]
            )
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return ConnectionTestResponse(service="llm", ok=True, message=f"LLM responded: {content or 'empty content'}")
        if service == "embedding":
            embeddings = embed_texts(["Patient360 Copilot connection test"])
            dimensions = len(embeddings[0]) if embeddings else 0
            return ConnectionTestResponse(service="embedding", ok=True, message=f"Embedding endpoint returned {dimensions} dimensions.")
        if service == "chroma":
            heartbeat = VectorStore().heartbeat()
            return ConnectionTestResponse(service="chroma", ok=True, message=f"ChromaDB heartbeat: {heartbeat}")
        raise HTTPException(status_code=404, detail=f"Unknown service: {service}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Connection test failed for %s: %s", service, exc)
        normalized_service = service if service in {"llm", "embedding", "chroma"} else "chroma"
        return ConnectionTestResponse(service=normalized_service, ok=False, message=str(exc))


@router.post("/reindex", tags=["rag"])
def reindex() -> dict[str, str]:
    """Rebuild ChromaDB indexes from generated PDF documents."""
    env = os.environ.copy()
    env.update(
        {
            "CHROMA_MODE": settings.chroma_mode,
            "CHROMA_HOST": settings.chroma_host,
            "CHROMA_PORT": str(settings.chroma_port),
            "CHROMA_SSL": str(settings.chroma_ssl).lower(),
            "CHROMA_SSL_VERIFY": str(settings.chroma_ssl_verify).lower(),
            "CHROMA_TENANT": settings.chroma_tenant,
            "CHROMA_DATABASE": settings.chroma_database,
            "EMBEDDING_MODEL": settings.embedding_model,
            "EMBEDDING_BASE_URL": settings.embedding_base_url,
            "EMBEDDING_API_KEY": settings.embedding_api_key,
            "EMBEDDING_SSL_VERIFY": str(settings.embedding_ssl_verify).lower(),
            "ANONYMIZED_TELEMETRY": "False",
        }
    )
    try:
        completed = subprocess.run(
            [sys.executable, "scripts/ingest_documents.py"],
            check=True,
            env=env,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        output = "\n".join(part for part in [exc.stdout, exc.stderr] if part).strip()
        detail = output[-4000:] if output else str(exc)
        raise HTTPException(status_code=500, detail=f"Reindex failed:\n{detail}") from exc
    rebuild_agent()
    return {"status": "reindexed", "output": completed.stdout.strip()}
