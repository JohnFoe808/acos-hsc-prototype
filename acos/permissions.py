from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    level: int
    reason: str


class PermissionBroker:
    """Capability broker: capability is not authority.

    Levels:
      0 observe/read-only
      1 routine safe action
      2 modification: explicit approval required
      3 sensitive: explicit approval required
      4 critical: deliberately unsupported in this prototype
      5 forbidden
    """

    ACTION_LEVELS = {
        "system.status": 0,
        "memory.read": 0,
        "memory.write": 1,
        "filesystem.list": 1,
        "quantum.bell": 1,
        "skill.create": 1,
        "skill.execute": 1,
        "compute.consequential": 2,
        "compute.local": 1,
        "filesystem.write": 2,
        "filesystem.delete": 3,
        "system.root": 5,
        "shell.arbitrary": 5,
        "self.modify.unreviewed": 5,
    }

    def check(self, action: str, approved: bool = False) -> PermissionDecision:
        level = self.ACTION_LEVELS.get(action, 5)
        if level >= 4:
            return PermissionDecision(False, level, "Action is disabled by prototype policy.")
        if level >= 2 and not approved:
            return PermissionDecision(False, level, "Explicit human approval is required.")
        return PermissionDecision(True, level, "Allowed by capability policy.")

    def deautomatize(self, action: str) -> PermissionDecision:
        """Force a human gate for actions that could otherwise be routine."""
        level = self.ACTION_LEVELS.get(action, 5)
        if level >= 4:
            return PermissionDecision(False, level, "Action is disabled by prototype policy.")
        return PermissionDecision(
            False, max(level, 2), "Deautomatization requires explicit approval."
        )
