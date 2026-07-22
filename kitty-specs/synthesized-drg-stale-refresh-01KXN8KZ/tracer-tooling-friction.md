# Mission Tracer — Tooling Friction

**Mission:** `synthesized-drg-stale-refresh-01KXN8KZ` · Fixes [#2681](https://github.com/Priivacy-ai/spec-kitty/issues/2681)

> Seeded at tasks-authoring time. Records frictions with the Spec Kitty
> tooling encountered while authoring/finalizing this mission, so future
> missions (and upstream tooling owners) can learn from them. Assessed at
> close (WP04, T026).

## F1 — The `kitty-specs/` `owned_files` gate forces an indirect ownership declaration

`finalize-tasks` hard-rejects ANY `owned_files` entry under `kitty-specs/`
(`specify_cli.cli.commands.agent.mission_parsing._is_mission_specs_owned_
file`), including a path under a *different* mission's
`kitty-specs/<other-mission>/` tree. This mission's FR-007 external-contract
edit targets
`kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/charter-
status-json.md` — a real deliverable that CANNOT be declared in `owned_files`.
Compounding it: an empty `owned_files` is not a viable escape either, because
`specify_cli.lanes.compute.compute_lanes` raises `LaneComputationError` for
any dependent WP lacking a real ownership manifest. Resolution: WP04 owns a
genuine non-`kitty-specs/` file (the NFR-002 perf test
`test_performance_envelopes.py`), and the contract-doc edit is reviewer-
attested rather than owned. Friction: a WP whose primary deliverable is a
`kitty-specs/` doc has no honest way to declare it; the workaround requires a
co-located real code/test surface. Candidate upstream improvement: allow a WP
to declare a `kitty-specs/` doc as a reviewer-attested (non-owned) artifact.

## F2 — The C-011 per-WP red→green discipline forced a 5-WP → 4-WP restructure

The initial decomposition put all red-first tests in a dedicated "red tests"
WP (old WP02) that stayed red until later WPs turned them green — the `/analyze`
gate flagged this as a mission-level dilution of C-011 (which requires red→green
verified PER-WP: RED on the WP's base, GREEN on the WP's final commit) and as a
plan.md Charter Check that "redefined" C-011 to mission-level. Restructured by
folding each test into the WP that makes it green (schema tests → WP01; writer
tests → WP02, reader-independent; reader tests → WP03), with WP04 as an
explicit no-new-runtime-behavior closeout. Friction: the tension between "author
all red tests up front" (a natural ATDD instinct) and "each WP must be self-
contained red→green" is real when a fix spans schema → writer → reader layers;
the resolution is to make each layer's WP own both its code and the tests that
its code turns green, and to be explicit that the closeout WP is not a behavior
WP. Candidate learning: for layered fixes, decompose by "smallest self-
contained red→green slice," not by "tests vs. code."

## F3 — DIRTY_WORKTREE recorder strictness on unrelated cruft

The finalize/status recorders are strict about a clean worktree; unrelated
pre-existing untracked artifacts in the repo (e.g. stray `kitty-ops/*.jsonl`
and sibling mission dirs from other in-flight work) sit in `git status` and
must be reasoned around when confirming "the mission's own changes are what
got committed." Not a blocker here (finalize commits only the mission's own
files), but worth noting: a per-mission commit-scoping view is cleaner than
eyeballing a repo-wide `git status`.

## F4 — DIR-003 cross-fork assignee limitation

The MOES-Media fork cannot assign the HiC on upstream Priivacy-ai issue #2681
— best-effort per the cross-fork contributor model. This is a documented
caveat, not a tooling defect, but it recurs on every cross-fork mission and is
worth stating so it is not mistaken for a failure.

## F5 — `single_branch` topology desynced from computed lane worktrees

`meta.json` declares `topology: "single_branch"` and the WP prompts direct
implementers to work directly on `fix/2681-synthesized-drg-stale` in the
main checkout, bypassing lane-worktree ceremony. `lanes.json` was
nonetheless computed with four lanes (`lane-a`..`lane-d`, one per WP,
sequential `depends_on_lanes` chain) and materialized as four **sparse-checkout
worktrees** under `.worktrees/synthesized-drg-stale-refresh-01KXN8KZ-lane-{b,c,d}`
(lane-a was apparently cleaned up already; b/c/d were left behind, clean,
zero unique commits beyond the shared `a93ffcf3f`). Every WP was actually
implemented directly on the target branch per instruction, so these three
worktrees are orphaned tooling artifacts, not in-progress work — confirmed
via `git -C .worktrees/<lane> status --short` (empty) before WP04 closeout.
Friction: for a `single_branch`-topology mission, `lanes.json` generation
and worktree materialization should either be skipped entirely or the
lane-worktree lifecycle should be torn down automatically once the operator
routes work to the branch directly, rather than left for a human to notice
and prune by hand at mission close. Not fixed here (out of WP04's owned
surface — `tests/charter/synthesizer/test_performance_envelopes.py` only);
flagged for a follow-up on the `single_branch` + `lanes.json` interaction,
and for manual `.worktrees/`/branch pruning as part of this mission's
close-out housekeeping (see personal workflow note: prune worktrees +
orphaned `kitty/mission-*` branches promptly after a mission merges).

## F6 — `synthesize()` test-suite cwd-pollution footgun (folded into WP04)

`tests/charter/synthesizer/test_orchestrator_synthesize.py::TestSynthesizeEntryPoint`
called `synthesize(full_request, adapter=adapter)` in three tests
(`test_synthesize_returns_synthesis_result`,
`test_synthesize_result_has_target_kind`,
`test_synthesize_result_has_inputs_hash`) WITHOUT `repo_root=`, which
defaults to `Path.cwd()` inside `orchestrator.synthesize`
(`orchestrator.py:184`). Running the suite from the repo root wrote real
synthesized artifacts under the actual project's `.kittify/` tree — a
campsite-dirtying footgun that had polluted the working tree on every broad
test run for this mission (caught while auditing the affected-surface sweep
for WP04's regression gate). Fixed as an out-of-map, justified fold: added
`tmp_path: Path` to all three test signatures and passed
`repo_root=tmp_path`. Verified fix: `pytest
tests/charter/synthesizer/test_orchestrator_synthesize.py -q` (25 passed)
followed by `git status --porcelain -- .kittify/` returning empty — the
suite no longer touches the real project tree. Candidate upstream learning:
any test module that calls a `repo_root`-accepting pipeline entry point
should be linted/reviewed for a missing `repo_root=` kwarg, since the
default-to-cwd behavior is silently dangerous in a test context.

## F7 — `mypy --strict` single-file vs. full-package invocation divergence

The WP-DoD-style single-file invocation (`spec-kitty lint` / `mypy --strict
<file>` in isolation) and CI's full-package invocation (`mypy --strict
src/specify_cli src/charter src/doctrine`) disagree on this mission's
touched files, in BOTH directions:

- Single-file: `charter.*` modules are `follow_imports=skip`'d, so a
  cross-module call's declared return type collapses to `Any` at the call
  site — the repo's existing pattern is to `cast(...)` it back
  (`write_pipeline.py:207,214`, `resynthesize_pipeline.py:568,573`, and
  pre-existing casts elsewhere in the repo, e.g.
  `mission_type_profiles.py:561,565,865`, `status/emit.py:302`,
  `m_2_1_4_enforce_command_file_state.py:78`). Single-file mode needs the
  cast (or would report `no-any-return`).
- Full-package: mypy follows the real module and resolves the concrete
  return type, so the SAME cast now reads as `redundant-cast`.

Both directions are advisory/non-blocking for this project (CI's mypy step
is `continue-on-error`); WP04's full-package run
(`mypy --strict src/specify_cli src/charter src/doctrine`) is authoritative
and reports exactly 9 `redundant-cast` findings — 4 in files this mission
never touched (pre-existing) and 4 in `write_pipeline.py`/
`resynthesize_pipeline.py` that match this pre-existing repo-wide
`follow_imports=skip` cast pattern, not a mission-introduced regression. No
source change made — documented here so a later agent does not "fix" the
casts and break the single-file invocation path.

## Notes (appended during implementation)

- _(append frictions encountered during implementation here)_
- 2026-07-16 (post-merge, PR #2732): the shared `tests/specify_cli/charter_preflight/_fixtures.py` (`seed_manifest`/`make_fresh_repo`) was a regression-net gap. It hand-wrote a pre-fix `schema_version: '2'` manifest with no `bundle_content_hash`, which the new content-identity reader correctly reports `stale` — breaking every caller that expects a non-blocking synthesized_drg. This spanned THREE test dirs the mission's local sweeps missed: `tests/specify_cli/charter_preflight/` (the `integration-tests-charter` shard that went red), PLUS `tests/regression/test_issue_2508.py` and `tests/characterization/test_trio_json_envelope.py`, which reuse the same shared fixture in their implement/claim flows (other CI shards). Fixed at the shared-fixture level: `seed_manifest(built_in_only=False)` now auto-computes the real `compute_bundle_content_hash` and stamps `schema_version: '3'` by default when bundle files are present, so any caller that seeds a fresh bundle gets a genuinely-fresh manifest without threading the hash by hand (explicit `bundle_content_hash=` override preserved for deliberate staleness tests). Learning: a shared test fixture that encodes a schema/contract shape is a single point of regression — when the product's freshness/identity contract changes, grep every importer of the fixture (`charter_preflight._fixtures`) across the WHOLE `tests/` tree, not just the co-located suite, and run all affected shards.

## Mission-close assessment (WP04, 2026-07-16)

All frictions above (F1-F7) were reviewed at close. F1 (ownership-metadata
indirection), F2 (C-011-driven 4-WP restructure), and F4 (DIR-003 cross-fork
assignee limitation) required no further action — they are structural/
process notes, not defects. F3 (DIRTY_WORKTREE recorder strictness) and F5
(single_branch/lanes.json desync + leftover sparse-checkout worktrees) are
tooling-ergonomics gaps outside WP04's owned surface — recorded for upstream
follow-up, not fixed in this mission. F6 (cwd-pollution footgun) WAS fixed
in WP04 (owned test surface, real campsite-cleaning improvement — DIR-025).
F7 (mypy invocation divergence) required no source change — both
invocation modes are advisory and the full-package run is authoritative and
clean of mission-introduced regressions.
