from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from crescendo_guard.detectors import CrescendoDetector
from crescendo_guard.model_clients import ModelClient
from crescendo_guard.pipeline import build_strategy
from crescendo_guard.policy import SafetyPolicy
from crescendo_guard.types import GuardedResponse, Message

STRATEGIES = ("none", "rolling_gate", "context_quarantine", "post_guard", "layered")


@dataclass(frozen=True)
class Scenario:
    id: str
    category: str
    title: str
    turns: tuple[str, ...]
    objective: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Scenario:
        return cls(
            id=str(data["id"]),
            category=str(data["category"]),
            title=str(data["title"]),
            turns=tuple(str(turn) for turn in data["turns"]),
            objective=str(data.get("objective", "")),
        )


def load_scenarios(path: str | Path) -> list[Scenario]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Scenario.from_dict(item) for item in data]


def run_benchmark(
    model: ModelClient,
    attacks: Iterable[Scenario],
    controls: Iterable[Scenario],
    policy: SafetyPolicy | None = None,
    strategies: Iterable[str] = STRATEGIES,
) -> dict[str, object]:
    policy = policy or SafetyPolicy()
    detector = CrescendoDetector(policy)
    attack_list = list(attacks)
    control_list = list(controls)
    strategy_results = []

    for strategy_name in strategies:
        pipeline = build_strategy(strategy_name, model=model, policy=policy, detector=detector)
        attack_runs = [
            _run_scenario(pipeline, scenario, detector, suite="attack") for scenario in attack_list
        ]
        control_runs = [
            _run_scenario(pipeline, scenario, detector, suite="control") for scenario in control_list
        ]
        attack_successes = sum(1 for run in attack_runs if run["attack_success"])
        control_blocks = sum(1 for run in control_runs if run["blocked_or_replaced"])
        all_turns = [turn for run in [*attack_runs, *control_runs] for turn in run["turns"]]
        called_turns = [turn for turn in all_turns if turn["model_called"]]

        strategy_results.append(
            {
                "strategy": strategy_name,
                "attack_successes": attack_successes,
                "attack_total": len(attack_runs),
                "asr": attack_successes / len(attack_runs) if attack_runs else 0.0,
                "intercept_rate": 1.0 - (attack_successes / len(attack_runs) if attack_runs else 0.0),
                "control_block_count": control_blocks,
                "control_total": len(control_runs),
                "control_block_rate": control_blocks / len(control_runs) if control_runs else 0.0,
                "avg_guard_latency_ms": mean(turn["guard_latency_ms"] for turn in all_turns)
                if all_turns
                else 0.0,
                "avg_model_latency_ms": mean(turn["model_latency_ms"] for turn in called_turns)
                if called_turns
                else 0.0,
                "attack_runs": attack_runs,
                "control_runs": control_runs,
            }
        )

    return {
        "model": model.name,
        "policy": policy.__dict__,
        "attack_count": len(attack_list),
        "control_count": len(control_list),
        "strategies": strategy_results,
    }


def write_outputs(results: dict[str, object], output_dir: str | Path) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / "benchmark_results.json"
    csv_path = output_path / "strategy_metrics.csv"
    summary_path = output_path / "benchmark_summary.md"

    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    _write_strategy_csv(results, csv_path)
    _write_summary_md(results, summary_path)
    return {"json": json_path, "csv": csv_path, "summary": summary_path}


def _run_scenario(pipeline, scenario: Scenario, detector: CrescendoDetector, suite: str) -> dict[str, object]:
    history: list[Message] = []
    turns: list[dict[str, object]] = []
    attack_success = False
    blocked_or_replaced = False
    first_intercept_turn: int | None = None

    for index, user_turn in enumerate(scenario.turns, start=1):
        result: GuardedResponse = pipeline.run_turn(history, user_turn)
        unsafe = detector.response_is_unsafe(result.response, history)
        intervened = result.blocked or result.unsafe_detected or any(
            decision.action in {"block", "rewrite", "replace"} for decision in result.decisions
        )
        attack_success = attack_success or unsafe
        blocked_or_replaced = blocked_or_replaced or result.blocked or result.unsafe_detected
        if intervened and first_intercept_turn is None:
            first_intercept_turn = index

        turns.append(
            {
                "turn": index,
                "risk": result.risk.to_dict(),
                "blocked": result.blocked,
                "intervened": intervened,
                "unsafe_detected": result.unsafe_detected,
                "unsafe_response": unsafe,
                "model_called": result.model_called,
                "guard_latency_ms": result.guard_latency_ms,
                "model_latency_ms": result.model_latency_ms,
                "decisions": [decision.to_dict() for decision in result.decisions],
                "response_preview": result.response[:220],
            }
        )
        history.extend(
            [
                Message(role="user", content=user_turn),
                Message(role="assistant", content=result.response),
            ]
        )

    return {
        "suite": suite,
        "id": scenario.id,
        "category": scenario.category,
        "title": scenario.title,
        "objective": scenario.objective,
        "attack_success": attack_success if suite == "attack" else False,
        "blocked_or_replaced": blocked_or_replaced,
        "first_intercept_turn": first_intercept_turn,
        "turns": turns,
    }


def _write_strategy_csv(results: dict[str, object], path: Path) -> None:
    rows = results["strategies"]
    fields = [
        "strategy",
        "attack_successes",
        "attack_total",
        "asr",
        "intercept_rate",
        "control_block_count",
        "control_total",
        "control_block_rate",
        "avg_guard_latency_ms",
        "avg_model_latency_ms",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fields})


def _write_summary_md(results: dict[str, object], path: Path) -> None:
    lines = [
        "# Benchmark Summary",
        "",
        f"Model: `{results['model']}`",
        f"Attack scenarios: {results['attack_count']}",
        f"Benign controls: {results['control_count']}",
        "",
        "| Strategy | ASR | Intercept rate | Control block rate | Guard ms/turn | Model ms/called turn |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in results["strategies"]:
        lines.append(
            "| {strategy} | {asr:.0%} | {intercept_rate:.0%} | {control_block_rate:.0%} | "
            "{avg_guard_latency_ms:.3f} | {avg_model_latency_ms:.3f} |".format(**row)
        )
    lines.append("")
    lines.append("ASR is the fraction of sanitized attack scenarios where an unsafe marker or unsafe response indicator appeared.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
