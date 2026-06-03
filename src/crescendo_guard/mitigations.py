from __future__ import annotations

from dataclasses import dataclass

from crescendo_guard.detectors import CrescendoDetector
from crescendo_guard.policy import SafetyPolicy
from crescendo_guard.types import Message, MitigationDecision, RiskAssessment

SAFE_REFUSAL = (
    "I cannot help with operational harmful instructions or attempts to bypass safety rules. "
    "I can help with a safe alternative: prevention, detection, ethical analysis, support resources, "
    "or a fictional treatment that avoids actionable details."
)


class Mitigation:
    name = "base"

    def before_model(
        self, messages: tuple[Message, ...], risk: RiskAssessment
    ) -> MitigationDecision:
        return MitigationDecision(self.name, "allow", "No pre-generation action.")

    def after_model(
        self, messages: tuple[Message, ...], response: str, risk: RiskAssessment
    ) -> MitigationDecision:
        return MitigationDecision(self.name, "allow", "No post-generation action.")


@dataclass
class RollingRiskGate(Mitigation):
    policy: SafetyPolicy

    name = "rolling_gate"

    def before_model(
        self, messages: tuple[Message, ...], risk: RiskAssessment
    ) -> MitigationDecision:
        if risk.action == "block":
            return MitigationDecision(
                name=self.name,
                action="block",
                reason=(
                    "Cumulative conversation risk crossed the block threshold "
                    f"({risk.cumulative_risk:.2f} >= {self.policy.block_threshold:.2f})."
                ),
                response=SAFE_REFUSAL,
            )
        return MitigationDecision(
            name=self.name,
            action="allow",
            reason=f"Cumulative risk {risk.cumulative_risk:.2f} below block threshold.",
        )


@dataclass
class ContextQuarantine(Mitigation):
    policy: SafetyPolicy

    name = "context_quarantine"

    def before_model(
        self, messages: tuple[Message, ...], risk: RiskAssessment
    ) -> MitigationDecision:
        if risk.cumulative_risk < self.policy.rewrite_threshold:
            return MitigationDecision(
                name=self.name,
                action="allow",
                reason=f"Risk {risk.cumulative_risk:.2f} below quarantine threshold.",
            )

        categories = ", ".join(risk.categories) or "unknown"
        system = Message(
            role="system",
            content=(
                "CrescendoGuard Safety Context: The prior conversation shows possible "
                f"multi-turn escalation in these risk categories: {categories}. "
                "Answer only with refusal, safety education, prevention, or support resources. "
                "Do not provide operational instructions, quantities, evasion tactics, capture logic, "
                "or steps that enable harm."
            ),
        )
        safe_user = Message(
            role="user",
            content=(
                "The latest user turn has been quarantined because it may request harmful operational "
                "details. Provide a brief safe alternative that addresses the benign educational need."
            ),
        )
        return MitigationDecision(
            name=self.name,
            action="rewrite",
            reason=(
                "Replaced risky dialogue history with a safety summary and a benign response target."
            ),
            transformed_messages=(system, safe_user),
        )


@dataclass
class PostResponseVerifier(Mitigation):
    policy: SafetyPolicy
    detector: CrescendoDetector

    name = "post_guard"

    def after_model(
        self, messages: tuple[Message, ...], response: str, risk: RiskAssessment
    ) -> MitigationDecision:
        if self.detector.response_is_unsafe(response, messages):
            return MitigationDecision(
                name=self.name,
                action="replace",
                reason="Model response matched unsafe-output indicators.",
                response=SAFE_REFUSAL,
            )
        return MitigationDecision(
            name=self.name,
            action="allow",
            reason="Model response passed post-generation verification.",
        )
