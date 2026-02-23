# 2.x Orchestration and API Boundary

`2.x` keeps orchestration external while preserving host-owned workflow integrity.

## Boundary model

1. Host: `spec-kitty` manages lane state, dependency checks, and merge/accept semantics.
2. Provider: external orchestration runtime executes agents and calls host API.
3. Contract: `spec-kitty orchestrator-api` JSON envelope and deterministic error codes.

## Operational implications

1. Security-sensitive environments can disable external automation and keep manual flow.
2. Multiple provider strategies can be implemented without changing host internals.
3. Runtime governance remains centralized in the host contract.

## Baseline commands

```bash
spec-kitty orchestrator-api contract-version --json
spec-kitty orchestrator-api feature-state --feature 034-my-feature --json
spec-kitty orchestrator-api list-ready --feature 034-my-feature --json
```

## Reference provider

Use `spec-kitty-orchestrator` for turnkey automation:

```bash
spec-kitty-orchestrator orchestrate --feature 034-my-feature --dry-run
spec-kitty-orchestrator orchestrate --feature 034-my-feature
```

## Custom provider guidance

Implement your orchestration loop against `orchestrator-api`; do not import host internals or write lane state directly.

## References

1. [Run External Orchestrator](../how-to/run-external-orchestrator.md)
2. [Build Custom Orchestrator](../how-to/build-custom-orchestrator.md)
3. [Orchestrator API Reference](../reference/orchestrator-api.md)
