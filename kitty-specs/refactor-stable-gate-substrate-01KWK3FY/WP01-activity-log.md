---
work_package_id: WP01
title: Resolution-gate Design-P conversion
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: tidy/gate-substrate
merge_target_branch: tidy/gate-substrate
branch_strategy: Planning artifacts for this mission were generated on tidy/gate-substrate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/gate-substrate unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Parallel substrate work
assignee: ''
agent: "claude:opus:python-pedro:implementer"
shell_pid: "1660876"
history:
- at: '2026-07-03T06:37:42Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_resolution_authority_gates.py
- tests/architectural/resolution_gate_allowlist.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Resolution-gate Design-P conversion

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Convert the LAST raw-line-keyed architectural gate to **Design-P** (spec FR-001/002/003;
the mission ADR): the stored comparand becomes the frozen tool-derived
`(rel_path, qualname, token)`; the YAML `line:` survives only as a non-authoritative
diagnostics locator; the live scanners emit matching composite keys with NO
`node.lineno` feeding any comparison. All 10 entries (3 canonicalizer + 7
coord_authority). Success = the theater TRIAD at BOTH top-level entry points:
+1-line drift → green; token edit to an allowlisted site → RED (staleness); synthetic
new offender → RED.

## Context & Constraints

Read FIRST (mission dir = kitty-specs/refactor-stable-gate-substrate-01KWK3FY/):
- `contracts/gate-conversion-contract.md` — ALL seven rules are binding.
- `research.md` D1 (why Design-P: renata's Scenario A/B proof — seed re-derivation is
  content-following and fails BOTH required properties; do not relitigate) + D2 (gate
  anatomy: every construction/comparison site enumerated).
- `data-model.md` — the converted key schema, YAML entry shape, and the
  within-function collision rule (`count:` qualifier).
- The Design-P reference implementation: `tests/architectural/test_no_worktree_name_guess.py`
  (`_ALLOWED_SITES_FILES` frozen composites :92 + staleness guard
  `test_name_compose_offenders_match_pinned_baseline` :420 + drift theater
  `test_composite_key_survives_line_drift` :936) —
  READ-ONLY inspiration; do not modify it (WP06 documents it).
- The composite primitives: `tests/architectural/_ratchet_keys.py`
  (`composite_key_from_file`, `code_tokens_by_line`, `enclosing_qualname`).

Constraints: C-001 (this WP's own theater tests are negative/behavioral — no literal
scans, no size checks); tokens are TOOL-derived, never hand-typed (contract rule 2);
`mypy --strict` clean at every commit (the type change cascades — convert everything
in this WP).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: tidy/gate-substrate
- **Merge target branch**: tidy/gate-substrate

## Subtasks & Detailed Guidance

### Subtask T001 – Fail-closed freeze converter → rewrite the 10 YAML entries

- **Purpose**: One-time tool-derivation of the frozen comparands (contract rules 2+6).
- **Steps**:
  1. Write a throwaway converter script (keep it in the mission dir as
     `kitty-specs/refactor-stable-gate-substrate-01KWK3FY/freeze_converter.py` for the
     record — it is NOT shipped tooling): for each current YAML entry, resolve
     `(qualname, line)` against the live source via `composite_key_from_file`;
     ABORT loudly if the seed resolves to `<module>` scope, an empty token, a qualname
     mismatch with the YAML's recorded qualname, or an unparseable file.
  2. Rewrite `tests/architectural/resolution_gate_allowlist.yaml`: each entry gains
     `file:` (repo-relative source path) and `token:` (the frozen string); `line:`
     stays as the locator; `reason:` unchanged. Add a header comment documenting the
     Design-P semantics + the freshen procedure (re-run the gate; it prints the
     replacement token on staleness).
  3. Determine each entry's `file:` from the gate's scanner scope (research D2: the
     qualname collisions `implement`/`review` — the file disambiguates them; derive
     the correct file per entry from the CURRENT scanner output, not guesswork).
- **Files**: the YAML + the recorded converter.

### Subtask T002 – GateAllowlistKey conversion + loader

- **Steps**:
  1. `GateAllowlistKey` becomes `(rel_path: str, enclosing_qualname: str, token: str)`
     (rename `token_line` — it no longer holds a line; a straight rename to `token`
     keeps grep-honesty).
  2. `load_allowlist` reads `file:`/`qualname:`/`token:` (the frozen comparand is read,
     NEVER re-derived at load — contract rule 1); `line:` is parsed into a separate
     locator map used only for messages.
  3. Staleness path: if a loaded key has no live match after the scan, the gate FAILS
     with the evict-or-re-approve message including the nearest live token for that
     qualname (freshen ergonomics).
- **Files**: `tests/architectural/test_resolution_authority_gates.py`.

### Subtask T003 – Scanners emit composite keys; diagnostics locator kept

- **Steps**:
  1. `scan_canonicalizer_call_sites` (:455 region) and `scan_coord_authority_call_sites`
     (:597 region) emit `GateAllowlistKey(rel_path, qualname, code_tokens_by_line(src)[node.lineno])` —
     `node.lineno` is used ONLY to index the token map and to carry the message locator,
     never stored in the key.
  2. `derive_live_key` (:270) converts to the same shape.
  3. Violation messages keep `{rel_path}:{lineno} ({qualname})` (live lineno from the
     scan — always fresh) + the token excerpt.
  4. Post-check: `grep -n "node.lineno" tests/architectural/test_resolution_authority_gates.py`
     shows lineno used only for token-map indexing/messages (record in Activity Log).
- **Files**: same file.

### Subtask T004 – Re-pin the int-line test constructors + derive_live_key unit tests

- **Steps**: The **10** constructors in the :645-647/:714-722/:1034/:1069 regions
  (`GateAllowlistKey("MarkStatusCmd.run", 100)` style) and the `test_derive_live_key_*`
  unit tests re-pin to token semantics (`GateAllowlistKey("f.py", "MarkStatusCmd.run",
  "x = 1")` style — synthetic tokens fine in unit tests OF the mechanism; they are not
  allowlist entries). `mypy --strict` on the file must be clean.
- **Files**: same file.

### Subtask T005 – Theater TRIAD + staleness-guard semantics

- **Steps** (contract rule 4 — all legs drive `check_canonicalizer_gate` /
  `check_coord_authority_gate` with synthetic source + a loaded allowlist, exactly the
  T005-self-mutation model already in the file):
  1. **Drift leg**: synthetic module containing an allowlisted-shaped site; freeze its
     key; insert a blank line ABOVE the site; run the check → 0 violations.
  2. **Content leg** (entry-point rule, squad hardening): the synthetic allowlisted
     site MUST be violation-class (a non-canonical/write call — the same class the
     T005 self-mutation tests already inject), so the token edit reds
     `check_*_gate` ITSELF (allowlist key no longer matches → the site reports as a
     violation). The separate staleness twin-guard (`test_staleness_twin_guard_*`)
     is ALSO updated/kept as the standing CI assertion — but the theater leg's
     assertion target is the entry point, never a helper.
  3. **New-offender leg**: add a second, un-allowlisted offending call → gate fails
     naming it.
  4. Cover BOTH entry points (parametrize or mirror).
  5. Within-function collision test — BIDIRECTIONAL (squad hardening): `count: 2`
     with 2 live identical-token sites → green, AND the same entry with only 1
     matching live site (or `count: 1` vs 2 sites) → RED. A green-only assertion is
     vacuous. Record in the design tracer that `count:` has zero real users today
     (speculative surface for the future drain — deliberate).
  6. Freeze-converter fail-closed proof (squad hardening): run the converter ONCE
     against a deliberately broken seed fixture (module-scope line / empty token)
     and paste the abort output into the Activity Log — fail-closed is demonstrated,
     not asserted.
- **Files**: same file (new test functions).

### Subtask T006 – WP01 validation sweep

- **Steps**: `PWHEADLESS=1 pytest tests/architectural/test_resolution_authority_gates.py -q`
  (everything incl. pre-existing tests green); `python -m mypy --strict
  tests/architectural/test_resolution_authority_gates.py` AND the whole-tree form
  `python -m mypy --strict src/specify_cli src/charter src/doctrine` (must stay at
  zero — the PR #2312 takeover just achieved whole-tree zero; do not regress it);
  `ruff check` on both owned files; a full `tests/architectural/` run to prove no
  neighbor broke.

## Test Strategy

```bash
export PATH="$PWD/.venv/bin:$PATH"; PYTHONPATH="$PWD/src"
PWHEADLESS=1 pytest tests/architectural/test_resolution_authority_gates.py -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
python -m mypy --strict tests/architectural/test_resolution_authority_gates.py
ruff check tests/architectural/test_resolution_authority_gates.py tests/architectural/resolution_gate_allowlist.yaml
```

## Risks & Mitigations

- **Wrong file: attribution during freeze** (the qualname-collision entries): derive
  from the live scanner output per entry — the converter cross-checks qualname AND
  that the derived token appears at the seed line; abort on mismatch.
- **Half-conversion** (a lineno comparand surviving on one side): the T003 post-check
  grep + the content-leg theater (which fails if the scanner side still keys on line).
- **Token churn ergonomics**: the staleness message MUST print the replacement token
  so legitimate site edits are a copy-paste freshen, not archaeology.

## Review Guidance

- Run the triad; verify each leg drives the top-level check functions (read the tests).
- **REJECT `str(node.lineno)` or any stringified-line token** — it passes mypy and the
  greps while silently re-introducing line coupling; the drift leg must insert a REAL
  blank line and stay green (a stringified-line implementation demonstrably reds it).
- Verify zero `node.lineno` in any stored/compared key (grep evidence in the log).
- Verify the YAML tokens match tool-derivation (spot-re-derive 3 entries with
  `composite_key_from_file` against the live tree).
- Whole-tree mypy still zero; fixtures/reasons untouched elsewhere.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T06:37:42Z – system – Prompt created.
- 2026-07-03T07:11:47Z – claude:opus:python-pedro:implementer – shell_pid=1660876 – Assigned agent via action command
- 2026-07-03T00:00:00Z – claude:opus:python-pedro:implementer – Loaded python-pedro profile. Converted the LAST raw-line-keyed architectural gate to Design-P. GateAllowlistKey is now `(rel_path, enclosing_qualname, token)`; the stored comparand is the frozen tool-derived `code_tokens_by_line` token; `line:` demoted to a non-authoritative locator (never compared/counted). Scanners emit composite keys; `node.lineno` is used ONLY to index the token map and to carry the message locator (post-check grep below). All 10 entries converted (3 canonicalizer + 7 coord_authority); NO key collisions — every `(file,qualname,token)` triple is unique, so `count:` has zero real users (speculative surface, pinned by `test_real_allowlist_declares_no_count_qualifiers`).
- 2026-07-03T00:00:01Z – claude:opus:python-pedro:implementer – FREEZE-CONVERTER (T001, throwaway; recorded at `kitty-specs/refactor-stable-gate-substrate-01KWK3FY/freeze_converter.py`). Tool-derived the 10 frozen tokens; wrote them to the YAML with no human keystroke (contract rule 2). Fail-closed PROOF (T005.6, `--demo-broken`, pasted verbatim):
    `[fail-closed OK] module-scope seed: canonicalizer: src/mission_runtime/resolution.py:1 resolves to <module> scope — refusing to freeze a module-scope seed (fail-closed)`
    `[fail-closed OK] no-live-match seed: canonicalizer: seed ('does_not_exist', 999999) matches NO live call site (unparseable file, drifted line, or renamed function) — cannot freeze`
- 2026-07-03T00:00:02Z – claude:opus:python-pedro:implementer – POST-CHECK grep (T003.4) `grep -n "node.lineno" tests/architectural/test_resolution_authority_gates.py`: appears ONLY at (a) `code_tokens_by_line(source).get(node.lineno,"")` token-map indexing in `derive_live_key`, (b) `token_map.get(node.lineno,"")` token-map indexing inside the two scanners' `GateAllowlistKey(...)` construction (yields the TOKEN, not a line), (c) `lineno=node.lineno` message-locator field on `CanonicalizerSite`/`CoordAuthoritySite`, (d) docstrings. Zero `node.lineno` in any stored/compared key. `grep "token_line\|str(...lineno)"` → NONE.
- 2026-07-03T00:00:03Z – claude:opus:python-pedro:implementer – VALIDATION. `pytest tests/architectural/test_resolution_authority_gates.py` → 45 passed (37 pre-existing re-keyed + 8 new: content leg + loader-token guard + staleness freshen-message + theater triad ×2 gates [3 legs] + bidirectional collision + count-surface pin). Full `tests/architectural/` → 618 passed, 4 skipped, 0 failed (no neighbor broke). `mypy --strict` on the gate file → clean. `ruff check` on the gate file → clean. Spot-re-derived 3 YAML tokens via `composite_key_from_file` against the live tree → all match. Theater TRIAD verified per gate: drift (+1 real blank line) → GREEN; token edit on the allowlisted violation-class site → RED at `check_*_gate` itself; new un-allowlisted offender → RED naming it.
- 2026-07-03T00:00:04Z – claude:opus:python-pedro:implementer – DEVIATIONS / pre-existing findings (report-only, NOT my diff): (1) Whole-tree `mypy --strict src/specify_cli src/charter src/doctrine` reports 37 errors in 6 src files (tasks_command_adapters.py, tasks_move_task.py, tasks_shared.py, tasks_status_cmd.py, _auth_doctor.py, core/paths.py) — PRE-EXISTING on the lane base (introduced by the prior tasks.py degod-wave2 work, commit 08db1736d on tidy/gate-substrate); my WP touches ZERO src/ (NFR-002 zero-production-diff holds), so this is not my regression and fixing it is outside this WP's authoritative surface (tests/architectural/). (2) The WP Test-Strategy `ruff check ... resolution_gate_allowlist.yaml` mis-parses YAML as Python and fails — the pre-existing HEAD YAML fails it identically (36 errors); ruff cannot lint YAML and its own directory discovery (`ruff check tests/architectural/`) correctly skips it and passes. Both flagged for the operator; neither is a WP01 regression.
