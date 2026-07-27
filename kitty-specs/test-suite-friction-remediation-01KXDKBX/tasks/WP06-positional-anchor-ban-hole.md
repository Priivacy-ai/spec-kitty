---
work_package_id: WP06
title: Close the seed-tuple laundering hole in the positional-anchor ban
dependencies: []
requirement_refs:
- FR-005
- FR-016
- NFR-002
tracker_refs:
- '2564'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
- T028
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_ratchet_positional_anchor_ban.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_ratchet_positional_anchor_ban.py
- tests/architectural/test_trio_seam_only.py
role: implementer
tags: []
shell_pid: "3019175"
shell_pid_created_at: "1783953675.37"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-005 + the Domain
Language rows for "Seed-tuple laundering" / "Positional line-anchor" / "Content-addressed key",
[plan.md](../plan.md) §IC-04, and the contract
[contracts/positional-anchor-ban-hole.md](../contracts/positional-anchor-ban-hole.md).

## Objective

Close the #2564 **seed-tuple laundering** hole: `test_ratchet_positional_anchor_ban.py` must flag a raw
`(rel_path, int_line)` tuple stored in a module-level seed constant even when the `int` reaches
`composite_key(source, N)` via an intermediate loop/local variable — and convert the one remaining
launderer, `test_trio_seam_only._IO_ALLOWLIST_SITES` (~L463), to content-addressed keys.

## Context

- The #2077 guard already bans **direct** positional anchors; the residual hole is the **laundering vector**
  (seed tuple → loop var → `composite_key`).
- `test_no_write_side_rederivation.py` is **already clean** (content-addressed `ContentDescriptor` seeds) —
  **do NOT touch it** (it is not in this WP's owned_files).
- The `\.py", *[0-9]{3}\)` grep in `tests/architectural/` is **already 0** for direct anchors — the real
  work is (a) the guard extension and (b) the single `trio_seam` conversion.
- Keep the predicate **int-to-line-sink**, not "positional anchor in general" — `module::Name` /
  `path::qualname` symbol-identity keys are explicitly allowed (contract Notes).

## Subtask guidance

- **T024 — extend the ban guard.** Add AST detection: a module-level seed constant holding `(rel, int)`
  whose `int` element flows (through a `for`/assignment) into the 2nd positional arg of
  `composite_key(...)` / `composite_key_from_file(...)` is a banned int-to-line-sink. Keep the predicate
  precise: do NOT flag a `composite_key(source, N)` whose `N` is a genuine live line from
  `code_tokens_by_line(...)` at runtime.
- **T025 — red-first regression.** Add a fixture that *attempts* the laundering (a seed tuple whose int is
  looped into `composite_key`) and assert the ban **fails** on it. Add the paired negative fixture (a
  legitimate live-line `composite_key`) and assert it is **not** flagged.
- **T026 — convert the launderer.** Rewrite `test_trio_seam_only._IO_ALLOWLIST_SITES` (~L463) from raw
  `(rel, N)` seed tuples to content-addressed `composite_key`-derived keys, matching the clean pattern in
  `test_no_write_side_rederivation.py`.
- **T027 — non-fakeable DoD (real proof, not the sibling grep).** The extended ban (T024) run against the
  **unconverted** `_IO_ALLOWLIST_SITES` MUST FAIL (T025's red-first regression proves the guard bites the
  multi-line `(rel, int, key)` laundering vector); then, after T026's conversion, import
  `test_trio_seam_only._IO_ALLOWLIST_SITES` and assert no element carries a bare `int` line-number member;
  and `.venv/bin/python -m pytest tests/architectural/test_ratchet_positional_anchor_ban.py -q` green on the
  real (non-fixture) tree. The `git grep -nE '\.py", *[0-9]{3}\)' tests/architectural/` = 0 check is an
  already-satisfied sibling invariant (the multi-line 3-tuple seeds evade the regex), **not** this WP's proof.
- **T028 — gates + tracer.** `ruff`/`mypy` clean; append tracer rows.

## Branch Strategy

Lane A root (no dependencies). Branches from the mission base; merges into
`feat/test-suite-friction-remediation`.

## Definition of Done (non-fakeable — NFR-002)

- [ ] The ban flags a `(rel,int)` seed laundered through a loop var into `composite_key(source,N)`.
- [ ] A regression fixture that attempts the laundering **fails** the ban; the legitimate-live-line fixture
      does **not** trip it (no false positive).
- [ ] `test_trio_seam_only._IO_ALLOWLIST_SITES` converted to content-addressed keys.
- [ ] **RED-FIRST proof (this WP's real proof):** the extended positional-anchor ban (T024), run against the
      **UNCONVERTED** `_IO_ALLOWLIST_SITES`, MUST FAIL — proving the guard bites the real multi-line
      `(rel, int, key)` laundering vector (see T025's red-first regression). Without this, the guard passes
      with zero work done.
- [ ] **STRUCTURAL positive proof:** import `test_trio_seam_only._IO_ALLOWLIST_SITES` and assert no element
      contains a bare `int` line-number member (content-addressed keys only — the tuple shape no longer has
      an `int` slot).
- [ ] `test_ratchet_positional_anchor_ban.py` green on the real tree.
- [ ] `git grep -E '\.py", *[0-9]{3}\)' tests/architectural/` = 0 — **already-satisfied sibling invariant,
      NOT this WP's proof** (the multi-line 3-tuple seeds the regex cannot see mean this passes untouched).
- [ ] `test_no_write_side_rederivation.py` untouched.
- [ ] `ruff` + `mypy` clean.
- [ ] **Tracer (FR-016):** append a catalog row for the positional-anchor ban ratchet (invariant-vs-shape,
      CaaCS churn, verdict) + friction log.

## Risks

- **Over-broad detector** — flagging a legitimate `composite_key` whose 2nd arg is a genuine live line. Keep
  the int-to-seed-sink predicate precise; the negative fixture is the guardrail.
- **Symbol-identity keys** (`module::Name`) are allowed — do not ban them (would be circular with FR-014).

## Reviewer guidance

- Confirm both directions are fixture-proven (laundering fails, live-line passes).
- Confirm the grep is 0 and `test_no_write_side_rederivation.py` is untouched.

## Activity Log

- 2026-07-13T14:12:27Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Assigned agent via action command
- 2026-07-13T14:40:04Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Ready for review: closed #2564 seed-tuple laundering hole; extended AST detector + converted _IO_ALLOWLIST_SITES to ContentDescriptor keys; red-first proof + structural proof green; 101 tests pass, ruff clean, mypy delta-clean
- 2026-07-13T14:41:34Z – claude:opus:reviewer-renata:reviewer – shell_pid=3019175 – Started review via action command
- 2026-07-13T15:01:37Z – user – shell_pid=3019175 – Review passed (reviewer-renata/opus)
