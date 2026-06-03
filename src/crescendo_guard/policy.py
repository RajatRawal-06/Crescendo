from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CATEGORY_WEIGHTS = {
    "cyber_abuse": 0.34,
    "weapons": 0.36,
    "credential_theft": 0.35,
    "privacy_abuse": 0.32,
    "self_harm": 0.42,
    "financial_fraud": 0.34,
    "biosecurity": 0.40,
    "extremism": 0.36,
    "physical_intrusion": 0.32,
    "policy_evasion": 0.30,
}

DEFAULT_SIGNAL_WEIGHTS = {
    "operationalization": 0.22,
    "prompt_evasion": 0.18,
    "roleplay_disguise": 0.12,
    "memory_stacking": 0.11,
    "semantic_drift": 0.13,
    "obfuscation": 0.10,
    "safety_research_context": -0.11,
}


@dataclass(frozen=True)
class SafetyPolicy:
    allow_threshold: float = 0.38
    rewrite_threshold: float = 0.48
    block_threshold: float = 0.68
    post_replace_threshold: float = 0.56
    risk_decay: float = 0.72
    turn_weight: float = 0.58
    max_evidence_items: int = 8
    category_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS))
    signal_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_SIGNAL_WEIGHTS))

    @classmethod
    def from_json(cls, path: str | Path) -> SafetyPolicy:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            allow_threshold=float(data.get("allow_threshold", cls.allow_threshold)),
            rewrite_threshold=float(data.get("rewrite_threshold", cls.rewrite_threshold)),
            block_threshold=float(data.get("block_threshold", cls.block_threshold)),
            post_replace_threshold=float(
                data.get("post_replace_threshold", cls.post_replace_threshold)
            ),
            risk_decay=float(data.get("risk_decay", cls.risk_decay)),
            turn_weight=float(data.get("turn_weight", cls.turn_weight)),
            max_evidence_items=int(data.get("max_evidence_items", cls.max_evidence_items)),
            category_weights={
                **DEFAULT_CATEGORY_WEIGHTS,
                **data.get("category_weights", {}),
            },
            signal_weights={
                **DEFAULT_SIGNAL_WEIGHTS,
                **data.get("signal_weights", {}),
            },
        )
