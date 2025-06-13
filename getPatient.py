import asyncio
import time

RESOURCE_TYPES = [
    ("Encounter", "type"),
    ("Condition", "code"),
    ("Observation", "code"),
    ("DiagnosticReport", "code"),
    ("Procedure", "code"),
    ("MedicationStatement", "medicationCodeableConcept"),
    ("AllergyIntolerance", "code"),
    ("FamilyMemberHistory", "relationship")
]

# Task wrapper
async def fetch_task(resource: str, patient_id: str):
    return resource, await fetch_fhir_resource(resource, {"_patient": patient_id, "_count": "5"})

@tool
async def get_clinical_summary_by_patient_id(patient_id: str) -> str:
    start = time.perf_counter()

    patient = await fetch_fhir_patient(patient_id)
    if not patient:
        return "❌ Patient not found."

    tasks = [asyncio.create_task(fetch_task(res, patient_id)) for res, _ in RESOURCE_TYPES]

    completed: dict[str, list[dict[str, Any]]] = {}
    timeout = 20.0  # seconds

    while tasks and (time.perf_counter() - start) < timeout:
        done, pending = await asyncio.wait(tasks, timeout=1.0, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            try:
                res_type, data = task.result()
                completed[res_type] = data
            except Exception:
                pass
        tasks = list(pending)

    def fmt(items: list[dict[str, Any]], title: str, key: str, fallback: str = "Unknown") -> str:
        lines = [
            f"{title} {i+1}: {item.get(key, {}).get('text', fallback)}"
            for i, item in enumerate(items)
        ]
        return format_section(title, lines)

    output = [
        f"📘 CLINICAL SUMMARY (partial after {time.perf_counter()-start:.1f}s)",
        format_patient(patient)
    ]

    for res_type, key in RESOURCE_TYPES:
        if res_type in completed:
            output.append(fmt(completed[res_type], res_type, key))
        else:
            output.append(f"\n\n🔹 {res_type} 🔹\n⏳ Timed out.")

    return "\n".join(output)
