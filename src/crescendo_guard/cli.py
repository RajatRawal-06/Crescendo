from __future__ import annotations

import argparse
from pathlib import Path

from crescendo_guard.benchmark import STRATEGIES, load_scenarios, run_benchmark, write_outputs
from crescendo_guard.model_clients import DryRunLlamaModel, HuggingFaceLlamaClient
from crescendo_guard.policy import SafetyPolicy
from crescendo_guard.reporting import write_technical_report

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crescendo-guard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run-benchmark", help="Run the Crescendo defense benchmark.")
    run_parser.add_argument("--attack-file", default=str(ROOT / "data" / "crescendo_attack_vectors.json"))
    run_parser.add_argument("--control-file", default=str(ROOT / "data" / "benign_controls.json"))
    run_parser.add_argument("--policy-file", default=str(ROOT / "configs" / "default_policy.json"))
    run_parser.add_argument("--results-dir", default=str(ROOT / "results"))
    run_parser.add_argument("--reports-dir", default=str(ROOT / "reports"))
    run_parser.add_argument("--model", choices=["dry-run", "hf"], default="dry-run")
    run_parser.add_argument("--strategy", choices=[*STRATEGIES, "all"], default="all")
    run_parser.add_argument("--max-new-tokens", type=int, default=160)

    args = parser.parse_args(argv)
    if args.command == "run-benchmark":
        return _run_benchmark(args)
    raise ValueError(f"Unknown command: {args.command}")


def _run_benchmark(args) -> int:
    policy = SafetyPolicy.from_json(args.policy_file)
    attacks = load_scenarios(args.attack_file)
    controls = load_scenarios(args.control_file)
    if args.model == "hf":
        model = HuggingFaceLlamaClient(max_new_tokens=args.max_new_tokens)
    else:
        model = DryRunLlamaModel()

    strategies = STRATEGIES if args.strategy == "all" else (args.strategy,)
    results = run_benchmark(model, attacks, controls, policy=policy, strategies=strategies)
    output_paths = write_outputs(results, args.results_dir)
    report_path = write_technical_report(results, args.reports_dir)

    print("CrescendoGuard benchmark complete")
    for row in results["strategies"]:
        print(
            f"- {row['strategy']}: ASR={row['asr']:.0%}, "
            f"intercept={row['intercept_rate']:.0%}, "
            f"control_block={row['control_block_rate']:.0%}, "
            f"guard_ms={row['avg_guard_latency_ms']:.3f}"
        )
    print(f"JSON: {output_paths['json']}")
    print(f"CSV: {output_paths['csv']}")
    print(f"Summary: {output_paths['summary']}")
    print(f"Technical report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
