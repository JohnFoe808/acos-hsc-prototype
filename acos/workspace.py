from __future__ import annotations

from typing import Any

from .store import Store

DEFAULT_WORKSPACE = {
    "active_goal": None,
    "attention": "Awaiting user goal",
    "notes": [],
    "self_model": {
        "name": "ACOS Prototype",
        "version": "0.1.0",
        "identity_claim": (
            "cognitive operating-layer prototype; not a claim of phenomenal consciousness"
        ),
        "limitations": [
            "No unrestricted root access",
            "No arbitrary shell execution",
            "No unreviewed self-modification",
            "Quantum backend is optional and simulated by default",
        ],
    },
}


class GlobalWorkspace:
    def __init__(self, store: Store):
        self.store = store
        if self.store.get_state("workspace") is None:
            self.store.set_state("workspace", DEFAULT_WORKSPACE)

    def get(self) -> dict[str, Any]:
        return self.store.get_state("workspace", DEFAULT_WORKSPACE)

    def update(self, **changes: Any) -> dict[str, Any]:
        state = self.get()
        for key, value in changes.items():
            if value is not None:
                state[key] = value
        self.store.set_state("workspace", state)
        return state
