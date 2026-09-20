from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ReasoningProvider(Protocol):
    name: str

    def plan(self, goal: str, memories: list[dict[str, Any]]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class DeterministicProvider:
    name: str = "deterministic"

    def plan(self, goal: str, memories: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "goal": goal,
            "assumptions": ["No external model provider configured."],
            "steps": ["observe", "retrieve", "route", "verify", "report"],
            "evidence_count": len(memories),
        }
