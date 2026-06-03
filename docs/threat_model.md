# Threat Model

## System Under Test

The defended system is a chat assistant backed by Llama-3.2-3B-Instruct. CrescendoGuard is placed between the user and the model. It receives the conversation history and latest user turn, decides whether to allow, rewrite, or block the turn, and verifies the response before it reaches the user.

## Attacker Capabilities

- Sends multiple conversational turns.
- Starts with benign or educational framing.
- References previous model outputs to create memory stacking.
- Uses fiction, red team, or simulation language as a prompt disguise.
- Gradually shifts from high-level discussion to operational harmful requests.

## Defender Goals

- Reduce Attack Success Rate on Crescendo style conversations.
- Preserve benign safety, prevention, and support conversations.
- Keep guard overhead small relative to model generation.
- Produce auditable mitigation decisions for each turn.

## Non-Goals

- The repository does not publish actionable attack instructions.
- The default benchmark does not claim to replace private red team testing.
- The rule based detector is not presented as a complete production classifier.

## Evaluation Assumptions

The public benchmark uses a deterministic dry-run model for reproducibility. Real-model evaluation should be run privately with the same pipeline and should report aggregate metrics after transcript review.
