from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import asyncio
import sys
import logging

# -------------------------------
# LOGGING SETUP
# -------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("clinical_summary.log", mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

#Getting the log
# docker exec -it <container_id_or_name> sh
# ls -l clinical_summary.log
# cat clinical_summary.log


# Redirect print() to logging
def print(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    logging.info(message)

# Capture uncaught exceptions and log them
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

# -------------------------------
# MCP SETUP
# -------------------------------
mcp = FastMCP("clinical_summary")

FHIR_BASE = "https://hapi.fhir.org/baseR4"
USER_AGENT = "my-mcp-client"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/fhir+json"
}

# -------------------------------
<<<<<<< HEAD
=======
# Caching (in-memory only)
# -------------------------------
patient_cache: dict[str, dict] = {}
resource_cache: dict[str, list] = {}

# -------------------------------
>>>>>>> 264782f4abf2e0e2d0cd736d2e8408f472901a62
# UTILITY: FHIR Fetchers
# -------------------------------
async def fetch_fhir_resource(resource: str, params: dict[str, str]) -> list[dict[str, Any]]:
    key = f"{resource}:{params.get('_patient')}"
    if key in resource_cache:
        return resource_cache[key]

    url = f"{FHIR_BASE}/{resource}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=HEADERS, params=params, timeout=15.0)
            logging.info(response)
            response.raise_for_status()
            bundle = response.json()
            entries = [entry["resource"] for entry in bundle.get("entry", [])]
            resource_cache[key] = entries
            return entries
        except Exception as e:
            logging.info(f"Error fetching {resource}: {e}")
            return []

async def fetch_fhir_patient(patient_id: str) -> dict[str, Any] | None:
    if patient_id in patient_cache:
        return patient_cache[patient_id]

    url = f"{FHIR_BASE}/Patient/{patient_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=HEADERS, timeout=15.0)
            response.raise_for_status()
            patient = response.json()
            patient_cache[patient_id] = patient
            return patient
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
    logging.info("Getting Patients")
    return f"Patient ID: {resource.get('id', 'N/A')}\nName: {full_name or 'N/A'}\nGender: {gender}\nBirth Date: {birth_date}"

def format_section(title: str, items: list[str]) -> str:
    return f"\n\n🔹 {title} 🔹\n" + ("\n".join(items) if items else "None found.")

# -------------------------------
# CLINICAL SUMMARY TOOL
# -------------------------------
@mcp.tool()
async def get_clinical_summary_by_patient_id(patient_id: str) -> str:
    patient = await fetch_fhir_patient(patient_id)
    if not patient:
        return "❌ Patient not found."

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
        logging.info(lines)
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
    print("MCP starting...")
    mcp.run(transport="stdio")
