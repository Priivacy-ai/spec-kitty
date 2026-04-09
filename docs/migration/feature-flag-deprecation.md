# Migration: `--feature` to `--mission`

**Status**: Deprecated as of Mission `077-mission-terminology-cleanup`.
**Removal**: Gated on named conditions. No calendar date is set.

## Why This Change

The `--feature` CLI flag has been replaced by `--mission` as the canonical
selector for tracked missions. This aligns the operator-facing CLI with the
canonical terminology boundary:

- **Mission Type** = reusable workflow blueprint (`software-dev`, `research`, `documentation`)
- **Mission** = concrete tracked item under `kitty-specs/<mission-slug>/`
- **Mission Run** = runtime/session execution instance only

`--feature` remains available only as a hidden deprecated alias during the
migration window so older scripts can keep running while first-party surfaces
finish moving to `--mission`.

## What Changed

| Before | After |
| --- | --- |
| `spec-kitty mission current --feature 077-foo` | `spec-kitty mission current --mission 077-foo` |
| `spec-kitty next --feature 077-foo` | `spec-kitty next --mission 077-foo` |
| `spec-kitty agent tasks status --feature 077-foo` | `spec-kitty agent tasks status --mission 077-foo` |

The alias still resolves, but it emits a deprecation warning on stderr.

## Behavioral Changes

1. Passing both `--mission` and `--feature` with different values now fails fast with a deterministic conflict error.
2. Passing both flags with the same value succeeds, but still emits the deprecation warning once.
3. `--feature` is hidden from `--help` output. New examples and docs must use `--mission`.

## How to Migrate Scripts

Replace `--feature` with `--mission` anywhere you invoke `spec-kitty`.

```bash
# Old
spec-kitty mission current --feature 077-mission-terminology-cleanup

# New
spec-kitty mission current --mission 077-mission-terminology-cleanup
```

For bulk shell-script migration:

```bash
find . -name "*.sh" -o -name "*.bash" | xargs sed -i '' 's/--feature /--mission /g'
```

Review the diff before committing. A blind replacement can catch unrelated tools
or documentation.

## Suppressing the Warning During Cutover

If CI or an automation wrapper cannot tolerate stderr noise while you migrate,
set:

```bash
export SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION=1
```

This suppresses the warning only. It does not disable conflict detection.

## Removal Criteria

The `--feature` alias can be removed only when all of the following are true:

1. First-party doctrine skills, examples, and user-facing docs teach `--mission` only.
2. First-party machine-facing surfaces have completed Scope B alignment.
3. A documented audit window shows zero first-party legacy `--feature` usage in active CI and shipped scripts.

Removal is a separate change. There is no date-based removal promise.

## References

- [Mission spec](../../kitty-specs/077-mission-terminology-cleanup/spec.md)
- [Mission Type / Mission / Mission Run Terminology Boundary ADR](../../architecture/2.x/adr/2026-04-04-2-mission-type-mission-and-mission-run-terminology-boundary.md)
- [Mission Nomenclature Reconciliation initiative](../../architecture/2.x/initiatives/2026-04-mission-nomenclature-reconciliation/README.md)
- [Tracking issue #241](https://github.com/Priivacy-ai/spec-kitty/issues/241)
