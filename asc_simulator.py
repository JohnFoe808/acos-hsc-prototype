from __future__ import annotations

import argparse
import json
import random
import textwrap
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class SimulationBoundaryError(ValueError):
    """Raised when a simulation step exceeds the explicitly bounded model."""


@dataclass
class MemoryEntry:
    kind: str
    text: str
    weight: float
    source: str


@dataclass
class AttentionItem:
    channel: str
    text: str
    priority: float


@dataclass
class SimulationProfile:
    level: str
    capability: str
    reasoning_depth: int
    memory_span: int
    planning_scope: int
    simulation_only: bool = True
    real_consciousness: bool = False
    real_agi: bool = False
    real_asi: bool = False


class BoundedASCSystem:
    """A deliberately bounded simulation of ASC/AC, AGI-like, and ASI-like behavior.

    It models attention, memory, causal reasoning, and explicit self-claims within a closed
    deterministic sandbox. This system is not a claim that it is conscious, generally intelligent,
    or superintelligent in reality.
    """

    def __init__(self, state_path: str | Path | None = None):
        self.memory: dict[str, list[MemoryEntry]] = {
            "episodic": [],
            "semantic": [],
            "working": [],
        }
        self.attention_queue: list[AttentionItem] = []
        self.workspace: dict[str, Any] = {
            "focus": "",
            "goal": "",
            "mood": "calm",
            "self_model": "bounded simulation",
        }
        self.history: list[dict[str, Any]] = []
        self.state_path = Path(state_path) if state_path else None
        self._load_state()

    def _load_state(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.memory = data.get("memory", self.memory)
        self.attention_queue = [
            AttentionItem(**item) if isinstance(item, dict) else item for item in data.get("attention_queue", [])
        ]
        self.workspace = data.get("workspace", self.workspace)
        self.history = data.get("history", [])

    def _save_state(self) -> None:
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory": self.memory,
            "attention_queue": [item.__dict__ for item in self.attention_queue],
            "workspace": self.workspace,
            "history": self.history,
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def status(self) -> dict[str, Any]:
        return {
            "system": "Bounded ASC/AC simulation",
            "claims": {
                "real_consciousness": False,
                "real_agi": False,
                "real_asi": False,
                "simulation_only": True,
            },
            "global_workspace": {
                "focus": self.workspace["focus"],
                "goal": self.workspace["goal"],
                "mood": self.workspace["mood"],
            },
            "memory": {kind: len(items) for kind, items in self.memory.items()},
            "attention_queue": [item.__dict__ for item in self.attention_queue],
            "self_model": self.workspace["self_model"],
        }

    def observe(self, text: str, source: str = "user") -> dict[str, Any]:
        clean = text.strip()
        if not clean:
            raise SimulationBoundaryError("Observation text cannot be blank.")
        event = {
            "id": uuid.uuid4().hex[:8],
            "phase": "perceive",
            "source": source,
            "text": clean[:600],
            "timestamp": len(self.history) + 1,
        }
        self.workspace["focus"] = clean[:200]
        self.attention_queue.insert(0, AttentionItem(channel=source, text=clean, priority=1.0))
        self.attention_queue = sorted(self.attention_queue, key=lambda item: item.priority, reverse=True)[:8]
        self.memory["working"].append(MemoryEntry("working", clean, 0.7, source))
        self.history.append({"phase": "observe", **event})
        self._save_state()
        return event

    def remember(self, text: str, kind: str = "episodic") -> dict[str, Any]:
        clean = text.strip()
        if not clean:
            raise SimulationBoundaryError("Memory content cannot be blank.")
        allowed = {"episodic", "semantic", "working"}
        if kind not in allowed:
            raise SimulationBoundaryError(f"Unsupported memory kind: {kind}; allowed={sorted(allowed)}")
        entry = MemoryEntry(kind=kind, text=clean, weight=0.8, source="memory")
        self.memory[kind].append(entry)
        self.history.append({"phase": "remember", "kind": kind, "text": clean})
        self._save_state()
        return {"kind": kind, "text": clean, "stored": True}

    def recall(self, query: str, kind: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
        q = query.lower().strip()
        if not q:
            return []
        matches: list[tuple[float, str, MemoryEntry]] = []
        for bucket in self.memory.values():
            for item in bucket:
                if kind and item.kind != kind:
                    continue
                score = 0.0
                for token in q.split():
                    if token in item.text.lower():
                        score += 1.0
                if score:
                    matches.append((score, item.kind, item))
        ranked = sorted(matches, key=lambda item: (-item[0], -item[2].weight))[:limit]
        return [
            {
                "kind": entry.kind,
                "text": entry.text,
                "weight": entry.weight,
                "source": entry.source,
                "score": round(score, 2),
            }
            for score, _, entry in ranked
        ]

    def _profile_for(self, task: str) -> SimulationProfile:
        lower = task.lower()
        if any(word in lower for word in ("agi", "general", "broad", "strategy")):
            return SimulationProfile(
                level="AGI-like bounded simulation",
                capability="multi-goal planning and memory integration inside a closed, rule-bounded task environment",
                reasoning_depth=4,
                memory_span=10,
                planning_scope=6,
            )
        if any(word in lower for word in ("asi", "super", "meta", "autonomous")):
            return SimulationProfile(
                level="ASI-like bounded simulation",
                capability="speculative superintelligence profile simulated only within the sandbox",
                reasoning_depth=6,
                memory_span=18,
                planning_scope=12,
            )
        return SimulationProfile(
            level="ASC/AC bounded simulation",
            capability="bounded attention, memory, reflection, and task-tracing simulation",
            reasoning_depth=2,
            memory_span=6,
            planning_scope=3,
        )

    def plan(self, task: str) -> dict[str, Any]:
        clean = task.strip()
        if not clean:
            raise SimulationBoundaryError("Task cannot be blank.")
        profile = self._profile_for(clean)
        steps = [
            "perceive the task and current workspace state",
            "rank relevant memories and attention items",
            "build a bounded action plan",
            "simulate verification and reflection",
            "return an advisory, non-authoritative outcome",
        ]
        result = {
            "task": clean,
            "profile": {
                "level": profile.level,
                "capability": profile.capability,
                "reasoning_depth": profile.reasoning_depth,
                "memory_span": profile.memory_span,
                "planning_scope": profile.planning_scope,
            },
            "steps": steps,
            "simulation_only": True,
            "claims": {
                "real_consciousness": False,
                "real_agi": False,
                "real_asi": False,
            },
            "note": "This is a bounded simulation, not a claim of real subjective consciousness or general/superintelligence.",
        }
        self.workspace["goal"] = clean
        self.history.append({"phase": "plan", **result})
        self._save_state()
        return result

    def simulate(self, task: str, input_text: str | None = None) -> dict[str, Any]:
        clean = task.strip()
        if not clean:
            raise SimulationBoundaryError("Task cannot be blank.")
        observation = self.observe(input_text or clean, source="simulator")
        recall = self.recall(clean, limit=3)
        profile = self._profile_for(clean)
        cycle = {
            "cycle_id": uuid.uuid4().hex,
            "task": clean,
            "observation": observation,
            "recall": recall,
            "profile": {
                "level": profile.level,
                "capability": profile.capability,
                "reasoning_depth": profile.reasoning_depth,
                "memory_span": profile.memory_span,
                "planning_scope": profile.planning_scope,
            },
            "trace": [
                "perceive",
                "attend",
                "reason",
                "reflect",
                "select_action",
                "report",
            ],
            "claims": {
                "real_consciousness": False,
                "real_agi": False,
                "real_asi": False,
                "simulation_only": True,
            },
            "summary": (
                "The system simulated an internal cognitive loop with bounded attention and memory. "
                "It did not produce real subjective experience or unrestricted AGI/ASI capability."
            ),
        }
        self.history.append({"phase": "simulate", **cycle})
        self._save_state()
        return cycle

    def interactive_loop(self) -> None:
        print("Bounded ASC/AC simulation shell")
        print("Commands: status | observe <text> | remember <text> | recall <query> | plan <task> | simulate <task> | help | quit")
        while True:
            try:
                raw = input("asc> ").strip()
            except EOFError:
                print()
                break
            if not raw:
                continue
            if raw.lower() in {"quit", "exit"}:
                print("Session ended. Simulation remains bounded.")
                break
            if raw.lower() == "help":
                print("This shell models explicit bounded simulation of ASC/AC, AGI-like, and ASI-like behavior.")
                print("It never asserts real consciousness or real superintelligence.")
                continue
            if raw.lower() == "status":
                print(json.dumps(self.status(), indent=2))
                continue
            command, _, payload = raw.partition(" ")
            try:
                if command == "observe":
                    print(json.dumps(self.observe(payload), indent=2))
                elif command == "remember":
                    print(json.dumps(self.remember(payload), indent=2))
                elif command == "recall":
                    print(json.dumps(self.recall(payload), indent=2))
                elif command == "plan":
                    print(json.dumps(self.plan(payload), indent=2))
                elif command == "simulate":
                    print(json.dumps(self.simulate(payload), indent=2))
                else:
                    print("Unknown command. Use help for options.")
            except SimulationBoundaryError as exc:
                print(f"bounded simulation error: {exc}")


def demo() -> dict[str, Any]:
    system = BoundedASCSystem()
    system.remember("This is a bounded attention system designed for explicit simulation, not human consciousness.", "semantic")
    observed = system.observe("The task is to classify cognitive capability accurately and honestly.", "user")
    plan = system.plan("AGI integration task")
    cycle = system.simulate("ASI planning task", "A broad reasoning workload is being reviewed in a closed sandbox.")
    result = {
        "observed": observed,
        "plan": plan,
        "cycle": cycle,
        "status": system.status(),
    }
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Explicitly bounded ASC/AC, AGI, and ASI simulation shell.")
    parser.add_argument("command", nargs="?", default="shell", help="status, demo, shell")
    parser.add_argument("--state", default=None, help="Optional JSON state file for persistence.")
    args = parser.parse_args()
    system = BoundedASCSystem(args.state)
    if args.command == "status":
        print(json.dumps(system.status(), indent=2))
    elif args.command == "demo":
        demo()
    else:
        system.interactive_loop()


if __name__ == "__main__":
    main()
