---
work_package_id: WP06
title: Re-key the line-pinned architectural ratchets
dependencies: []
requirement_refs:
- FR-008
- NFR-004
tracker_refs:
- '#2023'
planning_base_branch: feat/canonical-seams-path-trust-guard-capability
merge_target_branch: feat/canonical-seams-path-trust-guard-capability
branch_strategy: Planning artifacts for this mission were generated on feat/canonical-seams-path-trust-guard-capability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/canonical-seams-path-trust-guard-capability unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3713113"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_no_worktree_name_guess.py
create_intent:
- tests/architectural/_ratchet_keys.py
execution_mode: code_change
owned_files:
- tests/architectural/test_no_worktree_name_guess.py
- tests/architectural/_ratchet_keys.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read:
1. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/spec.md` — **FR-008, NFR-004**, **C-007**
   (the `status_transition.py:295` pin is OUT of scope).
2. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/research.md` — **§(f)/D-4** the exact pins.

> **CORRECTION (post-tasks squad, BINDING):** the qualname/AST machinery does **NOT** already exist. Verified:
> `test_no_write_side_rederivation.py::as_allow_key` returns `(path, lineno)` — it is **itself line-keyed**; only
> the **tokenize-based `_code_tokens_by_line` (token half)** exists there. The **enclosing-function-qualname
> resolution is net-new** and you must write it (via `ast.walk` + `FunctionDef.lineno` range mapping, or
> `ast.get_source_segment`). This WP is therefore **larger than a "reuse"** — budget for building the qualname
> layer. Do NOT claim to "lift existing qualname machinery"; there is none.

## Objective

Re-key the line-number-keyed allow-lists in `tests/architectural/test_no_worktree_name_guess.py` to a drift-proof
**enclosing-function-qualname + normalized-token-line** composite, so a `+1` line drift in a guarded source file
(e.g. `doctor.py`) no longer flips the ratchet RED with zero semantic change. Independent WP. (#2023 under #1931.)

**OUT of scope (C-007):** `test_no_write_side_rederivation._ALLOW_LIST` (`status_transition.py:295`) — a deliberate
#1716-blocked pin. Do NOT touch that file's allow-list.

## Subtasks

### T024 — Build the shared key module + re-key the allow-lists
**MANDATORY (ownership-clean):** Create `tests/architectural/_ratchet_keys.py` (owned by this WP) containing:
- `code_tokens_by_line(source)` — lifted from `test_no_write_side_rederivation.py::_code_tokens_by_line` (tokenize-based).
- `enclosing_qualname(source, lineno)` — **NET-NEW** (walk the `ast` tree, map each `FunctionDef`/`AsyncFunctionDef`/
  `ClassDef` lineno-range, return the dotted qualname enclosing `lineno`).
- Do **NOT** edit `test_no_write_side_rederivation.py` in this WP (it is C-007/`:295` out-of-scope — its private
  line-keyed copy stays; a follow-up may de-dupe it onto this module). Creating a second *inline* copy inside
  `test_no_worktree_name_guess.py` is the C-001 sin this mission fights — use the shared module.

In `tests/architectural/test_no_worktree_name_guess.py`:
- `_ALLOWED_SITES` (~:82) and `_SHORTID_ALLOWED_SITES` (~:619; the `doctor.py:3074`/`:3166` pins at ~:629/:630) are
  keyed `file:lineno`. Re-key each entry to `(enclosing_qualname, normalized-token-line)` via the shared module.
- The two `doctor.py` offenders are byte-identical (`short = resolve_mid8(...) or mission_id[:8]`), so the composite
  MUST include the qualname to disambiguate — a bare token-line key collides.
- Note `invocation/executor.py:469` is an `invocation_id[:8]` short-tag (a DIFFERENT identifier than mid8) — keep it
  keyed as its own distinct entry; do not mis-fold it into the mid8 sites.
- Keep the count baselines (`_NAME_COMPOSE_BASELINE_RAW_MATCHES`, the `_SHORTID` baseline) AND the per-site keys —
  do NOT collapse to a count-only baseline (loses per-site accountability; research.md §(f)).

### T025 — Executable drift + non-vacuity tests (NO "document" escape)
Write three EXECUTABLE tests (not prose):
1. **Drift-survives:** programmatically build a source string with a blank/comment line inserted ABOVE a pinned
   offender, run the scanner against it, assert the composite key is UNCHANGED (ratchet stays GREEN). Strike any
   "or document via the keying" option — it must actually drift the source and re-scan.
2. **New-offender-in-allowlisted-function flagged RED:** insert a NEW offending line INSIDE an allow-listed function
   (same qualname, DIFFERENT token-line) → assert it is NOT matched by the allow-list (flagged). This proves the
   token-line component is load-bearing (the key isn't vacuous/too-loose).
3. **Distinct-keys:** assert the two `doctor.py` sites produce DISTINCT composite keys (a qualname-less/colliding
   implementation fails this).

### T026 — Leave `:295` untouched (executable check); preserve accountability
- `test_no_write_side_rederivation.py` must be byte-unchanged. Prove it, don't assert it in prose: in the handoff,
  paste `git diff --stat -- tests/architectural/test_no_write_side_rederivation.py` showing **zero** lines changed
  (it is not in `owned_files`). The T025 #2 non-vacuity test is the per-site-accountability proof.

### T027 — Quality gate
- `ruff`+`mypy` clean on the test file (≤15, no suppressions).
- The re-keyed ratchet + its stale-detection meta-tests + the new drift test all green.

## Branch Strategy

Planning/merge base `feat/canonical-seams-path-trust-guard-capability` (PR → main). Worktree per lane from
`lanes.json`. **No dependencies — parallel with WP01/WP03/WP05.**

## Definition of Done

- [ ] `tests/architectural/_ratchet_keys.py` created with `code_tokens_by_line` (lifted) + `enclosing_qualname` (net-new ast).
- [ ] `_ALLOWED_SITES` + `_SHORTID_ALLOWED_SITES` re-keyed to (qualname, normalized-token-line) composites via the shared module.
- [ ] Count baselines + per-site keys both retained (no count-only collapse); `invocation/executor.py` kept as its own distinct entry.
- [ ] Three executable tests pass: drift-survives, new-offender-in-allowlisted-function-flagged-RED, distinct-keys-for-the-two-doctor-sites.
- [ ] `git diff --stat` proves `test_no_write_side_rederivation.py` byte-unchanged (`:295` untouched).
- [ ] `ruff`+`mypy` clean; existing ratchet/stale-detection tests green.

## Risks / reviewer guidance

- **Qualname disambiguation is mandatory** — the two `doctor.py` pins are byte-identical; a token-only key collides.
  Reviewer: verify the composite includes the enclosing-function qualname.
- **Don't weaken the ratchet** — re-keying must keep catching genuine new offenders (T026). A re-key that makes the
  ratchet vacuous (e.g. matching too loosely) is a review rejection.
- **Shared helper:** if lifting the token machinery from the sibling test, do NOT create a second parallel copy
  (that re-introduces the duplication this mission fights) — extract to one shared location both reference.
- C-007: confirm `:295` / `test_no_write_side_rederivation.py` is genuinely untouched.

## Activity Log

- 2026-06-17T20:17:02Z – claude:sonnet:python-pedro:implementer – shell_pid=3633670 – Assigned agent via action command
- 2026-06-17T20:34:12Z – user – shell_pid=3633670 – Moved to claimed
- 2026-06-17T20:34:17Z – user – shell_pid=3633670 – Moved to in_progress
- 2026-06-17T20:36:22Z – claude:sonnet:python-pedro:implementer – shell_pid=3633670 – WP06 implementation complete: _ratchet_keys.py created + allow-lists re-keyed to (qualname, token_line) composites. 11/12 tests GREEN (1 pre-existing NFR-001). ruff+mypy clean. test_no_write_side_rederivation.py byte-unchanged.
- 2026-06-17T20:38:07Z – user – shell_pid=3633670 – Moved to claimed
- 2026-06-17T20:38:14Z – user – shell_pid=3633670 – Moved to in_progress
- 2026-06-17T20:38:24Z – claude:sonnet:python-pedro:implementer – shell_pid=3633670 – Ready for review: _ratchet_keys.py (code_tokens_by_line + enclosing_qualname). All allow-lists re-keyed to (qualname, token_line) composites. 3 executable drift/non-vacuity tests pass. ruff+mypy clean. test_no_write_side_rederivation.py byte-unchanged. 11/12 GREEN (1 pre-existing NFR-001).
- 2026-06-17T20:40:26Z – claude:opus:reviewer-renata:reviewer – shell_pid=3713113 – Started review via action command
- 2026-06-17T20:43:51Z – user – shell_pid=3713113 – Review passed: _ratchet_keys.py created with real ast-walking enclosing_qualname + lifted code_tokens_by_line + composite_key. Allow-lists re-keyed to (qualname, normalized-token-line) composites; executor.py kept as distinct named exclusion; count baselines retained. 3 executable tests non-vacuous and pass (drift-survives, new-offender-in-allowlisted-fn flagged RED proving token-line load-bearing, distinct-keys for byte-identical doctor.py sites). test_no_write_side_rederivation.py byte-unchanged (C-007). ruff+mypy clean. 11/12 pass; sole failure test_nfr001_consolidation... is pre-existing cross-mission status/ contamination (write-side-01KV9W0X/01KV0S99), NOT WP06 — WP06 lane diff touches zero status/ files.
