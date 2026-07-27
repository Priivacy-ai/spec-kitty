# Quickstart — Review/Merge Gate Hardening (3.2.x)

**Mission**: `review-merge-gate-hardening-3-2-x-01KRC57C` | **Date**: 2026-05-12

Operator-facing walkthrough of the new commands and behaviors this mission introduces. Use this as the integration-test plan companion.

---

## 1. Running `spec-kitty review` in the two modes (WP03)

### Lightweight mode (default for pre-merge missions)

```bash
spec-kitty review --mission <slug>
# or explicitly:
spec-kitty review --mission <slug> --mode lightweight
```

Output (stdout):

```
[spec-kitty review] mode=lightweight (not a release gate)
WP lane check: <result>
Report: <path-to-mission-review-report.md>
```

The persisted report begins with the line:

> Lightweight consistency check; not a release gate.

### Post-merge mode (auto-detected once merged)

```bash
spec-kitty review --mission <slug>
# auto-detects from meta.json.baseline_merge_commit
```

Output:

```
[spec-kitty review] mode=post-merge (release gate)
Gate 1 (wp_lane_check): pass
Gate 2 (dead_code_scan): pass (or skipped with reason)
Gate 3 (ble001_audit): pass
Gate 4 (report_writer): pass
issue_matrix_present: true
mission_exception_present: not_applicable
verdict: pass
```

### Mode mismatch (operator footgun caught)

```bash
spec-kitty review --mission <pre-merge-slug> --mode post-merge
```

Exits non-zero with `MISSION_REVIEW_MODE_MISMATCH`. The diagnostic body lists three remediation options. Read it; don't bypass.

---

## 2. Authoring `issue-matrix.md` against the canonical schema

Minimal valid matrix:

```markdown
| issue | verdict | evidence_ref |
|-------|---------|--------------|
| #985  | fixed   | WP03; src/specify_cli/cli/commands/review/_mode.py; tests/specify_cli/cli/commands/review/test_mode_resolution.py |
```

Full canonical (with named-optional columns):

```markdown
| issue | scope | wp | fr | verdict | evidence_ref |
|-------|-------|----|----|---------|--------------|
| #985  | P1    | WP03 | FR-005 | fixed | <evidence> |
| #987  | P1    | WP01 | FR-001 | fixed | <evidence> |
```

**Verdict allow-list** (closed): `fixed | verified-already-fixed | deferred-with-followup`.

**Forbidden**: any column outside the mandatory + named-optional set. The validator will tell you which one.

For `deferred-with-followup` rows, `evidence_ref` MUST contain a follow-up handle (issue link like `#1234`, or the substring `Follow-up: ...`).

---

## 3. Reading `mission-review-report.md`

Frontmatter (machine-readable):

```yaml
---
verdict: pass
mode: post-merge
reviewed_at: 2026-05-15T14:30:00+00:00
findings: 0
gates_recorded:
  - id: gate_1
    name: wp_lane_check
    command: spec-kitty agent tasks status --mission <slug> --json
    exit_code: 0
    result: pass
  - id: gate_2
    name: dead_code_scan
    command: ...
    exit_code: 0
    result: pass
  # ... gate_3, gate_4
issue_matrix_present: true
mission_exception_present: not_applicable
---
```

Consumers (cross-surface harness #992 Phase 0, dashboards, future tooling) read this frontmatter; never infer the mode from filesystem state.

---

## 4. Resuming an interrupted merge (WP04)

If `spec-kitty merge` fails after assigning `mission_number`:

```bash
spec-kitty merge --resume
```

Behavior:
- Reads `MergeState` from `.kittify/merge-state.json`.
- If `mission_number_baked: true` was persisted, the assignment step is skipped on resume — no empty commit, no foot-gun.
- Else, the idempotency check reads `meta.json.mission_number` and only writes if the value changed.

Manual reset (only if state is genuinely corrupt):

```bash
spec-kitty merge --abort
```

This clears the merge state file. Use only when you know the merge cannot continue from where it stopped.

---

## 5. Verifying a merged SHA from a detached worktree (WP05)

Common pattern after a PR merges:

```bash
cd ~/spec-kitty-verifications
git worktree add /tmp/verify-mission-X main
cd /tmp/verify-mission-X
git checkout <merge-sha>

spec-kitty agent tasks status --mission <slug> --json
```

After WP05 lands, the status reflects **this worktree's** events, not the primary checkout's potentially-divergent state. Verification is now trustworthy.

If the command intentionally cannot serve from a detached worktree, it fails loudly with a diagnostic naming the constraint — never silently returns stale state.

---

## 6. Running `spec-kitty migrate charter-encoding` (WP08)

Inspect every mission's charter content for non-UTF-8 encoding:

```bash
spec-kitty migrate charter-encoding --dry-run
```

Output: per-file report (detected encoding, action that would be taken).

Apply normalization interactively:

```bash
spec-kitty migrate charter-encoding
# prompts before each file that requires action
```

For CI:

```bash
spec-kitty migrate charter-encoding --yes
# applies without prompting; fails non-zero if any file is genuinely ambiguous
```

Re-running on an already-normalized corpus is a no-op (NFR-006).

---

## 7. Bypassing `CHARTER_ENCODING_AMBIGUOUS` (WP06 escape hatch)

If the chokepoint fails with `CHARTER_ENCODING_AMBIGUOUS` on a file you've inspected and accept the risk:

```bash
spec-kitty charter compile --unsafe
# or whichever entry path you're invoking
```

This:
- Uses the highest-confidence decode candidate.
- Records `bypass_used: true` in `.encoding-provenance.jsonl`.
- The audit trail captures your override — use it sparingly; the chokepoint exists for a reason.

---

## 8. Smoke test for the whole mission

After all WPs land, the eat-our-own-dogfood smoke (NFR-003):

```bash
# This mission's own review must satisfy the new contract.
spec-kitty review --mission review-merge-gate-hardening-3-2-x-01KRC57C --mode post-merge

# Required artifacts produced by the mission itself:
ls kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/issue-matrix.md
ls kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/mission-review-report.md
```

Both files must exist and pass validation when the mission ships.

---

## 9. ERROR_CODES.md location reference

If you encounter a diagnostic code, the human-readable explanation is documented next to the code:

- `MISSION_REVIEW_*` → [`src/specify_cli/cli/commands/review/ERROR_CODES.md`](../../src/specify_cli/cli/commands/review/ERROR_CODES.md)
- `CHARTER_ENCODING_*` → [`src/charter/ERROR_CODES.md`](../../src/charter/ERROR_CODES.md)

The `StrEnum` class docstring in the corresponding `_diagnostics.py` module names the file path. Drift between the enum and the doc is caught by `tests/.../test_diagnostic_codes_documented.py` (NFR-008 enforcement).
