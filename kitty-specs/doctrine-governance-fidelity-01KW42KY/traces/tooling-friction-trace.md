# Tooling-Friction Trace — Doctrine Governance Fidelity

Append every place the tooling fought the mission. Feeds the tooling-gap backlog.

## Planning

- **`spec-kitty specify` forces `topology: coord` by default.** The mission was
  created with a `coordination_branch` and `topology: coord` even though the
  intended shape is `lanes` (no coord). There is no `--topology`/`--lanes` flag on
  `specify`. Workaround: removed the `coordination_branch` key, deleted the coord
  branch, set `topology: lanes` + `flattened: false` in `meta.json`. Candidate
  gap: `specify` should accept a topology choice (or default to `lanes` for
  multi-lane missions).
- **`spec-kitty migrate backfill-topology` is repo-global, not mission-scoped.**
  Running it to recompute one mission's topology rewrote `topology` into **203**
  unrelated `meta.json` files across `kitty-specs/`. Had to `git checkout --` the
  203 incidental files to keep the mission diff clean. Candidate gap: a
  `--mission <slug>` scope flag for `backfill-topology`, or a pure
  `read_topology` path that the planning flow uses without persisting globally.
- (Note: `read_topology(feature_dir)` correctly returns `lanes` once `meta.json`
  carries it; the lanes value will also derive naturally once `lanes.json` exists
  at finalize-tasks.)

## Tasks

- **WP `owned_files` must be RELATIVE, not absolute.** `tasks/guidelines.md` says "Use absolute paths," but the ownership validator (`_CODE_PREFIXES = ("src/", "tests/")`) only matches relative prefixes → absolute paths trigger "code_change WP does not own any files under src/ or tests/". Doctrine/validator inconsistency.
- **WP frontmatter needs `authoritative_surface` + `execution_mode`** (neither shown in `task-prompt-template.md`); finalize-tasks errors "authoritative_surface is empty" without them.
- **Planned-new files need `create_intent:`** (kept in `owned_files` too) or finalize errors "literal file path matches zero files."
- **`finalize-tasks` re-introduces a `kitty/mission-...` mission_branch in `lanes.json`** for lane-worktree coordination — distinct from the removed `coordination_branch` in `meta.json`; topology stays `lanes` (not `lanes_with_coord`). Not friction, just noted.

## Implementation

- **`agent action implement` is gated on `/spec-kitty.analyze`** — must produce `analysis-report.md` via `agent mission record-analysis` (with the `analysis-findings/v1` carrier) before any WP can be claimed.
- **Also gated on `charter sync`** — a `charter_source stale` preflight blocks the claim until `spec-kitty charter sync` runs (regenerates governance/directives/metadata.yaml).
- **The implement workflow writes `vcs`/`vcs_locked_at` into `meta.json` then blocks the NEXT WP claim** until that change is committed (auto-commit disabled). Claiming WP01 dirtied `meta.json`; the WP02 claim then failed "Planning artifacts not committed." Had to `git commit` meta between claims. Friction in a parallel-claim loop — claim all roots back-to-back fails after the first.
- **Worktree ≠ venv**: lane worktrees share `.git` but not `.venv`; each implementer subagent builds its own venv in the worktree (uv cache makes it fast) so tests run against the worktree's code, not the main clone's editable install.
- **Status-desync on `move-task` from a lane worktree** (known friction, reconfirmed): WP01's `move-task --to for_review` run from inside lane-a misread the WP status as `planned`; re-running from the PRIMARY checkout on `mission/doctrine-governance-fidelity` read the correct `in_progress` and succeeded. Mitigation adopted: orchestrator runs the terminal lane transitions (move-task / approve / reject) from the primary checkout; review subagents RETURN a verdict rather than self-transitioning.

- **Issue-matrix acceptance guard is strict** (blocks the first WP `approved`): (1) **exactly ONE** Markdown table allowed in `issue-matrix.md` — a multi-table matrix (targets / reference-by-checklist / prior-art) is rejected; consolidate to one `| Issue | Title | Verdict | Evidence ref |` table, everything else as prose. (2) EVERY `#NNNN` ref detected in `spec.md` needs a row (incl. parent epics, prior-art, even PR numbers). (3) verdict ∈ {`fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission`}; **`deferred-with-followup` requires a follow-up handle** (`#NNN` or the literal `Follow-up:`) in the Evidence cell or it fails. Parents/refs that aren't fixed here → `deferred-with-followup` with a handle; prior-art closed elsewhere → `verified-already-fixed`.

## Campsite / pre-existing debt observed (not introduced by this mission)

- `src/charter/compiler.py:279` (`_resolve_template_set`) — `mypy` `no-any-return`, present on the lane base before WP01's diff. Outside WP01 scope; verify at the pre-PR full-gate sweep whether to campsite-fix.
- **`tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py` — ~20 FAILURES present at the mission base** (constant across WP07 parent → WP08 tip; not caused by any WP). Strongly suspected local Typer/venv-skew (cf. the known golden `isinstance(<TyperGroup>, click.Group)` / help-snapshot skew that fails locally but passes in CI). **Pre-PR action**: determine on CI whether these are real or venv-skew; if skew, gate on CI not the local venv; if real, campsite-fix. (WP08 cycle-1 re-pins ONLY the 1 net-new doctrine snapshot it caused.)
- Test fixtures using the **deprecated top-level `organisation_packs`** config key emit a DeprecationWarning; canonical is `doctrine.org.packs[].local_path` (reviewer-renata, WP08). Non-blocking; deferred.

## Post-merge full-gate sweep — adjudication (campsite, FIXED in merge commit)

Full `tests/architectural/` on the merged branch surfaced **4 mission-caused** cumulative-integration failures no single WP review caught (each lane's gate ran without the full merged picture) — all FIXED:
- `test_no_dead_symbols::test_no_public_symbol_in_all_is_unimported` — `org_profiles.ResolvedOrgProfile` dead in `__all__` (same UnsanctionedOverride pattern) → narrowed `__all__`.
- `test_pytest_marker_convention` + `test_gate_coverage::test_no_new_orphan_surfaces` — 6 new test files had `unit`/no marker → CI-orphans; normalized to `pytest.mark.fast` (the marker WP01/WP06 used and pass).
- `test_no_tmp_paths_in_tests` — `/tmp/acme-org` source_ref literal in the doctor test → `org-packs/acme-org`.

**Pre-existing (NOT mission-caused, confirmed via cross-base on upstream/main — gate on CI):**
- 4× `test_tid251_enforcement` — this primary venv lacks `ruff`/`mypy` (the gates shell to `python -m ruff`); same 4 fail on upstream/main; pass in CI.
- `mypy compiler.py:279` (`no-any-return`) — byte-identical on upstream/main; 665 lines from WP01's change.
- `mypy` yaml-stub errors — missing `types-PyYAML` in the primary venv only (CI has it).

Lesson reinforced: **run the full `tests/architectural/` sweep at the integration/merge point** — per-WP reviews don't run the cross-cutting gates, so dead-`__all__` symbols + orphan-test markers only surface here ([[feedback_post_merge_arch_gate_adjudication]]).
