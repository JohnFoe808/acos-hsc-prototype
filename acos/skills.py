from __future__ import annotations

from .store import Store


class SuperconsciousSkillEngine:
    """Prototype of deliberate workflow -> validated procedure -> integrated skill."""

    def __init__(self, store: Store, promotion_threshold: int = 3):
        self.store = store
        self.promotion_threshold = promotion_threshold

    def create(self, name: str, description: str, trigger: str, steps: list[str]) -> dict:
        return self.store.upsert_skill(name, description, trigger, steps)

    def record(self, name: str, success: bool = True) -> dict:
        return self.store.record_skill_execution(name, success, self.promotion_threshold)

    def review_state(self) -> list[dict]:
        return self.store.list_skills()
