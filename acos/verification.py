from __future__ import annotations

from typing import Any


def verify_plan(plan: dict[str, Any], evidence: list[str] | None = None) -> dict[str, Any]:
    """Conservative verification: a plan is verified only with explicit evidence."""
    evidence = [item.strip() for item in (evidence or []) if item.strip()]
    verified = bool(evidence) and bool(plan.get("steps"))
    return {
        "verified": verified,
        "confidence": 0.85 if verified else 0.35,
        "evidence": evidence,
        "reason": (
            "Explicit evidence supplied."
            if verified
            else "No explicit evidence; outcome remains provisional."
        ),
    }
