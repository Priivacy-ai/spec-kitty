# Contract: charter activate

**Command**: `spec-kitty charter activate <kind> <id> [--cascade <scope>]`

## Synopsis

Adds an artifact to the project's activated set for its kind. Once at least one artifact of a kind is explicitly activated, only activated artifacts of that kind are available (hard restriction). When no activation entry exists for a kind, all built-in artifacts remain available (backward-compat fallback).

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `kind` | ActivationKind | Yes | One of: `mission-type`, `directive`, `tactic`, `styleguide`, `toolguide`, `paradigm`, `procedure`, `agent-profile`, `mission-step-contract` |
| `id` | string | Yes | Artifact ID as it appears in doctrine (e.g., `python-style-guide`, `software-dev`) |
| `--cascade` | string | No | Cascade scope: `all`, or one or more comma-separated CLI kind names (hyphen form: `directive`, `tactic`, `styleguide`, `toolguide`, `paradigm`, `procedure`, `agent-profile`, `mission-step-contract`). Default: no cascade. |

## Behavior

1. Validate `kind` is one of the 9 activatable kinds. Error if unknown.
2. Validate `id` exists in the doctrine catalog for that kind. Error if unknown artifact.
3. Read current activation state from `.kittify/config.yaml`.
4. If `activated_<kind>` key is absent in config.yaml (pre-upgrade project): materialize the initial activation set from `src/charter/packs/default.yaml` for that kind before adding `id`. If the live doctrine catalog for this kind has entries absent from `default.yaml` (third-party artifacts), emit a visible warning that those artifacts will not be included in the materialized set.
5. Add `id` to the activation set for `kind` in config.yaml.
6. If `--cascade` is absent: emit a warning listing cross-kind references from `id` that were NOT cascaded, with hint to use `--cascade`.
7. If `--cascade <scope>` is present: activate all artifacts of the specified kinds that `id` references (DRG edges or catalog cross-references).
8. Write updated activation state to `.kittify/config.yaml` (ruamel.yaml round-trip, comment-preserving).
9. Print confirmation: which artifact was activated, which were cascade-activated (if any), which cross-references were skipped (if cascade was partial).

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Activation successful |
| 1 | Unknown kind or unknown artifact ID |
| 2 | config.yaml write error |

## Output (human-readable)

```
Activated: directive/python-style-guide
Cross-references not cascaded (use --cascade tactic to include):
  - tactic/test-driven-development
  - tactic/clean-arch
Hint: spec-kitty charter activate directive python-style-guide --cascade tactic
```

With `--cascade tactic`:
```
Activated: directive/python-style-guide
Cascade-activated (tactic): test-driven-development, clean-arch
```

## State Written (config.yaml)

```yaml
activated_directives:
  - python-style-guide
activated_tactics:           # only if --cascade tactic was used
  - test-driven-development
  - clean-arch
```
