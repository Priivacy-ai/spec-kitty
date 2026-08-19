---
work_package_id: WP07
title: Store-report core + authority adapters
dependencies:
- WP06
requirement_refs:
- C-002
- C-007
- FR-002
- FR-004
planning_base_branch: refactor/wave4-sync-degod
merge_target_branch: refactor/wave4-sync-degod
branch_strategy: Planning artifacts for this mission were generated on refactor/wave4-sync-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/wave4-sync-degod unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
history:
- Created by /spec-kitty.tasks (Wave-4 sync degod)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- src/specify_cli/sync/sync_store_report_core.py
- src/specify_cli/sync/sync_authority.py
- tests/architectural/test_sync_two_authority.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/sync/sync_store_report_core.py
- src/specify_cli/sync/sync_authority.py
- tests/architectural/test_sync_two_authority.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```bash
/ad-hoc-profile-load python-pedro
spec-kitty charter context --action implement --json
```

State which profile loaded and which doctrine constraints apply — this WP leans hard
on `DIRECTIVE_044` (single canonical authority; adapters **delegate**, never
re-implement) and `DIRECTIVE_001`/`043` (the new two-authority arch-test is a gate).
Also expect `DIRECTIVE_025` campsite and the ATDD-first tactic. If profile load fails,
stop and report.

## Objective

Two coupled extractions that must land **before the `status`/`doctor` monsters** (WP09/
WP10 consume them):

1. **T014 — `sync_store_report_core.py`**: split the **three shared render+`issues`
   helpers** — `_render_per_project_store` (used by **both** `status` **and** `doctor`),
   `_render_consent_readability`, `_render_tracker_egress` — into a **pure compute
   half** (row/issue derivation) that lands in the new core, and a **render half** (the
   Console emit) that calls the WP04 Render port. This decouples `status ↔ doctor`
   (pedro Pd-2): both currently share helpers that **print AND mutate `issues`**.

2. **T015 — `sync_authority.py`**: extract the authority adapters across **three
   surfaces** — READ, WRITE, delivery-ADMISSION — each a thin adapter that
   **delegates** to the canonical surface (`preflight` / `sharing_client` /
   `target_authority`). Author the FR-004 arch-test `test_sync_two_authority.py`.

**Zero behavior change.** Serial chain: WP06 → **WP07** → WP08 (edits the single
`sync.py`).

## Read first (source of truth)

- **`plan.md` IC-03** — the **THREE authorities** (architect A-2): READ, WRITE,
  delivery-ADMISSION. The invariant is **non-unification of ports/classes, not call
  flows**. `_open_project_dispatch_runtime` and `opt_out` legitimately mix read+write
  at the flow level and are **frozen verbatim (C-007)** — do NOT "purify" them.
  Adapters **delegate** to canonical surfaces (DIRECTIVE_044), never re-implement (A-3:
  the package already has ≥5 `*Authority*` surfaces — do not fork a new one).
- **`plan.md` IC-04** — the three shared render helpers' compute-half lands in
  `sync_store_report_core` **before** both degods (Pd-2); the shells call the
  render-half.
- **`plan.md` § "WP-translation guards"** — guard #1 (serial on `sync.py`), guard #6
  ("the FR-004 two-authority arch-test lands with the authority-port WP"), guard #8
  (test env).
- **`contracts/sync-cli-characterization-contract.md`** — rule 4 (two-authority test
  asserts distinct read/write port symbols, no shared authority class = INV-2),
  rules 2/3 (behavior-stable + ~60-seam co-gate).
- **`data-model.md`** — the `AuthorityGate` read/write/admission rows; **INV-2**
  (authority non-unification of ports/classes, not call flows). `test_sync_two_authority.py`
  is distinct from the existing `tests/architectural/test_2093_authority_invariant.py`.
- **Zero-behavior-change**: the golden protects every extraction; `status`/`doctor`
  goldens are frozen later (WP09/WP10) but the current per-project-store /
  consent / tracker suites (`test_sync_doctor_per_project_3030.py`,
  `test_sync_report_label_is_a_purge_selector_3030.py`) must stay green now.

## Environment

- Lane worktree from `lanes.json` (`spec-kitty implement WP07`; call it `$WT`). Rebase
  on the WP06-shrunk `sync.py` first (serial chain).
- Repo `.venv` is editable-installed against the **MAIN checkout** — run everything
  with `PYTHONPATH=$WT/src` and `$VENV/python`. Never bare `python`/`spec-kitty`
  (pyenv → wrong fork), never `uv run`.
- **Targeted tests**:

  ```bash
  SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 \
    PYTHONPATH=$WT/src $VENV/python -m pytest \
    tests/architectural/test_sync_two_authority.py \
    tests/architectural/test_2093_authority_invariant.py \
    tests/architectural/test_sync_writer_census.py \
    tests/characterization/test_sync_*.py \
    tests/cli/commands/test_sync_commands.py \
    tests/cli/commands/test_sync_doctor_per_project_3030.py \
    tests/sync/ src/specify_cli/sync/ -q -p no:cacheprovider
  ```

  `-n0` for daemon/real-port files. Fast `review.test_command` to avoid the claim-time
  full-suite hang.
- Lint/type changed files only via `$VENV/bin/ruff` / `$VENV/bin/mypy`,
  `PYTHONPATH=$WT/src`.

## Subtasks

### T014 — `sync_store_report_core.py`: compute half of the 3 shared render+issues helpers

Re-grep in `$WT` (WP06 shifted lines). Current anchors:

- **`_render_per_project_store`** — **L1609**; called by **`status` at L5583** and
  **`doctor` at L6200**. This is the coupling: one helper, two commands, prints and
  mutates `issues`.
- **`_render_consent_readability`** — **L1843** (called at doctor L6205).
- **`_render_tracker_egress`** — **L1989** (+ its row helper `_render_tracker_egress_row`
  **L1929**; called at doctor L6210).

Already-pure compute helpers these lean on (relocate into the core alongside the
compute halves): `_per_project_store_issues` (**L1454**), `_empty_selection_cause`
(**L1044**), `_unresolved_origin_clause` (**L1500**), `_event_sync_report` (**L1001**).

**The split:**
1. For each of the three helpers, carve out a **pure compute function** in
   `sync_store_report_core.py` that returns the derived rows/data + the list of issue
   strings (no `Console`, no `print`). Leave a **render function** that takes the
   computed data and emits via the WP04 Render port + extends the caller's `issues`.
2. Because `_render_per_project_store` feeds **both** `status` and `doctor`, the
   compute half must land here so WP09 (`status` core) and WP10 (`doctor` core) both
   import the **same** pure computation — that is the decoupling (Pd-2). Do not leave a
   status→doctor or doctor→status dependency.
3. Preserve exact output: the same rows, same issue strings, same order, same "No
   issues"/unhealthy summary text. This is a **compute/render split, not a rewrite** —
   the golden and the doctor/per-project suites pin the bytes.
4. Author focused unit tests for each new pure compute function (Sonar new-code
   coverage) with stub `PerProjectStoreReport` inputs — empty selection, unresolved
   origin, tracker egress local/hosted rows.

### T015 — `sync_authority.py`: three delegating authority surfaces + arch-test

Extract into `sync_authority.py` **three distinct adapter surfaces**, each delegating
to its canonical implementation — **never re-implementing** (DIRECTIVE_044 / A-3):

- **READ** authority → delegate to `specify_cli.sync.preflight.run_preflight` and the
  coord/owner-coherence guard `_require_daemon_owner_coherence` (**L1357**).
- **WRITE** authority (share/unshare/opt-in/opt-out) → delegate to
  `specify_cli.sync.sharing_client`.
- **delivery-ADMISSION** (read-shaped, bound to the dispatch path) → delegate to
  `specify_cli.sync.target_authority`, wrapping:
  `_assert_event_sync_runtime_authority` (**L620**),
  `_assert_delivery_target_matches_context` (**L653**),
  `_resolve_gated_receiver` (**L799**).

**Guards:**
1. **Delegate, do not re-implement.** Each adapter is a thin pass-through to the named
   canonical surface. Do not copy `preflight`/`sharing_client`/`target_authority`
   logic into `sync_authority.py`.
2. **Do NOT purify the mixed-authority flows.** `_open_project_dispatch_runtime`
   (moved to `sync_runtime.py` in WP05) and `opt_out` (**L2386**) irreducibly mix
   read+write at the flow level — they are **frozen verbatim (C-007)**. Relocating the
   admission asserts must not change how those flows call them; the flows keep reaching
   the asserts late-bound through the seam. INV-2 is about **ports/classes**, not call
   flows.
3. Late-bind moved asserts via the `sync_module` convention so
   `monkeypatch.setattr("...commands.sync._assert_*", ...)` and
   `..._resolve_gated_receiver` still intercept (INV-4). Note the dispatch runtime
   opener in `sync_runtime.py` (WP05) references these asserts — after this WP they
   live in `sync_authority.py`; ensure that back-reference still resolves late-bound.

**Author `tests/architectural/test_sync_two_authority.py`** (FR-004 / INV-2):
- Assert the **read**, **write**, and **admission** authority ports are **distinct
  symbols in distinct modules with no shared authority base class** — i.e. no single
  `*Authority*` class is imported/subclassed by more than one of the three surfaces.
- **Scope the discriminator to an explicit symbol/module allowlist** (A-3) — enumerate
  the exact symbols/modules the test governs (the `sync_authority.py` read/write/
  admission adapter symbols + their canonical delegates), so the test is neither
  brittle against the package's other 5+ `*Authority*` surfaces nor vacuous. Make it
  **distinct from** `test_2093_authority_invariant.py` (do not duplicate its
  discriminator).

## Branch Strategy

- **Base + merge target:** `refactor/wave4-sync-degod`. `branch_strategy: lane-per-wp`.
- Worktree from `lanes.json` for WP07. **Depends on WP06** — rebase on the WP06-shrunk
  `sync.py` first. Serial chain (every degod WP edits `sync.py`).
- Commit in units: store-report core + its tests; then authority adapters; then the
  arch-test.

## Definition of Done

- `sync_store_report_core.py` holds the **pure compute** half of all three shared
  helpers (+ the pure derivations they use); `status` L5583 and `doctor` L6200 both
  route through the same compute, decoupled. Render halves call the WP04 Render port.
- `sync_authority.py` exposes **three delegating** adapter surfaces (read/write/
  admission); each delegates to `preflight`/`sharing_client`/`target_authority` and
  re-implements nothing.
- **`test_sync_two_authority.py` green** — distinct read/write/admission ports, no
  shared authority class, allowlist-scoped, distinct from
  `test_2093_authority_invariant.py`.
- Golden snapshots + the ~60 `sync`-monkeypatch tests + the per-project-store/consent/
  tracker suites green pre/post (INV-1, INV-4).
- Mixed-authority flows (`_open_project_dispatch_runtime`, `opt_out`) unchanged (C-007).
- New focused unit tests for each pure compute function pass (new-code coverage).
- `ruff` + `mypy --strict` clean; zero net-new `C901`/`S3776`. Each relocated writer is
  a **1:1 census-key swap** (`test_sync_writer_census.py` green).
- No `runtime`-package import (INV-3); AST early-bind guard green (INV-4).

## Reviewer Guidance

- **Verify delegation, not duplication:** grep `sync_authority.py` — the bodies should
  call into `preflight`/`sharing_client`/`target_authority`, not carry copied
  authority logic. Copied logic is a DIRECTIVE_044 fork → reject.
- Confirm `test_sync_two_authority.py` uses an **explicit allowlist** and would
  actually fail if someone unified read+write into one class — read the assertion, and
  sanity-check it is not a tautology and not a copy of `test_2093_authority_invariant.py`.
- Confirm `_render_per_project_store`'s compute half is genuinely shared by both
  `status` and `doctor` (no status↔doctor edge remains) and that both emit identical
  output to before (byte-check the golden + doctor per-project suite).
- Confirm the mixed-authority flows were **not** refactored (C-007) — diff
  `opt_out` and the dispatch opener against pre-WP bodies.
- Check the core compute functions are I/O-free (no `Console`/`print`).


## Post-tasks squad corrections (BINDING — read before implementing)
- **Rn-1 (freeze protection):** the `status` and `doctor` full-render goldens are now frozen in **WP02** (`test_sync_cli_safe.py`), because this WP's shared-helper compute/render split churns them. After splitting `_render_per_project_store`/`_render_consent_readability`/`_render_tracker_egress`, run the WP02 `status`/`doctor` render snapshots and confirm they stay **byte-green** — that is the safety net for this seam.
- **Rn-2 (`_resolve_gated_receiver` L799 split boundary):** this WP wraps ONLY the delivery-**admission** assert portion (`_assert_delivery_target_matches_context` / gate-context) into `sync_authority.py`; it LEAVES the receiver-plumbing/resolution body in `sync.py` for WP08 to relocate. State explicitly in your commit what remains. **DoD:** `_resolve_gated_receiver` behavior byte-identical — the admission assert AND the receiver resolution are both reached, no branch dropped — verified against the `now`/dispatch golden.
