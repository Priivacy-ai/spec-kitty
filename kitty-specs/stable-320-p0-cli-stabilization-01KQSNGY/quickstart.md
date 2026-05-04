# Quickstart: 3.2.0 Stable P0 CLI Stabilization

## Preconditions

Run from the repository root checkout:

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260504-101120-ahKkaN/spec-kitty
```

Default validation is local and offline. If a command path intentionally touches hosted auth, tracker, SaaS, or sync behavior on this computer, set:

```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
```

## Focused Validation

Status hang guard:

```bash
uv run pytest tests/status -q --timeout=30
```

Review consistency and task transition behavior:

```bash
uv run pytest tests/post_merge tests/review tests/tasks -q
```

Runtime, installer, command generation, and skill generation behavior:

```bash
uv run pytest tests/runtime tests/specify_cli -q
```

Lint:

```bash
uv run ruff check src tests
```

Type checking:

```bash
uv run mypy --strict src/specify_cli src/charter src/doctrine
```

## Release Evidence Checklist

- #967: Status bootstrap and emit paths finish under the 30-second timeout or fail with diagnostics.
- #904: Latest rejected review-cycle artifacts block approved/done transitions before mutation unless a durable override is recorded.
- #968: Fresh generated command surface contains no active `spec-kitty.checklist*` command and inventory counts agree.
- #964: Fresh generated `SKILL.md` files contain required YAML frontmatter, including the Codex/global `spec-kitty.advise` repro.

## Merge And Review

```bash
spec-kitty merge --mission stable-320-p0-cli-stabilization-01KQSNGY
spec-kitty review --mission stable-320-p0-cli-stabilization-01KQSNGY
```

After merge, rerun the focused validation from the merged branch and append any
new findings to `release-evidence.md`.
