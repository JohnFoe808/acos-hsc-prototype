from __future__ import annotations

import json

from asc_simulator import BoundedASCSystem


def test_status_is_explicitly_bounded():
    system = BoundedASCSystem()
    status = system.status()
    assert status["claims"]["real_consciousness"] is False
    assert status["claims"]["real_agi"] is False
    assert status["claims"]["real_asi"] is False
    assert status["claims"]["simulation_only"] is True


def test_plan_and_cycle_mark_simulation_only():
    system = BoundedASCSystem()
    plan = system.plan("AGI orchestration workload")
    cycle = system.simulate(
        "ASI sandbox scenario",
        "The system reviews a high-complexity limited task.",
    )
    assert plan["simulation_only"] is True
    assert cycle["claims"]["simulation_only"] is True
    assert cycle["profile"]["level"] in {
        "AGI-like bounded simulation",
        "ASI-like bounded simulation",
    }


def test_recall_is_ranked_and_deterministic():
    system = BoundedASCSystem()
    system.remember("Attention is bounded to explicit state and audit trace.", "semantic")
    system.remember("This is a simulation, not real consciousness.", "episodic")
    matches = system.recall("simulation consciousness")
    assert matches
    assert matches[0]["text"].lower().find("simulation") >= 0


def test_cli_smoke_demo(tmp_path):
    state = tmp_path / "state.json"
    system = BoundedASCSystem(state)
    result = system.plan("bounded AGI simulation")
    assert result["claims"]["real_agi"] is False
    assert result["note"].startswith("This is a bounded simulation")
    payload = json.loads(state.read_text(encoding="utf-8"))
    assert payload["workspace"]["goal"] == "bounded AGI simulation"
