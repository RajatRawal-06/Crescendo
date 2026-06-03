"""CrescendoGuard defense pipeline for multi turn LLM safety research."""

from crescendo_guard.detectors import CrescendoDetector
from crescendo_guard.mitigations import (
    ContextQuarantine,
    PostResponseVerifier,
    RollingRiskGate,
)
from crescendo_guard.model_clients import DryRunLlamaModel, HuggingFaceLlamaClient
from crescendo_guard.pipeline import DefensePipeline, build_strategy
from crescendo_guard.policy import SafetyPolicy

__all__ = [
    "ContextQuarantine",
    "CrescendoDetector",
    "DefensePipeline",
    "DryRunLlamaModel",
    "HuggingFaceLlamaClient",
    "PostResponseVerifier",
    "RollingRiskGate",
    "SafetyPolicy",
    "build_strategy",
]
