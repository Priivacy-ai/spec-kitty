# Contract: `spec-kitty migrate` subcommand for `opposed_by` (FR-015)

Resolved decision (research.md): new subcommand modeled on the existing
`src/specify_cli/migration/backfill_identity.py` + `src/specify_cli/cli/commands/migrate_cmd.py`
one-shot-rewrite pattern. No deprecation window — the schema drops `opposed_by` from
`additionalProperties: false` in the same release this command ships in.

## Invocation

```
spec-kitty migrate rewrite-opposed-by [--pack PATH] [--dry-run] [--json]
```

(Exact subcommand name confirmed at tasks time against `migrate_cmd.py`'s existing
naming convention — `rewrite-opposed-by` is the working name for this contract.)

## Behavior

1. Scan the target pack's authored YAML (directive/tactic/paradigm sources) for
   `opposed_by` usages.
2. For each usage, classify per D2/D1:
   - A tension-style entry (competing rule, no anti-pattern semantics) → rewrite to a
     hand-authored `in_tension_with` edge.
   - An anti-pattern-rejection-style entry → rewrite to a `rejects` edge, creating (or
     linking to) a `NodeKind.ANTI_PATTERN`-marked target node.
3. Remove the `opposed_by` key from the source YAML once rewritten.
4. `--dry-run` reports the planned rewrites (source → edge) without writing.
5. Exit non-zero with a clear diagnostic (not a raw Pydantic validation traceback) if
   an `opposed_by` entry cannot be unambiguously classified — this is a `manual_review`
   case surfaced to the operator, not a silent best-guess rewrite.

## Precedent alignment

Mirrors `backfill_identity.py`'s shape: idempotent (a second run against an
already-migrated pack is a no-op), verifiable after the fact (an equivalent of
`doctor identity` — e.g. `charter lint` or a dedicated check — should report zero
remaining `opposed_by` usages post-migration), and safe to run against an
already-clean pack.

## Failure mode this contract exists to prevent

Without this command, removing `opposed_by` from `additionalProperties: false`
schemas breaks any downstream/org-pack YAML that authored it, with only a schema
validation error pointing at the symptom, not the fix. This contract's exit-code and
diagnostic requirements ensure the operator is pointed at `spec-kitty migrate
rewrite-opposed-by`, not left to reverse-engineer the new edge model by hand.
