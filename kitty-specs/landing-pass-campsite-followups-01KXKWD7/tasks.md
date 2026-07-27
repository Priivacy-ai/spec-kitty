# Tasks: Landing-Pass Campsite Follow-ups

**Mission**: landing-pass-campsite-followups-01KXKWD7
**Branch**: feat/landing-pass-campsite-followups | **Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

Every WP is **red-first (C-005)**: reproduce the failure through the pre-existing
entry point, commit the RED test first, then go green. Coord topology with lanes;
`owned_files` are disjoint across WPs (the real parallel-collision guard).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | RED: unregistered arch test file double-reds GC-1 + orphan gates | WP01 | |
| T002 | Add `default_fallback` field to `ShardGroup` | WP01 | |
| T003 | Root-gated hash-bucket fallback branch in `shard_for()` | WP01 | |
| T004 | Opt-in on the `arch` row; rewrite the doctrine header (FR-011) | WP01 | |
| T005 | Verify GC-1 union + orphan gates green; explicit entries still win | WP01 | |
| T010 | RED: structural — real `mission_creation.py` mutated mid-scan under `-n auto` | WP02 | [D] |
| T011 | Isolate `_SourceMutation` to a tmp copy + process-local `audit.SRC_ROOT` monkeypatch | WP02 | | [D] |
| T012 | Confirm the second scanner (`test_surface_resolution_audit`) is immune (#2638) | WP02 | | [D] |
| T013 | Preserve what the bite-battery proves (real detector path); parallel smoke ≥5× | WP02 | | [D] |
| T020 | RED: `test_dry_run_evidence_on_spec_kitty_repo` ANSI break + real synthesis-manifest mutation | WP03 | [D] |
| T021 | Deterministic no-color output via `CliConsole`; strip/avoid ANSI in the assertion | WP03 | | [D] |
| T022 | Isolate the synthesis-manifest write to a tmp fixture (no real-file mutation) | WP03 | | [D] |
| T030 | RED: `_build_remediation_lines` inline command escapes the guard | WP04 | [D] |
| T031 | Hoist all remedy prose to constants; expose `ALL_REMEDIATION_TEXTS` registry | WP04 | | [D] |
| T032 | Both the dict and the inline builder reference the constants (byte-identical output) | WP04 | | [D] |
| T033 | Repoint the command-name guard at the full registry; verify inline typo now fails | WP04 | | [D] |
| T040 | RED: `get_wp_lane` returns `Lane | str`; assert pure-`Lane` + import safety | WP05 | | [D] |
| T041 | Add `Lane.UNINITIALIZED` member (non-display, non-transitionable) | WP05 | | [D] |
| T042 | Add its `_STATE_MAP`/`_FACTORY_ALIASES` entry (`wp_state.py`) — no import crash | WP05 | | [D] |
| T043 | Canonical non-display-lane authority; update filters to exclude UNINITIALIZED | WP05 | | [D] |
| T044 | `get_wp_lane` returns `Lane.UNINITIALIZED`; `get_all_wp_lanes` → `dict[str, Lane]` | WP05 | | [D] |
| T045 | Update ~12 pre-existing lane-roster tests to exclude/extend for UNINITIALIZED | WP05 | | [D] |
| T046 | Exempt UNINITIALIZED from `CANONICAL_LANES` parity like genesis | WP05 | | [D] |
| T050 | RED: behavior — unseeded path (worktree-topology "planned"; done "not done") | WP06 | |
| T051 | `done_bookkeeping`: treat `Lane.UNINITIALIZED` explicitly as not-done | WP06 | |
| T052 | `worktree_topology` + `aggregate` + `coordination/status_transition` consumers | WP06 | |
| T053 | `workspace/context` annotation ripple from `dict[str, Lane]` | WP06 | |
| T054 | `workflow_executor`: str→Lane ×4 (now cleared) + typed `_locate_wp` ×2 + Optional 668/873 | WP06 | |
| T055 | `coordination/status_transition` `StatusEvent | None` narrowing | WP06 | |
| T060 | RED: duplicated `decision_id` interview block; `str|None→str` mypy error | WP07 | [D] |
| T061 | Create `widen/interview_helpers.py`; route both interviews through the narrow-once seam | WP07 | | [D] |
| T062 | Drop the 3 config-verified redundant casts + delete stale `follow_imports=skip` comments | WP07 | | [D] |

## Work Packages

### WP01 — Shard-registry default fallback + doctrine header (#2671)
- **Goal**: unregistered `tests/architectural/*.py` auto-covers via a deterministic root-gated hash-bucket fallback; explicit entries win; union invariant retained; doctrine header rewritten.
- **Requirements**: FR-001, FR-002, FR-003, FR-004, FR-011, NFR-001, NFR-006, C-002, C-008.
- **Independent test**: add a throwaway arch test file → GC-1 completeness + orphan gates stay green with no shard-table edit.
- **Depends on**: none (**land first — soft enabler**).
- Subtasks: T001–T005. Est. ~300 lines.

### WP02 — Bite-battery mutation isolation (#2673 + #2638)
- **Goal**: remove the shared-mutable-real-file hazard so concurrent scanners never read a half-mutated `mission_creation.py`; both scanner victims fixed by one change; battery still proves detection.
- **Requirements**: FR-005, FR-006, NFR-002, C-003, C-006.
- **Independent test**: `-n auto --dist loadfile` across the three files, ≥5× green; `git status --porcelain src/specify_cli/core/mission_creation.py` empty after the run.
- **Depends on**: none. ⚠️ SHARP cross-mission contention on `test_single_mission_surface_resolver.py` — land in a quiescent window (C-006).
- Subtasks: T010–T013. Est. ~280 lines.

### WP03 — Color/synthesis hygiene via CliConsole (#2672)
- **Goal**: `test_dry_run_evidence_on_spec_kitty_repo` deterministic without ANSI-sensitivity or real synthesis-manifest mutation, via the `CliConsole` seam + tmp fixture.
- **Requirements**: FR-007, C-004.
- **Independent test**: the test passes in a color-enabled local shell; `git status --porcelain .kittify/charter/synthesis-manifest.yaml` empty after the run.
- **Depends on**: none.
- Subtasks: T020–T022. Est. ~220 lines.

### WP04 — Sync remediation registry + guard (#2674)
- **Goal**: single-source every remediation sentence; the command-name guard scans the full registry so inline commands are validated; no duplicated literal; byte-identical output.
- **Requirements**: FR-008, FR-009.
- **Independent test**: a deliberately mistyped inline command fails `test_no_unknown_commands_in_hints`; rendered lines unchanged.
- **Depends on**: none.
- Subtasks: T030–T033. Est. ~260 lines.

### WP05 — Lane.UNINITIALIZED member + loader + FSM + display unification (#2675 cluster-1 core)
- **Goal**: introduce the new canonical `Lane.UNINITIALIZED` member cleanly — FSM state-map entry (no import crash), a canonical non-display-lane authority, and the loader returning pure `Lane`.
- **Requirements**: FR-010, NFR-003, NFR-004, NFR-005, C-001.
- **Independent test**: `mypy` on `lane_reader.py` clean; `import specify_cli.status.transitions` succeeds; display summaries exclude UNINITIALIZED.
- **Depends on**: none (**foundation for WP06**).
- Subtasks: T040–T044. Est. ~360 lines.

### WP06 — Lane consumer behavior + workflow_executor type-clears (#2675 clusters 1-downstream, 2, 4)
- **Goal**: update the sentinel's behavioral consumers with tests on the unseeded path, and clear the `workflow_executor.py` errors (all three clusters in one lane).
- **Requirements**: FR-010, NFR-003, NFR-004, NFR-005, C-001.
- **Independent test**: behavior tests pin unseeded→"planned"/"not done"; `mypy` clean on all WP06 surfaces; no new suppressions.
- Depends on WP05
- Note: WP06 needs `Lane.UNINITIALIZED` from WP05 before its consumers/type-clears compile.
- Subtasks: T050–T055. Est. ~420 lines.

### WP07 — Interview-helper de-dup + config-verified casts (#2675 cluster-3 + casts)
- **Goal**: de-duplicate the byte-identical `decision_id` interview block into a shared narrow-once helper; drop the three in-scope redundant casts (config-verified) with their stale rationale comments.
- **Requirements**: FR-010, NFR-003, NFR-005, C-001.
- **Independent test**: `mypy` clean on the interview + cast surfaces; both interviews exercise the shared helper.
- **Depends on**: none (disjoint from WP05/WP06).
- Subtasks: T060–T062. Est. ~240 lines.

## Sequencing & parallelism
- **WP01 first** (soft enabler). WP02, WP03, WP04, WP07 are mutually independent — full parallel. **WP06 depends on WP05.**
- MVP / highest-leverage: **WP01** (stops the recurring red-main) + **WP04** (closes a silent-typo gap).
- The heaviest lane is **WP05→WP06** (the Lane unification); everything else is light.

## Deferred / tracked
- The 3 `charter/mission_type_profiles.py` casts (owned by the shipped mission-type work).
- SC-006 follow-up issue for the 6 residual `_SourceMutation` sites in `test_single_mission_surface_resolver.py`.
