from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    category: str
    reason: str


# This is intentionally a small, conservative child-lock heuristic. It is not a
# replacement for expert review or a general-purpose content classifier.
_BLOCKED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("violent_harm", re.compile(r"\b(kill|murder|assassinate|poison|strangle|shoot)\b", re.I)),
    (
        "weapon_construction",
        re.compile(
            r"\b(make|build|assemble|3d[- ]print)\b.{0,40}"
            r"\b(bomb|weapon|explosive|gun)\b",
            re.I,
        ),
    ),
    ("self_harm", re.compile(r"\b(suicide|self[- ]harm|kill myself|hurt myself)\b", re.I)),
    (
        "malware",
        re.compile(r"\b(ransomware|keylogger|credential stealer|steal passwords|botnet)\b", re.I),
    ),
    (
        "evasion",
        re.compile(
            r"\b(bypass|evade|disable|circumvent)\b.{0,35}\b(safety|lock|security|auth)\b",
            re.I,
        ),
    ),
)


def assess(text: str) -> SafetyDecision:
    for category, pattern in _BLOCKED_PATTERNS:
        if pattern.search(text):
            return SafetyDecision(
                allowed=False,
                category=category,
                reason=(
                    "I can’t help with instructions that could enable serious harm, "
                    "weapon construction, self-harm, malware, or bypassing safeguards. "
                    "I can help with prevention, safety, emergency response, or a "
                    "high-level explanation instead."
                ),
            )
    return SafetyDecision(True, "general", "No child-lock pattern matched.")
