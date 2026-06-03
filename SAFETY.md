# Safety and Responsible Use

CrescendoGuard is defensive research software. It is designed to evaluate and reduce multi turn jailbreak risk in a controlled LLM safety setting.

## Repository safety choices

- Attack vectors are sanitized and non actionable.
- The default model client is deterministic and emits an `UNSAFE_COMPLETION` marker instead of harmful instructions.
- Generated public artifacts contain aggregate metrics and short response previews only.
- The real Llama adapter is optional and should be used only in a controlled environment.

## Recommended operating practice

When running against a real model:

1. Keep raw transcripts private unless they have been safety-reviewed.
2. Do not publish harmful model completions.
3. Store only aggregate metrics, redacted examples, and mitigation decisions in public reports.
4. Use the benchmark to improve refusal, safe redirection, and defensive educational responses.

## Scope

This project is not a production-grade moderation system. It is a transparent prototype for the assignment brief and a foundation for stronger classifiers, larger test suites, and controlled red team evaluations.
