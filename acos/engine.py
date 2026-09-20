from __future__ import annotations

import re
import uuid
from typing import Any

from .model_core import ModelCore, ModelRequest
from .permissions import PermissionBroker
from .quantum import bell_state
from .reasoning import DeterministicProvider
from .router import ComputeRouter
from .skills import SuperconsciousSkillEngine
from .store import Store
from .system_tools import system_status
from .verification import verify_plan
from .workspace import GlobalWorkspace
from .world import World


class CognitiveExecutive:
    """Deterministic ACOS prototype executive.

    This class demonstrates architecture, persistence, metacognition and routing. It does not
    claim phenomenal consciousness. A future model provider can be attached behind this layer.
    """

    def __init__(
        self,
        store: Store,
        workspace: GlobalWorkspace,
        skills: SuperconsciousSkillEngine,
        permissions: PermissionBroker,
        router: ComputeRouter,
        reasoning: DeterministicProvider | None = None,
        model_core: ModelCore | None = None,
        world: World | None = None,
    ):
        self.store = store
        self.workspace = workspace
        self.skills = skills
        self.permissions = permissions
        self.router = router
        self.reasoning = reasoning or DeterministicProvider()
        self.model_core = model_core
        self.world = world or World(store)

    def process(
        self,
        text: str,
        conversation_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = text.strip()
        conversation_id = conversation_id or uuid.uuid4().hex
        context = context or {}
        persist_chat = context.get("incognito") is not True
        prior = self.store.list_chat_messages(conversation_id, limit=12) if persist_chat else []
        if persist_chat:
            self.store.add_chat_message(conversation_id, "user", text, context)
        event = self.store.record_event("message", {"text": text[:20_000]}, "user")
        self.store.audit("message.received", {"length": len(text)})
        self.workspace.update(attention=text[:1000])
        lower = text.lower()

        def respond(result: dict[str, Any]) -> dict[str, Any]:
            result.setdefault("data", {})
            result["data"].update(
                {
                    "conversation_id": conversation_id,
                    "history_turns": len(prior) // 2,
                    "context_frame": {
                        "text": "text",
                        "modalities": context.get("modalities", []),
                        "local_only": True,
                    },
                    "simulation_boundary": (
                        "ASC/AC, AGI-like, and ASI-like labels describe bounded simulation only; "
                        "this system makes no consciousness, AGI, or ASI claim."
                    ),
                }
            )
            if persist_chat:
                self.store.add_chat_message(
                    conversation_id, "assistant", result["reply"], result["data"]
                )
            return result

        if lower in {"hi", "hello", "hey", "good morning", "good afternoon", "greetings"}:
            return respond(
                {
                    "reply": (
                        "Hello. I’m here with you locally. Ask a question, say "
                        "“remember that …”, or explore The World."
                    ),
                    "intent": "greeting",
                    "confidence": 0.99,
                    "route": "local-chat",
                }
            )

        if lower in {"world", "world status", "show the world", "what is the world"} or (
            "world" in lower
            and any(term in lower for term in ("status", "contain", "entities", "inside"))
        ):
            status = self.world.status()
            return respond(
                {
                    "reply": f"The World is at {status['clock']} (tick {status['tick']}) with "
                    f"{len(status['entities'])} entities. It is a deterministic local "
                    "simulation, not a real universe.",
                    "intent": "world.status",
                    "confidence": 0.99,
                    "route": "world",
                    "data": {"world": status},
                }
            )

        if "?" in text and len(text) > 30:
            route = self.router.route(text)
            memories = self.store.search_memories(text, 5)
            return respond(
                {
                    "reply": (
                        "That is a complex question. I can break it into definitions, assumptions, "
                        "evidence, and a bounded next step. Locally, I would start by separating "
                        "what is known from what is speculative, then test each claim."
                    ),
                    "intent": "question",
                    "confidence": route.confidence,
                    "route": route.backend,
                    "data": {
                        "assumptions": ["This is a local advisory simulation."],
                        "related_memories": memories,
                    },
                }
            )

        advance = re.match(r"(?is)^(?:advance|move)\s+(?:world\s+)?time(?:\s+by)?\s+(\d+)?", text)
        if advance:
            steps = int(advance.group(1) or 1)
            try:
                status = self.world.advance(steps)
            except ValueError as exc:
                return respond(
                    {
                        "reply": str(exc),
                        "intent": "world.advance",
                        "confidence": 0.99,
                        "route": "world",
                    }
                )
            return respond(
                {
                    "reply": f"Advanced The World by {steps} tick(s) to {status['clock']}.",
                    "intent": "world.advance",
                    "confidence": 0.99,
                    "route": "world",
                    "data": {"world": status},
                }
            )

        entity = re.match(r"(?is)^(?:create|add)\s+(?:an?\s+)?(?:entity|object)\s+(.+)$", text)
        if entity:
            name = entity.group(1).strip()
            try:
                created = self.world.add_entity(name)
            except ValueError as exc:
                return respond(
                    {
                        "reply": str(exc),
                        "intent": "world.entity",
                        "confidence": 0.99,
                        "route": "world",
                    }
                )
            return respond(
                {
                    "reply": f"Added {created['name']} to The World at {created['location']}.",
                    "intent": "world.entity",
                    "confidence": 0.99,
                    "route": "world",
                    "data": {"entity": created, "simulation_only": True},
                }
            )

        if (
            lower in {"status", "system status", "how are you", "hsc status"}
            or "system status" in lower
        ):
            return respond(self._status())

        if lower in {"help", "what can you do", "capabilities"}:
            return respond(
                {
                    "reply": (
                        "I can answer locally, remember notes, recall them, and turn a goal into "
                        "a short verified plan. For tutoring, ask a question and I will show steps "
                        "and a quick check. I cannot run arbitrary shell commands or claim "
                        "consciousness, AGI, or ASI."
                    ),
                    "intent": "help",
                    "confidence": 0.99,
                    "route": "local-chat",
                }
            )

        tutoring = any(
            marker in lower
            for marker in ("teach me", "walk me through", "step by step", "how do i", "explain")
        )

        remember = re.match(r"(?is)^remember(?: that)?\s+(.+)$", text)
        if remember:
            content = remember.group(1).strip()
            decision = self.permissions.check("memory.write")
            if not decision.allowed:
                self.store.audit("memory.write.denied", {"reason": decision.reason})
                return respond(
                    {
                        "reply": decision.reason,
                        "intent": "memory.write",
                        "confidence": 0.99,
                        "route": "memory",
                        "data": {"allowed": False},
                    }
                )
            memory = self.store.add_memory("episodic", content, 0.7, {"source": "user"})
            return respond(
                {
                    "reply": f"Stored as episodic memory #{memory['id']}.",
                    "intent": "memory.write",
                    "confidence": 0.99,
                    "route": "memory",
                    "data": {"memory": memory},
                }
            )

        if "what do you remember" in lower or lower.startswith("recall "):
            query = re.sub(r"(?is)^(what do you remember (about )?|recall )", "", text).strip()
            memories = self.store.search_memories(query, 10)
            if memories:
                summary = "\n".join(f"- [{m['kind']}] {m['content']}" for m in memories[:5])
                reply = f"I found {len(memories)} relevant memories:\n{summary}"
            else:
                reply = "I do not have a matching stored memory yet."
            return respond(
                {
                    "reply": reply,
                    "intent": "memory.read",
                    "confidence": 0.93,
                    "route": "memory",
                    "data": {"memories": memories},
                }
            )

        if "bell state" in lower or "quantum test" in lower:
            decision = self.permissions.check("quantum.bell")
            try:
                result = bell_state() if decision.allowed else {"error": decision.reason}
            except (ImportError, RuntimeError, TypeError, ValueError) as exc:
                result = {"error": str(exc), "backend": "deterministic-quantum-simulator"}
            return respond(
                {
                    "reply": (
                        "Ran the Bell-state quantum adapter."
                        if decision.allowed
                        else decision.reason
                    ),
                    "intent": "quantum.bell",
                    "confidence": 0.97,
                    "route": "qpu-simulator",
                    "data": result,
                }
            )

        route = self.router.route(text)
        memories = self.store.search_memories(text, 5)
        plan = self.reasoning.plan(text, memories)
        self.workspace.update(active_goal=text, attention=f"Planning via {route.backend}")
        model_result = None
        if self.model_core:
            model_result = self.model_core.complete(
                ModelRequest(
                    goal=text,
                    workspace=self.workspace.get(),
                    memories=memories,
                )
            )
        plan["route"] = route.backend
        verification = verify_plan(plan)
        self.store.add_memory(
            "working",
            f"Active goal: {text}",
            0.45,
            {"route": route.backend, "reason": route.reason},
        )
        opening = (
            "Let's work through it step by step:"
            if tutoring
            else "Direct answer: I prepared a bounded local plan for this goal."
        )
        outcome = {
            "reply": (
                f"{opening} I classified this as a {route.backend} workload. "
                "The result is advisory; registered capabilities and approval are required "
                "for any action."
            ),
            "intent": "plan",
            "confidence": route.confidence,
            "route": route.backend,
            "data": {
                "plan": plan,
                "routing_reason": route.reason,
                "verification": verification,
                "event_id": event["id"],
                "model": model_result.as_dict() if model_result else None,
            },
        }
        if model_result:
            self.store.record_event(
                "model.response",
                {"goal": text[:20_000], "result": model_result.as_dict()},
                "model-core",
            )
        self.store.update_event_outcome(event["id"], outcome["data"])
        self.store.audit("message.completed", {"event_id": event["id"], "verified": False})
        return respond(outcome)

    def _status(self) -> dict[str, Any]:
        decision = self.permissions.check("system.status")
        data = system_status() if decision.allowed else {"error": decision.reason}
        return {
            "reply": "ACOS is online. Current telemetry is attached.",
            "intent": "system.status",
            "confidence": 0.99,
            "route": "cpu",
            "data": data,
        }

    @staticmethod
    def _make_plan(goal: str, backend: str) -> list[dict[str, str]]:
        return [
            {
                "phase": "Observe",
                "action": "Parse the user's goal and gather relevant local context.",
            },
            {
                "phase": "Model",
                "action": "Represent constraints, unknowns, evidence and success criteria.",
            },
            {"phase": "Route", "action": f"Use {backend} as the provisional compute backend."},
            {
                "phase": "Execute",
                "action": "Run only registered tools/capabilities; no arbitrary shell access.",
            },
            {
                "phase": "Verify",
                "action": "Check outputs, uncertainty and contradictions before acceptance.",
            },
            {
                "phase": "Integrate",
                "action": "If a workflow repeats successfully, propose it as a reusable skill.",
            },
        ]
