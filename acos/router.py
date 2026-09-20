from __future__ import annotations

from dataclasses import dataclass

from .quantum import qiskit_available


@dataclass(frozen=True)
class ComputeRoute:
    backend: str
    reason: str
    confidence: float


class ComputeRouter:
    """Prototype heterogeneous compute router.

    It intentionally chooses quantum only for explicitly quantum-native work; a mature HSC
    would benchmark cost, latency, fidelity and expected advantage before routing.
    """

    QUANTUM_TERMS = {"quantum", "qubit", "bell state", "grover", "qaoa", "hamiltonian"}
    GPU_TERMS = {"gpu", "matrix", "tensor", "render", "neural", "embedding", "vision"}

    def route(self, text: str) -> ComputeRoute:
        lower = text.lower()
        if any(term in lower for term in self.QUANTUM_TERMS):
            if qiskit_available():
                return ComputeRoute(
                    "qpu-simulator",
                    "Quantum-native terms detected; Qiskit is available.",
                    0.86,
                )
            return ComputeRoute(
                "cpu", "Quantum work detected, but no quantum backend is installed.", 0.74
            )
        if any(term in lower for term in self.GPU_TERMS):
            return ComputeRoute("gpu-preferred", "Parallel numerical/AI workload detected.", 0.78)
        return ComputeRoute("cpu", "General-purpose control/reasoning workload.", 0.70)
