---
work_package_id: WP04
title: '`decision` single authority'
dependencies:
- WP01
requirement_refs:
- FR-003
tracker_refs: []
planning_base_branch: feat/read-path-error-fidelity
merge_target_branch: feat/read-path-error-fidelity
branch_strategy: Planning artifacts for this mission were generated on feat/read-path-error-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-path-error-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T043
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2566958"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/decision.py
create_intent:
- tests/specify_cli/cli/commands/test_decision_single_authority.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/decision.py
- tests/specify_cli/cli/commands/test_decision_single_authority.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any code, load the implementer profile so your identity, governance scope, and
boundaries are active for this session:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order, so the behavior you implement matches the canonical intent:

- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/spec.md` — FR-003; US-2; SC-002; the
  issue-matrix rows for **#8** and **#1889** (folded-in GitHub tracker).
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/plan.md` — IC-04 (purpose, affected
  surfaces, risks), decision **D-4**, and the sequencing note (WP04 depends on WP01).
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/contracts/behavioral-contracts.md` —
  **C-IC03** (`decision open` single authority) is your acceptance contract.
- `research/live-repro.md` — repro **#8** (note the correction: the live failure is an **uncaught
  `ActionContextError` traceback**, not the escape-check string — the escape-check is masked by the
  earlier crash but is still the dead second authority to delete).
- `research/call-site-inventory.md` — call-sites **C6, C7**, §3 "decision.py dual authority —
  DEFINITIVE", and the §6 line-number drift table (treat §6 as authoritative over any earlier cite).

## Objective

Make `decision open` (and the helper `cmd_verify` shares) resolve mission handles through the
**single** canonical read-path authority, satisfying **FR-003**:

1. Delete the primary-anchored **escape-walk for resolved paths** in `_resolve_repo_root_and_slug`
   (`decision.py:57-119`, walk `:86-97`, escape-check `:101-109`), which rejects a legitimate
   coord-worktree path the resolver returns.
2. Derive `repo_root` from the **canonical root authority** rather than a private 20-level walk.
3. Structure the typed `ActionContextError` so it surfaces as a **structured diagnostic**, not a raw
   Python traceback (`decision.py:103` calls `resolve_feature_dir_for_mission` →
   `resolve_action_context`, which raises uncaught on HEAD).
4. Keep `_SAFE_SLUG_RE` (`decision.py:79`) traversal-rejection on the **raw operator token only**.

`cmd_verify` (C7) shares `_resolve_repo_root_and_slug`, so that part of the fix lands **once**.
**However (M5 — SHOULD-FIX, do NOT drop):** `cmd_verify` ALSO has its **OWN** primary-only
`load_meta` pre-read seeding `resolve_mid8` at `decision.py:421` and its **OWN uncaught**
`resolve_mission_read_path` at `:425` — the **same #8 uncaught-traceback class** WP04 deletes on
`cmd_open` (`:103`), left live on `verify`. WP04 already owns `decision.py`, so it MUST also structure
the typed error on the `verify` path (no ownership change). Confirm verify still works AND no longer
crashes raw on a coord topology.

## Context

**C-001: adopt, do not build.** `decision open` is **NOT a second resolver** — it is a
**root-determination + escape-validation** wrapper around the correct coord-aware resolver
(`resolve_feature_dir_for_mission` → `resolve_action_context`). The fix removes the redundant
escape-walk, not the resolver. No new resolver, root authority, or error type (DIR-031: pure
bounded-context translation).

**The dual-authority leak (call-site-inventory §3, DEFINITIVE).** `repo_root` is derived by a private
walk to `kitty-specs/` (`:86-97`); the resolved mission dir is then asserted to live under
`repo_root/kitty-specs/` (`:101-109`). Because `resolve_feature_dir_for_mission` returns a
**coord-worktree** path (`.worktrees/<slug>-<mid8>-coord/kitty-specs/…`) while `repo_root` is the
**primary** checkout, the `startswith(base)` check at `:105` fails → `"Mission path would escape
kitty-specs/"`. Two anchors (primary base vs coord resolved path), one decision — the textbook
bounded-context leak. On the binary the escape-check is **never reached** because the earlier
`resolve_feature_dir_for_mission` call (`:103`) raises uncaught — so BOTH the dead escape-walk must
go AND the typed error must be caught and structured.

**Function-over-form + verification-by-deletion.** The proof of adoption is that **removing the
escape-walk for resolved paths keeps both coord and primary handles working** (C-IC03 deletion proof).
Tests assert observable behavior (a coord handle succeeds; a traversal token is rejected; no raw
traceback), not internal structure.

**TDD-first (C-002).** #8 reproduces on HEAD — write the failing test first (a coord-aware handle
currently crashes with a traceback), watch it fail for the real symptom from `live-repro.md#8`, then
make it pass.

**Topology-true fixtures (NFR-002 — binding).** Use production-shaped data only: full **26-char ULID**
`mission_id`, the **coord-declared-no-worktree** topology (meta.json declares `coordination_branch`,
no coord branch/worktree materialized) — the exact `/tmp/debbie-coord` fixture from repro #8. No
fabricated short ids, no single-repo stand-in.

**Quality gates (NFR-004).** New/changed code passes `ruff` and `mypy` with zero issues, complexity
≤ 15, **no suppressions**. No `# noqa`/`# type: ignore` additions.

## Subtasks

### T020 — TDD: decision open accepts coord handle; traversal token rejected
- Write `tests/specify_cli/cli/commands/test_decision_single_authority.py` (NEW).
- Case A (coord-aware handle): build the topology-true coord-declared fixture (full ULID, meta.json
  declares the coordination branch). Invoke `agent decision open --mission <slug> --flow plan
  --input-key approach --question "Which approach?" --options '["a","b"]' --json` and assert it
  resolves through the single canonical authority — **no** `"Mission path would escape kitty-specs/"`
  and **no raw `ActionContextError` traceback**. Mirror `research/live-repro.md#8`.
- Case B (traversal token): pass a raw operator token containing `../` or path traversal; assert it is
  **still rejected** by `_SAFE_SLUG_RE` (`decision.py:79`).
- Case C (read-path miss): on a coord-declared-no-worktree topology where the resolver genuinely cannot
  resolve, assert the failure surfaces as a **structured typed error** (the resolver's `code`), not a
  traceback.
- **Validation:** Cases A and C FAIL first (uncaught traceback on HEAD per repro #8); Case B passes.

### T021 — Delete escape-walk for resolved paths; repo_root from canonical authority
- In `_resolve_repo_root_and_slug` (`decision.py:57-119`): **delete** the private walk-up-to-`kitty-specs/`
  (`:86-97`) and the escape-check assertion for **resolved** paths (`:101-109`).
- Derive `repo_root` from the **canonical root authority** (the same authority the resolver uses), not a
  private walk — so the primary base and the resolver's coord-aware resolved path agree.
- **DO NOT** delete `_SAFE_SLUG_RE` traversal-rejection on the raw operator token (`:79`) — it stays
  (DIR-031: validate the raw input boundary, not the resolved output).
- **Validation:** T020 Case A passes (coord handle resolves); Case B still rejects the traversal token.

### T022 — Structure the typed error (no raw traceback) at decision.py:103
- Wrap the `resolve_feature_dir_for_mission(...)` call (`decision.py:103`) in a `try/except
  ActionContextError` (the call routes `resolve_action_context` via `feature_dir_resolver.py:60` →
  `resolution.py:436`, which raises uncaught on HEAD).
- On `ActionContextError`, emit a **structured diagnostic** carrying the resolver's real `code` (and
  checked paths where the `--json` envelope supports it) — NOT a raw Rich traceback. Mirror the
  reference pattern in `agent context resolve` (`agent/context.py:158`, the GOOD citizen — copy it).
- **Validation:** T020 Case C passes (structured typed error, not a traceback); `ruff`/`mypy` clean.

### T023 — Keep _SAFE_SLUG_RE on raw token; confirm cmd_verify unaffected
- Confirm `_SAFE_SLUG_RE` (`decision.py:79`) still rejects traversal in the raw operator token (T020
  Case B regression).
- `cmd_verify` (C7, `decision.py:408` + canonical resolver at `:425`) shares
  `_resolve_repo_root_and_slug` — exercise it after the helper change and assert verify still resolves
  a valid handle and rejects a traversal token.
- **Validation:** verify path green; traversal-token rejection preserved on both `open` and `verify`.

### T043 — Structure the typed error on cmd_verify too (M5; verify's own seam)
- **M5 (SHOULD-FIX — do NOT drop):** `cmd_verify` has its OWN primary-only `load_meta` pre-read seeding
  `resolve_mid8` at `decision.py:421` and its OWN **uncaught** `resolve_mission_read_path` at `:425`
  (the same #8 uncaught-traceback class deleted on `cmd_open` at `:103`). Structure THAT raise too:
  wrap the `verify` resolver call in a `try/except ActionContextError` and emit a **structured typed
  diagnostic** (the resolver's real `code`), not a raw traceback — mirroring T022 / `agent context
  resolve` (`agent/context.py:158`). Where appropriate, route identity through the WP01 factory
  boundary instead of the primary-only empty-identity pre-read (D-6), matching the `decision.py:421`
  primitive pattern.
- **TDD — Case D (coord handle for `decision verify`):** add a `decision verify` test on the
  coord-declared topology that FAILS FIRST on HEAD with the uncaught `ActionContextError` traceback at
  `:425` (capture the red into the Activity Log), and passes after — surfacing the structured typed
  code, not a traceback.
- **file:line:** `cmd_verify` def `~:398` (NOT `:408`); `resolve_mission_read_path` call `~:425` (the
  primary-only pre-read at `~:421`). Re-locate by symbol.
- **Validation:** Case D passes after the fix; `ruff`/`mypy` clean; complexity ≤ 15.

## Branch Strategy

Planning artifacts were generated on `feat/read-path-error-fidelity`. During
`/spec-kitty.implement` this WP may branch from a dependency-specific base (it depends on WP01), but
completed changes merge back into `feat/read-path-error-fidelity` unless the human explicitly
redirects the landing branch. Do not push to `origin/main`; the mission lands via PR.

## Definition of Done

- [ ] `/ad-hoc-profile-load python-pedro` invoked; spec/plan/contracts/research read.
- [ ] **T020–T021 (FR-003):** the escape-walk for resolved paths is **deleted**; `repo_root` derives
      from the canonical root authority; a valid coord-aware handle resolves through the single
      authority and no longer hits `"Mission path would escape kitty-specs/"`.
- [ ] **T022:** the `ActionContextError` at `decision.py:103` is caught and rendered as a **structured
      typed diagnostic** (real `code`), not a raw traceback — mirroring `agent context resolve`.
- [ ] **T023:** `_SAFE_SLUG_RE` traversal-rejection on the **raw operator token** is preserved; the
      shared `cmd_verify` still resolves valid handles and rejects traversal (fix landed once).
- [ ] **T043 (M5):** `cmd_verify`'s OWN uncaught `resolve_mission_read_path` raise at `decision.py:425`
      (seeded by its primary-only `load_meta` pre-read at `:421`) is structured as a typed diagnostic
      (real `code`), not a raw traceback; a `decision verify` coord-handle test (Case D) FAILED FIRST
      on HEAD with the uncaught traceback (captured red) and passes after. The #8 crash class is gone
      on **both** `open` and `verify`.
- [ ] All new tests use topology-true fixtures (full 26-char ULID, coord-declared topology).
- [ ] The #8 fix landed **test-first** and the test failed for the real symptom (uncaught traceback)
      before the fix.
- [ ] **Verification-by-deletion:** removing the escape-walk keeps both coord and primary handles
      working and the suite green.
- [ ] `ruff` and `mypy` clean on changed code; complexity ≤ 15; no `# noqa`/`# type: ignore` added.
- [ ] Suite green (`PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_decision_single_authority.py tests/specify_cli/cli/commands/ -k decision -n0 -q`).

## Risks / reviewer guidance

- **The live symptom is an uncaught traceback, not the escape-check string** (repro #8 correction).
  The escape-check is masked by the earlier crash but is still the dead second authority FR-003 wants
  deleted — a reviewer must confirm BOTH happened (escape-walk deleted AND the typed error structured).
- **`_SAFE_SLUG_RE` must stay.** Deleting traversal-rejection on the raw token would be a security
  regression. The deletion target is the escape-walk on the **resolved** path only (DIR-031: validate
  input, trust the resolver's output).
- **`cmd_verify` shares the helper** — the fix lands once, but verify must be re-exercised; a reviewer
  should see a verify regression test, not just an `open` test.
- **Copy `agent context resolve`** (`agent/context.py:158`) for the typed-error structuring — it is the
  reference GOOD citizen; do not invent a new error envelope (C-001).
- **Line numbers** are from HEAD `87697e5e4` per §6 (authoritative); re-locate by symbol after WP01.
- Consume WP01's frozen context / canonical root authority; never re-derive identity here (D-6).

## Activity Log

- 2026-06-16 — Prompt generated via /spec-kitty.tasks (IC-04; FR-003; #8/#1889; C6/C7).
- 2026-06-16T21:03:46Z – claude:opus:python-pedro:implementer – shell_pid=2432976 – Assigned agent via action command
- 2026-06-16T21:24:15Z – claude:opus:python-pedro:implementer – shell_pid=2432976 – retry
- 2026-06-16T21:25:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=2566958 – Started review via action command
- 2026-06-16T21:31:19Z – user – shell_pid=2566958 – Review PASS (renata): escape-walk deleted + canonical root authority; structured typed error on open+verify(M5); captured-red verified; stash-integrity clean
