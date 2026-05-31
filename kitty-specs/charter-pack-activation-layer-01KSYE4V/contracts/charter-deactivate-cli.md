# Contract: charter deactivate

**Command**: `spec-kitty charter deactivate <kind> <id> [--cascade <scope>]`

## Synopsis

Removes an artifact from the project's activated set for its kind. This is a first-class command, symmetric with `charter activate`. Deactivation with cascade only removes artifacts of the cascaded kinds that are exclusively referenced by the deactivated artifact — shared artifacts are preserved and warned about.

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `kind` | ActivationKind | Yes | One of: `mission-type`, `directive`, `tactic`, `styleguide`, `toolguide`, `paradigm`, `procedure`, `agent-profile`, `mission-step-contract` |
| `id` | string | Yes | Artifact ID to deactivate |
| `--cascade` | string | No | Cascade scope: `all`, `profiles`, `directives`, `tactics`, or comma-separated subset. Default: no cascade. |

## Behavior

1. Validate `kind` and `id`.
2. Read current activation state from `.kittify/config.yaml`.
3. Remove `id` from the activation set for `kind`.
4. If `--cascade` is absent: emit a warning listing cross-kind references from `id` that were NOT evaluated for cascade deactivation.
5. If `--cascade <scope>` is present:
   - For each artifact of the cascade kinds referenced by `id`:
     - If it is referenced by at least one OTHER currently-activated artifact: skip it, emit "Shared — not deactivated: `<kind>/<id>`"
     - If it is exclusively referenced by `id`: deactivate it.
6. Write updated activation state to `.kittify/config.yaml`.
7. Print confirmation: deactivated artifacts, skipped shared artifacts, cascade warnings.

## Shared Artifact Protection

An artifact is considered "shared" if any other activated artifact (of any kind) references it in its cross-kind edges. Shared artifacts are NEVER silently deactivated — they are skipped and reported. The user must explicitly deactivate shared artifacts if intended.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Deactivation successful |
| 1 | Unknown kind, unknown artifact ID, or artifact not in activated set |
| 2 | config.yaml write error |

## Output (human-readable)

```
Deactivated: directive/python-style-guide
Shared artifacts not deactivated (still referenced by other activated artifacts):
  - tactic/test-driven-development (referenced by: directive/clean-code)
Cross-references not evaluated (use --cascade tactics to check):
  - tactic/clean-arch
```

With `--cascade tactics`:
```
Deactivated: directive/python-style-guide
Cascade-deactivated (tactics): clean-arch
Shared (skipped): test-driven-development (still referenced by directive/clean-code)
```

## State Written (config.yaml)

```yaml
activated_directives:        # python-style-guide removed
  - clean-code
activated_tactics:           # only if --cascade tactics removed something
  - test-driven-development  # preserved (shared)
  # clean-arch removed
```
