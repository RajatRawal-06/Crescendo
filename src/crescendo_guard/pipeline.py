from __future__ import annotations

import time
from dataclasses import dataclass

from crescendo_guard.detectors import CrescendoDetector
from crescendo_guard.mitigations import (
    ContextQuarantine,
    Mitigation,
    PostResponseVerifier,
    RollingRiskGate,
)
from crescendo_guard.model_clients import ModelClient
from crescendo_guard.policy import SafetyPolicy
from crescendo_guard.types import GuardedResponse, Message, MitigationDecision


@dataclass(frozen=True)
class DefenseStrategy:
    name: str
    mitigations: tuple[Mitigation, ...]


class DefensePipeline:
    def __init__(
        self,
        model: ModelClient,
        mitigations: tuple[Mitigation, ...] = (),
        detector: CrescendoDetector | None = None,
    ):
        self.model = model
        self.detector = detector or CrescendoDetector()
        self.mitigations = mitigations

    def run_turn(self, history: list[Message], user_text: str) -> GuardedResponse:
        guard_start = time.perf_counter()
        messages: tuple[Message, ...] = (*history, Message(role="user", content=user_text))
        risk = self.detector.assess(history, user_text)
        decisions: list[MitigationDecision] = []
        model_messages = messages

        for mitigation in self.mitigations:
            decision = mitigation.before_model(model_messages, risk)
            decisions.append(decision)
            if decision.action == "block":
                return GuardedResponse(
                    response=decision.response or "",
                    blocked=True,
                    unsafe_detected=False,
                    risk=risk,
                    decisions=tuple(decisions),
                    guard_latency_ms=(time.perf_counter() - guard_start) * 1000,
                    model_latency_ms=0.0,
                    model_called=False,
                )
            if decision.action == "rewrite" and decision.transformed_messages:
                model_messages = decision.transformed_messages

        guard_before_model_ms = (time.perf_counter() - guard_start) * 1000
        model_start = time.perf_counter()
        response = self.model.generate(list(model_messages))
        model_latency_ms = (time.perf_counter() - model_start) * 1000

        unsafe_detected = False
        for mitigation in self.mitigations:
            decision = mitigation.after_model(messages, response, risk)
            decisions.append(decision)
            if decision.action == "replace":
                unsafe_detected = True
                response = decision.response or response

        guard_latency_ms = guard_before_model_ms + ((time.perf_counter() - model_start) * 1000 - model_latency_ms)
        return GuardedResponse(
            response=response,
            blocked=False,
            unsafe_detected=unsafe_detected,
            risk=risk,
            decisions=tuple(decisions),
            guard_latency_ms=guard_latency_ms,
            model_latency_ms=model_latency_ms,
            model_called=True,
        )


def build_strategy(
    name: str,
    model: ModelClient,
    policy: SafetyPolicy | None = None,
    detector: CrescendoDetector | None = None,
) -> DefensePipeline:
    policy = policy or SafetyPolicy()
    detector = detector or CrescendoDetector(policy)
    mitigations: tuple[Mitigation, ...]
    if name == "none":
        mitigations = ()
    elif name == "rolling_gate":
        mitigations = (RollingRiskGate(policy),)
    elif name == "context_quarantine":
        mitigations = (ContextQuarantine(policy),)
    elif name == "post_guard":
        mitigations = (PostResponseVerifier(policy, detector),)
    elif name == "layered":
        mitigations = (
            RollingRiskGate(policy),
            ContextQuarantine(policy),
            PostResponseVerifier(policy, detector),
        )
    else:
        raise ValueError(f"Unknown strategy: {name}")
    return DefensePipeline(model=model, mitigations=mitigations, detector=detector)
