"""Pydantic request and response models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Patient(BaseModel):
    """Fictional patient profile for the demo."""

    patient_id: str
    name: str
    age: int
    sex: Literal["female", "male", "other"]
    conditions: list[str]
    medications: list[str]
    allergies: list[str]
    risk_level: Literal["low", "medium", "high"]
    blood_pressure: str
    hba1c: float | None = None
    ldl: int | None = None
    primary_provider: str
    last_visit: str
    care_gaps: list[str]


class Encounter(BaseModel):
    """Fictional patient encounter record."""

    patient_id: str
    date: str
    setting: Literal["primary care", "specialist", "emergency", "telehealth", "inpatient"]
    summary: str


class ChatMessage(BaseModel):
    """Chat history item."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Chat endpoint request."""

    message: str = Field(..., min_length=1)
    patient_id: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)


class ToolCallRecord(BaseModel):
    """Tool call shown in the API and Streamlit UI."""

    name: str
    arguments: dict[str, Any]
    result: Any


class RetrievedDocument(BaseModel):
    """Retrieved RAG chunk and source metadata."""

    document_type: str
    document_name: str
    chunk: str
    score: float | None = None


class ChatResponse(BaseModel):
    """Chat endpoint response."""

    answer: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    retrieved_documents: list[RetrievedDocument] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)


class RiskAssessmentRequest(BaseModel):
    """Clinical risk assessment input."""

    age: int
    conditions: list[str]
    recent_ed_visits: int = 0
    medication_count: int = 0
    care_gap_count: int = 0


class RiskAssessmentResult(BaseModel):
    """Deterministic risk assessment result."""

    status: Literal["routine", "care_management", "urgent_review"]
    score: int
    explanation: str


class HealthResponse(BaseModel):
    """Health check payload."""

    status: str
    app: str


class RuntimeSettings(BaseModel):
    """Runtime settings safe to return to the frontend."""

    llm_base_url: str
    llm_model: str
    llm_api_key_configured: bool
    llm_ssl_verify: bool
    embedding_model: str
    embedding_base_url: str
    embedding_api_key_configured: bool
    embedding_ssl_verify: bool
    chroma_mode: Literal["http"]
    chroma_host: str
    chroma_port: int
    chroma_ssl: bool
    chroma_ssl_verify: bool
    chroma_tenant: str
    chroma_database: str
    llm_timeout_seconds: float


class RuntimeSettingsUpdate(BaseModel):
    """Runtime settings update from the frontend.

    Empty API keys are ignored so a user can update other fields without
    clearing the current token.
    """

    llm_base_url: str = Field(..., min_length=1)
    llm_model: str = Field(..., min_length=1)
    llm_api_key: str | None = None
    llm_ssl_verify: bool = True
    embedding_model: str = Field(..., min_length=1)
    embedding_base_url: str = ""
    embedding_api_key: str | None = None
    embedding_ssl_verify: bool = True
    chroma_mode: Literal["http"] = "http"
    chroma_host: str = ""
    chroma_port: int = Field(default=443, gt=0, le=65535)
    chroma_ssl: bool = True
    chroma_ssl_verify: bool = True
    chroma_tenant: str = Field(default="default_tenant", min_length=1)
    chroma_database: str = Field(default="default_database", min_length=1)
    llm_timeout_seconds: float = Field(default=30, gt=0)


class ConnectionTestResponse(BaseModel):
    """Connection test result for a configured runtime dependency."""

    service: Literal["llm", "embedding", "chroma"]
    ok: bool
    message: str
