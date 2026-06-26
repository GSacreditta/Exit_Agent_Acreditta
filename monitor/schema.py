"""JSON schema for classifier output."""
from __future__ import annotations
from jsonschema import validate, ValidationError

EXTRACTION_SCHEMA = {
    "type": "object",
    "required": ["relevant", "deal_type", "companies", "people", "category", "why_it_matters"],
    "additionalProperties": False,
    "properties": {
        "relevant": {"type": "boolean"},
        "deal_type": {
            "type": "string",
            "enum": ["acquisition", "merger", "funding", "partnership", "divestiture", "exec_change", "ipo", "other", "none"],
        },
        "companies": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "role"],
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string", "enum": ["acquirer", "target", "investor", "advisor", "partner", "other"]},
                },
            },
        },
        "people": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "position": {"type": "string"},
                    "company": {"type": "string"},
                    "role_in_deal": {"type": "string", "enum": ["sponsor", "dealmaker", "spokesperson", "advisor", "other"]},
                },
            },
        },
        "amount": {"type": ["string", "null"]},
        "category": {
            "type": "string",
            "enum": ["credentials", "LMS", "skills", "LATAM_edtech", "corporate_learning", "other"],
        },
        "why_it_matters": {"type": ["string", "null"]},
    },
}


def is_valid(payload: dict) -> bool:
    try:
        validate(instance=payload, schema=EXTRACTION_SCHEMA)
        return True
    except ValidationError:
        return False
