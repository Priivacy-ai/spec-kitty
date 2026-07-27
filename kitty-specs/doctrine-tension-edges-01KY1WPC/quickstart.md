# Quickstart: Doctrine Tension as First-Class DRG Edges

Manual walkthrough exercising the mission's core behavior end-to-end (US1 + US2).
Intended as the acceptance script implementers/reviewers run by hand before trusting
the automated tests.

## 1. See tension surfaced (US1)

The built-in pack already ships two directives in tension:
`directive:024-locality-of-change` and `directive:025-boy-scout-rule`.

```bash
spec-kitty charter pack consistency-check --json
```

**Expect**: `coherent: true` (out of the box, per SC-002 — the reconciliation
directive keeps it clear) and `unreconciled_tensions: []`, because
`reconcile-change-scope-tensions` (FR-011) already bridges the pair.

```bash
spec-kitty charter activate <some-artefact-that-does-not-touch-024-or-025>
```

**Expect**: no tension warning (US1 Acceptance Scenario 3 — only fires when both
sides are co-active).

## 2. Prove the reconciler is load-bearing (SC-002)

```bash
# Temporarily deactivate the reconciliation directive
spec-kitty charter deactivate reconcile-change-scope-tensions
spec-kitty charter pack consistency-check --json
```

**Expect**: `unreconciled_tensions` now contains the `directive:024-locality-of-change`
/ `directive:025-boy-scout-rule` pair (and the
`tactic:change-apply-smallest-viable-diff` / `directive:025-boy-scout-rule` pair —
INV-005), each with both resolution-path strings. `coherent` stays `true`
(NFR-001 — advisory, never hard-blocks).

```bash
# Restore
spec-kitty charter activate reconcile-change-scope-tensions
spec-kitty charter pack consistency-check --json
```

**Expect**: `unreconciled_tensions: []` again — the reconciler demonstrably clears the
finding (this before/after pair is what makes SC-002 a live assertion, not vacuous).

## 3. Author a new tension and resolve it (US2)

```yaml
# in a test/example directive fragment
edges:
  - source: "directive:example-a"
    target: "directive:example-b"
    relation: in_tension_with
```

```bash
spec-kitty charter activate directive:example-a directive:example-b
```

**Expect**: a `tension_unreconciled` warning naming both, with both resolution paths.

Add a reconciler with `reconciles_tension` edges to **both** `example-a` and
`example-b`, activate it, and re-run:

**Expect**: the finding clears. Add `reconciles_tension` to only one side and re-run:

**Expect**: the finding is still present (half-reconciled does not resolve — Edge
Case, User Story 2 Acceptance Scenario 2).

## 4. Confirm `opposed_by` is gone (US3)

```bash
grep -rn "opposed_by" src/ docs/ tests/
```

**Expect**: zero hits (SC-004). If downstream org-pack YAML still authors it:

```bash
spec-kitty migrate rewrite-opposed-by --pack <path> --dry-run
```

**Expect**: a report of planned rewrites (see contracts/migrate-opposed-by.md); running
without `--dry-run` performs them.

## 5. Confirm orphan-lint no longer false-positives (US4)

```bash
spec-kitty charter lint
```

**Expect**: `orphaned_directive` findings equal exactly
`{DIRECTIVE_035, DIRECTIVE_039}` (SC-003) — no other built-in directive flagged.

## 6. Confirm doc parity (US5)

Mutate one of the three new relations' descriptions in
`docs/architecture/doctrine-relationships.md` only (not the registry), then run the
parity check (module TBD at tasks time).

**Expect**: the check fails, naming the mutated relation. Revert the doc edit; the
check passes again.
