from __future__ import annotations

import concurrent.futures
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

import psutil

from .permissions import PermissionBroker
from .quantum import bell_state, qiskit_available
from .store import Store


@dataclass(frozen=True)
class BackendCapability:
    identity: str
    kind: str
    available: bool
    health: str
    utilization: float | None
    memory: dict[str, Any]
    operations: tuple[str, ...]
    latency_ms: float | None
    estimated_runtime_ms: float | None
    energy_cost: dict[str, Any]
    queue_state: dict[str, Any]
    failure: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "kind": self.kind,
            "available": self.available,
            "health": self.health,
            "utilization": self.utilization,
            "memory": self.memory,
            "operations": list(self.operations),
            "latency_ms": self.latency_ms,
            "estimated_runtime_ms": self.estimated_runtime_ms,
            "energy_cost": self.energy_cost,
            "queue_state": self.queue_state,
            "failure": self.failure,
        }


class ComputeBackend(Protocol):
    name: str

    def capability(self) -> BackendCapability: ...

    def execute(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class CPUFabricBackend:
    name: str = "cpu"

    def capability(self) -> BackendCapability:
        return BackendCapability(
            self.name,
            "cpu",
            True,
            "healthy",
            psutil.cpu_percent(interval=0.01) / 100,
            {"system_memory_percent": psutil.virtual_memory().percent},
            ("sum", "identity", "sleep", "benchmark"),
            1.0,
            1.0,
            {"energy": "measured by host telemetry", "cost": "local"},
            {"queued": 0, "running": 0},
        )

    def execute(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        if operation == "sum":
            values = payload.get("values", [])
            if not isinstance(values, list) or not all(isinstance(v, (int, float)) for v in values):
                raise ValueError("sum requires numeric values")
            return {"value": sum(values), "backend": self.name}
        if operation == "identity":
            return {"value": payload.get("value"), "backend": self.name}
        if operation == "sleep":
            time.sleep(min(float(payload.get("seconds", 0)), 10))
            return {"value": "complete", "backend": self.name}
        if operation == "benchmark":
            started = time.perf_counter()
            sum(range(10_000))
            return {"elapsed_ms": (time.perf_counter() - started) * 1000, "backend": self.name}
        raise ValueError(f"Unsupported CPU operation: {operation}")


@dataclass
class GPUFabricBackend:
    name: str = "gpu"
    mock_available: bool = False

    def capability(self) -> BackendCapability:
        detected = self.mock_available or bool(__import__("shutil").which("nvidia-smi"))
        return BackendCapability(
            self.name,
            "gpu",
            detected,
            "healthy" if detected else "unavailable",
            None,
            {},
            ("vector_sum", "benchmark") if detected else (),
            None,
            None,
            {"energy": "unavailable", "cost": "local"},
            {"queued": 0, "running": 0},
            None if detected else "No supported GPU detected.",
        )

    def execute(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.capability().available:
            raise RuntimeError("GPU backend unavailable")
        if operation in {"vector_sum", "benchmark"}:
            return CPUFabricBackend().execute("sum", {"values": payload.get("values", [])})
        raise ValueError(f"Unsupported GPU operation: {operation}")


@dataclass
class QuantumSimulatorBackend:
    name: str = "qpu-simulator"

    def capability(self) -> BackendCapability:
        available = True
        return BackendCapability(
            self.name,
            "quantum-simulator",
            available,
            "healthy" if available else "unavailable",
            None,
            {},
            ("bell",) if available else (),
            None,
            None,
            {"energy": "not measured", "cost": "local simulator"},
            {"queued": 0, "running": 0},
            "Deterministic simulator; Qiskit optional." if not qiskit_available() else None,
        )

    def execute(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        if operation != "bell" or not self.capability().available:
            raise RuntimeError("Quantum simulator operation unavailable")
        return {**bell_state(), "backend": self.name, "physical_qpu": False}


@dataclass
class UnavailableQPUBackend:
    name: str
    kind: str = "remote-qpu"

    def capability(self) -> BackendCapability:
        return BackendCapability(
            self.name,
            self.kind,
            False,
            "unavailable",
            None,
            {},
            (),
            None,
            None,
            {"energy": "unknown", "cost": "external"},
            {"queued": 0, "running": 0},
            "No external QPU adapter configured.",
        )

    def execute(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("External QPU backend is unavailable")


@dataclass
class ComputeFabric:
    store: Store
    permissions: PermissionBroker
    backends: list[ComputeBackend] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.backends:
            self.backends = [
                CPUFabricBackend(),
                GPUFabricBackend(),
                QuantumSimulatorBackend(),
                UnavailableQPUBackend("remote-qpu"),
                UnavailableQPUBackend("local-qpu"),
            ]

    def topology(self) -> list[dict[str, Any]]:
        return [backend.capability().as_dict() for backend in self.backends]

    def backend(self, name: str) -> ComputeBackend:
        for backend in self.backends:
            if backend.name == name:
                return backend
        raise KeyError(name)

    def benchmark(self) -> list[dict[str, Any]]:
        results = []
        for backend in self.backends:
            capability = backend.capability()
            if not capability.available or "benchmark" not in capability.operations:
                continue
            started = time.perf_counter()
            try:
                result = backend.execute("benchmark", {})
                result["measured_ms"] = (time.perf_counter() - started) * 1000
                result["backend"] = backend.name
                results.append(result)
            except (RuntimeError, ValueError) as exc:
                results.append({"backend": backend.name, "error": str(exc)})
        self.store.record_event("compute.benchmark", {"results": results}, "compute")
        return results

    def plan(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        eligible = [
            item
            for item in self.topology()
            if item["available"] and operation in item["operations"]
        ]
        selected = (
            min(eligible, key=lambda item: item["estimated_runtime_ms"] or 999999)
            if eligible
            else None
        )
        return {
            "graph_id": str(uuid.uuid4()),
            "nodes": [{"id": "task-1", "operation": operation, "payload": payload}],
            "selected_backend": selected["identity"] if selected else None,
            "rationale": (
                "Selected from available measurable capabilities; no quantum advantage assumed."
            ),
            "confidence": 0.75 if selected else 0.0,
            "eligible_backends": [item["identity"] for item in eligible],
        }

    def submit(
        self,
        operation: str,
        payload: dict[str, Any],
        backend: str | None = None,
        approved: bool = False,
        timeout: float = 10,
        retries: int = 1,
    ) -> dict[str, Any]:
        plan = self.plan(operation, payload)
        selected = backend or plan["selected_backend"]
        if not selected:
            raise RuntimeError("No eligible backend")
        if selected in {"qpu-simulator", "remote-qpu", "local-qpu"}:
            decision = self.permissions.check("compute.consequential", approved=approved)
            if not decision.allowed:
                raise PermissionError(decision.reason)
        job_id = self.store.create_compute_job(selected, operation, payload, plan)
        self.store.update_compute_job(job_id, "running")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.backend(selected).execute, operation, payload)
                result = future.result(timeout=timeout)
            self.store.update_compute_job(job_id, "completed", result)
            self.store.record_event(
                "compute.outcome", {"job_id": job_id, "result": result}, "compute"
            )
            return self.store.get_compute_job(job_id)
        except (TimeoutError, concurrent.futures.TimeoutError):
            self.store.update_compute_job(job_id, "timed_out", {"error": "timeout"})
            raise TimeoutError("Compute job timed out") from None
        except (RuntimeError, ValueError, PermissionError) as exc:
            self.store.update_compute_job(job_id, "failed", {"error": str(exc)})
            raise
