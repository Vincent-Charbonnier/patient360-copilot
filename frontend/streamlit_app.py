"""Streamlit frontend for Patient360 Copilot."""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
CONDITION_OPTIONS = [
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
MEDICATION_OPTIONS = [
    "Metformin",
    "Lisinopril",
    "Atorvastatin",
    "Amlodipine",
    "Albuterol inhaler",
    "Sertraline",
    "Furosemide",
    "Aspirin",
]
CARE_GAP_OPTIONS = [
    "Annual wellness visit due",
    "Medication reconciliation needed",
    "A1c follow-up overdue",
    "Blood pressure recheck needed",
    "LDL monitoring due",
    "Vaccination review due",
    "Care plan review needed",
]
ALLERGY_OPTIONS = ["Penicillin", "Sulfa", "Latex", "Shellfish", "NSAIDs"]


def raise_for_status_with_detail(response: requests.Response) -> None:
    """Raise an HTTP error that includes FastAPI's detail payload when present."""
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = response.text
        raise requests.HTTPError(f"{response.status_code} {response.reason}: {detail}") from exc


def api_get(path: str) -> Any:
    """Call a backend GET endpoint."""
    response = requests.get(f"{API_BASE_URL}{path}", timeout=15)
    raise_for_status_with_detail(response)
    return response.json()


def api_post(path: str, payload: dict[str, Any] | None = None) -> Any:
    """Call a backend POST endpoint."""
    response = requests.post(f"{API_BASE_URL}{path}", json=payload or {}, timeout=180)
    raise_for_status_with_detail(response)
    return response.json()


def api_put(path: str, payload: dict[str, Any]) -> Any:
    """Call a backend PUT endpoint."""
    response = requests.put(f"{API_BASE_URL}{path}", json=payload, timeout=30)
    raise_for_status_with_detail(response)
    return response.json()


def inject_css() -> None:
    """Apply app UI styling."""
    st.markdown(
        """
        <style>
        :root {
          --ink: #17211d;
          --muted: #66736d;
          --line: #d9dfd8;
          --green: #315c48;
          --blue: #285e7b;
          --amber: #a66d1b;
          --red: #9b3f3f;
        }
        html, body, [class*="css"] { font-family: 'Aptos', 'SF Pro Display', 'Segoe UI', sans-serif; }
        .stApp {
          background: linear-gradient(135deg, rgba(49, 92, 72, 0.08), rgba(40, 94, 123, 0.05) 38%, rgba(247, 248, 244, 1) 72%);
          color: var(--ink);
        }
        #MainMenu, footer, header { visibility: hidden; }
        .block-container { padding: 1.1rem 1.6rem 2rem; max-width: 1500px; }
        [data-testid="stSidebar"] { background: #edf2e9; border-right: 1px solid var(--line); }
        .topbar { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; padding: 1rem 0 1.15rem; border-bottom: 1px solid rgba(23, 33, 29, 0.12); margin-bottom: 1rem; }
        .title-block h1 { margin: 0; font-size: 2rem; line-height: 1.1; font-weight: 800; color: var(--ink); }
        .title-block p { margin: 0.35rem 0 0; color: var(--muted); font-size: 0.95rem; }
        .status-pill { display: inline-flex; align-items: center; gap: 0.45rem; border: 1px solid rgba(49, 92, 72, 0.25); border-radius: 999px; background: rgba(255,255,255,0.78); padding: 0.45rem 0.75rem; font-size: 0.82rem; color: var(--green); white-space: nowrap; }
        .status-dot { width: 0.55rem; height: 0.55rem; border-radius: 99px; background: #3f8f62; }
        .metric-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.75rem; margin: 0.9rem 0 1rem; }
        .metric-card { background: rgba(255,255,255,0.86); border: 1px solid var(--line); border-radius: 8px; padding: 0.85rem 0.95rem; min-height: 82px; }
        .metric-label { color: var(--muted); font-size: 0.74rem; font-weight: 700; text-transform: uppercase; }
        .metric-value { margin-top: 0.35rem; font-size: 1.08rem; font-weight: 800; color: var(--ink); overflow-wrap: anywhere; }
        .risk-low { color: var(--green); } .risk-medium { color: var(--amber); } .risk-high { color: var(--red); }
        .section-title { font-size: 0.86rem; font-weight: 800; text-transform: uppercase; color: #35413b; margin: 0.75rem 0 0.65rem; }
        .chip { display: inline-block; padding: 0.28rem 0.5rem; margin: 0.12rem 0.18rem 0.12rem 0; border-radius: 999px; background: #e9efe5; border: 1px solid #d6dfd1; font-size: 0.78rem; color: #2d3a33; }
        .source-chip { display: block; padding: 0.48rem 0.58rem; margin-bottom: 0.35rem; border-radius: 7px; background: #eef4f6; border: 1px solid #d6e5ea; color: #26485a; font-size: 0.78rem; }
        div[data-testid="stChatMessage"] { background: rgba(255,255,255,0.75); border: 1px solid rgba(217, 223, 216, 0.9); border-radius: 8px; padding: 0.7rem; }
        @media (max-width: 900px) { .metric-row { grid-template-columns: repeat(2, minmax(0, 1fr)); } .topbar { flex-direction: column; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def empty_response_state() -> dict[str, list[Any]]:
    """Return empty assistant response state."""
    return {"tool_calls": [], "retrieved_documents": [], "sources": [], "suggested_questions": []}


def empty_patient_form() -> dict[str, Any]:
    """Return defaults for the add-patient form."""
    return {
        "patient_id": "",
        "name": "",
        "age": 45,
        "sex": "female",
        "conditions": ["Hypertension"],
        "medications": ["Lisinopril"],
        "allergies": [],
        "risk_level": "medium",
        "blood_pressure": "132/82",
        "hba1c": None,
        "ldl": None,
        "primary_provider": "Dr. Smith",
        "last_visit": date.today().isoformat(),
        "care_gaps": ["Annual wellness visit due"],
    }


def normalize_patient_form(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize uploaded or generated patient data for form widgets."""
    def pick_list(key: str, options: list[str]) -> list[str]:
        value = payload.get(key, [])
        if not isinstance(value, list):
            return []
        return [item for item in value if item in options]

    return {
        "patient_id": str(payload.get("patient_id", "")).zfill(3) if payload.get("patient_id") else "",
        "name": str(payload.get("name", "")),
        "age": int(payload.get("age", 45)),
        "sex": payload.get("sex", "female") if payload.get("sex") in {"female", "male", "other"} else "female",
        "conditions": pick_list("conditions", CONDITION_OPTIONS) or ["Hypertension"],
        "medications": pick_list("medications", MEDICATION_OPTIONS),
        "allergies": pick_list("allergies", ALLERGY_OPTIONS),
        "risk_level": payload.get("risk_level", "medium") if payload.get("risk_level") in {"low", "medium", "high"} else "medium",
        "blood_pressure": str(payload.get("blood_pressure", "132/82")),
        "hba1c": payload.get("hba1c"),
        "ldl": payload.get("ldl"),
        "primary_provider": str(payload.get("primary_provider", "Dr. Smith")),
        "last_visit": str(payload.get("last_visit", date.today().isoformat())),
        "care_gaps": pick_list("care_gaps", CARE_GAP_OPTIONS) or ["Annual wellness visit due"],
    }


def render_header(settings: dict[str, Any]) -> None:
    """Render app header."""
    model = settings.get("llm_model", "not configured")
    st.markdown(
        f"""
        <div class="topbar">
          <div class="title-block">
            <h1>Patient360 Copilot</h1>
            <p>Clinical workspace for patient summaries, care gaps, guideline evidence, risk scoring, and follow-up messaging.</p>
          </div>
          <div class="status-pill"><span class="status-dot"></span>{model} / Chroma HTTP</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_patient(patients: list[dict[str, Any]]) -> dict[str, Any]:
    """Render patient selector and profile details."""
    with st.sidebar:
        st.subheader("Panel")
        selected_id = st.session_state.get("selected_patient_id")
        selected_index = next((index for index, item in enumerate(patients) if item["patient_id"] == selected_id), 0)
        selected_patient = st.selectbox(
            "Patient",
            patients,
            index=selected_index,
            format_func=lambda item: f"{item['patient_id']} - {item['name']}",
        )
        st.divider()
        st.markdown(f"### {selected_patient['name']}")
        st.caption(f"Patient {selected_patient['patient_id']} / Last visit {selected_patient['last_visit']}")
        st.markdown("".join(f'<span class="chip">{condition}</span>' for condition in selected_patient["conditions"]), unsafe_allow_html=True)
        st.divider()
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_response = empty_response_state()
            st.rerun()
    return selected_patient


def render_patient_metrics(patient: dict[str, Any]) -> None:
    """Render selected patient metrics."""
    risk_class = f"risk-{patient['risk_level']}"
    hba1c = patient.get("hba1c") if patient.get("hba1c") is not None else "N/A"
    ldl = patient.get("ldl") if patient.get("ldl") is not None else "N/A"
    st.markdown(
        f"""
        <div class="metric-row">
          <div class="metric-card"><div class="metric-label">Age / sex</div><div class="metric-value">{patient['age']} / {patient['sex'].title()}</div></div>
          <div class="metric-card"><div class="metric-label">Risk level</div><div class="metric-value {risk_class}">{patient['risk_level'].title()}</div></div>
          <div class="metric-card"><div class="metric-label">Blood pressure</div><div class="metric-value">{patient['blood_pressure']}</div></div>
          <div class="metric-card"><div class="metric-label">A1c / LDL</div><div class="metric-value">{hba1c} / {ldl}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_prompt_suggestions(patient_id: str) -> None:
    """Render context-aware prompt suggestions."""
    suggestions = st.session_state.last_response.get("suggested_questions", [])
    if not st.session_state.messages or not suggestions:
        suggestions = [f"Summarize patient {patient_id}"]
    st.markdown('<div class="section-title">Suggested Questions</div>', unsafe_allow_html=True)
    cols = st.columns(min(len(suggestions), 4))
    for index, suggestion in enumerate(suggestions[:4]):
        with cols[index]:
            if st.button(suggestion, use_container_width=True, key=f"suggestion_{index}"):
                st.session_state.pending_prompt = suggestion
                st.rerun()


def run_chat_prompt(prompt: str, selected_patient: dict[str, Any]) -> None:
    """Submit a prompt to the backend and update chat state."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    response = api_post(
        "/chat",
        {"message": prompt, "patient_id": selected_patient["patient_id"], "history": st.session_state.messages[:-1]},
    )
    st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
    st.session_state.last_response = response


def render_message_box(selected_patient: dict[str, Any]) -> None:
    """Render prompt box below the conversation."""
    with st.form("advisor_prompt_form", clear_on_submit=True):
        prompt = st.text_area(
            "Ask Patient360 Copilot",
            placeholder="Ask about care gaps, care programs, guideline evidence, risk, or follow-up messaging",
            height=88,
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Send", use_container_width=True)
    if submitted and prompt.strip():
        with st.spinner("Running clinical tools"):
            run_chat_prompt(prompt.strip(), selected_patient)
        st.rerun()


def render_evidence_panel() -> None:
    """Render tool calls, retrieved documents, and sources."""
    response = st.session_state.last_response
    st.markdown('<div class="section-title">Tool Calls</div>', unsafe_allow_html=True)
    tool_calls = response.get("tool_calls", [])
    if not tool_calls:
        st.caption("No tool calls yet.")
    for call in tool_calls:
        with st.expander(call["name"], expanded=False):
            st.json({"arguments": call["arguments"], "result": call["result"]})

    st.markdown('<div class="section-title">Retrieved Documents</div>', unsafe_allow_html=True)
    docs = response.get("retrieved_documents", [])
    if not docs:
        st.caption("No documents retrieved yet.")
    for doc in docs:
        with st.expander(f"{doc['document_name']} ({doc['document_type']})", expanded=False):
            st.caption(f"Score: {doc.get('score')}")
            st.write(doc["chunk"])

    st.markdown('<div class="section-title">Sources</div>', unsafe_allow_html=True)
    sources = response.get("sources", [])
    if sources:
        for source in sources:
            st.markdown(f'<span class="source-chip">{source}</span>', unsafe_allow_html=True)
    else:
        st.caption("No citations yet.")


def render_workspace_tab(selected_patient: dict[str, Any]) -> None:
    """Render Patient360 chat workspace."""
    render_patient_metrics(selected_patient)
    pending_prompt = st.session_state.pop("pending_prompt", None)
    if pending_prompt:
        with st.spinner("Running clinical tools"):
            run_chat_prompt(pending_prompt, selected_patient)

    chat_col, evidence_col = st.columns([0.64, 0.36], gap="large")
    with chat_col:
        st.markdown('<div class="section-title">Clinical Conversation</div>', unsafe_allow_html=True)
        for item in st.session_state.messages:
            with st.chat_message(item["role"]):
                st.markdown(item["content"])
        render_message_box(selected_patient)
        render_prompt_suggestions(selected_patient["patient_id"])
    with evidence_col:
        render_evidence_panel()


def render_add_patient_tab() -> None:
    """Render a form for adding a new patient profile."""
    if "new_patient_form" not in st.session_state:
        st.session_state.new_patient_form = empty_patient_form()

    st.markdown('<div class="section-title">Add A New Patient</div>', unsafe_allow_html=True)
    st.caption("Patient profiles are stored as JSON files and are available immediately. ChromaDB reindexing is not required.")
    upload_col, generate_col = st.columns([0.58, 0.42], gap="large")
    with upload_col:
        uploaded_file = st.file_uploader("Patient JSON file", type=["json"])
        if st.button("Load from file", use_container_width=True):
            if uploaded_file is None:
                st.warning("Upload a JSON patient file first.")
            else:
                try:
                    payload = json.loads(uploaded_file.getvalue().decode("utf-8"))
                    st.session_state.new_patient_form = normalize_patient_form(payload)
                    st.success("Patient data loaded into the form.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not load patient file: {exc}")
    with generate_col:
        st.write("")
        st.write("")
        if st.button("Generate data", use_container_width=True):
            generated = api_get("/patients/demo-profile")
            st.session_state.new_patient_form = normalize_patient_form(generated)
            st.success("Demo patient generated.")
            st.rerun()

    form_state = st.session_state.new_patient_form
    try:
        last_visit = date.fromisoformat(form_state["last_visit"])
    except ValueError:
        last_visit = date.today()

    with st.form("add_patient_form"):
        left, right = st.columns(2, gap="large")
        with left:
            patient_id = st.text_input("Patient ID", value=form_state["patient_id"], placeholder="Leave blank to use next ID")
            name = st.text_input("Name", value=form_state["name"])
            age = st.number_input("Age", min_value=0, max_value=110, value=int(form_state["age"]), step=1)
            sex = st.selectbox("Sex", ["female", "male", "other"], index=["female", "male", "other"].index(form_state["sex"]))
            primary_provider = st.text_input("Primary provider", value=form_state["primary_provider"])
            blood_pressure = st.text_input("Blood pressure", value=form_state["blood_pressure"])
            hba1c = st.number_input("A1c", min_value=0.0, max_value=16.0, value=float(form_state["hba1c"] or 0.0), step=0.1)
            ldl = st.number_input("LDL", min_value=0, max_value=300, value=int(form_state["ldl"] or 0), step=1)
        with right:
            risk_level = st.selectbox("Risk level", ["low", "medium", "high"], index=["low", "medium", "high"].index(form_state["risk_level"]))
            conditions = st.multiselect("Conditions", CONDITION_OPTIONS, default=form_state["conditions"])
            medications = st.multiselect("Medications", MEDICATION_OPTIONS, default=form_state["medications"])
            allergies = st.multiselect("Allergies", ALLERGY_OPTIONS, default=form_state["allergies"])
            care_gaps = st.multiselect("Care gaps", CARE_GAP_OPTIONS, default=form_state["care_gaps"])
            last_visit_value = st.date_input("Last visit", value=last_visit)
        submitted = st.form_submit_button("Submit new patient", use_container_width=True)

    if submitted:
        payload = {
            "patient_id": patient_id.strip().zfill(3) if patient_id.strip() else api_get("/patients/demo-profile")["patient_id"],
            "name": name.strip(),
            "age": int(age),
            "sex": sex,
            "conditions": conditions or ["Hypertension"],
            "medications": medications,
            "allergies": allergies,
            "risk_level": risk_level,
            "blood_pressure": blood_pressure.strip() or "120/80",
            "hba1c": float(hba1c) if hba1c else None,
            "ldl": int(ldl) if ldl else None,
            "primary_provider": primary_provider.strip() or "Dr. Smith",
            "last_visit": last_visit_value.isoformat(),
            "care_gaps": care_gaps or ["Annual wellness visit due"],
        }
        try:
            created = api_post("/patients", payload)
        except Exception as exc:
            st.error(f"Could not create patient: {exc}")
        else:
            st.session_state.new_patient_form = empty_patient_form()
            st.session_state.selected_patient_id = created["patient_id"]
            st.session_state.messages = []
            st.session_state.last_response = empty_response_state()
            st.success(f"Patient {created['patient_id']} added. No document reindexing required.")
            st.rerun()


def render_connection_test(service: str, label: str) -> None:
    """Render a connection test button."""
    if st.button(label, use_container_width=True):
        with st.spinner(f"Testing {service}"):
            result = api_post(f"/settings/test/{service}")
        if result["ok"]:
            st.success(result["message"])
        else:
            st.error(result["message"])


def render_settings_tab(settings: dict[str, Any]) -> None:
    """Render runtime settings controls."""
    left, right = st.columns([0.58, 0.42], gap="large")
    with left:
        st.markdown('<div class="section-title">Runtime Configuration</div>', unsafe_allow_html=True)
        with st.form("runtime_settings_form"):
            llm_base_url = st.text_input("LLM endpoint", value=settings["llm_base_url"])
            llm_model = st.text_input("LLM model name", value=settings["llm_model"])
            llm_api_key = st.text_input("LLM token", value="", type="password", placeholder="Leave blank to keep the current token")
            llm_ssl_verify = st.checkbox("Verify LLM TLS certificate", value=bool(settings["llm_ssl_verify"]))
            embedding_model = st.text_input("Embedding model", value=settings["embedding_model"])
            embedding_base_url = st.text_input("Embedding endpoint", value=settings["embedding_base_url"])
            embedding_api_key = st.text_input("Embedding token", value="", type="password", placeholder="Leave blank to keep the current token")
            embedding_ssl_verify = st.checkbox("Verify embedding TLS certificate", value=bool(settings["embedding_ssl_verify"]))
            st.caption("ChromaDB is remote-only. Leave it blank until your server endpoint is ready.")
            chroma_host = st.text_input("ChromaDB endpoint or host", value=settings["chroma_host"])
            chroma_port = st.number_input("ChromaDB port", min_value=1, max_value=65535, value=int(settings["chroma_port"]), step=1)
            chroma_ssl = st.checkbox("Use SSL for ChromaDB", value=bool(settings["chroma_ssl"]))
            chroma_ssl_verify = st.checkbox("Verify ChromaDB TLS certificate", value=bool(settings["chroma_ssl_verify"]))
            chroma_tenant = st.text_input("ChromaDB tenant", value=settings["chroma_tenant"])
            chroma_database = st.text_input("ChromaDB database", value=settings["chroma_database"])
            llm_timeout_seconds = st.number_input("LLM timeout seconds", min_value=1.0, max_value=300.0, value=float(settings["llm_timeout_seconds"]), step=1.0)
            submitted = st.form_submit_button("Save settings", use_container_width=True)
        if submitted:
            updated = api_put(
                "/settings",
                {
                    "llm_base_url": llm_base_url,
                    "llm_model": llm_model,
                    "llm_api_key": llm_api_key or None,
                    "llm_ssl_verify": llm_ssl_verify,
                    "embedding_model": embedding_model,
                    "embedding_base_url": embedding_base_url,
                    "embedding_api_key": embedding_api_key or None,
                    "embedding_ssl_verify": embedding_ssl_verify,
                    "chroma_mode": "http",
                    "chroma_host": chroma_host,
                    "chroma_port": chroma_port,
                    "chroma_ssl": chroma_ssl,
                    "chroma_ssl_verify": chroma_ssl_verify,
                    "chroma_tenant": chroma_tenant,
                    "chroma_database": chroma_database,
                    "llm_timeout_seconds": llm_timeout_seconds,
                },
            )
            st.session_state.runtime_settings = updated
            st.success("Settings saved. They will be reused after backend restarts.")
    with right:
        st.markdown('<div class="section-title">Active Backend State</div>', unsafe_allow_html=True)
        current = st.session_state.get("runtime_settings", settings)
        st.json(current)
        st.markdown('<div class="section-title">Connection Tests</div>', unsafe_allow_html=True)
        st.caption("Save settings first, then test the active backend configuration.")
        test_llm_col, test_embedding_col, test_chroma_col = st.columns(3)
        with test_llm_col:
            render_connection_test("llm", "Test LLM")
        with test_embedding_col:
            render_connection_test("embedding", "Test embeddings")
        with test_chroma_col:
            render_connection_test("chroma", "Test ChromaDB")
        st.markdown('<div class="section-title">Index Maintenance</div>', unsafe_allow_html=True)
        if st.button("Reindex documents", use_container_width=True):
            with st.spinner("Rebuilding care program and guideline indexes"):
                api_post("/reindex")
            st.success("Care program and guideline indexes rebuilt.")


st.set_page_config(page_title="Patient360 Copilot", layout="wide")
inject_css()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_response" not in st.session_state:
    st.session_state.last_response = empty_response_state()

try:
    patients = api_get("/patients")
    runtime_settings = api_get("/settings")
    st.session_state.runtime_settings = runtime_settings
except Exception as exc:
    st.error(f"Backend unavailable at {API_BASE_URL}: {exc}")
    st.stop()

if not patients:
    st.error("No patients found. Run the demo data generator or restart the app startup script.")
    st.stop()

render_header(st.session_state.runtime_settings)
selected = render_sidebar_patient(patients)
if st.session_state.get("selected_patient_id") != selected["patient_id"]:
    st.session_state.selected_patient_id = selected["patient_id"]
    st.session_state.messages = []
    st.session_state.last_response = empty_response_state()
workspace_tab, add_patient_tab, settings_tab = st.tabs(["Patient360 Workspace", "Add A New Patient", "Settings"])

with workspace_tab:
    render_workspace_tab(selected)
with add_patient_tab:
    render_add_patient_tab()
with settings_tab:
    render_settings_tab(st.session_state.runtime_settings)
