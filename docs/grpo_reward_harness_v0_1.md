# Phase 45 — GRPO reward harness

This phase does not train a model. It defines auditable reward components,
training-case contracts, reward-hacking regression tests, and a hard
training/evaluation case-ID leakage guard.

Rewards use externally observable behavior: correctness labels, refusal,
citation validity, evidence support, structured output, required-tool use, and
tool-call efficiency. Hidden chain-of-thought is not part of the reward
contract.

The `rl` optional dependency is added for Phase 46. Training results must not be
claimed until a real run is executed and evaluated on a disjoint frozen set.
