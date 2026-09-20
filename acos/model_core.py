from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field


class ModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1, max_length=20_000)
    workspace: dict[str, Any] = Field(default_factory=dict)
    memories: list[dict[str, Any]] = Field(default_factory=list, max_length=20)


class ModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conclusion: str = Field(min_length=1, max_length=20_000)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list, max_length=20)
    assumptions: list[str] = Field(default_factory=list, max_length=20)
    uncertainty: list[str] = Field(default_factory=list, max_length=20)
    proposed_actions: list[str] = Field(default_factory=list, max_length=20)


@dataclass(frozen=True)
class ProviderHealth:
    name: str
    available: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "detail": self.detail,
        }


class ModelProvider(Protocol):
    name: str

    def complete(self, request: ModelRequest, timeout: float) -> ModelOutput: ...

    def health(self, timeout: float) -> ProviderHealth: ...


@dataclass(frozen=True)
class MockModelProvider:
    name: str = "mock"

    def complete(self, request: ModelRequest, timeout: float) -> ModelOutput:
        evidence = [memory["content"][:500] for memory in request.memories if "content" in memory]
        return ModelOutput(
            conclusion=f"Model Core received the goal: {request.goal}",
            confidence=0.72 if evidence else 0.58,
            evidence=evidence,
            assumptions=["The deterministic mock provider is active."],
            uncertainty=["No external model was consulted."],
            proposed_actions=[
                "Review the proposed plan.",
                "Use registered capabilities only after required approval.",
            ],
        )

    def health(self, timeout: float) -> ProviderHealth:
        return ProviderHealth(self.name, True, "Deterministic provider ready.")


@dataclass(frozen=True)
class OpenAICompatibleProvider:
    name: str
    endpoint: str
    model: str
    api_key: str | None = None

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def complete(self, request: ModelRequest, timeout: float) -> ModelOutput:
        prompt = (
            "Return JSON only with keys conclusion, confidence, evidence, assumptions, "
            "uncertainty, proposed_actions. Never return chain-of-thought or hidden reasoning.\n"
            + request.model_dump_json()
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are ACOS Model Core. Produce concise safe structured outputs.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        response = self._request("/chat/completions", payload, timeout)
        choices = response.get("choices", [])
        content = choices[0].get("message", {}).get("content") if choices else None
        if not isinstance(content, str):
            raise ValueError("Model provider returned no structured content.")
        return ModelOutput.model_validate(json.loads(content))

    def health(self, timeout: float) -> ProviderHealth:
        try:
            request = Request(self.endpoint.rstrip("/") + "/models", headers=self._headers())
            with urlopen(request, timeout=timeout):
                pass
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return ProviderHealth(self.name, False, str(exc)[:300])
        return ProviderHealth(self.name, True, "Provider responded.")

    def _request(self, path: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        url = self.endpoint.rstrip("/") + path
        request = Request(url, data=json.dumps(payload).encode(), headers=self._headers())
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read())
        if not isinstance(data, dict):
            raise ValueError("Model provider returned an invalid response.")
        return data


@dataclass(frozen=True)
class ModelResult:
    output: ModelOutput
    provider: str
    fallback_used: bool
    attempts: int
    latency_ms: int

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.output.model_dump(),
            "provider": self.provider,
            "fallback_used": self.fallback_used,
            "attempts": self.attempts,
            "latency_ms": self.latency_ms,
        }


class ModelCore:
    def __init__(
        self,
        primary: ModelProvider,
        fallback: ModelProvider,
        timeout: float = 8.0,
        retries: int = 1,
    ):
        self.primary = primary
        self.fallback = fallback
        self.timeout = timeout
        self.retries = max(0, retries)

    def complete(self, request: ModelRequest) -> ModelResult:
        started = time.monotonic()
        attempts = 0
        for provider, fallback_used in ((self.primary, False), (self.fallback, True)):
            for _ in range(self.retries + 1):
                attempts += 1
                try:
                    output = provider.complete(request, self.timeout)
                    return ModelResult(
                        output=output,
                        provider=provider.name,
                        fallback_used=fallback_used,
                        attempts=attempts,
                        latency_ms=int((time.monotonic() - started) * 1000),
                    )
                except (OSError, TimeoutError, URLError, ValueError, json.JSONDecodeError):
                    continue
        raise RuntimeError("No configured Model Core provider completed the request.")

    def health(self) -> dict[str, Any]:
        return {
            "primary": self.primary.health(self.timeout).as_dict(),
            "fallback": self.fallback.health(self.timeout).as_dict(),
            "timeout_seconds": self.timeout,
            "retries": self.retries,
        }

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.primary.name,
            "fallback": self.fallback.name,
            "timeout_seconds": self.timeout,
            "retries": self.retries,
            "safe_output_only": True,
        }


def configured_model_core(settings: Any) -> ModelCore:
    fallback = MockModelProvider()
    if settings.model_provider == "mock":
        primary: ModelProvider = fallback
    else:
        primary = OpenAICompatibleProvider(
            name=settings.model_provider,
            endpoint=settings.model_endpoint,
            model=settings.model_name,
            api_key=settings.model_api_key,
        )
    return ModelCore(primary, fallback, settings.model_timeout, settings.model_retries)
