from typing import Any
from strands import tool
import httpx
import asyncio

FHIR_BASE = "https://hapi.fhir.org/baseR4"
USER_AGENT = "my-mcp-client"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/fhir+json"
}

# Shared HTTP client (reuse connection pool)
client = httpx.AsyncClient(timeout=15.0, headers=HEADERS)

# -------------------------------
# UTILITY: Fetch Patient + Related Resources in One Call
# -------------------------------
async def fetch_patient_bundle(patient_id: str) -> dict[str, Any] | None:
    url = f"{FHIR_BASE}/Patient/{patient_id}"
    params = {
        "_revinclude": [
            "Encounter:patient",
            "Condition:patient",
            "Observation:patient",
            "DiagnosticReport:patient",
            "Procedure:patient",
            "MedicationStatement:patient",
            "AllergyIntolerance:patient",
            "FamilyMemberHistory:patient"
        ],
        "_count": "5"
    }
    try:
        response = await client.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching patient bundle: {e}")
        return None

# -------------------------------
# FORMATTERS
# -------------------------------
def format_patient(resource: dict[str, Any]) -> str:
    name = resource.get("name", [{}])[0]
    full_name = " ".join(name.get("given", []) + [name.get("family", "")]).strip()
    gender = resource.get("gender", "Unknown")
    birth_date = resource.get("birthDate", "Unknown")
    return f"Patient ID: {resource.get('id', 'N/A')}\nName: {full_name or 'N/A'}\nGender: {gender}\nBirth Date: {birth_date}"

def format_section(title: str, items: list[str]) -> str:
    return f"\n\n🔹 {title} 🔹\n" + ("\n".join(items) if items else "None found.")

# Group entries by resource type
def group_entries(bundle: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in bundle.get("entry", []):
        res = entry.get("resource")
        if not res:
            continue
        res_type = res.get("resourceType")
        if res_type not in grouped:
            grouped[res_type] = []
        grouped[res_type].append(res)
    return grouped

def fmt(items: list[dict[str, Any]], title: str, key: str, fallback: str = "Unknown") -> str:
    lines = [
        f"{title} {i+1}: {item.get(key, {}).get('text', fallback)}"
        for i, item in enumerate(items)
    ]
    return format_section(title, lines)

# -------------------------------
# TOOL FUNCTION
# -------------------------------
@tool
async def get_clinical_summary_by_patient_id(patient_id: str) -> str:
    bundle = await fetch_patient_bundle(patient_id)
    if not bundle:
        return "❌ Patient not found."

    grouped = group_entries(bundle)
    patient = grouped.get("Patient", [{}])[0]

    output = [
        "📘 CLINICAL SUMMARY",
        format_patient(patient),
        fmt(grouped.get("Encounter", []), "Encounter", "type"),
        fmt(grouped.get("Condition", []), "Condition", "code"),
        fmt(grouped.get("Observation", []), "Observation", "code"),
        fmt(grouped.get("DiagnosticReport", []), "Diagnostic Report", "code"),
        fmt(grouped.get("Procedure", []), "Procedure", "code"),
        fmt(grouped.get("MedicationStatement", []), "Medication", "medicationCodeableConcept"),
        fmt(grouped.get("AllergyIntolerance", []), "Allergy", "code"),
        fmt(grouped.get("FamilyMemberHistory", []), "Family History", "relationship"),
    ]

    return "\n".join(output)

# -------------------------------
# Export tools list for Lambda
# -------------------------------
tools = [get_clinical_summary_by_patient_id]
