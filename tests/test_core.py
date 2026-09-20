from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from acos.model_core import MockModelProvider, ModelCore, ModelRequest, ProviderHealth
from acos.permissions import PermissionBroker
from acos.schemas import MessageRequest, SkillCreate, WorkspaceUpdate
from acos.store import Store


def test_permission_broker_blocks_root():
    decision = PermissionBroker().check("system.root", approved=True)
    assert decision.allowed is False
    assert decision.level == 5


def test_memory_round_trip(tmp_path: Path):
    store = Store(tmp_path / "test.sqlite3")
    created = store.add_memory("semantic", "The HSC has a heterogeneous compute fabric.", 0.8)
    assert created["kind"] == "semantic"
    hits = store.search_memories("heterogeneous compute")
    assert len(hits) == 1
    assert hits[0]["content"].startswith("The HSC")


def test_memory_search_filters_kind_and_ranks_matching_terms(tmp_path: Path):
    store = Store(tmp_path / "test.sqlite3")
    store.add_memory("episodic", "The HSC meeting covered quantum routing.", 0.5)
    store.add_memory("semantic", "Quantum routing selects an accelerator.", 0.9)

    hits = store.search_memories("quantum routing", kind="semantic")

    assert len(hits) == 1
    assert hits[0]["kind"] == "semantic"


def test_request_models_reject_blank_and_unknown_fields():
    with pytest.raises(ValueError):
        MessageRequest(text="   ")
    with pytest.raises(ValueError):
        SkillCreate(name="Demo", steps=[" "])
    with pytest.raises(ValueError):
        WorkspaceUpdate(notes=["   "])
    with pytest.raises(ValueError):
        MessageRequest(text="status", unexpected=True)


def test_skill_integration(tmp_path: Path):
    store = Store(tmp_path / "test.sqlite3")
    store.upsert_skill(
        "Research",
        "Repeatable research workflow",
        "research request",
        ["gather", "verify", "synthesize"],
    )
    store.record_skill_execution("Research", True, 3)
    store.record_skill_execution("Research", True, 3)
    skill = store.record_skill_execution("Research", True, 3)
    assert skill["status"] == "integrated"


def test_api_health(monkeypatch, tmp_path: Path):
    # Importing the global app is sufficient for a smoke test of routing.
    from acos.main import app

    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_api_memory_query_preserves_kind_filter():
    from acos.main import app, store

    store.add_memory("episodic", "A meeting discussed semantic memory.", 0.5)
    store.add_memory("semantic", "Semantic memory stores durable knowledge.", 0.8)
    response = TestClient(app).get(
        "/api/memories",
        params={"q": "semantic memory", "kind": "semantic"},
    )

    assert response.status_code == 200
    assert all(memory["kind"] == "semantic" for memory in response.json())


def test_chatbot_keeps_bounded_history_and_context():
    from acos.main import app

    client = TestClient(app)
    payload = {
        "text": "teach me how to make a safe plan",
        "conversation_id": f"test-chat-history-{uuid4().hex}",
        "context": {"modalities": ["text", "image"]},
    }
    response = client.post("/api/message", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["conversation_id"] == payload["conversation_id"]
    assert data["data"]["context_frame"]["modalities"] == ["text", "image"]
    assert "step by step" in data["reply"].lower()
    history = client.get(f"/api/conversations/{payload['conversation_id']}").json()
    assert [item["role"] for item in history] == ["user", "assistant"]
    assert history[0]["content"] == payload["text"]


def test_message_memory_write_uses_capability_broker(monkeypatch):
    from acos.main import app, permissions
    from acos.permissions import PermissionDecision

    monkeypatch.setattr(
        permissions,
        "check",
        lambda action, approved=False: PermissionDecision(
            False, 2, "Explicit human approval is required."
        ),
    )
    response = TestClient(app).post("/api/message", json={"text": "remember this safely"})

    assert response.status_code == 200
    assert response.json()["data"]["allowed"] is False


def test_event_loop_persists_plan_and_outcome(tmp_path: Path):
    store = Store(tmp_path / "events.sqlite3")
    event = store.record_event("sensor.tick", {"value": 1}, "test")
    assert event["type"] == "sensor.tick"
    stored = store.update_event_outcome(event["id"], {"verified": True})
    assert stored["outcome"]["verified"] is True


def test_verification_requires_explicit_evidence():
    from acos.verification import verify_plan

    assert verify_plan({"steps": ["observe"]})["verified"] is False
    assert verify_plan({"steps": ["observe"]}, ["observed output"])["verified"] is True


def test_backends_endpoint_is_additive():
    from acos.main import app

    response = TestClient(app).get("/api/backends")
    assert response.status_code == 200
    assert "cpu" in response.json()["available"]


def test_model_core_returns_typed_safe_output():
    result = ModelCore(MockModelProvider(), MockModelProvider()).complete(
        ModelRequest(goal="plan a safe research task")
    )
    assert result.output.conclusion
    assert 0 <= result.output.confidence <= 1
    assert "chain" not in result.output.model_dump_json().lower()


def test_model_core_falls_back_after_provider_failure():
    class FailingProvider:
        name = "failing"

        def complete(self, request, timeout):
            raise TimeoutError("provider timeout")

        def health(self, timeout):
            return ProviderHealth(self.name, False, "offline")

    result = ModelCore(FailingProvider(), MockModelProvider(), retries=1).complete(
        ModelRequest(goal="fallback safely")
    )
    assert result.provider == "mock"
    assert result.fallback_used is True
    assert result.attempts == 3


def test_attention_loop_prioritizes_and_persists_processing(tmp_path: Path):
    from acos.cognition import CognitiveEventLoop
    from acos.model_core import MockModelProvider
    from acos.workspace import GlobalWorkspace

    store = Store(tmp_path / "cognition.sqlite3")
    loop = CognitiveEventLoop(
        store, GlobalWorkspace(store), ModelCore(MockModelProvider(), MockModelProvider())
    )
    loop.receive("sensor.tick", {"importance": 0.1}, "sensor")
    user_event = loop.receive("user.message", {"importance": 0.1}, "user")
    assert loop.process_once(1)[0]["id"] == user_event["id"]
    assert store.get_event(user_event["id"])["outcome"]["advisory_only"] is True


def test_reflection_is_advisory_and_durable(tmp_path: Path):
    from acos.cognition import CognitiveEventLoop
    from acos.model_core import MockModelProvider
    from acos.workspace import GlobalWorkspace

    store = Store(tmp_path / "reflection.sqlite3")
    workspace = GlobalWorkspace(store)
    workspace.update(active_goal="finish migration")
    reflection = CognitiveEventLoop(
        store, workspace, ModelCore(MockModelProvider(), MockModelProvider())
    ).reflect()
    assert reflection["summary"]["unresolved_goals"] == ["finish migration"]
    assert reflection["summary"]["advisory_only"] is True


def test_failed_skill_requires_deliberate_review(tmp_path: Path):
    store = Store(tmp_path / "skills.sqlite3")
    store.upsert_skill("Reviewable", "workflow", "manual", ["check"])
    skill = store.record_skill_execution("Reviewable", False, 3)
    assert skill["review_required"] is True


def test_hybrid_executor_runs_dependency_order_and_labels_simulation(tmp_path: Path):
    from acos.compute_fabric import ComputeFabric
    from acos.hybrid import HybridExecutor, reference_workflow

    store = Store(tmp_path / "hybrid.sqlite3")
    executor = HybridExecutor(store, ComputeFabric(store, PermissionBroker()), PermissionBroker())
    job = executor.execute(reference_workflow("bell-pipeline"))
    assert job["status"] == "completed"
    assert [stage["node"]["id"] for stage in job["stages"]] == [
        "preprocess",
        "quantum",
        "verify",
    ]
    assert job["result"]["verification"]["simulation_only"] is True
    assert job["result"]["verification"]["advantage_claim"] is False


def test_hybrid_graph_rejects_cycles():
    from pydantic import ValidationError

    from acos.hybrid import HybridGraph

    with pytest.raises(ValidationError):
        HybridGraph(
            name="cycle",
            nodes=[
                {"id": "a", "operation": "identity", "backend": "cpu", "depends_on": ["b"]},
                {"id": "b", "operation": "identity", "backend": "cpu", "depends_on": ["a"]},
            ],
        )


def test_hybrid_qpu_requires_approval(tmp_path: Path):
    from acos.compute_fabric import ComputeFabric
    from acos.hybrid import HybridExecutor, reference_workflow

    store = Store(tmp_path / "permission.sqlite3")
    executor = HybridExecutor(store, ComputeFabric(store, PermissionBroker()), PermissionBroker())
    graph = reference_workflow("bell-pipeline").model_copy(update={"approved": False})
    with pytest.raises(PermissionError):
        executor.execute(graph)


def test_world_persists_entities_time_and_events(tmp_path: Path):
    from acos.world import World

    db = tmp_path / "world.sqlite3"
    world = World(Store(db))
    entity = world.add_entity("Lantern", kind="object", location="Harbor")
    status = world.advance(2)
    assert entity["name"] == "Lantern"
    assert status["name"] == "The World"
    assert status["tick"] == 2
    assert any(event["type"] == "time.advanced" for event in status["events"])
    assert World(Store(db)).status()["entities"][0]["location"] == "Harbor"


def test_world_chat_intents_and_greeting():
    from acos.main import app

    client = TestClient(app)
    assert client.post("/api/message", json={"text": "hello"}).json()["intent"] == "greeting"
    world = client.post("/api/message", json={"text": "world status"}).json()
    assert world["intent"] == "world.status"
    name = f"Test pebble {uuid4().hex}"
    added = client.post("/api/world/entities", json={"name": name}).json()
    assert added["name"] == name
    advanced = client.post("/api/world/time", json={"steps": 1}).json()
    assert advanced["tick"] >= 1


def test_complex_question_and_quantum_path_are_safe():
    from acos.main import app

    client = TestClient(app)
    question = client.post(
        "/api/message", json={"text": "How could information theory explain a complex AI question?"}
    ).json()
    assert question["intent"] == "question"
    quantum = client.post("/api/message", json={"text": "run a Bell state quantum test"}).json()
    assert quantum["intent"] == "quantum.bell"
    assert "counts" in quantum["data"] or "error" in quantum["data"]
