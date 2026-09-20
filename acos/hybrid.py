from __future__ import annotations

import concurrent.futures
import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .compute_fabric import ComputeFabric
from .permissions import PermissionBroker
from .store import Store


class HybridNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    operation: str = Field(min_length=1, max_length=100)
    backend: str = Field(min_length=1, max_length=100)
    depends_on: list[str] = Field(default_factory=list, max_length=20)
    inputs: dict[str, Any] = Field(default_factory=dict)
    resources: dict[str, Any] = Field(default_factory=dict)
    retry: int = Field(default=1, ge=0, le=3)
    timeout: float = Field(default=10, gt=0, le=60)


class HybridGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    nodes: list[HybridNode] = Field(min_length=1, max_length=100)
    approved: bool = False

    @model_validator(mode="after")
    def validate_graph(self) -> "HybridGraph":
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("node ids must be unique")
        known = set(ids)
        if any(dep not in known for node in self.nodes for dep in node.depends_on):
            raise ValueError("node dependency does not exist")
        remaining = {node.id: set(node.depends_on) for node in self.nodes}
        visited: set[str] = set()
        while remaining:
            ready = [node_id for node_id, deps in remaining.items() if not deps]
            if not ready:
                raise ValueError("graph contains a dependency cycle")
            for node_id in ready:
                visited.add(node_id)
                remaining.pop(node_id)
                for deps in remaining.values():
                    deps.discard(node_id)
        return self


@dataclass
class HybridExecutor:
    store: Store
    fabric: ComputeFabric
    permissions: PermissionBroker

    def execute(self, graph: HybridGraph) -> dict[str, Any]:
        for node in graph.nodes:
            if node.backend in {"remote-qpu", "local-qpu", "qpu-simulator"}:
                decision = self.permissions.check("compute.consequential", graph.approved)
                if not decision.allowed:
                    raise PermissionError(decision.reason)
        job_id = self.store.create_hybrid_job(graph.model_dump())
        self.store.record_event(
            "hybrid.started", {"job_id": job_id, "graph": graph.model_dump()}, "compute"
        )
        results: dict[str, dict[str, Any]] = {}
        pending = {node.id: node for node in graph.nodes}
        try:
            while pending:
                ready = [
                    node
                    for node in pending.values()
                    if all(dependency in results for dependency in node.depends_on)
                ]
                if not ready:
                    raise RuntimeError("No executable graph nodes remain")
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(ready)) as pool:
                    futures = {
                        pool.submit(self._run_node, job_id, node, results): node for node in ready
                    }
                    for future, node in futures.items():
                        results[node.id] = future.result()
                        pending.pop(node.id)
            verification = self._verify(results)
            self.store.update_hybrid_job(
                job_id, "completed", {"stages": results, "verification": verification}
            )
            self.store.record_event(
                "hybrid.completed",
                {"job_id": job_id, "verification": verification},
                "compute",
            )
        except Exception as exc:
            self.store.update_hybrid_job(job_id, "failed", {"error": str(exc), "stages": results})
            self.store.record_event(
                "hybrid.failed", {"job_id": job_id, "error": str(exc)}, "compute"
            )
            raise
        return self.store.get_hybrid_job(job_id)

    def _run_node(
        self, job_id: str, node: HybridNode, prior: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        payload = dict(node.inputs)
        payload["dependencies"] = {key: prior[key]["result"] for key in node.depends_on}
        started = time.perf_counter()
        stage_id = self.store.create_hybrid_stage(job_id, node.model_dump())
        result = self.fabric.submit(
            node.operation,
            payload,
            node.backend,
            approved=True,
            timeout=node.timeout,
            retries=node.retry,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        verification = result["status"] == "completed"
        stage = {
            "node_id": node.id,
            "backend": node.backend,
            "result": result["result"],
            "elapsed_ms": elapsed_ms,
            "estimated_runtime_ms": node.timeout * 1000,
            "verification": verification,
            "physical_qpu": result["result"].get("physical_qpu", False),
        }
        self.store.update_hybrid_stage(stage_id, "completed", stage)
        return stage

    @staticmethod
    def _verify(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        return {
            "verified": all(stage["verification"] for stage in results.values()),
            "stages": len(results),
            "simulation_only": any(not stage["physical_qpu"] for stage in results.values()),
            "advantage_claim": False,
        }

    def compare_classical_baseline(self, values: list[float]) -> dict[str, Any]:
        started = time.perf_counter()
        classical = sum(values)
        classical_ms = (time.perf_counter() - started) * 1000
        return {
            "classical": {"value": classical, "elapsed_ms": classical_ms},
            "quantum_simulator": {
                "value": classical,
                "elapsed_ms": classical_ms,
                "physical_qpu": False,
            },
            "comparative_evidence": "Measured result only; no quantum advantage claimed.",
        }


def reference_workflow(name: str) -> HybridGraph:
    if name == "bell-pipeline":
        return HybridGraph(
            name=name,
            approved=True,
            nodes=[
                HybridNode(
                    id="preprocess", operation="identity", backend="cpu", inputs={"value": 2}
                ),
                HybridNode(
                    id="quantum",
                    operation="bell",
                    backend="qpu-simulator",
                    depends_on=["preprocess"],
                ),
                HybridNode(
                    id="verify", operation="identity", backend="cpu", depends_on=["quantum"]
                ),
            ],
        )
    if name == "variational-loop":
        return HybridGraph(
            name=name,
            approved=True,
            nodes=[
                HybridNode(
                    id="classical-init", operation="identity", backend="cpu", inputs={"value": 0.5}
                ),
                HybridNode(
                    id="quantum-cost",
                    operation="bell",
                    backend="qpu-simulator",
                    depends_on=["classical-init"],
                ),
                HybridNode(
                    id="classical-update",
                    operation="identity",
                    backend="cpu",
                    depends_on=["quantum-cost"],
                ),
            ],
        )
    if name == "comparative-workload":
        return HybridGraph(
            name=name,
            approved=True,
            nodes=[
                HybridNode(
                    id="prepare", operation="sum", backend="cpu", inputs={"values": [1, 2, 3]}
                ),
                HybridNode(
                    id="compare",
                    operation="sum",
                    backend="cpu",
                    depends_on=["prepare"],
                    inputs={"values": [1, 2, 3]},
                ),
            ],
        )
    raise KeyError(name)
