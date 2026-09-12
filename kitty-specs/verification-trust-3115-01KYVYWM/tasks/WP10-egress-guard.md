---
work_package_id: WP10
title: 'Egress guard: count first, state limit 8, add two positional shapes, tighten only at zero FPs'
dependencies: []
requirement_refs:
- FR-013
- FR-014
- FR-015
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: 9ed8757b6fa46ef3fa51544ff791ded9765df4ee
created_at: '2026-07-31T16:18:44.519503+00:00'
subtasks:
- T029
- T030
- T031
- T032
history: []
authoritative_surface: tests/architectural/
execution_mode: code_change
owned_files:
- tests/architectural/test_egress_consent_boundary.py
- tests/architectural/_baselines.yaml
tags: []
tracker_refs: []
---

# WP10 — The egress guard

**The deeper problem is not the hole, it is that a negative control which only tests the shape you
thought of is not a negative control.** It reports *"the scanner is not blind"* while being blind — and
the squad found that `#3113`'s own mandated bite-test would have certified exactly that.

## Why one WP, and why it also owns `_baselines.yaml`

All three FRs edit `tests/architectural/test_egress_consent_boundary.py` (1,080 lines); C-007 permits
one live agent per file, and **three WPs on one file is the shared-index failure that lost 13 files on
`#3030`**. It owns `tests/architectural/_baselines.yaml` because the FR-015 measurement is the **only**
thing in this mission that can move `egress_allowlist_files: 28` (`:368`) or `known_ungated_files: 0`
(`:375`), and that reconciliation must happen **in the same change** as the matcher edit — growth
**fails** `test_ratchet_baselines.py`, *a different test in a different file*. **No other WP may edit
`_baselines.yaml`.**

## ORDER IS BINDING — re-ordered post-plan (F4)

The earlier draft let the WP restructure the scanner and *then* measure. **Reversed:**

1. **FR-013** (limit 7 → 8, plus the meta-test) and **FR-014**'s two positional cases **red-first**.
   Neither depends on the measurement.
2. **The `src/`-wide false-positive count is taken FIRST**, against the *candidate* predicate,
   **before any matcher edit**.
3. **The scanner restructure is funded only if that count returns zero.** If it does not, **the matcher
   is left alone and FR-014 lands as two `xfail(..., strict=True)` — which is a pass.**

**The WP starts from the non-adoption expectation.** The measurement has already been run once and its
numbers are stated below so the WP does not re-derive the *scoping decision* — **but the WP still
re-runs and quotes its own count, because a planning paragraph is not a measurement.**

## Definition of done — measurable evidence

### T029 — FR-013: the limit list grows by exactly one

The module docstring's "Completeness limits" list currently runs **1-7** (verified: `getattr`-by-string;
empty callback registries; dynamic import/`exec`; variable-command `subprocess`; at-rest pooling; bare
`.put(x)`; multi-sink-per-file). The **all-positional / no-`headers=` transport call** becomes **limit
8**, in the same voice as its neighbours: what the shape is, why AST matching cannot see it, and what
does catch it (review, and the file-keyed allowlist if the sink lands in an unlisted file).

- **Both counts stated**: before **7**, after exactly **8**.
- **A meta-test asserts the entry exists**, so a future docstring trim **reds**.
- The cross-reference to `kitty-specs/journal-project-consent-3030-01KYKWQS/egress-inventory.md` is
  **one-directional**: that file belongs to a **closed mission** and is **not edited** (C-010).

### T030 — FR-014 red first, and case (B) is the adoption gate

`test_scanner_detects_each_sink_shape` (`:933`) is parametrised over eight shapes. **Two positional
cases are added:**

- **(A)** `def go(poster, url, body, hdrs): return poster(url, body, hdrs)` — whose first argument name
  *is* in `_URL_ARG_NAMES` (`:197`), and which therefore **passes trivially under a name-keyed rule**
  because `_attr_tail` (`:266-272`) returns `node.id` verbatim for a bare `Name`. **(A) alone certifies
  a blind matcher.**
- **(B)** `def relay(post, u, payload, meta): return post(u, payload, meta)` — names **outside** that
  set. **This is the adoption gate.** *A matcher that passes (A) and fails (B) is blind in exactly the
  way `#3113` is about.*

**Red first**: on `bb2020fea9` **both** fail with `scanner went blind to transport-call` (`:938`), and
**each failure text is quoted**. A silent deletion of either case is a spec violation.

**Generalisation recorded in the file**: *a negative control that only tests the shape you thought of is
not a negative control* — every rule in the sink vocabulary carries a bite-test case per **shape** it
claims to cover, not one per rule.

### T031 — FR-015: the count comes first, and the command is quoted

`_transmits_a_body` (`:295-306`) requires `headers` **and** a body keyword, so an all-positional call is
invisible. The **candidate tightening is structural**: the callee is a bare `ast.Name` whose `id`
resolves to a **parameter of the enclosing `FunctionDef`** — transport injected as a parameter.
**Decidable with no author-chosen word.**

- **Sites / files / false positives over the whole of `src/` are reported BEFORE adoption**, the way
  the callee-agnostic rule itself was adopted (25 sites / 13 files / 0 FPs).
- **The command that produced the count and the count itself are both quoted** — *a false-positive
  number with no reproducible command is a recollection*.
- **The sites the tightening newly adds are reported separately from the pre-existing ones** (H9).
- **Reconciliation obligation**: the recorded measurement is **5 false positives** over `src/`, arising
  in four named enclosing functions — `resolve_workspace_for_wp`, `locate_work_package`,
  `behind_commits_touch_only_planning_artifacts`, `get_wp_lane` — against **211 candidate sites across
  13 files**. **If the WP's own count differs, the discrepancy is named and reconciled, not silently
  preferred in either direction.**

### T032 — the outcome, both branches of which are a pass

- **Why this is a scanner restructure, not a branch edit** — stated so the cost is visible before it is
  committed to: the predicate needs enclosing-scope information that `_classify(node: ast.Call)`
  (`:309`) does not carry. `_classify` is reached from a **flat `ast.walk(tree)` at `:347`**, which
  discards the enclosing `FunctionDef`. The bare-`Name` branch (`:312-316`,
  `return SinkKind.TRANSPORT_CALL if _transmits_a_body(node) else None`) is where the *decision* would
  live, but **the information to decide with is not there**. Threading the enclosing function's
  parameter set through the walk is the actual change. **That cost is paid only against a zero count.**
- **If false positives are non-zero**: the matcher is **left alone**, the number is **recorded in the
  docstring next to limit 8**, and FR-014 lands as two `xfail(..., strict=True)` cases naming FR-013's
  stated limit. **This is the expected outcome, and it closes `#3113`.**
- **A zero delta is written down verbatim as *"the only demonstrated bite is the synthetic case"***
  rather than passing as a success.
- **C-011**: `strict=True` is **explicit on every `xfail`**. `pytest.ini` sets no `xfail_strict` and
  `pyproject.toml:183-192` forbids a `[tool.pytest.ini_options]` block, so the default is **non-strict**
  — a "pinned hole" that starts passing would report `XPASS` and the run would stay green, i.e. **the
  FR's stated pinning mechanism would not exist**.
- **C-006**: a tightening that cannot be expressed without an author-chosen identifier — **including
  `_URL_ARG_NAMES`** — is **rejected regardless of its false-positive count**. Keying on an *argument*
  name is the `RETIRED_DRAIN_NAMES` failure with a different subject.
- **Either outcome is a pass; an unmeasured tightening is not.**

### `_baselines.yaml` reconciliation

Any change to the sink/allowlist counts is reconciled **deliberately** in the same change: a changed
count is either an **intended ratchet move with a written justification** or a **regression**. Never
absorbed.

> Noted and **out of scope**: `egress_allowlist_files: 28` is **count-anchored**, so a *substitution* —
> one entry removed and another added — passes the ratchet silently. Real, **pre-existing**, a follow-up
> candidate. Do not fix it here.

### Cross-cutting

**NFR-009**: merge the mission branch into the worktree before the first measurement; state the commit
and merge-base. **NFR-003**: output to a file, tail of the file read; quote the count line **with its
assertion text**. **NFR-008**: print the input count beside any "all checks passed" — sites scanned,
files scanned, candidate sites considered.

## Files other agents hold

`tests/architectural/test_cli_console_render_width.py` and `tests/_arch_shard_map.py` are **WP03's** —
this WP adds **no new file** under `tests/architectural/`, so it needs no shard-map row.
`tests/architectural/_gate_coverage_baseline.json` is **nobody's**.
`kitty-specs/journal-project-consent-3030-01KYKWQS/**` is **nobody's** (C-010) — the cross-reference is
one-directional. `src/**` is nobody's: FR-015's matcher logic lives in a **test module**, which is why
this mission's "no production behaviour change" gate still passes.
