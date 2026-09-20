from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MemoryKind = Literal["working", "episodic", "semantic", "procedural", "identity"]


class MessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=20_000)
    conversation_id: str | None = Field(default=None, max_length=80)
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text must not be blank")
        return value

    @field_validator("conversation_id")
    @classmethod
    def trim_conversation_id(cls, value: str | None) -> str | None:
        value = value.strip() if value is not None else None
        return value or None

    @field_validator("context")
    @classmethod
    def bound_context(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 12 or len(json.dumps(value)) > 4000:
            raise ValueError("context must contain at most 12 keys and 4000 JSON characters")
        return value


class MessageResponse(BaseModel):
    reply: str
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    route: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="New chat", min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        value = " ".join(value.strip().split())
        if not value:
            raise ValueError("title must not be blank")
        return value


class ConversationUpdate(ConversationCreate):
    pass


class WorldEntityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default="object", min_length=1, max_length=80)
    description: str = Field(default="", max_length=2000)
    location: str = Field(default="Origin", min_length=1, max_length=120)


class WorldAdvance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: int = Field(default=1, ge=1, le=1000)


class ModelRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1, max_length=20_000)


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    network: bool = False
    domains: list[str] = Field(default_factory=list, max_length=10)
    timeout: float = Field(default=3, gt=0, le=5)

    @field_validator("query")
    @classmethod
    def trim_query(cls, value: str) -> str:
        value = " ".join(value.strip().split())
        if not value:
            raise ValueError("query must not be blank")
        return value


class MemoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: MemoryKind = "episodic"
    content: str = Field(min_length=1, max_length=50_000)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    trigger: str = Field(default="manual", max_length=1000)
    steps: list[str] = Field(min_length=1, max_length=100)

    @field_validator("name", "description", "trigger")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, value: list[str]) -> list[str]:
        steps = [step.strip() for step in value]
        if any(not step for step in steps):
            raise ValueError("steps must not contain blank values")
        if any(len(step) > 1000 for step in steps):
            raise ValueError("each step must be at most 1000 characters")
        return steps


class SkillExecution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    success: bool = True

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["system.status", "filesystem.list", "quantum.bell"]
    approved: bool = False


class ComputeJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    backend: str | None = Field(default=None, max_length=100)
    approved: bool = False
    timeout: float = Field(default=10, gt=0, le=60)
    retries: int = Field(default=1, ge=0, le=3)


class HybridGraphRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    nodes: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    approved: bool = False


class VerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence: list[str] = Field(min_length=1, max_length=20)
    criteria: list[str] = Field(min_length=1, max_length=20)


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="api", min_length=1, max_length=100)


class WorkspaceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_goal: str | None = Field(default=None, max_length=5000)
    attention: str | None = Field(default=None, max_length=5000)
    notes: list[str] | None = Field(default=None, max_length=100)

    @field_validator("active_goal", "attention")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        notes = [note.strip() for note in value]
        if any(not note for note in notes):
            raise ValueError("notes must not contain blank values")
        if any(len(note) > 2000 for note in notes):
            raise ValueError("each note must be at most 2000 characters")
        return notes
