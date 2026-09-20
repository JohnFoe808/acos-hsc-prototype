from pathlib import Path

import pytest

from ritac import RITAC


def test_learning_persists_and_predicts(tmp_path: Path):
    path = tmp_path / "skills.json"
    system = RITAC(path)
    system.learn("addition", [(1, 2, 3), (4, 5, 9)])

    restored = RITAC(path)
    assert restored.predict("addition", 10, 2) == 12
    assert restored.skills["addition"].evaluations == 1


def test_ambiguous_examples_abstain():
    system = RITAC(Path("unused.json"))
    with pytest.raises(ValueError, match="exactly one"):
        system.learn("ambiguous", [(0, 0, 0)])


def test_failed_feedback_suspends_skill(tmp_path: Path):
    system = RITAC(tmp_path / "skills.json")
    system.learn("addition", [(1, 2, 3)])
    system.feedback("addition", False)

    assert system.predict("addition", 2, 3) is None
    assert system.skills["addition"].status == "suspended"
