"""Small, deterministic Recursive Integration Theory of Artificial Consciousness demo.

This is an engineering demonstration of rule learning and consolidation.  It is
not a claim of consciousness, AGI, or subjective experience.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

Operation = Callable[[float, float], float]


def _safe_divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("division by zero")
    return a / b


OPERATIONS: dict[str, Operation] = {
    "add": lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
    "multiply": lambda a, b: a * b,
    "divide": _safe_divide,
}


@dataclass
class Skill:
    name: str
    operation: str
    evidence: list[dict[str, float]]
    status: str = "deliberative"
    successes: int = 0
    failures: int = 0
    review_required: bool = False
    evaluations: int = 0


@dataclass
class RITAC:
    path: Path = Path("ritac_skills.json")
    skills: dict[str, Skill] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.skills = {name: Skill(**value) for name, value in raw.items()}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {name: asdict(skill) for name, skill in self.skills.items()}
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def learn(self, name: str, examples: list[tuple[float, float, float]]) -> Skill:
        hypotheses: list[str] = []
        for operation_name, operation in OPERATIONS.items():
            try:
                if all(math.isclose(operation(a, b), result, rel_tol=1e-9, abs_tol=1e-9)
                       for a, b, result in examples):
                    hypotheses.append(operation_name)
            except ValueError:
                continue
        if len(hypotheses) != 1:
            raise ValueError("examples do not identify exactly one supported rule")
        skill = Skill(
            name=name,
            operation=hypotheses[0],
            evidence=[{"a": a, "b": b, "result": result} for a, b, result in examples],
        )
        self.skills[name] = skill
        self.save()
        return skill

    def predict(self, name: str, a: float, b: float) -> float | None:
        skill = self.skills[name]
        matches = []
        for operation_name, operation in OPERATIONS.items():
            try:
                value = operation(a, b)
            except ValueError:
                continue
            if operation_name == skill.operation:
                matches.append(value)
        skill.evaluations += 1
        if len(matches) != 1 or skill.review_required:
            return None
        return matches[0]

    def feedback(self, name: str, correct: bool) -> Skill:
        skill = self.skills[name]
        if correct:
            skill.successes += 1
        else:
            skill.failures += 1
            skill.review_required = True
            skill.status = "suspended"
        self.save()
        return skill

    def consolidate(self, name: str) -> Skill:
        skill = self.skills[name]
        if skill.review_required or skill.successes < 3:
            raise ValueError("skill needs three successful validations and no failed feedback")
        skill.status = "automatic"
        self.save()
        return skill


def demo() -> None:
    path = Path(".ritac-demo-skills.json")
    if path.exists():
        path.unlink()
    system = RITAC(path)
    skill = system.learn("addition", [(2, 3, 5), (10, 4, 14), (-2, 8, 6)])
    for _ in range(3):
        system.feedback(skill.name, True)
    system.consolidate(skill.name)
    answer = system.predict("addition", 41, 1)
    print("RITAC recursive learning demo")
    print(f"learned: {skill.name} = {skill.operation}")
    print(f"validated: {skill.successes} successful examples")
    print(f"consolidated: {system.skills['addition'].status}")
    print(f"prediction: 41 + 1 = {answer:g}")
    print("abstention: conflicting or suspended skills return None")
    path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["demo"])
    args = parser.parse_args()
    if args.command == "demo":
        demo()


if __name__ == "__main__":
    main()
