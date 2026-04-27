from __future__ import annotations

from typing import Any

from app.models.domain import Policy
from app.services.openai_json import JSONLLMClient
from app.services.vector_store import VectorStore


CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "fleet_type": {"type": "string", "enum": ["Commercial", "Passenger"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string"},
    },
    "required": ["fleet_type", "confidence", "reason"],
    "additionalProperties": False,
}

VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "passed": {"type": "boolean"},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "missing_documents": {"type": "array", "items": {"type": "string"}},
        "policy_results": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["passed", "reasons", "missing_documents", "policy_results"],
    "additionalProperties": False,
}

REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "recommendation": {"type": "string", "enum": ["APPROVE", "REJECT", "REQUEST_MORE_INFO"]},
        "details": {"type": "object"},
    },
    "required": ["title", "summary", "recommendation", "details"],
    "additionalProperties": False,
}


def _fallback_classification(text: str) -> dict[str, Any]:
    commercial_terms = ("bill of lading", "cargo", "container", "freight", "pallet", "tractor", "trailer")
    passenger_terms = ("passenger", "shuttle", "sedan", "suv", "van", "ride", "bus")
    lowered = text.lower()
    commercial_score = sum(term in lowered for term in commercial_terms)
    passenger_score = sum(term in lowered for term in passenger_terms)
    fleet_type = "Passenger" if passenger_score > commercial_score else "Commercial"
    return {
        "fleet_type": fleet_type,
        "confidence": 0.68 if commercial_score or passenger_score else 0.51,
        "reason": "Fallback classifier matched invoice vocabulary without an OpenAI API key.",
    }


async def classify_invoice(text: str, llm: JSONLLMClient) -> dict[str, Any]:
    return await llm.complete_json(
        name="classify_invoice",
        schema=CLASSIFICATION_SCHEMA,
        system="Classify the invoice as Commercial or Passenger fleet. Return only structured JSON.",
        user=f"Invoice text:\n{text[:8000]}",
        fallback=_fallback_classification(text),
    )


async def retrieve_policies(fleet_type: str, region: str, vector_store: VectorStore) -> list[dict[str, Any]]:
    policies: list[Policy] = await vector_store.search_policies(fleet_type=fleet_type, region=region)
    return [
        {
            "id": policy.id,
            "name": policy.name,
            "category": policy.category,
            "region": policy.region,
            "description": policy.description,
        }
        for policy in policies
    ]


def _fallback_validation(text: str, policies: list[dict[str, Any]]) -> dict[str, Any]:
    lowered = text.lower()
    policy_results: list[dict[str, Any]] = []
    missing_documents: list[str] = []

    if "invoice" not in lowered:
        missing_documents.append("Invoice copy")
    if "vin" not in lowered and "vehicle" not in lowered:
        missing_documents.append("Vehicle identification document")
    if not policies:
        missing_documents.append("Applicable shipping policy")

    for policy in policies:
        passed = any(token in lowered for token in policy["description"].lower().split()[:8])
        policy_results.append(
            {
                "policy_id": policy["id"],
                "policy_name": policy["name"],
                "passed": passed,
                "notes": "Heuristic validation used because OpenAI API key is not configured.",
            }
        )

    passed = not missing_documents and all(item["passed"] for item in policy_results)
    return {
        "passed": passed,
        "reasons": ["All required evidence found."] if passed else ["Required inspection evidence is incomplete."],
        "missing_documents": missing_documents,
        "policy_results": policy_results,
    }


async def validate_compliance(text: str, policies: list[dict[str, Any]], llm: JSONLLMClient) -> dict[str, Any]:
    return await llm.complete_json(
        name="validate_compliance",
        schema=VALIDATION_SCHEMA,
        system="Validate shipping invoice text against the supplied policies. Return only structured JSON.",
        user=f"Invoice text:\n{text[:8000]}\n\nPolicies:\n{policies}",
        fallback=_fallback_validation(text, policies),
    )


def _fallback_report(validation: dict[str, Any]) -> dict[str, Any]:
    recommendation = "APPROVE" if validation.get("passed") else "REQUEST_MORE_INFO"
    return {
        "title": "Shipping Inspection Report",
        "summary": "Validation completed with local fallback agent logic.",
        "recommendation": recommendation,
        "details": {
            "validation": validation,
            "next_action": "Human inspector review required.",
        },
    }


async def generate_report(validation: dict[str, Any], llm: JSONLLMClient) -> dict[str, Any]:
    return await llm.complete_json(
        name="generate_report",
        schema=REPORT_SCHEMA,
        system="Generate a concise inspection report for a human shipping inspector. Return only structured JSON.",
        user=f"Validation result:\n{validation}",
        fallback=_fallback_report(validation),
    )

