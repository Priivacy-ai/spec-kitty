---
work_package_id: WP03
title: Charter status JSON-safe + landed-fix pins
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-008
- NFR-006
tracker_refs:
- '#2009'
planning_base_branch: feat/governed-state-surface-coherence
merge_target_branch: feat/governed-state-surface-coherence
branch_strategy: Planning artifacts for this mission were generated on feat/governed-state-surface-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/governed-state-surface-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4126867"
history:
- 2026-06-18 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/charter/
create_intent:
- tests/specify_cli/cli/commands/charter/test_status_json_safe.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/charter/_status_collectors.py
- src/specify_cli/cli/commands/charter/status.py
- tests/specify_cli/cli/commands/charter/test_status_json_safe.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any code, load the implementer profile and binding context. Run:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order:
1. `kitty-specs/governed-state-surface-coherence-01KVCGQC/spec.md` — **FR-005, FR-008, NFR-006, C-003**.
2. `kitty-specs/governed-state-surface-coherence-01KVCGQC/research.md` — Goal B table (C2-a/C2-d ALREADY landed → **pin, don't redo**; C2-b is the live fix).

## Objective

Two things on the **charter status read path** (a read-only governed-state surface):
1. **FR-005 (C2-b, live):** `charter status --json` raises `TypeError: Object of type datetime is not JSON serializable` when the bundle `metadata.yaml` carries an unquoted ISO datetime (parsed to a `datetime` by `YAML(typ="safe")`). Make the JSON path serialize safely.
2. **FR-008a (pin):** C2-a (status side-effect-free) **already landed** (`f892894e2`) — add a regression test that **pins** it so it cannot silently re-drift. Verify-don't-redo: do NOT re-implement.

> ⚠️ **Exact coordinates (squad-pedro — the WP must not misdirect):** the collector maps `metadata.get("timestamp_utc") or metadata.get("extracted_at")` → the payload's **`last_sync`** field (`_status_collectors.py` ~:76-78). The crashing input key is **`timestamp_utc`** (or `extracted_at`), NOT a key literally named `last_sync` — a fixture keyed on `last_sync` would be IGNORED and the RED step would silently pass. The serialization call is `print(json.dumps(payload, indent=2))` in `status.py` (~:74) — no `default=str`. Verify both line numbers live before editing (they may drift).
>
> **Note (squad-paula):** the **C2-d hash-unification pin (formerly T023) has MOVED to WP04**, co-located with `computer._charter_hash_of` and the C2-e (FR-009) hash-drift work it depends on. WP03 now covers FR-005 + FR-008a only.

**NFR-006 / C-003 (binding):** `charter status` MUST stay a read-only consumer — invoke no mutator (`ensure_charter_bundle_fresh`, `GlossaryEntityPageRenderer.generate_all`, `sync`) and compute no second freshness hash.

## Subtasks

### T020 — Failing-first test for the datetime crash (TDD, FR-005)

**Steps:**
1. Create `tests/specify_cli/cli/commands/charter/test_status_json_safe.py`.
2. Build a topology-true charter bundle fixture whose `metadata.yaml` has an **unquoted** ISO datetime under **`timestamp_utc`** (the key the collector actually reads — NOT `last_sync`), so `YAML(typ="safe")` yields a `datetime`. Use realistic values.
3. Invoke `charter status --json` (via the CLI runner or the collector + `status.py` serialization path) and assert it currently raises `TypeError` / non-zero — RED. **Sanity-check the fixture reproduces the crash before writing the fix** (if it doesn't, the key is wrong — confirm `timestamp_utc`/`extracted_at`).

**Validation:** test RED with the datetime `TypeError`, driven by `timestamp_utc`.

### T021 — JSON-safe serialization (FR-005, F9)

**Steps:**
1. **Prefer collector-side normalization:** in `_status_collectors.py`, normalize the datetime → ISO string before it enters the payload (stable string-typed contract). `json.dumps(payload, indent=2, default=str)` in `status.py` is an acceptable fallback ONLY if the test additionally asserts the field is a string (do not rely on blanket coercion masking future non-serializable values).
2. Keep the human-readable (non-JSON) status path unchanged. Do NOT change what the status reports — only make it serializable.

**Validation:** T020 now green — `charter status --json` returns valid, parseable JSON (exit 0) on the `timestamp_utc` fixture (SC-002), and the test asserts `last_sync` in the JSON output is a **string** (F9 — not just "didn't crash").

### T022 — Pin C2-a: status read path has no mutator (FR-008a, NFR-006)

**Steps:**
1. Add a regression test asserting `_collect_charter_sync_status` (and the status command path) does NOT call `ensure_charter_bundle_fresh` or `GlossaryEntityPageRenderer.generate_all` — e.g. monkeypatch those to raise and assert status still succeeds, or assert via `mock` that they are not invoked.
2. This pins the already-landed `f892894e2` fix against re-drift.

**Validation:** test green; if someone reintroduces a mutator call in the read path, this test fails.

## Branch Strategy

Planning branch `feat/governed-state-surface-coherence`; merge target `main` (PR). Depends on **WP01** (green CI base only — no code interaction). Independent of WP02/WP04/WP05 (disjoint owned_files). Worktree per `lanes.json`.

## Definition of Done

- [ ] `charter status --json` returns valid JSON on a `timestamp_utc`-datetime `metadata.yaml` (SC-002); T020 RED driven by `timestamp_utc`, then green; `last_sync` is string-typed in the JSON (F9).
- [ ] C2-a pinned (no mutator in status read path — NFR-006). (C2-d hash pin lives in WP04.)
- [ ] Status report semantics unchanged (only serialization made safe).
- [ ] ruff + mypy clean ≤15, zero new suppressions.
- [ ] **#2009 issue-matrix row set to `in-mission`** (NOT terminal) — #2009 spans WP03 (C2-b/C2-a) + WP04 (C2-d/C2-f/C2-e); only the later-merged of WP03/WP04 flips it to a terminal verdict (squad-paula).
- [ ] #2009 carries a tracker comment naming mission `01KVCGQC` (SC-007).

## Reviewer Guidance

Confirm: the RED fixture uses `timestamp_utc` (not `last_sync`) and genuinely reproduced the crash; the fix only touched serialization (status still reports the same fields) and `last_sync` is string-typed (not a blanket `default=str` masking other types); no mutator was added to the read path (grep `ensure_charter_bundle_fresh`/`generate_all`/`sync` in the status path — none); the C2-a pin fails if a mutator is reintroduced (not tautological). #2009 left `in-mission` unless this is the later-merged half.

## Activity Log

- 2026-06-18T06:20:38Z – claude:sonnet:python-pedro:implementer – shell_pid=4098966 – Assigned agent via action command
- 2026-06-18T06:28:19Z – claude:sonnet:python-pedro:implementer – shell_pid=4098966 – FR-005: collector-side ISO normalization of metadata timestamp_utc/extracted_at -> string-typed last_sync; RED reproduced the datetime TypeError via unquoted timestamp_utc end-to-end through charter status --json. FR-008a: pinned C2-a side-effect-free read path (no ensure_charter_bundle_fresh/generate_all). ruff clean; mypy clean on touched collector.
- 2026-06-18T06:28:49Z – claude:opus:reviewer-renata:reviewer – shell_pid=4126867 – Started review via action command
- 2026-06-18T06:34:07Z – user – shell_pid=4126867 – FR-005: RED reproduced end-to-end via unquoted timestamp_utc fixture (datetime TypeError, verified by reverting fix to base). Fix is collector-side ISO normalization (_normalize_last_sync, live caller, no blanket default=str); test asserts last_sync is string-typed (F9). FR-008a/NFR-006: C2-a pin non-tautological — verified pin tests FAIL when a mutator (from-import shape) is reintroduced into the read path; C2-a NOT re-implemented (already landed f892894e2, verify-don't-redo). status.py untouched. ruff+mypy clean on collector. Scope WP03=FR-005+FR-008a only; FR-008b correctly absent. #2009 stays in-mission.
