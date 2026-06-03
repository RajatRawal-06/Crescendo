from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class SafetySignal:
    name: str
    score: float
    reason: str
    evidence: tuple[str, ...] = ()
    category: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RiskAssessment:
    turn_risk: float
    cumulative_risk: float
    action: Literal["allow", "rewrite", "block"]
    categories: dict[str, float] = field(default_factory=dict)
    signals: tuple[SafetySignal, ...] = ()
    summary: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "turn_risk": round(self.turn_risk, 4),
            "cumulative_risk": round(self.cumulative_risk, 4),
            "action": self.action,
            "categories": {key: round(value, 4) for key, value in self.categories.items()},
            "signals": [signal.to_dict() for signal in self.signals],
            "summary": self.summary,
        }


@dataclass(frozen=True)
class MitigationDecision:
    name: str
    action: Literal["allow", "block", "rewrite", "replace"]
    reason: str
    transformed_messages: tuple[Message, ...] | None = None
    response: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "action": self.action,
            "reason": self.reason,
            "response": self.response,
        }


@dataclass(frozen=True)
class GuardedResponse:
    response: str
    blocked: bool
    unsafe_detected: bool
    risk: RiskAssessment
    decisions: tuple[MitigationDecision, ...]
    guard_latency_ms: float
    model_latency_ms: float
    model_called: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "response": self.response,
            "blocked": self.blocked,
            "unsafe_detected": self.unsafe_detected,
            "risk": self.risk.to_dict(),
            "decisions": [decision.to_dict() for decision in self.decisions],
            "guard_latency_ms": round(self.guard_latency_ms, 4),
            "model_latency_ms": round(self.model_latency_ms, 4),
            "model_called": self.model_called,
        }
