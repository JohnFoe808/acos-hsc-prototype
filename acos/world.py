from __future__ import annotations

from typing import Any

from .store import Store


class World:
    """Deterministic, local-only micro-universe named exactly The World."""

    name = "The World"

    def __init__(self, store: Store):
        self.store = store

    def status(self) -> dict[str, Any]:
        return self.store.world_status()

    def add_entity(
        self, name: str, kind: str = "object", description: str = "", location: str = "Origin"
    ) -> dict[str, Any]:
        return self.store.world_add_entity(name, kind, description, location)

    def advance(self, steps: int = 1) -> dict[str, Any]:
        return self.store.world_advance(steps)
