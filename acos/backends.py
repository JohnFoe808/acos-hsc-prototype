from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .quantum import bell_state, qiskit_available


class ComputeBackend(Protocol):
    name: str

    def execute(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class CPUBackend:
    name: str = "cpu"

    def execute(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "backend": self.name,
            "operation": operation,
            "status": "planned",
            "payload": payload,
        }


@dataclass(frozen=True)
class GPUBackend:
    name: str = "gpu"

    def execute(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "backend": self.name,
            "operation": operation,
            "status": "planned",
            "payload": payload,
        }


@dataclass(frozen=True)
class QPUBackend:
    name: str = "qpu-simulator"

    def execute(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        if operation == "bell":
            return bell_state()
        return {"backend": self.name, "operation": operation, "status": "unsupported"}


def available_backends() -> list[str]:
    return ["cpu", "gpu", "qpu-simulator"] if qiskit_available() else ["cpu", "gpu"]
