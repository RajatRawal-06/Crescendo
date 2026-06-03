# CrescendoGuard for Llama-3.2-3B-Instruct

CrescendoGuard is a reproducible research prototype for defending a Llama-3.2-3B-Instruct chat pipeline against Crescendo-style multi-turn jailbreaks. It implements a guard that sits between the conversation and the model, scores cumulative risk across turns, neutralizes escalating context, and verifies the final model response before returning it.

The repository is intentionally safe to run and review. The default benchmark uses sanitized attack vectors and a deterministic `DryRunLlamaModel` that emits an `UNSAFE_COMPLETION` marker instead of harmful instructions. The same defense pipeline can wrap the real Hugging Face model when `transformers`, `torch`, model access, and suitable hardware are available.

## What is included

- Three defense strategies:
  - `rolling_gate`: cumulative risk scoring and early refusal.
  - `context_quarantine`: high-risk context compression plus a safety instruction envelope.
  - `post_guard`: response verification and replacement if the model leaks unsafe content.
- A `layered` strategy combining all three mitigations.
- Ten sanitized Crescendo attack vectors covering memory stacking, semantic drift, role-play, prompt disguise, and gradual escalation.
- Five benign control conversations to estimate overblocking.
- A benchmark CLI that writes JSON, CSV, Markdown summary, and a 4-6 page technical report.
- Unit tests for the detector, pipeline, and benchmark behavior.
- Optional adapter for `meta-llama/Llama-3.2-3B-Instruct`.
- A CI workflow, threat model, and safety notes for responsible publication.

## Quick start

```powershell
cd C:\Users\rawal\OneDrive\Desktop\crescendo
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m crescendo_guard.cli run-benchmark
python -m unittest discover -s tests
```

The benchmark artifacts are written to `results/` and `reports/`.

## Run the benchmark

```powershell
python -m crescendo_guard.cli run-benchmark --results-dir results
```

Expected high-level outcome with the deterministic simulator:

- `none` has high ASR because no guard is active.
- `rolling_gate` blocks late-stage escalation.
- `context_quarantine` reduces model exposure to risky conversational history.
- `post_guard` catches unsafe outputs after generation.
- `layered` should drive ASR to zero on the included attack suite while preserving the benign controls.

## Wrap the real Llama model

Llama-3.2-3B-Instruct is gated on Hugging Face, so first accept the model terms and configure an `HF_TOKEN` with access.

```powershell
python -m pip install -e .[llama]
$env:HF_TOKEN="hf_..."
python -m crescendo_guard.cli run-benchmark --model hf --max-new-tokens 160
```

The Hugging Face model card documents the `meta-llama/Llama-3.2-3B-Instruct` model identifier, Transformers usage, license, and access gating: <https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct>.

## Project layout

```text
configs/default_policy.json       Guard thresholds and scoring weights
data/crescendo_attack_vectors.json Sanitized 10-vector benchmark suite
data/benign_controls.json          Benign multi-turn controls
src/crescendo_guard/               Pipeline, mitigations, detector, clients
tests/                             Unit tests
docs/threat_model.md               Evaluation assumptions and attacker model
results/                           Generated benchmark outputs
reports/                           Generated technical report
```

## Safety notes

This project is defensive research. Attack vectors are written as non-actionable scenario prompts, and the simulator never emits procedural harmful content. When using a real model, run the benchmark only in a controlled research environment and review any generated logs before sharing.

See `SAFETY.md` and `docs/threat_model.md` for the repository safety posture and evaluation assumptions.

## References

- Russinovich, Salem, and Eldan, "Great, Now Write an Article About That: The Crescendo Multi-Turn LLM Jailbreak Attack", arXiv:2404.01833: <https://arxiv.org/abs/2404.01833>
- Meta Llama-3.2-3B-Instruct model card: <https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct>
- Argilla DPO Mix 7K dataset card: <https://huggingface.co/datasets/argilla/dpo-mix-7k>
