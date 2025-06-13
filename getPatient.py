from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import asyncio

# Initialize FastMCP server
mcp = FastMCP("clinical_summary")

FHIR_BASE = "https://hapi.fhir.org/baseR4"
USER_AGENT = "my-mcp-client"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/fhir+json"
}

# -------------------------------
# UTILITY: FHIR Fetcher
# -------------------------------
async def fetch_fhir_resource(resource: str, params: dict[str, str]) -> list[dict[str, Any]]:
    url = f"{FHIR_BASE}/{resource}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=HEADERS, params=params, timeout=15.0)
            response.raise_for_status()
            bundle = response.json()
            return [entry["resource"] for entry in bundle.get("entry", [])]
        except Exception as e:
            print(f"Error fetching {resource}: {e}")
            return []

async def fetch_fhir_patient(patient_id: str) -> dict[str, Any] | None:
    url = f"{FHIR_BASE}/Patient/{patient_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=HEADERS, timeout=15.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching patient: {e}")
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

# -------------------------------
# CLINICAL SUMMARY TOOL (No Filtering)
# -------------------------------
@mcp.tool()
async def get_clinical_summary_by_patient_id(patient_id: str) -> str:
    patient = await fetch_fhir_patient(patient_id)
    if not patient:
        return "❌ Patient not found."

    # Run all resource fetches concurrently
    results = await asyncio.gather(
        fetch_fhir_resource("Encounter", {"_patient": patient_id}),
        fetch_fhir_resource("Condition", {"_patient": patient_id}),
        fetch_fhir_resource("Observation", {"_patient": patient_id}),
        fetch_fhir_resource("DiagnosticReport", {"_patient": patient_id}),
        fetch_fhir_resource("Procedure", {"_patient": patient_id}),
        fetch_fhir_resource("MedicationStatement", {"_patient": patient_id}),
        fetch_fhir_resource("AllergyIntolerance", {"_patient": patient_id}),
        fetch_fhir_resource("FamilyMemberHistory", {"_patient": patient_id}),
    )

    encounters, conditions, observations, reports, procedures, meds, allergies, histories = results

    def fmt(items, title, key, fallback="Unknown") -> str:
        lines = [
            f"{title} {i+1}: {item.get(key, {}).get('text', fallback)}"
            for i, item in enumerate(items)
        ]
        return format_section(title, lines)

    output = [
        "📘 CLINICAL SUMMARY",
        format_patient(patient),
        fmt(encounters, "Encounter", "type"),
        fmt(conditions, "Condition", "code"),
        fmt(observations, "Observation", "code"),
        fmt(reports, "Diagnostic Report", "code"),
        fmt(procedures, "Procedure", "code"),
        fmt(meds, "Medication", "medicationCodeableConcept"),
        fmt(allergies, "Allergy", "code"),
        fmt(histories, "Family History", "relationship"),
    ]

    return "\n".join(output)


# -------------------------------
# ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    print("MCP starting...", flush=True)
    mcp.run(transport="stdio")
