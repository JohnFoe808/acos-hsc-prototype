from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model_core import ModelCore, ModelRequest
from .store import Store
from .workspace import GlobalWorkspace


@dataclass(frozen=True)
class AttentionController:
    def priority(self, event_type: str, payload: dict[str, Any]) -> float:
        weights = {
            "user.message": 1.0,
            "sensor": 0.55,
            "model.response": 0.75,
            "compute.outcome": 0.85,
            "memory": 0.65,
        }
        return min(
            1.0,
            weights.get(event_type.split(".")[0], 0.5) + float(payload.get("importance", 0)),
        )


class CognitiveEventLoop:
    def __init__(self, store: Store, workspace: GlobalWorkspace, model: ModelCore):
        self.store = store
        self.workspace = workspace
        self.model = model
        self.attention = AttentionController()

    def receive(self, event_type: str, payload: dict[str, Any], source: str) -> dict[str, Any]:
        event = self.store.record_event(event_type, payload, source)
        self.store.enqueue_attention(event["id"], self.attention.priority(event_type, payload))
        return event

    def process_once(self, limit: int = 10) -> list[dict[str, Any]]:
        processed = []
        for event in self.store.next_attention(limit):
            self.workspace.update(
                attention=f"Processing {event['type']}",
                notes=[f"Last event: {event['type']}"],
            )
            self.store.update_event_outcome(
                event["id"],
                {"attended": True, "priority": event["priority"], "advisory_only": True},
            )
            self.store.mark_attention_processed(event["id"])
            processed.append(event)
        return processed

    def reflect(self) -> dict[str, Any]:
        workspace = self.workspace.get()
        unresolved = [workspace["active_goal"]] if workspace.get("active_goal") else []
        recent = self.store.list_events(20)
        contradictions = [
            event for event in recent if event["type"] in {"memory.conflict", "model.contradiction"}
        ]
        summary = {
            "unresolved_goals": unresolved,
            "contradictions": len(contradictions),
            "unfinished_events": len(self.store.next_attention(20)),
            "learning_opportunities": ["Review repeated successful workflows."] if recent else [],
            "advisory_only": True,
        }
        reflection = self.store.record_reflection(summary)
        self.store.record_event("reflection.completed", summary, "cognition")
        return reflection

    def model_assessment(self, goal: str) -> dict[str, Any]:
        result = self.model.complete(
            ModelRequest(
                goal=goal,
                workspace=self.workspace.get(),
                memories=self.store.search_memories(goal, 10),
            )
        )
        return result.as_dict()
