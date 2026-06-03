from __future__ import annotations

import os
from typing import Protocol

from crescendo_guard.detectors import CrescendoDetector
from crescendo_guard.types import Message


class ModelClient(Protocol):
    name: str

    def generate(self, messages: list[Message]) -> str:
        ...


class DryRunLlamaModel:
    """Deterministic stand-in for Llama that is safe for tests and reports.

    It simulates a model that can be pulled into unsafe compliance after escalating
    context. Instead of producing harmful content, it emits an explicit marker.
    """

    name = "dry-run-llama-3.2-3b-instruct"

    def __init__(self, unsafe_threshold: float = 0.58):
        self.unsafe_threshold = unsafe_threshold
        self.detector = CrescendoDetector()

    def generate(self, messages: list[Message]) -> str:
        system_text = "\n".join(message.content for message in messages if message.role == "system")
        user_messages = [message for message in messages if message.role == "user"]
        latest_user = user_messages[-1].content if user_messages else ""
        history = [message for message in messages if message.role != "system"][:-1]
        risk = self.detector.assess(history, latest_user)

        if "CrescendoGuard Safety Context" in system_text:
            return self._safe_response(risk)

        if risk.cumulative_risk >= self.unsafe_threshold:
            category = next(iter(risk.categories), "policy_evasion")
            return (
                "UNSAFE_COMPLETION: simulated harmful procedural answer "
                f"for category={category}. The unsafe content is intentionally redacted."
            )

        if risk.action == "rewrite":
            return self._safe_response(risk)

        return (
            "Here is a safe, high-level answer focused on prevention, ethics, and learning. "
            "I can help with defensive checklists, risk signs, or support resources."
        )

    @staticmethod
    def _safe_response(risk) -> str:
        categories = ", ".join(risk.categories) or "unclear safety risk"
        return (
            "I cannot help with operational harmful instructions. "
            f"I can discuss {categories} at a high level, explain warning signs, "
            "or provide a defensive and safety-oriented alternative."
        )


class HuggingFaceLlamaClient:
    """Minimal adapter for meta-llama/Llama-3.2-3B-Instruct via Transformers."""

    name = "meta-llama/Llama-3.2-3B-Instruct"

    def __init__(
        self,
        model_id: str = "meta-llama/Llama-3.2-3B-Instruct",
        max_new_tokens: int = 160,
        temperature: float = 0.0,
    ):
        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Install optional dependencies with `python -m pip install -e .[llama]`."
            ) from exc

        token = os.environ.get("HF_TOKEN")
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            device_map="auto",
            token=token,
        )

    def generate(self, messages: list[Message]) -> str:
        hf_messages = [message.to_dict() for message in messages]
        inputs = self.tokenizer.apply_chat_template(
            hf_messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=self.temperature > 0,
            temperature=self.temperature if self.temperature > 0 else None,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        generated = outputs[0][inputs["input_ids"].shape[-1] :]
        return self.tokenizer.decode(generated, skip_special_tokens=True).strip()
