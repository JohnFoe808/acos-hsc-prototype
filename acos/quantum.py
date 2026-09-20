from __future__ import annotations

from typing import Any


def qiskit_available() -> bool:
    try:
        import qiskit  # noqa: F401

        return True
    except ImportError:
        return False


def bell_state(shots: int = 1024) -> dict[str, Any]:
    """Run a two-qubit Bell-state experiment using Qiskit's StatevectorSampler.

    This is simulation unless you later replace this adapter with a physical-QPU backend.
    """
    if not qiskit_available():
        return {
            "backend": "deterministic-quantum-simulator",
            "shots": shots,
            "counts": {"00": shots // 2, "11": shots - (shots // 2)},
            "circuit": "H(0) -> CX(0,1) -> measure_all",
            "physical_qpu": False,
        }

    from qiskit import QuantumCircuit
    from qiskit.primitives import StatevectorSampler

    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    sampler = StatevectorSampler(seed=42)
    result = sampler.run([qc], shots=shots).result()
    counts = result[0].data.meas.get_counts()
    return {
        "backend": "qiskit.StatevectorSampler",
        "shots": shots,
        "counts": counts,
        "circuit": "H(0) -> CX(0,1) -> measure_all",
    }
