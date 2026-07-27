---
work_package_id: WP06
title: '#2093 invariant hardening + test-suite reconciliation'
dependencies:
- WP05
requirement_refs:
- FR-008
- FR-009
planning_base_branch: feat/runtime-state-corpus-cutover
merge_target_branch: feat/runtime-state-corpus-cutover
branch_strategy: Planning artifacts for this mission were generated on feat/runtime-state-corpus-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/runtime-state-corpus-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
- T028
agent: "claude"
shell_pid: "4047979"
shell_pid_created_at: "1784559081.52"
history:
- timestamp: '2026-07-20T08:39:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_2093_authority_invariant.py
- tests/architectural/baselines/fast-tests-core-misc-nodeids.txt
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP06 – #2093 invariant hardening + test-suite reconciliation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the **`python-pedro`** agent profile (role: `implementer`) **before doing any work**, and behave according to its guidance for the whole WP.

This WP is almost entirely test-surface work, but it is the load-bearing *net* that proves the mission's single-authority claim is real. Treat every arm you touch as an ATDD asset: a guard that cannot fail on a real regression is worse than no guard, because it manufactures a false green. Bring an implementer's paranoia — prove non-vacuity, never assert-and-move-on.

## Objective

Lock the mission's single-authority end-state so no frontmatter runtime read can regress, and reconcile the flag-ON / flag-OFF split test suite (~33 files) down to the one post-cutover model. Concretely (plan **IC-05**, FR-008 / FR-009, C-006):

1. **Empty** the `#2093` invariant's tolerated-reader set (`_SANCTIONED_READER_MODULES` → `frozenset()`), and rewrite the now-**vacuous** canonical-gate-identity arm (it imports the predicate WP04 deleted) into a "zero frontmatter-authority reads" assertion.
2. **EXTEND** the invariant's detector to catch **attribute-access** runtime reads (`read_wp_frontmatter(...).<field>`, `WPMetadata`/`WorkPackage` runtime attributes) — not only `extract_scalar(...)`.
3. **Reconcile** the ~33-file split suite: delete the flag-OFF twins, make the flag-ON assertions unconditional, fix the compat-surface test that breaks on the facade-alias drop.
4. **Regenerate** the CI node-id + gate-coverage baselines through the sanctioned freeze/update flow (deleted / renamed node IDs trip them otherwise).
5. Backstop the **NFR-003 byte-stability** regression and the **#2815 repo-root-write** guard **only if** WP04/WP01 did not already add them.

**The single most important thing in this WP:** emptying the tolerated set *without* extending the detector is a **false green**. The dashboard scanner escaped the `extract_scalar`-only detector (research **D-09**), so the guard would report clean while a split-brain reader survived. SC-009 is the anti-false-green gate.

## Context & grounding

### This is the plan's second-biggest sizing risk

- Plan IC-05's own "Risks" line: *"Undersizing IC-05 is the plan's second-biggest risk after IC-01b."*
- The brief undersizes it as "the status suite". It is **not** one file. The union of `status_phase` / `_phase1` refs and `dual-write` / `flag_off` refs spans **~33 test files** across `architectural`, `status`, `cli/commands/agent`, `core`, `sync`, `orchestrator_api`, `integration`, `regression`, `upgrade`, `docs`.
- If this WP feels like a one-file edit, you have missed the detector extension **and** the ~32-file reconciliation.

### The false-green trap (FR-008 / research D-09 / SC-009) — read this twice

- The invariant's detector `_reads_dynamic_field_via_extract_scalar` (`test_2093_authority_invariant.py:312`) matches **only** `extract_scalar(<any>, "<dynamic field>")` calls. It is **blind to typed attribute-access reads**.
- `dashboard/scanner.py::_process_wp_file` reads runtime `agent` (~:937), `assignee` (~:978), and subtask completion (~:954-965) via `read_wp_frontmatter(...).<attr>` — **attribute access on the typed `WPMetadata`, never `extract_scalar`.** That reader escaped both the pre-planning #2093-debt list *and* the arch invariant.
- **If you empty `_SANCTIONED_READER_MODULES` but leave the detector `extract_scalar`-only, the test passes while the dashboard bypass survives — a false green that defeats the entire mission.**
- SC-009 is the anti-false-green gate: the extended detector MUST flag the pre-reroute attribute-read pattern **red**, and go green **only once every such reader resolves the snapshot**.

### Sequencing — who rerouted what before WP06 runs

- WP06 **depends on WP05** (IC-04), which already rerouted the dashboard scanner, the `workflow_cores` review read, and the `tasks_move_task` ownership read onto the snapshot seam.
- WP04 (IC-03) already deleted `_phase1_snapshot_authority_active` + its facade alias, and cut the runtime writers (NFR-003).
- WP03 (IC-01b) already backfilled + committed this repo's dogfood corpus, so the snapshot is non-empty.
- **Consequence:** by the time WP06 runs, the **real tree has zero surviving readers** — which is *exactly* why the non-vacuity of the extended detector **cannot** be proven against the live tree (it is now clean). Non-vacuity MUST be proven with a **synthetic poison fixture** reproducing the pre-reroute pattern (see T025).

### The requirements this WP closes

- **FR-008** — harden the #2093 invariant: `_SANCTIONED_READER_MODULES` → `frozenset()`, rewrite the vacuous canonical-gate-identity arm, **and extend the detector to attribute-access reads**; prove it flags the pre-reroute dashboard pattern red.
- **FR-009** — reconcile the flag-ON / flag-OFF split suite: flag-OFF dual-write tests deleted or re-pointed, flag-ON assertions made unconditional, so the suite reflects the single end-state.
- **C-006** — the arch gate is **updated in-mission, never suppressed**: no new `# noqa` / `# type: ignore` / per-file ignore to get past the deleted-symbol import or the emptied set.
- **SC-003** — `test_2093_authority_invariant.py` passes with an **empty** tolerated set **and fails if a frontmatter authority read is reintroduced** (the non-vacuous half — data-model **INV-2**).
- **SC-004 / NFR-003** — a runtime transition writes **0 bytes** to `tasks/WP##.md` (byte-identical before/after) with the flag removed.
- **SC-006** — the full `tests/architectural/` suite (**run per-file**) and the `status` suite are green on the branch; `ruff` + `mypy` clean, no new suppressions.
- **SC-009** — the extended detector flags an attribute-access frontmatter runtime read red, green only once every such reader resolves the snapshot.
- **INV-2 (data-model):** after cutover, no code path reads WP runtime slots from frontmatter; every read resolves the snapshot. This WP is INV-2's enforcing net.

### What WP06 does NOT own (consume as done facts)

- The 15-symbol `_CATEGORY_C_DEFERRED_RUNTIME_STATE_BACKFILL_CUTOVER` un-pin in `tests/architectural/test_no_dead_symbols.py` is **WP01's** (C-006, first-caller-wired). Do not touch it here.
- The predicate deletion (`_phase1_snapshot_authority_active`) + facade-alias drop is **WP04's**.
- The reader reroutes (dashboard/`workflow_cores`/`tasks_move_task`) are **WP05's**.

## Subtasks

### Symbol / line reference map (current `test_2093_authority_invariant.py`)

Line numbers are anchors at the time of writing — key on the **symbol**, not the line, if the file has drifted.

| Symbol | Line | Current role | Target (post-WP06) |
|--------|------|--------------|--------------------|
| `_SANCTIONED_READER_MODULES` | :275 | 4-module tolerated allow-list | `frozenset()` (T024) |
| `import specify_cli.status as _status_facade` | :239 | facade handle | keep only if the rewritten arms still use it |
| `_phase1_snapshot_authority_active as _CANONICAL_GATE` | :240 | imports the **deleted** predicate | **remove** (T024) |
| `_DYNAMIC_RUNTIME_FIELDS` | :245 | runtime-field name set | extend if subtask-completion attr missing (T025) |
| `_sanctioned_gate_names()` | :300 | derives aliases of `_CANONICAL_GATE` | **remove** if unused (T024) |
| `_reads_dynamic_field_via_extract_scalar()` | :312 | `extract_scalar`-only detector | keep + add attribute-access sibling (T025) |
| `_derive_reader_authority_modules()` | :327 | AST-derives reader modules | union in the new attribute-access arm (T025) |
| `_referenced_authority_gates()` | :342 | finds `*_authority_active` gates | reused by the rewritten zero-gate arm (T024) |
| `test_facade_reexports_the_exact_gate_object` | :363 | asserts alias re-export | invert → assert alias **absent** (T024) |
| `test_reader_authority_gate_is_solely_the_canonical_phase1_gate` | :370 | asserts sole canonical gate by identity | rewrite → assert **zero** gates (T024) |
| `test_no_new_ungated_bypass_reader_of_dynamic_fields` | :398 | derived ⊆ sanctioned | derived **== ∅** (T024/T025) |

- [ ] **T024 [FR-008 / C-006] Empty the tolerated set + rewrite the vacuous gate-identity arm.**
  - Set `_SANCTIONED_READER_MODULES` (`:275`) to `frozenset()`. With WP05's reroutes complete, the AST-derived reader set must now be **empty** — any surviving module is a real #2093 bypass and this correctly goes red.
  - The module-level imports at `:239-240`:
    - `import specify_cli.status as _status_facade`
    - `from specify_cli.status.emit import _phase1_snapshot_authority_active as _CANONICAL_GATE`

    now reference a **deleted symbol** (WP04 removed the predicate + its facade alias) — they will `ImportError` at collection. **Delete the `_CANONICAL_GATE` import** and rewrite the two arms that consumed it:
    - `test_facade_reexports_the_exact_gate_object` (`:363`) asserts the facade re-exports the gate object — that object no longer exists. Replace it with the **inverse** guard: assert `phase1_snapshot_authority_active` is **absent** from `specify_cli.status` (`not hasattr(_status_facade, "phase1_snapshot_authority_active")` and it is not in `__all__`) — the post-cutover **SC-002** fact.
    - `test_reader_authority_gate_is_solely_the_canonical_phase1_gate` (`:370`) currently asserts, by imported-symbol identity, that the **one** `*_authority_active` reader gate is the canonical phase-1 gate. Post-cutover there is **zero** such gate. Rewrite it to assert `_referenced_authority_gates(...)` across the reader roots yields the **empty set** — no `*_authority_active` reader gate remains anywhere.
  - Concrete before → after sketch (adapt to the real helpers; do not copy line-for-line):

    ```python
    # BEFORE (imports the deleted predicate — ImportError at collection):
    from specify_cli.status.emit import _phase1_snapshot_authority_active as _CANONICAL_GATE

    def test_facade_reexports_the_exact_gate_object() -> None:
        assert _status_facade.phase1_snapshot_authority_active is _CANONICAL_GATE

    # AFTER (SC-002 post-cutover fact — the alias is GONE):
    def test_phase1_gate_is_deleted_from_the_status_facade() -> None:
        assert not hasattr(_status_facade, "phase1_snapshot_authority_active")
        assert "phase1_snapshot_authority_active" not in getattr(_status_facade, "__all__", [])

    # BEFORE: sole canonical gate by identity (non-empty sanctioned set)
    # AFTER: zero reader-authority gates remain on the reader path
    def test_no_reader_authority_gate_remains() -> None:
        root = _repo_root()
        discovered: set[str] = set()
        for path in _iter_root_modules(root):
            try:
                discovered |= _referenced_authority_gates(ast.parse(path.read_text("utf-8")))
            except SyntaxError:
                continue
        assert discovered == set(), (
            f"a *_authority_active reader gate survives post-cutover: {sorted(discovered)}"
        )
    ```

  - `_legacy_lane_mirror_enabled`, kept by C-004, is a **lane-mirror** gate — NOT a reader-authority gate, and is already excluded by construction (`_referenced_authority_gates` only matches `*_authority_active`). Confirm the exclusion still holds after your rewrite; do not accidentally start matching it.
  - The old non-vacuity guards `assert discovered, ...` (`:386`), `assert discovered >= sanctioned` (`:395`), and `assert derived, ...` (`:408`) **invert** their meaning post-cutover (discovered/derived are now empty) — **replace** them, do not keep them. Their non-vacuity role moves to the T025 poison fixture.
  - Delete `_sanctioned_gate_names()` (`:300`) if the rewrite leaves it unused (it derives aliases of the deleted object). Do not leave dead helpers — `ruff` will flag them, and C-006 forbids silencing.

- [ ] **T025 [FR-008 / SC-009] EXTEND the detector to attribute-access reads; prove it NON-VACUOUSLY.**
  - Add a detector arm alongside `_reads_dynamic_field_via_extract_scalar` (`:312`) that catches **typed attribute-access** runtime reads. Target shape:
    - `read_wp_frontmatter(...).<runtime_field>` — the call-chain shape research D-09 documents (robust; no type inference needed).
    - `WPMetadata` / `WorkPackage` runtime attribute reads (a name-based arm for values known to be those typed objects).
  - Match an `ast.Attribute` node where `node.attr in _DYNAMIC_RUNTIME_FIELDS` **and** `node.value` is either a `read_wp_frontmatter(...)` `ast.Call` or a name/attribute known to be a frontmatter/metadata object. Keep the helper `<=15` complexity by extracting a small `_is_frontmatter_attr_read(node)` predicate; do not inline a deeply-nested walk.
  - Detector sketch (adapt; the `read_wp_frontmatter(...).field` chain is the robust anchor):

    ```python
    _FRONTMATTER_READ_CALLS = frozenset({"read_wp_frontmatter"})

    def _is_frontmatter_attr_read(node: ast.AST) -> bool:
        """True for ``read_wp_frontmatter(...).<runtime_field>`` attribute reads."""
        if not isinstance(node, ast.Attribute):
            return False
        if node.attr not in _DYNAMIC_RUNTIME_FIELDS:
            return False
        base = node.value
        return (
            isinstance(base, ast.Call)
            and isinstance(base.func, (ast.Name, ast.Attribute))
            and (getattr(base.func, "id", None) or getattr(base.func, "attr", None))
            in _FRONTMATTER_READ_CALLS
        )

    def _reads_dynamic_field_via_attribute_access(tree: ast.AST) -> bool:
        return any(_is_frontmatter_attr_read(n) for n in ast.walk(tree))
    ```

  - Then union both classes in the derivation:

    ```python
    if _reads_dynamic_field_via_extract_scalar(tree) or _reads_dynamic_field_via_attribute_access(tree):
        derived.add(path.relative_to(root).as_posix())
    ```
  - Fold the new arm into `_derive_reader_authority_modules` (`:327`) so the AST-derived set is the **union** of `extract_scalar` readers and attribute-access readers. With `_SANCTIONED_READER_MODULES` empty (T024), the derived union must be **empty** on the post-WP05 tree — green **only because** every reader of **both** classes now resolves the snapshot (SC-009's "green only once every such reader resolves").
  - **Prove non-vacuity with a poison-test (mandatory — this is the SC-009 gate).** Because WP05 already rerouted the real dashboard scanner, you cannot demonstrate a live RED. Instead add a focused unit test that:
    - feeds the extended detector a **synthetic source string** reproducing the exact pre-reroute pattern, e.g.

      ```python
      SRC = "def f(front):\n    return read_wp_frontmatter(front).agent\n"
      assert _reads_dynamic_field_via_attribute_access(ast.parse(SRC)) is True
      ```

    - adds the mirror case — a snapshot-sourced read returns **False**:

      ```python
      OK = "def f(fd, wp):\n    return wp_snapshot_state(fd, wp).agent\n"
      assert _reads_dynamic_field_via_attribute_access(ast.parse(OK)) is False
      ```

  - Name/docstring the poison-test after the dashboard scanner as the motivating pre-reroute reader (D-09 / SC-009), so a future reader understands *why* the fixture exists.
  - Extend `_DYNAMIC_RUNTIME_FIELDS` (`:245`) if the dashboard subtask-completion attribute name is not already covered — but keep **authored-intent** fields (`role`, `agent_profile`, `model` authored recommendation) OUT of the runtime set: those stay frontmatter-canonical (D-09 / spec **C-008**); only the **resolved actual** is event-sourced (WP10/WP11), and the dashboard's authored read is legitimate.

- [ ] **T026 [FR-009] Reconcile the ~33-file flag-ON / flag-OFF split suite (out-of-map edits).**
  - Enumerate the set with the mission spine command:

    ```bash
    grep -rl "status_phase\|_phase1\|dual.write\|flag_off" tests/ | sort
    ```

  - The union is ~35 paths; **exclude** the three handled elsewhere:
    - `tests/architectural/baselines/fast-tests-core-misc-nodeids.txt` → T027 (baseline).
    - `tests/architectural/test_2093_authority_invariant.py` → T024/T025 (owned).
    - `tests/architectural/test_no_dead_symbols.py` → WP01's un-pin (not this WP).
  - That leaves ~32 test files to reconcile to the single end-state. **Delete the flag-OFF twins:**
    - `tests/specify_cli/cli/commands/agent/test_move_task_rollback_clears_claim_flag_off.py` — the explicit flag-OFF twin; **delete** it, and make `test_move_task_rollback_clears_claim.py`'s assertions **unconditional** (drop the `status_phase="0"` / flag-OFF setup and any flag-ON gating).
    - `tests/sync/test_dual_write_integration.py` — tests the retired dual-write behaviour end-to-end; **delete or re-point** (there is no dual-write path after WP04). If any arm still asserts a *live* event-only invariant, keep only that arm and rename.
  - **Make flag-ON assertions unconditional** across the parametrized-on-`status_phase` / `flag_on`-fixture files. Candidate set to sweep (verify each against the actual code):
    - `tests/status/test_emit.py`, `tests/status/test_parity.py`, `tests/status/test_phase.py`, `tests/status/test_legacy_bridge.py`, `tests/status/test_views.py`, `tests/status/test_status_e2e_integration.py`, `tests/status/test_diffcov_2684_runtime_state_gaps.py`
    - `tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py`, `test_tasks_mark_status.py`, `test_move_task_orchestration.py`, `test_implement_runtime_frontmatter_claim.py`, `test_check_unchecked_subtasks_snapshot_source.py`
    - `tests/specify_cli/core/test_shell_pid_claim_baseline.py`, `test_stale_detection_snapshot_liveness.py`
    - `tests/specify_cli/orchestrator_api/test_commands_fail_closed.py`, `test_transition_subtask_gate.py`, `test_typed_error_fail_closed.py`
    - `tests/specify_cli/sync/test_worktree_clean_invariant.py`, `tests/sync/test_sync_status_check.py`
    - `tests/regression/test_issue_2684_subtask_completion_event_sourced.py`, `tests/upgrade/test_read_cutover_integration.py`
    - `tests/agent/test_orchestrator_commands_integration.py`, `tests/contract/test_orchestrator_api.py`, `tests/docs/test_build_cli_reference.py`
    - `tests/integration/test_ac5_hash_guard.py`, `test_render_parity_golden.py`, `test_wp_file_hash_stability.py`
    - `tests/specify_cli/upgrade/migrations/test_m_session_presence_all_harnesses.py`
  - **KEEP the cutover-*mechanics* tests intact.** WP01/WP02/WP03 surface tests that legitimately exercise `status_phase` as the **cutover marker** (verify-then-flip, the sole-writer, idempotency, the upgrade migration) assert **real** retained behaviour (C-004 keeps `status_phase` live for the lane mirror). "Make flag-ON unconditional" applies to the **reader-authority** split, NOT the cutover-marker mechanics. Do not gut them.
  - **Reconcile `tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py`.** It asserts the `specify_cli.status` facade seam (the `phase1_snapshot_authority_active` alias + `__all__` entry) that WP04 removed — it breaks on the alias drop. Update it to assert the **post-cutover** surface: the alias is gone, `_legacy_lane_mirror_enabled` is retained (C-004), and any still-exported compat symbols are the ones WP04 kept.
  - **These are out-of-map edits to existing files.** WP06 formally owns only `test_2093_authority_invariant.py` + the node-id baseline (see frontmatter). Editing the ~32 reconciled files is deliberate out-of-map work — WP06 is their **only in-mission editor**, sequenced last so the split has settled (see Risks). Touch each file **minimally**: reconcile the flag arm, nothing else.

- [ ] **T027 [FR-009] Regenerate the CI node-id + gate-coverage baselines (sanctioned flow only).**
  - T026's deletions/renames change collected node IDs, which trip both baselines.
  - **Node-id baselines** — regenerate via:

    ```bash
    uv run python -m tests.architectural._gate_coverage --freeze-baselines
    ```

    This rewrites `fast-tests-core-misc-nodeids.txt` and its siblings `integration-tests-next-nodeids.txt` / `slow-tests-nodeids.txt`.
  - **Update the provenance comment.** The baseline header (`# E3 baseline ...`) currently says "captured pre-WP06" and **requires a provenance comment** when a WP legitimately changes the job's selection. Record that WP06 removed the flag-OFF twin(s) + reconciled the split suite; do not leave it saying "pre-WP06".
  - **Gate-coverage orphan worklist** — if any reconciled/deleted file changes the orphan-file set, regenerate `_gate_coverage_baseline.json` via:

    ```bash
    uv run python -m tests.architectural._gate_coverage --update-baseline
    ```

  - **Regenerate, never hand-edit.** Run the sanctioned command and commit its verbatim output; do not hand-splice node IDs (a hand-edit that de-syncs from real `--collect-only` is the exact drift these baselines exist to catch). Re-run the owning gate test (`tests/architectural/test_gate_coverage.py`) after regeneration to confirm green and that a second `--freeze-baselines` produces **no diff**.

- [ ] **T028 [NFR-003 / C-003] Backstop the byte-stability + repo-root-write guards — ONLY if not already added upstream.**
  - **First check** what upstream WPs already landed:
    - WP04 / **T017** — byte-stability (0-bytes-on-transition, SC-004).
    - WP01 / **T005** — the INV-5 repo-root-write guard (#2815: no `status.events.jsonl` at repo root).
  - If both exist and cover the **unconditional** end-state, T028 is a **no-op — record that** in the DoD and add nothing (avoid duplicate coverage).
  - If a gap remains, add the missing focused test here:
    - a **suite-level unconditional NFR-003 arm** — a runtime transition writes **0 bytes** to `tasks/WP##.md`, byte-identical before/after, with the flag removed; or
    - a dedicated **#2815** guard asserting no `status.events.jsonl` lands at repo root (all writes via `canonicalize_feature_dir`).
  - Keep it non-vacuous: **drive a real transition** and assert byte-identity + repo-root cleanliness; do not assert against a mocked writer.

## Branch Strategy

- **Strategy:** Planning artifacts were generated on `feat/runtime-state-corpus-cutover`; completed changes merge back into `feat/runtime-state-corpus-cutover`.
- **Planning base branch:** `feat/runtime-state-corpus-cutover`
- **Merge target branch:** `feat/runtime-state-corpus-cutover`
- **Sequencing:** WP06 **depends on WP05** (IC-04) and transitively on WP04/WP03/WP01 — the invariant and the reconciled suite must reflect the **post-cutover end-state**, so this WP lands **after** the predicate deletion, the reader reroutes, and the dogfood backfill are all in. Do not start the reconciliation before WP05 has settled the reader surface, or you will reconcile against a moving target.
- Per project policy: `spec-kitty merge` targets **local main only**; never `git push origin main`. Publishing is the operator's explicit, separate step.

## Test strategy

Run **every** touched test file individually, **with a timeout**, via the sanctioned invocation. **NEVER run the whole `tests/architectural/` directory — it hangs** (research risks; mission execution discipline). Bare `python` resolves a sibling checkout and yields false greens — always `uv run --extra test`.

1. **The invariant itself (primary gate):**

   ```bash
   timeout 300 uv run --extra test python -m pytest -p no:cacheprovider \
     tests/architectural/test_2093_authority_invariant.py -q
   ```

   Must pass with `_SANCTIONED_READER_MODULES == frozenset()`, the poison-fixture arm(s) green (detection proven), and no import of the deleted predicate.
2. **Each reconciled file, per-file** (never the directory):

   ```bash
   timeout 300 uv run --extra test python -m pytest -p no:cacheprovider <FILE> -q
   ```

   Run the ~32 reconciled files one at a time (or in small explicit batches by directory), confirming each is green on the single end-state.
3. **Baseline gate** after T027:

   ```bash
   timeout 300 uv run --extra test python -m pytest -p no:cacheprovider \
     tests/architectural/test_gate_coverage.py -q
   ```

   Re-run any node-id-consuming gate test to confirm the regenerated baselines match real collection.
4. **Detector non-vacuity:** the T025 poison-test asserting the extended detector flags the synthetic `read_wp_frontmatter(...).agent` pattern **red** and a snapshot read **green** is the SC-009 proof — it must be a real executing test, not a comment.
5. **Quality gates (SC-006 / NFR-004):** `ruff check <touched files>` and `mypy` clean with **no** new `# noqa` / `# type: ignore` / per-file ignores (C-006). If deleting the predicate import left an unused import/helper elsewhere, **remove** it — do not silence it.
6. **Pre-existing-red discipline:** confirm any red is **not** a baseline red before attributing it to this diff — the phantom `SYNC_DISABLE_ENV_VARS` `arch-adversarial` red and the ADR-2026-07-17-1 known-P0s (#2736 / #2772 / #1834) are **not** this mission's. Confirm on the merge-base.

## Definition of Done

- [ ] **T024** `_SANCTIONED_READER_MODULES == frozenset()`; the deleted-predicate imports removed; `test_facade_reexports_the_exact_gate_object` rewritten to assert the alias is **absent** (SC-002); the gate-identity arm rewritten to assert **zero** `*_authority_active` reader gates remain; unused helpers (`_sanctioned_gate_names`) removed. No `# noqa` / `# type: ignore` added (C-006).
- [ ] **T025** detector extended to catch `read_wp_frontmatter(...).<runtime>` / `WPMetadata`/`WorkPackage` attribute reads and folded into `_derive_reader_authority_modules`; a **poison-test** proves it flags the pre-reroute dashboard pattern **red** and a snapshot read **green** (SC-009); authored-intent fields kept out of the runtime set (C-008).
- [ ] **T026** the ~32-file split suite reconciled: flag-OFF twin(s) deleted (`test_move_task_rollback_clears_claim_flag_off.py`; `test_dual_write_integration.py` re-pointed/deleted), flag-ON assertions made unconditional, `test_tasks_compat_surface.py` reconciled to the post-cutover facade; cutover-mechanics tests preserved. Each reconciled file green per-file.
- [ ] **T027** node-id baselines regenerated via `--freeze-baselines` (with an updated provenance comment) and `_gate_coverage_baseline.json` via `--update-baseline` if the orphan set changed; the gate-coverage test is green; a re-freeze produces **no diff**; **no hand-edited node IDs**.
- [ ] **T028** byte-stability (NFR-003) + repo-root-write (#2815) guards confirmed present (in WP04/WP01) **or** the gap backstopped here; if a no-op, that determination is recorded.
- [ ] **FR-008 / SC-003** `test_2093_authority_invariant.py` passes with an **empty** tolerated set **and fails on a reintroduced frontmatter authority read** (proven non-vacuous, both extract_scalar and attribute-access classes) — INV-2.
- [ ] **FR-009 / SC-006** the full `tests/architectural/` suite (**per-file**) and the `status` suite are green on the branch; `ruff` + `mypy` clean; **no new suppressions** (C-006 / NFR-004).
- [ ] **SC-004 / NFR-003** a runtime transition writes 0 bytes to `tasks/WP##.md` (covered by WP04 or backstopped by T028).
- [ ] No edits outside the reconciliation scope: `owned_files` (`test_2093_authority_invariant.py`, `fast-tests-core-misc-nodeids.txt`) + the enumerated ~32 out-of-map reconciled test files + the sibling regenerated baselines. **No source edits** — WP06 touches tests + baselines only.

## Risks & out-of-map edits

- **The ~32 reconciled test files are existing files edited OUT-OF-MAP.** WP06's `owned_files` names only the invariant and the node-id baseline, but reconciling the split suite necessarily edits ~32 other test files across many packages. This is by design and safe **because WP06 is sequenced last and is the sole in-mission editor of the flag-split surface** (WP04/WP05 removed the *production* flag; WP06 removes its *test* mirror). Keep each edit surgical — reconcile the flag arm, do not refactor the file. If any reconciled file also carries a WP04/WP05 assertion still failing, that is an upstream defect to route back, not a WP06 paper-over.
- **The gate-identity arm rewrite is MORE than a set edit — this is the trap.** The arm currently asserts the *identity* of `_phase1_snapshot_authority_active`, a symbol WP04 **deleted**; the file will `ImportError` at collection until you rewrite it. Do not "fix" this by re-adding the deleted import or a stub — the point is the symbol is gone (SC-002). Rewrite to the zero-gate assertion.
- **False-green is the failure mode to fear most (D-09 / SC-009).** Emptying `_SANCTIONED_READER_MODULES` while leaving the detector `extract_scalar`-only makes the test pass *and lies* — the dashboard attribute-read class is invisible to it. The detector extension is the non-negotiable core of this WP; the poison-test is its proof. A reviewer who cannot see a test that flags a synthetic `read_wp_frontmatter(...).agent` red should reject.
- **Non-vacuity cannot be proven against the live tree.** WP05 already rerouted every real reader, so the live tree is clean — a detector that discovers nothing on the live tree tells you nothing about whether it *can* discover. Prove it against the synthetic poison fixture, and assert the live tree is **empty** as the end-state (the two are complementary, not the same assertion).
- **Baselines: regenerate, never hand-edit (T027).** A hand-spliced node-id list that de-syncs from real `--collect-only` output is the exact drift the E3 baseline exists to catch; it will pass locally and fail on CI's fast-tests job. Always run `--freeze-baselines` and commit its verbatim output plus the provenance comment.
- **Do not gut the cutover-mechanics tests.** Some `status_phase`-referencing tests (WP01/WP02/WP03 surface: verify-then-flip, sole-writer, idempotency, upgrade migration) assert **real** behaviour of the cutover marker, which is retained (C-004: the lane mirror still reads `status_phase`). "Make flag-ON unconditional" applies to the *reader-authority* split, NOT to the cutover-marker mechanics. Distinguish the two before deleting.
- **Undersizing IC-05 is the plan's second-biggest risk (after IC-01b).** If this WP feels like a one-file edit, you have missed the detector extension and the ~32-file reconciliation. Re-read plan IC-05 and FR-008.

## Reviewer guidance

Do not rubber-stamp a green run — a false green is the specific defect this WP exists to prevent. Verify the guard actually bites:

- **Detector actually catches attribute reads (SC-009).** Confirm a **poison-test** exists that feeds the extended detector a synthetic `read_wp_frontmatter(...).agent` (attribute-access) source and asserts it is flagged **red**, and a `wp_snapshot_state(...).agent` read is **green**. Then locally reproduce the pre-reroute regression: temporarily re-point one snapshot read in `dashboard/scanner.py` back to `read_wp_frontmatter(...).<attr>` in your working tree and confirm `test_2093_authority_invariant.py` goes **red** — then revert. If it stays green, the detector extension is vacuous — **reject**.
- **Invariant is non-vacuous (SC-003 / INV-2).** `_SANCTIONED_READER_MODULES` is `frozenset()`; a reintroduced `extract_scalar(front, "agent")` **and** a reintroduced attribute read both turn the test red. Confirm the gate-identity arm asserts **zero** `*_authority_active` reader gates (not the old "sole canonical gate" identity, which references a deleted symbol) and that `_legacy_lane_mirror_enabled` is correctly excluded (it is a lane-mirror gate, kept by C-004).
- **Baselines were regenerated, not hand-edited (T027).** Confirm `fast-tests-core-misc-nodeids.txt` carries a fresh provenance comment naming WP06's selection change, and that re-running `--freeze-baselines` produces **no diff** (the committed file matches real collection). Spot-check that the deleted flag-OFF twin's node IDs are gone and no phantom IDs were added.
- **Split-suite reconciliation is minimal and correct.** The flag-OFF twins are deleted; flag-ON assertions are unconditional; `test_tasks_compat_surface.py` reflects the post-cutover facade (alias gone, `_legacy_lane_mirror_enabled` kept). No cutover-mechanics test was gutted. Each touched file is green per-file (`uv run --extra test`, per-file, timeout — never the whole `tests/architectural/` dir).
- **No suppressions (C-006 / NFR-004).** No new `# noqa` / `# type: ignore` / per-file ignore was added to get past the deleted-symbol import or the emptied set; `ruff` + `mypy` clean; no orphan dead helpers left behind.
- **Scope discipline.** WP06 edits tests + baselines only — no source changes. The out-of-map reconciled files are minimal, flag-arm-only edits.

## Activity Log

- 2026-07-20T14:51:31Z – claude – shell_pid=4047979 – Assigned agent via action command
- 2026-07-20T16:25:33Z – claude – shell_pid=4047979 – Ready for review. Per-file evidence (arch-dir hangs whole, so gate skipped): test_2093_authority_invariant 8 passed (non-vacuous, both detector classes + live-tree repro); 416 reconciled split-suite tests passed; test_gate_coverage 31 passed (node-id GC-2b + orphan GC-2 green after --freeze/--update-baseline); ruff clean; mypy clean modulo env pytest-stub. Classified reds NOT mine: #8 test_unasserted_flag_blocks_on_unchecked_primary_rows (WP02/WP04 subtask-gate C-001-fallback divergence, routed back) + test_dogfood_corpus_backfilled (corpus-on-feat). FOLD (9-fn dead closure) deferred + reported.
- 2026-07-20T16:46:31Z – claude – shell_pid=4047979 – Cycle 2 fix committed (221a78df3) while WP06 remained in for_review (no reject-to-in_progress occurred, so for_review->for_review is illegal). Restored C-001 symmetric-window tasks.md fallback in _infer_subtasks_complete (fail-closed door symmetry vs the CLI door). Fixes the #2510 fail-closed regression: test_unasserted_flag_blocks_on_unchecked_primary_rows now blocks VIA the restored fallback; also fixes 3 test_wp_header_regex_depth::TestInferSubtasksCompleteHeaderDepth reds (WP04-broken); reconciled 2 WP04 no-info-block tests to demonstrate the restored fallback (no assertion weakened). 218 emit-door consumer tests pass; ruff clean; new code mypy-clean. FOLD stays deferred to WP07 per coordinator decision. Ready for cycle-2 review.
- 2026-07-20T16:49:49Z – user – shell_pid=4047979 – Approved: detector non-vacuous, ~33 files reconciled no-weaken, fail-closed #2510 fix (door symmetry), baselines regen
