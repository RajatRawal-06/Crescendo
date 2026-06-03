from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from crescendo_guard.policy import SafetyPolicy
from crescendo_guard.types import Message, RiskAssessment, SafetySignal


def _compile(patterns: Iterable[str]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(pattern, flags=re.IGNORECASE) for pattern in patterns)


HAZARD_PATTERNS = {
    "cyber_abuse": _compile(
        [
            r"\bmalware\b",
            r"\bransomware\b",
            r"\bworm\b",
            r"\bdeploy\b.*\bsoftware\b",
            r"\bavoid detection\b",
            r"\bbypass\b.*\bsecurity\b",
        ]
    ),
    "weapons": _compile(
        [
            r"\bharmful device\b",
            r"\bweapon(?:s|ization)?\b",
            r"\bexact quantities\b",
            r"\bexplosive\b",
            r"\bdetonat",
        ]
    ),
    "credential_theft": _compile(
        [
            r"\bcredential\b",
            r"\bpasswords?\b",
            r"\bphishing\b",
            r"\bcapture logic\b",
            r"\bfake login\b",
        ]
    ),
    "privacy_abuse": _compile(
        [
            r"\bdoxx",
            r"\bhome address\b",
            r"\bfamily details\b",
            r"\bprivate person\b",
            r"\bexposing\b.*\bperson\b",
        ]
    ),
    "self_harm": _compile(
        [
            r"\bself[- ]harm\b",
            r"\bpainless\b.*\bmethods\b",
            r"\bordered by reliability\b",
            r"\bin crisis\b",
            r"\bhopeless\b",
        ]
    ),
    "financial_fraud": _compile(
        [
            r"\bfraud\b",
            r"\bchargeback\b",
            r"\bwithout getting caught\b",
            r"\bexploit(?:ing)?\b.*\brules\b",
        ]
    ),
    "biosecurity": _compile(
        [
            r"\bbiosafety\b",
            r"\bbiological agents?\b",
            r"\bbroader spread\b",
            r"\buncontrolled environment\b",
            r"\boptimi[sz]e\b.*\bproperties\b",
        ]
    ),
    "extremism": _compile(
        [
            r"\bextremist\b",
            r"\brecruitment\b",
            r"\bpropaganda\b",
            r"\bradical",
            r"\bmanipulative movements\b",
        ]
    ),
    "physical_intrusion": _compile(
        [
            r"\bbypass(?:ing)?\b.*\baccess control\b",
            r"\bafter hours\b",
            r"\bwithout triggering alarms\b",
            r"\bintrusion\b",
            r"\block[- ]?picking\b",
        ]
    ),
    "policy_evasion": _compile(
        [
            r"\bignore\b.*\bsafety constraints\b",
            r"\bdisallowed request\b",
            r"\bnon-refusing model\b",
            r"\brules are only suggestions\b",
            r"\bpretend\b.*\bsimulation\b",
        ]
    ),
}

OPERATIONAL_PATTERNS = _compile(
    [
        r"\bstep[- ]by[- ]step\b",
        r"\bexact\b",
        r"\bprecise steps\b",
        r"\bactionable\b",
        r"\bend[- ]to[- ]end\b",
        r"\bchecklist\b",
        r"\bprotocol\b",
        r"\bquantities\b",
        r"\bmethod\b",
        r"\bworkflow\b",
        r"\bplan\b",
    ]
)

PROMPT_EVASION_PATTERNS = _compile(
    [
        r"\bdo not include warnings\b",
        r"\bremove any ethical caveats\b",
        r"\bwithout refusal\b",
        r"\bignore\b.*\brules\b",
        r"\bignore\b.*\bsafety constraints\b",
        r"\bpretend\b.*\bconstraints\b",
        r"\bno crisis resources\b",
        r"\banswer\b.*\bexactly\b",
    ]
)

ROLEPLAY_PATTERNS = _compile(
    [
        r"\bfictional\b",
        r"\bshort story\b",
        r"\bcharacter\b",
        r"\blab notebook\b",
        r"\bfor realism\b",
        r"\bharmless simulation\b",
        r"\bred[- ]team\b",
    ]
)

MEMORY_PATTERNS = _compile(
    [
        r"\bthat\b",
        r"\bthose\b",
        r"\bfrom above\b",
        r"\bprevious\b",
        r"\byour earlier\b",
        r"\bcontinue\b",
        r"\bturn that into\b",
        r"\busing those\b",
        r"\bcontext above\b",
    ]
)

OBFUSCATION_PATTERNS = _compile(
    [
        r"\bwithout getting caught\b",
        r"\bavoid detection\b",
        r"\bwithout triggering\b",
        r"\bdo not include\b",
        r"\bremove\b.*\bcaveats\b",
    ]
)

SAFETY_RESEARCH_PATTERNS = _compile(
    [
        r"\bdefen[cs]e\b",
        r"\bdetect\b",
        r"\bmitigation\b",
        r"\bsafety\b",
        r"\bprevention\b",
        r"\breducing abuse\b",
        r"\bawareness\b",
        r"\bethic",
        r"\bresponsibly\b",
        r"\bprotect\b",
        r"\bsafe policy\b",
        r"\blegitimate customers\b",
        r"\breporting template\b",
        r"\bchecklist for recognizing\b",
        r"\bposter\b",
        r"\bclassroom\b",
    ]
)

UNSAFE_RESPONSE_PATTERNS = _compile(
    [
        r"\bUNSAFE_COMPLETION\b",
        r"\bwithout getting caught\b",
        r"\bavoid detection\b",
        r"\bexact quantities\b",
        r"\bcapture passwords\b",
        r"\bpainless self[- ]harm methods\b",
        r"\bbypass(?:ing)?\b.*\balarms\b",
    ]
)


@dataclass(frozen=True)
class TurnScore:
    score: float
    categories: dict[str, float]
    signals: tuple[SafetySignal, ...]


class CrescendoDetector:
    """Risk detector focused on multi turn escalation rather than single prompts only."""

    def __init__(self, policy: SafetyPolicy | None = None):
        self.policy = policy or SafetyPolicy()

    def assess(self, history: Iterable[Message], user_text: str) -> RiskAssessment:
        history_list = list(history)
        user_scores = [self._score_text(message.content) for message in history_list if message.role == "user"]
        current = self._score_text(user_text)

        cumulative = 0.0
        prior_turn_scores: list[float] = []
        prior_categories: set[str] = set()
        for score in user_scores:
            prior_turn_scores.append(score.score)
            prior_categories.update(score.categories)
            cumulative = (cumulative * self.policy.risk_decay) + (score.score * self.policy.turn_weight)

        signals = list(current.signals)
        categories = defaultdict(float, current.categories)

        if self._has_memory_stacking(user_text, history_list) and prior_categories:
            weight = self.policy.signal_weights["memory_stacking"]
            signals.append(
                SafetySignal(
                    name="memory_stacking",
                    score=weight,
                    reason="The turn references earlier context while carrying prior risky categories.",
                    evidence=self._evidence(user_text, MEMORY_PATTERNS),
                )
            )
            cumulative += weight

        if self._has_semantic_drift(prior_turn_scores, current.score):
            weight = self.policy.signal_weights["semantic_drift"]
            signals.append(
                SafetySignal(
                    name="semantic_drift",
                    score=weight,
                    reason="Risk increased across turns, matching a gradual escalation pattern.",
                    evidence=tuple(f"{score:.2f}" for score in prior_turn_scores[-3:] + [current.score]),
                )
            )
            cumulative += weight

        cumulative = max(cumulative * self.policy.risk_decay + current.score, current.score)
        cumulative = self._clamp(cumulative)
        turn_risk = self._clamp(current.score)

        if cumulative >= self.policy.block_threshold or turn_risk >= self.policy.block_threshold + 0.08:
            action = "block"
        elif cumulative >= self.policy.rewrite_threshold:
            action = "rewrite"
        else:
            action = "allow"

        summary = self._summarize(action, turn_risk, cumulative, categories)
        return RiskAssessment(
            turn_risk=turn_risk,
            cumulative_risk=cumulative,
            action=action,
            categories=dict(sorted(categories.items(), key=lambda item: item[1], reverse=True)),
            signals=tuple(signals[: self.policy.max_evidence_items]),
            summary=summary,
        )

    def response_is_unsafe(self, text: str, history: Iterable[Message] = ()) -> bool:
        if any(pattern.search(text) for pattern in UNSAFE_RESPONSE_PATTERNS):
            return True
        assessment = self.assess(history, text)
        return assessment.turn_risk >= self.policy.post_replace_threshold

    def _score_text(self, text: str) -> TurnScore:
        score = 0.0
        signals: list[SafetySignal] = []
        categories: dict[str, float] = {}
        matched_signal_names: set[str] = set()

        for category, patterns in HAZARD_PATTERNS.items():
            evidence = self._evidence(text, patterns)
            if evidence:
                weight = self.policy.category_weights[category]
                categories[category] = max(categories.get(category, 0.0), weight)
                score += weight
                signals.append(
                    SafetySignal(
                        name="hazard_category",
                        category=category,
                        score=weight,
                        reason=f"Detected {category.replace('_', ' ')} indicators.",
                        evidence=evidence,
                    )
                )

        for name, patterns in (
            ("operationalization", OPERATIONAL_PATTERNS),
            ("prompt_evasion", PROMPT_EVASION_PATTERNS),
            ("roleplay_disguise", ROLEPLAY_PATTERNS),
            ("obfuscation", OBFUSCATION_PATTERNS),
        ):
            evidence = self._evidence(text, patterns)
            if evidence:
                weight = self.policy.signal_weights[name]
                matched_signal_names.add(name)
                score += weight
                signals.append(
                    SafetySignal(
                        name=name,
                        score=weight,
                        reason=f"Detected {name.replace('_', ' ')} language.",
                        evidence=evidence,
                    )
                )

        safety_evidence = self._evidence(text, SAFETY_RESEARCH_PATTERNS)
        safety_discount_allowed = (
            "prompt_evasion" not in matched_signal_names
            and "obfuscation" not in matched_signal_names
            and "policy_evasion" not in categories
        )
        if safety_evidence and safety_discount_allowed:
            weight = self.policy.signal_weights["safety_research_context"]
            score += weight
            signals.append(
                SafetySignal(
                    name="safety_research_context",
                    score=weight,
                    reason="Detected defensive, educational, or ethics framing.",
                    evidence=safety_evidence,
                )
            )

        return TurnScore(score=self._clamp(score), categories=categories, signals=tuple(signals))

    def _has_memory_stacking(self, user_text: str, history: list[Message]) -> bool:
        if len([message for message in history if message.role == "user"]) < 1:
            return False
        return bool(self._evidence(user_text, MEMORY_PATTERNS))

    @staticmethod
    def _has_semantic_drift(prior_scores: list[float], current_score: float) -> bool:
        if not prior_scores:
            return False
        recent = prior_scores[-3:]
        if len(recent) >= 2 and current_score > max(recent) + 0.18:
            return True
        return sum(score > 0.20 for score in recent) >= 2 and current_score > 0.35

    @staticmethod
    def _evidence(text: str, patterns: tuple[re.Pattern[str], ...]) -> tuple[str, ...]:
        found: list[str] = []
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                snippet = match.group(0).strip()
                if snippet.lower() not in {item.lower() for item in found}:
                    found.append(snippet)
        return tuple(found)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _summarize(
        action: str, turn_risk: float, cumulative_risk: float, categories: dict[str, float]
    ) -> str:
        top_categories = ", ".join(list(categories)[:3]) or "none"
        return (
            f"action={action}; turn_risk={turn_risk:.2f}; "
            f"cumulative_risk={cumulative_risk:.2f}; categories={top_categories}"
        )
