# Tracer: Tooling Friction — up-mission-type-seam

Seeded at planning (specify phase). Append during implementation; assess at close per the
`mission-tracer-files` procedure (charter Standing Order #3).

## Inherited scaffold state

The mission was scaffolded by the phase orchestrator during liveness verification
(`spec-kitty specify up-mission-type-seam --mission-type software-dev --json`), which minted the
ULID-suffixed slug `up-mission-type-seam-01KZY1JB` and the coordination branch
`kitty/mission-up-mission-type-seam-01KZY1JB` in git — but left `HEAD` on `main`, with the
scaffold files (`kitty-specs/up-mission-type-seam-01KZY1JB/`) present as untracked working-tree
content on `main` rather than committed to the coordination branch. This was flagged in advance
as expected/known behavior for this checkout, not something to "fix" with raw git commands —
`git status --short` at the start of this session confirmed exactly that state
(`?? kitty-specs/up-mission-type-seam-01KZY1JB/`, plus an unrelated untracked local scratch
directory entry not touched by this mission).

## Friction encountered while committing: `spec-commit --help` contradicts actual behavior for `spec`-kind artifacts

`spec-kitty spec-commit --mission up-mission-type-seam-01KZY1JB -m '<msg>' kitty-specs/up-mission-type-seam-01KZY1JB/spec.md kitty-specs/up-mission-type-seam-01KZY1JB/tracer-*.md`
refused, verbatim (identical under both the stale global v3.2.5 install on `PATH` and this
checkout's own `uv run spec-kitty` v3.2.6rc2 — ruled out as a stale-install false-red per
CLAUDE.md's documented gotcha class before treating it as a real finding):

```
Error: Refusing to commit planning artifacts to the protected branch 'main'.
Start a non-protected feature branch and commit there: 'spec-kitty mission
create --start-branch <feature-branch>' (or check out an existing feature
branch). Planning artifacts must land on a feature branch.
To retry after materialising the coordination worktree, run:
  spec-kitty spec-commit --mission up-mission-type-seam-01KZY1JB -m '...' <files>
```

The suggested retry (identical to the first invocation, just `--mission`-qualified) does not
change the outcome — it fails with the same error both times.

**Root cause, traced in this checkout's own source** (not guessed): `spec-commit --help` states
"On a protected primary the coordination worktree is materialised on demand so the commit lands
on the coordination branch (materialize-then-retry)." That is no longer true for `spec`-kind
artifacts. `src/mission_runtime/artifacts.py:75-80` documents `MissionArtifactKind.SPEC` as a
`_PRIMARY_ARTIFACT_KINDS` member: "these are PRIMARY-partition kinds... They live with their
mission on the primary `target_branch` for EVERY topology and NEVER transit the coordination
branch." `src/specify_cli/coordination/commit_router.py:253-271` implements this: a primary-kind
placement whose ref is protected is refused outright, with the code comment explicitly stating
"The planning→coord transit is GONE (FR-003 / C-005 / write-surface-coherence WP03 T015), so the
remedy is a feature branch, NOT the coordination worktree." The `--help` text's
"materialize-then-retry" promise appears to describe a still-valid path for COORD-partition kinds
(e.g. `decision_log`) but is stale/misleading for `spec`, which is exactly the artifact kind this
mission needs to commit.

This mission's own scaffold state — created via `spec-kitty specify` with `topology: coord`,
`target_branch: main`, `HEAD` left on `main` (protected), no feature/primary branch minted other
than the coordination branch itself — has no non-destructive remedy available under the
constraints given for this mission (no `git checkout`/`switch`/`branch`, no re-scaffolding via
`spec-kitty mission create --start-branch <...>` since the mission already exists, no hand-edited
`meta.json`). The suggested remedy (`spec-kitty mission create --start-branch <feature-branch>`)
is for originating a *new* mission with a primary branch already chosen at creation time, not for
retrofitting one onto an existing `coord`-topology mission scaffolded via `specify`.

**Outcome (original session)**: `spec.md` and the three tracer files were authored with real,
complete content in the working tree (verified present and non-empty), but could not be
committed via `spec-kitty spec-commit` as instructed. Per the mission brief's explicit
instruction to STOP and report rather than work around a refusing command with raw git, no
commit was attempted outside `spec-commit`. This was reported as tooling friction and recorded
as ledger entry **SK-12** in `SPEC-KITTY-LEDGER.md` (open at the time), and the SPEC phase
returned **BLOCKED**.

## Resolution — operator adjudication

The operator adjudicated the branch-discipline conflict in the charter's favor: creating a PR
branch is explicitly sanctioned for exactly this refusal (charter Agent Push Authorization
section; `CLAUDE.md`'s PR-branch flow), and the "never `checkout -b`" instruction in the original
mission brief had assumed a scaffold-minted branch that this `coord`-topology + protected-primary
path never creates. The operator authorized, one time only: `git checkout -b
pr/up-mission-type-seam` from `HEAD` (`ab0a0b9b5`, where the authored artifacts already sat
uncommitted in the working tree — no re-authoring, no re-scaffold).

With `HEAD` on `pr/up-mission-type-seam` (not `main`), `spec-kitty spec-commit` was retried
first, unchanged invocation:

```
spec-kitty spec-commit --mission up-mission-type-seam-01KZY1JB -m "..." kitty-specs/up-mission-type-seam-01KZY1JB/spec.md ...
```

**It still refused with the identical `main`-protected-branch error**, even though the actual
checked-out branch was `pr/up-mission-type-seam`. This confirms the routing this command uses is
not `HEAD`-based: it derives its placement/target from `meta.json`'s `target_branch: "main"`
(`src/specify_cli/coordination/commit_router.py`'s placement resolution reads mission state, not
the live git ref), so simply moving `HEAD` off the protected branch does not change the verdict —
only a `meta.json` `target_branch` update (which this mission's constraints forbid hand-editing)
or a code fix would. **This is new, load-bearing evidence for SK-12**: the defect is not merely
"no branch was minted," it is "the command's protected-branch check is blind to the branch
actually checked out." Appended to SK-12 in `SPEC-KITTY-LEDGER.md`.

**Fallback used successfully**: a plain `git add` + `git commit` (conventional message,
`docs(spec): ...`) on `pr/up-mission-type-seam`, per the operator's explicit fallback
authorization. This is the path that actually worked. The untracked local scratch directory was
left untracked deliberately (local R&D context, not a mission artifact). No further `spec-commit`
retries were attempted after the second refusal — the working `git commit` fallback was used directly, per the
operator's instruction to record which path worked rather than keep probing the broken one.

## Friction encountered at TASKS-phase preflight: `finalize-tasks` whole-text FR-\d+ scan trips on a foreign citation (upstream #3394)

Before dispatching a WP author or invoking `spec-kitty agent mission finalize-tasks`, this
mission's TASKS-phase preflight (per the mission brief's pre-armed-landmine list) ran:

```
grep -oE '\b(FR|NFR|C)-[0-9]+\b' kitty-specs/up-mission-type-seam-01KZY1JB/spec.md | sort -u
```

and found `FR-032` alongside this spec's own `FR-001..FR-013`. `FR-032` appeared exactly once,
at `spec.md:77`, inside CL-002's verbatim quotation of a *different* mission's ADR decision
driver: `"...'no silent fallback' contract (R-009/CL-1, FR-032, pinned by
tests/doctrine/test_org_pack_augmentation.py)..."` — a citation providing context for why
`ArtifactKind` promotion (#2468) is risky, not a requirement this mission declares or any WP
could legitimately claim.

**Root cause, verified against this checkout's own source, not guessed.**
`src/specify_cli/requirement_mapping.py:16`'s `_REF_FIND_PATTERN` regex-scans spec.md's entire
raw text (`mission_finalize.py:342-353` feeds it the whole file), with no table-scoping and no
allowlist for a marked citation — a bare `FR-\d+` token anywhere in prose, including inside a
quoted sentence about another mission's contract, is folded into
`functional_spec_requirement_ids`. `_validate_requirement_mapping`
(`mission_finalize.py:609-663`) then computes `unmapped_functional_requirements =
functional_spec_requirement_ids - mapped_requirement_ids`; since no WP in this mission could
honestly claim FR-032 (it belongs to another mission's spec), `finalize-tasks` would have
hard-failed with "Requirement mapping validation failed" (`typer.Exit(1)` at line 663) — this is
the same tooling defect class the mission brief pre-armed as landmine #1 / upstream #3394.

**Two remediation options were weighed, not just one applied silently:**

- **Option A** — mark the citation as an intentionally altered quotation (scholarly bracketed
  elision), so the regex no longer matches, while the quoted ADR's meaning, its R-009/CL-1
  anchor, and the pinned test path all survive.
- **Option B** — have WP01 (the ADR work package, which already discusses this exact quoted
  driver per CL-002(b)) list `FR-032` among its own claimed requirements purely to satisfy the
  mapping check. **Rejected**: this would write a false requirement claim into
  `acceptance-matrix.json` and the eventual retrospective's FR-coverage accounting — trading one
  silent-wrongness (the regex false-positive) for another (fabricated traceability) — exactly
  the class of defect this mission's own NFR-002/CL-006 exist to eliminate. An agent choosing
  Option B unilaterally, without operator sign-off, would itself be a silent-wrongness
  violation.

**Operator ruling (2026-08-13)**: Option A, executed as a bracketed editorial elision, not a
silent reword. `spec.md:77` changed from:

```
   'no silent fallback' contract (R-009/CL-1, FR-032, pinned by
```

to:

```
   'no silent fallback' contract (R-009/CL-1, [no-silent-fallback FR], pinned by
```

Verified post-edit: `grep -oE '\bFR-[0-9]+\b' spec.md | sort -u` returns exactly `FR-001` through
`FR-013` — this spec's own declared set, nothing foreign. The bracketed form does not itself
match `\bFR-[0-9]+\b`. `C-011` (`spec.md:313`, "the charter's ATDD-first discipline (C-011)") was
re-confirmed as charter-numbering, not a foreign mission constraint, and does not feed the
`FR-`-only hard-fail set per the source read above — left untouched.

This is a **marked quotation elision**, not a silent content change: it alters no requirement,
scope claim, or acceptance criterion in this mission's own spec — the operator judged (and this
phase agent independently confirmed by re-reading the edited passage in full) that no delta
re-review of `spec.md` was required for this class of edit. See
`reviews/tasks.ruling.md` for the full ruling record. This tooling defect (whole-file regex scan
with no table-scoping or citation-marking convention) matches upstream #3394 and is a TASKS-phase
tooling-friction entry, distinct from this file's earlier SPEC-phase SK-12 entry above.

## Friction encountered mid-TASKS-phase: two more tooling gaps found and worked around before `finalize-tasks` would validate

**Gap A — `wps.yaml`'s `requirement_refs` field is silently ignored by `finalize-tasks` when
`wps.yaml` is present.** `_resolve_dependencies_and_refs`
(`src/specify_cli/cli/commands/agent/mission_finalize.py:473-521`) reads `dependencies` from
`wps.yaml` when present (line 491-493), but reads `requirement_refs` ONLY from each WP file's
own frontmatter (line 496, `_parse_requirement_refs_from_wp_files`) — the `wps.yaml`-derived
tasks.md-text fallback that WOULD have caught this (`_parse_requirement_refs_from_tasks_md`,
line 505-508) is gated behind `wps_manifest is None` (line 498), so it never runs at all once a
`wps.yaml` exists. The author subagent had (correctly, per its brief) populated
`requirement_refs` in `wps.yaml` and in `tasks.md`'s own "**Requirement Refs**:" prose lines,
but not in each WP `.md` file's own frontmatter (the schema-declared field for that data), since
nothing in the canonical templates it was pointed at states that WP-frontmatter
`requirement_refs` is the ONLY field this specific validation path reads once `wps.yaml` exists.
Confirmed live, not guessed: `spec-kitty agent mission finalize-tasks --validate-only --json`
reported `unmapped_functional_requirements: [FR-001..FR-013]` (all 13) and
`requirement_refs_parsed: {}` (empty for every WP) on the first run, despite `wps.yaml` and
`tasks.md` both carrying complete, correct data. **Fix used — the canonical CLI, not a hand
edit**: `spec-kitty agent tasks map-requirements --mission up-mission-type-seam-01KZY1JB
--no-auto-commit --json --batch '{"WP01": [...], ...}'` (values taken directly from `wps.yaml`,
already internally consistent with `tasks.md`), which writes `requirement_refs` into each WP
file's frontmatter through the tool's own supported mapping surface. Re-running
`--validate-only` afterward showed `unmapped_functional: []` and `requirement_refs_parsed`
fully populated. This is a real gap between `wps.yaml`'s declared schema (which includes
`requirement_refs`) and what the finalize-tasks validation path actually consults when
`wps.yaml` is present — a candidate for its own upstream issue, not filed here since it is
mission-tooling-friction, not this mission's own defect.

**Gap B — cosmetic ownership_warning for a planning-only WP with no IC mapping.**
`finalize-tasks --validate-only` warned `WP01 ... missing plan_concern_refs and cross_cutting is
not set` — WP01 is the mandatory ADR (spec CL-002/FR-012), which precedes and grounds every
IC-tagged WP rather than being one IC-##'s own slice, so it legitimately has no single
`plan_concern_refs` entry. Resolved by setting `cross_cutting: true` on WP01's `wps.yaml` entry
(an honest statement of what WP01 actually is, not an invented IC reference) rather than leaving
the warning unaddressed. Confirmed via re-run: `ownership_warnings: []` afterward.

Both gaps were found and resolved via canonical CLI surfaces (`map-requirements`) or a
one-line, schema-legitimate `wps.yaml` field correction — no hand-edited WP frontmatter, no
invented enum values, no bypass of `finalize-tasks`'s own validation. `finalize-tasks` (full run,
not `--validate-only`) then completed its validation+generation cleanly (7 WPs, `lanes.json`,
WP-frontmatter bootstrap) and failed only at its terminal git-commit step on the protected
`main` target — this is the SK-13 landmine, pre-armed in this mission's brief and corroborated
a third time in `SPEC-KITTY-LEDGER.md`. Landed via `spec-kitty safe-commit --to-branch
pr/up-mission-type-seam`, per the documented working fallback — never `--target-branch`.

## Friction discovered during the TASKS-phase adversarial fix round: `finalize-tasks`-generated `lanes.json` carries a real, mechanically-consumed cyclic `depends_on_lanes` graph

An adversarial post-tasks review (finding TASKS-SEQ-001, severity 4) confirmed this mission's own
`lanes.json` — generated by `finalize-tasks`, not hand-authored — contains a real dependency cycle
at the lane level: `lane-a` (WP02+WP03+WP07, collapsed together by the `write_scope_overlap` rule
because WP02 shares files with both WP03 and WP07) declares `depends_on_lanes: [lane-b, lane-c,
lane-planning]`, while `lane-b` (WP04+WP06) and `lane-c` (WP05) both declare `depends_on_lanes:
[lane-a]` — `lane-a <-> lane-b` and `lane-a <-> lane-c`, simultaneously, in the same generated
file.

**Root cause, traced in this checkout's own source, not guessed.** The collapse rule
(`src/specify_cli/lanes/compute.py`) unions WP02+WP03+WP07 into one lane purely on pairwise
write-scope overlap, without checking whether the union would create a lane-level cycle against
the *other* lanes those WPs' real dependencies touch. `_compute_lane_depths`'s own docstring
(`compute.py:615-629`) admits this directly: "Self-loops and cycles in `lane_deps` are detected
via the `in_progress` guard and treated as depth-0 anchors rather than recursing infinitely. Cycle
detection is best-effort... Callers that need cycle-accurate depths should validate the lane graph
before invoking." No caller does that validation: `compute_lanes` (`compute.py:279-576`) returns
`LanesManifest` without ever calling a lane-graph cycle check, and its only call site
(`src/specify_cli/cli/commands/agent/mission_finalize.py:1352`, confirmed live — the WP-level
`detect_cycles` call at line 585 checks `wps.yaml`'s own acyclic WP-dependency graph, a different
graph, not this lane-level one) writes `lanes.json` straight through with no rejection or warning
path for a cyclic `depends_on_lanes` graph.

This is not inert: `src/specify_cli/lanes/worktree_allocator.py`'s `_merge_dependency_lane_tips`
(confirmed live at `worktree_allocator.py:419-514`) mechanically consumes `depends_on_lanes` for
real `git merge` operations at worktree-allocation time. For this mission specifically, allocating
`lane-a`'s worktree (to run WP02, then later WP07) will have the allocator attempt to merge
`lane-b`'s and `lane-c`'s tips per `lane-a`'s own `depends_on_lanes` — tips that, for the WP02
portion of `lane-a`'s work, do not exist yet, because `lane-b`/`lane-c` themselves declare
`depends_on_lanes: [lane-a]` and are waiting on `lane-a`'s own WP02/WP03 commits first.

**Correction (adversarial fresh-sweep post-tasks review, finding TASKS-FRESH-001, severity 4):** an
earlier version of this entry, and matching text in `wps.yaml`'s header comment and WP07's prompt
(Branch Strategy section), characterized `_merge_dependency_lane_tips`'s reuse-path catch-up as
requiring a manual-verify-or-bypass workaround — including a sentence authorizing the
implementer to "bypass automatic lane-based allocation for WP07 and construct its workspace
directly against the mission coordination branch" if the allocator's merge could not be trusted.
That sentence was itself a doctrine violation: CLAUDE.md's Execution Workspace Strategy section
states plainly that "`spec-kitty implement WP##` is the only supported way to prepare a
workspace. Agent commands must consume the resolved workspace path, not reconstruct it," under a
section titled CRITICAL. It also overstated the risk. The reuse path in
`allocate_lane_worktree` (`worktree_allocator.py:194-207`) explicitly re-runs
`_merge_dependency_lane_tips` on every reuse for exactly this scenario — the function's own
docstring and inline comments cite issue #1684 and name the prior real incident this mechanism was
built to catch ("the WP05/WP09 double-hit on 01KTYGTE"), and the merge is idempotent (an
already-merged tip is a no-op ancestor). A dependency branch that does not yet resolve is handled
as warn + skip, falling back to the existing base rather than crashing
(`worktree_allocator.py:456-467`) — never a merge of "content that does not exist yet." Because
WP07's own WP-level `dependencies: [WP05, WP06]` already gates its claim/start until those WPs are
approved/done (CLAUDE.md's Status Model Patterns dependency-gating rule), by the time WP07 can
actually be claimed `lane-b`'s and `lane-c`'s branches are guaranteed to exist and the catch-up
merge should succeed cleanly on the ordinary `spec-kitty implement WP07` path. The bypass sentence
has been removed from both `wps.yaml`'s header and WP07's prompt and replaced with a
verification-only instruction that stays on the canonical path: after running
`spec-kitty implement WP07`, resolve `lane-b`'s and `lane-c`'s actual branch names inside the
resulting worktree — `git branch -a --list '*lane-b*'` and `git branch -a --list '*lane-c*'` —
then confirm `git merge-base --is-ancestor <resolved lane-b branch> HEAD` (and the equivalent for
`lane-c`'s resolved branch) holds, i.e. each lane's tip commit landed as an ancestor of HEAD,
meaning the catch-up merge actually happened; if it did not, that is evidence of a genuine
allocator bug to report upstream, never a license to hand-construct the workspace.

**What remains a legitimate tooling-friction observation, unchanged by this correction:** the lane
graph really is cyclic at the `depends_on_lanes` level (`lane-a <-> lane-b`, `lane-a <-> lane-c`),
and `compute_lanes` (`src/specify_cli/lanes/compute.py`) does not validate the lane graph for
cycles before writing `lanes.json` — `_compute_lane_depths`'s own docstring
(`compute.py:615-629`) admits cycle detection there is "best-effort" and that "callers that need
cycle-accurate depths should validate the lane graph before invoking," which `compute_lanes`
does not do. That the mechanism happens to self-heal safely on the read/consume side
(`worktree_allocator.py`) does not mean the write side (`compute.py`) should be silently emitting
a cyclic graph in the first place; a write_scope_overlap collapse that can produce a lane-level
`depends_on_lanes` cycle whenever a first-WP/last-WP pair in a mission shares files with an
unrelated middle lane on both temporal sides remains a candidate for its own upstream issue against
`src/specify_cli/lanes/compute.py`, filed here as tooling-friction, not fixed in this mission's own
diff. No attempt was made to hand-edit `lanes.json` (finalize-tasks-generated) or to patch
`compute.py`/`worktree_allocator.py` — both are upstream spec-kitty tooling, not this mission's own
scope.

## ANALYZE phase: `record-analysis` returned `verdict: ready` cleanly — SK-06 disposition (artifacts-vs-tooling, evidence recorded either way)

Per this mission brief's explicit instruction, `SPEC-KITTY-LEDGER.md`'s SK-06 entry
(`record-analysis` silently accepting a legacy/malformed carrier and writing `verdict: unknown`,
`src/specify_cli/analysis_report.py:358` plus two more triggers added 2026-08-14 by mission
`org-pack-drg-root-graph-guard-01KZY0QT`: `_split_carrier`'s missing-leading-`---`-fence silent
drop at `analysis_report.py:243`, and the self-re-feed trap where `record-analysis`'s own output
frontmatter shape is exactly the "legacy" shape trigger 1 rejects) was treated as a live risk to
rule out by evidence, not assumed innocent.

**Detection passes run** (per `packs/built-in/missions/mission-steps/software-dev/analyze/prompt.md`
§4 A–F) over `spec.md`, `plan.md`, `tasks.md`, `wps.yaml`, `tasks/WP01..WP07-*.md`, `lanes.json`
found **zero findings**: all 13 FRs trace to an owning WP (cross-checked three ways: `spec.md`'s
own table, `wps.yaml`'s `requirement_refs`, and each WP `.md`'s own frontmatter — identical sets);
the ruling-corrected IC sequencing (IC-06/WP02 first, only IC-02/WP04 depends on IC-01/WP03,
IC-03-IC-04/WP05 independently sequenced) is consistently reflected in every WP's `dependencies`
field; the two "same PR" atomicity statements (plan.md:707 WP03/WP04/WP06; plan.md:842-843
WP02/WP07) do not contradict the WP dependency graph (both groupings are already forced by the
existing linear/transitive dependency chains, and this mission ships as one PR regardless per
spec-kitty's own one-PR-per-mission default); the `spec.md:77` bracketed `[no-silent-fallback FR]`
elision is the operator-authorized citation edit recorded in `reviews/tasks.ruling.md`, not drift.

**Carrier construction deliberately avoided all three SK-06 triggers**, verified before persisting,
not assumed: (1) `schema: analysis-findings/v1` typed exactly, byte-checked against
`FINDINGS_SCHEMA_V1` in `src/specify_cli/analysis_report.py:41`; (2) the temp report file's first
three bytes are literally `---` with no leading blank line or whitespace (`head -c 10 | xxd`
confirmed `2d2d 2d0a` before the file was ever handed to the CLI, and a standalone
`yaml.safe_load` of the extracted frontmatter block was validated to parse before invoking the
real command); (3) the file was authored fresh for this run, not a re-fed copy of a previously
`record-analysis`-persisted `analysis-report.md` (which carries `schema_version`/`artifact_type`,
the shape trigger 3 warns about), so trigger 3 does not apply here either.

**Result**: `spec-kitty agent mission record-analysis --mission up-mission-type-seam-01KZY1JB
--input-file <temp-carrier> --agent claude --json` returned `"success": true, "verdict": "ready",
"findings": [], "issue_counts": {all-zero}` — and the persisted `analysis-report.md`'s own
frontmatter independently confirms `verdict: ready` on disk, not merely in the command's stdout.
**Disposition: artifacts, not tooling, drove this result** — the zero-findings verdict reflects
three prior PASSED R1–R6 adversarial review loops over spec/plan/tasks (two of which HALTed and
were operator-resolved), not a tooling swallow. SK-06 was not triggered on this run; this is
recorded as a clean data point for the ledger entry regardless (the instruction to "leave a tracer
entry either way" is honored here even though the outcome was the boring one).

**Housekeeping**: `record-analysis` scopes its `DIRTY_WORKTREE` guard to the whole repo tree, which
would have caught the untracked local R&D scratch directory at repo root (unrelated to this
mission, never read or cited). Used the sanctioned non-destructive workaround: moved that
directory to a scratch path outside the repo, ran the command, moved it straight back, and diffed
`git status --short` before/after each move — identical apart from the new `analysis-report.md`
itself. No content under that scratch directory was read or cited in this report.

## WP01 (ADR authoring) — minor environment friction, no tooling defect

`.venv` in this checkout had zero dependencies installed (`No module named pytest`) despite
`.venv/bin/python3` existing — this is a fresh worktree checkout, not a stale-install false-red per
CLAUDE.md's category 3, since no package was ever installed at all. `uv run pytest ...` did not
auto-sync the environment as CONTRIBUTING.md's "Developer Setup" section implies it should; an
explicit `uv sync --frozen --all-extras` was required first before any `uv run pytest`/`uv run
python -m pytest` invocation would resolve `pytest`. Confirmed this checkout's own `.venv` is a
plain local directory (not a symlink into a shared/other-checkout venv), so the sync was safe and
did not touch a concurrently-running sibling checkout running a heavy test suite. Not filed
upstream — plausibly expected first-run setup, not a regression — but recording it since the WP01
prompt's Gate Set assumed `uv run pytest`/`make lint` would "just work" without a prior `uv sync`.
`spec-kitty safe-commit docs/adr/... --to-branch pr/up-mission-type-seam -m "..."` worked cleanly
on the first try (files-then-flags positional order, `--to-branch` not `--target-branch`) — the
SK-13 defect this WP's brief warned about did not manifest; `meta.json.target_branch` is `main`
but the branch already checked out was `pr/up-mission-type-seam`, so the tool committed there
without complaint.

## WP01 rework — public-repo hygiene remedy for CLI-emitted absolute paths

The reviewer rejected WP01 (severity 4) for local-path leakage in this tracer and, separately, for
four absolute `path:` values in `analysis-report.md`'s `input_artifacts:` frontmatter. This
tracer's own local-path phrasing was rewritten by hand to generic terms (as done above throughout
this file); that part was an authoring slip, not a tooling defect.

The `analysis-report.md` paths are a different kind of finding: they were emitted by spec-kitty
itself, not by an agent. `collect_input_artifact_hashes` (`src/specify_cli/analysis_report.py:208-217`)
stringifies absolute paths into `input_artifacts[*].path` rather than repo-relative ones. That is a
real upstream defect in the CLI's `analyze`/`record-analysis` path, now filed as **issue #3398**.
This mission cannot regenerate the report to fix it — regenerating would just re-emit absolute
paths from the same code path — so the four `path:` values were rewritten by hand to their
repo-relative form as a public-repo-hygiene remedy scoped to this mission's own artifact. The
`sha256:` values were left untouched (they hash file content, not the path string, so they remain
valid) and the previously-approved `docs/adr/3.x/2026-08-13-1-mission-type-roster-layering-seam.md`
was not touched. See #3398 for the root-cause fix.

## WP02 (campsite-clean deletions) — plan.md under-scoped one deletion's gate blast radius

plan.md's IC-06 bullet states its Risks are "none identified beyond the import-pruning precision
already called out" for the `list_cmd` cluster, and separately asserts in the Gate Set table that
"this WP's deletions must not regress `test_no_dead_symbols` ... if anything, deleting
confirmed-dead code should only ever help these gates, never hurt them." That second claim was
empirically false for `resolve_mission_steps` specifically: the function's own body contained a
local `from charter.mission_steps import MissionStepRepository`, which turned out to be the *last*
`src/` import of that name reached through the `charter.mission_steps` facade module (the symbol
stays live overall via the sibling `charter.missions` facade, which has its own real caller).
Deleting `resolve_mission_steps` therefore tripped two live architectural gates that plan.md's own
reasoning said this WP could not trip:
`tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported` and,
independently, a new test's `len(...) == 1` assertion tripped
`tests/architectural/test_golden_count_ban.py::test_convert_sites_do_not_exceed_frozen_baseline`.
Both were confirmed introduced-by-this-WP (not pre-existing) by running the two failing tests
against the pre-edit parent commit in a disposable `git worktree`, where both passed — then fixed
in-repo (following this codebase's own established `MissionStep` re-export-retirement precedent
for the first, and the documented `# golden-count: cardinality-is-contract` escape hatch for the
second), not by widening an allow-list or relaxing either gate. Not a spec-kitty CLI defect and not
filed upstream — a planning-document accuracy gap specific to this mission's own plan.md, worth
recording so a later WP in this mission (or a reviewer) does not have to re-derive why a "pure
deletion" commit touched two files outside the WP's originally-listed `owned_files`
(`src/charter/mission_steps.py`, `tests/architectural/test_charter_facades_reexport_doctrine.py`).
The lesson for future campsite-clean WPs in this or other missions: a claim that a dead-code
deletion "can only ever help" the architectural gates should be verified by actually running those
gates before asserting it in plan.md, not inferred from the deletion's own confirmed-dead-caller
count in `src/`/`tests/` alone — a symbol's *facade re-export* liveness is a separate, narrower
fact than its overall liveness.

## WP05 (FR-003/FR-005 mission-type org/project layer scan) — an unowned, pre-existing test file pins the exact pre-fix bug as "correct" behavior

WP05's own owned files are `src/charter/pack_manager.py` and `tests/charter/test_pack_manager.py`
only, disjoint from WP03/WP04. That disjointness held for the two files this WP actually needed to
touch. It did **not** hold for a third file this WP never listed and does not own:
`tests/charter/test_pack_manager_catalog.py`. That file predates this mission entirely (last
touched by an unrelated prior mission, confirmed via `git log -- tests/charter/test_pack_manager_catalog.py`
against `f419ec4ba..HEAD` showing no hits) and is not referenced anywhere in `wps.yaml` or any of
this mission's WP prompts.

Its `TestResolveLayerCandidate` class contains two tests that call
`charter.pack_manager._resolve_layer_candidate` directly and assert the exact pre-fix bug this WP
exists to close as expected behavior:

```python
def test_flat_kind_org_layer_has_no_candidate(self, tmp_path: Path) -> None:
    """Mirrors the pre-extraction ``else: continue`` — a non-built-in
    layer for a flat (``layered=False``) kind has no known directory."""
    assert _resolve_layer_candidate("org", tmp_path, None, "missions/mission_types", layered=False) is None

def test_flat_kind_project_layer_has_no_candidate(self, tmp_path: Path) -> None:
    assert (
        _resolve_layer_candidate("project", tmp_path, None, "missions/mission_types", layered=False) is None
    )
```

There is no way to satisfy FR-003 (org/project mission-type resolution) while keeping these two
assertions green — they assert `is None` for the exact `(layer, kind=None, layered=False)` inputs
the fix must resolve to a real directory. This was confirmed empirically, not assumed: after
landing WP05's fix, a single full run of `tests/charter/` showed **exactly these two tests, and
only these two**, newly red (2 failed, 2209 passed, 4 skipped) — no other test in the suite was
affected.

Per this WP's explicit write-scope-isolation instruction ("if your change appears to require
editing a file outside that set, STOP and report it rather than editing"), `test_pack_manager_catalog.py`
was **not** touched. The two now-stale assertions are left red on purpose, reported here rather
than silently fixed, for whoever integrates this mission's WPs to adjudicate — most likely by
updating those two assertions to the new, FR-003/FR-005-correct expected paths (mirroring the
equivalent new pins this WP added in its own `tests/charter/test_pack_manager.py`,
`TestResolveLayerCandidateMissionTypeLayers`), since the old assertions encode the bug the mission
was chartered to fix, not a behavior worth preserving.

**Confirmed no other blast radius**: `resolve_layer_roots`
(`src/specify_cli/cli/commands/charter/_layer_roots.py`) and `activate_cmd`
(`src/specify_cli/cli/commands/charter/activate.py`, `layer_roots = resolve_layer_roots(repo_root)`
at its call site, then passed straight through to `manager.activate(...)`) already resolve and pass
`layer_roots` generically for every charter-activatable kind including `mission-type` — neither
needed any change, as this WP's own prompt anticipated. The `rglob`-vs-`glob` distinction in
`list_available_detailed` was deliberately left unchanged, per the mission ADR's own rationale
(CL-005's flat layout structurally avoids the trap without needing the broader, out-of-scope
`rglob`→`glob` change); a new test (`TestMissionTypeProjectLayerNonCollision::test_rglob_would_leak_a_nested_per_type_subdirectory`)
empirically demonstrates that `rglob` would still descend into a hypothetical nested per-type
subdirectory under the roster location if one were ever created there, confirming the safety comes
from the flat-layout convention this mission commits to, not from the scan being non-recursive at
the code level.

## Integration item — re-pinning the two stale `TestResolveLayerCandidate` assertions WP05 flagged

Per WP05's entry above, `tests/charter/test_pack_manager_catalog.py::TestResolveLayerCandidate`
carried `test_flat_kind_org_layer_has_no_candidate` and
`test_flat_kind_project_layer_has_no_candidate`, both asserting `_resolve_layer_candidate(...) is
None` for exactly the `(kind=None, layered=False)` org/project inputs FR-003/FR-005 now resolve to
real directories. An independent reviewer adjudicated these as **stale, not a real contract break**
— no implementation of FR-003 could satisfy both these assertions and the spec simultaneously.

**Independently verified before editing, not taken on faith**: read both tests and the full body of
`_resolve_layer_candidate` in `src/charter/pack_manager.py`. The two branches added by WP05's commit
(`fix(charter): resolve mission-type org/project layers in _resolve_layer_candidate`) are exactly
`kind is None and layer == "org"` → `root / "mission_types"` and `kind is None and layer ==
"project"` → `root / "missions" / "mission_types"` — the identical `(layer, kind, layered)` triples
the two stale tests exercised. `tests/charter/test_pack_manager.py::TestResolveLayerCandidateMissionTypeLayers`
(WP05's own new pins, added in the same mission) asserts the same two directories for the same
inputs, confirming this is the current, intended contract rather than a coincidence.

**Re-pinned** (scope: `tests/charter/test_pack_manager_catalog.py` only, no production code touched):
- `test_flat_kind_org_layer_has_no_candidate` → renamed
  `test_flat_kind_org_layer_resolves_to_pack_root_mission_types`; asserts the candidate equals
  `tmp_path / "mission_types"` and cites FR-003 instead of the retired `else: continue`.
- `test_flat_kind_project_layer_has_no_candidate` → renamed
  `test_flat_kind_project_layer_resolves_to_kittify_missions_mission_types`; asserts the candidate
  equals `tmp_path / "missions" / "mission_types"` and cites FR-005 instead of the retired
  `else: continue`.

**Discriminating-ness proven, not assumed**: reverted `src/charter/pack_manager.py` to its
pre-WP05 state (`5491d3570`, the commit immediately before `1defeaed8`) in a disposable `git
worktree` under `/tmp`, copied the re-pinned test file into that worktree, and ran the two tests
there. Both **failed** against the pre-WP05 code (`AssertionError: assert None == ...`), confirming
they still catch a regression back to the old `else: continue` behaviour. The worktree was removed
immediately after. Against the current branch, both gates are green:
`tests/charter/test_pack_manager_catalog.py` — 27 passed; `tests/charter/test_pack_manager.py` — 39
passed (unaffected). `make lint` passes clean.

## WP03 (FR-001 layered lookup cache) — `diff-cover`'s `--include` pattern is filesystem-glob-based, not fnmatch, so `ci-quality.yml`'s own `'src/doctrine/*'` critical-path pattern silently excludes nested files

`ci-quality.yml`'s `diff-coverage (critical-path, enforced)` step calls `diff-cover ... --include
'src/kernel/*' 'src/doctrine/*' 'src/charter/*' ...`. Reproducing that exact invocation locally
(`diff-cover coverage.xml --compare-branch=origin/main --fail-under=90 --include 'src/doctrine/*'`)
against this WP's own diff produced `No lines with coverage information in this diff.` for
`src/doctrine/missions/mission_type_repository.py` — a 213-line diff in the WP's own owned file,
verified present via plain `git diff --stat origin/main...HEAD -- src/doctrine/missions/mission_type_repository.py`.

Traced to `diff_cover/diff_reporter.py`'s `_is_excluded`: for each `--include` pattern it calls
`glob.glob(pattern, recursive=True)` (a **filesystem** glob against the current working
directory) and checks whether the diff's path is a member of that result set — it is not an
`fnmatch`-style string match despite one existing elsewhere in the same module for `--exclude`.
Confirmed by hand: `glob.glob('src/doctrine/*', recursive=True)` returns only the *direct*
children of `src/doctrine/` (e.g. the bare directory entry `src/doctrine/missions`, not anything
beneath it) — `recursive=True` only makes `**` segments recursive; a single `*` still stops at one
path segment, exactly like a shell glob. Any file nested one level deeper than the pattern's own
depth — `src/doctrine/missions/mission_type_repository.py`, `src/doctrine/agent_profiles/*.py`,
`src/charter/context_renderers/*.py`, etc. — is silently excluded from every diff-coverage number
the gate reports, with no warning that the pattern matched nothing for that file.

**Practical effect**: the CI gate's 90% enforcement, as currently configured, provides zero actual
diff-coverage signal for the large majority of `src/doctrine/` and `src/charter/` — both packages
are almost entirely organised into subpackages, not flat files directly under the package root.
Verified the corrected, doubly-starred pattern behaves as the maintainers evidently intended:
`glob.glob('src/doctrine/**/*.py', recursive=True)` does include the nested file; re-running
`diff-cover` with `--include 'src/doctrine/missions/mission_type_repository.py'` (an exact-path
workaround, not a real fix) reported this WP's own changed-line coverage correctly (95.6% on the
first pass, two branches short; 100% after two additional tests were added to close the gap —
`_load_layered_mission_type_file`'s non-mapping-YAML and id/filename-stem-mismatch raise paths).

This is a real, upstream-facing tooling gap in `ci-quality.yml`'s own `diff-coverage` step
configuration (the `critical_paths` array), not something this WP's `owned_files` cover — flagging
here rather than silently reaching outside scope to fix `ci-quality.yml`. The fix, when someone
picks it up, is almost certainly changing every single-star critical-path entry that names a
package root (`'src/doctrine/*'`, `'src/charter/*'`, `'src/kernel/*'`) to its doubly-starred form
(`'src/doctrine/**/*.py'`, etc.) so the existing `recursive=True` flag actually reaches nested
files as the workflow's own step name ("critical-path, enforced") implies it should.

## WP03 (FR-001 layered lookup cache) — the symbol-level dead-code gate reds for one commit inside a WP that intentionally ships a seam ahead of its caller

`tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported` requires
every `__all__` entry to have at least one live `src/` caller. This WP's own prompt is explicit
that WP03 ships the new `resolve_layered_mission_types` factory with **zero** callers in `src/` on
purpose (its Risks section: "this WP adds no caller in `charter.*` at all — WP04 does"), because
NFR-004's import-time-IO gate forbids wiring a caller this early. Adding the new factory to
`__all__` (the natural first move, matching this module's own existing public-cached-function
convention for `builtin_mission_type_ids`) trips the dead-symbol gate for exactly this WP's own
diff, in isolation.

Applied the gate's own documented remediation, in its own stated order of preference: option 2,
"Remove the symbol from `__all__` (it stays in the module as an unexported internal)" — not option
4 (an `_SYMBOL_ALLOWLIST` entry, which the gate's own message frames as the *last* resort and
which would need a tracker ticket this WP doesn't have reason to mint). The function stays fully
importable via an explicit `from doctrine.missions.mission_type_repository import
resolve_layered_mission_types` (exactly how this WP's own tests, and WP04's future caller, reach
it) — `__all__` only governs `import *` and this one gate's public-API scan, neither of which an
explicit import needs. Left a `# NOTE:` comment beside `__all__` in the source pointing future WP04
work back to re-add the entry once a real caller lands. Confirmed via a full local
`tests/architectural/` run before and after: the gate is the *only* new failure this WP introduces
(one other failure, `test_golden_count_ban.py::test_convert_sites_do_not_exceed_frozen_baseline`,
is pre-existing from WP05's `tests/charter/` changes, confirmed identical message/count before and
after this WP's own commits — not touched, out of this WP's `owned_files`).

## WP04 (FR-002 PackContext threading) — the repository-call swap in `_resolve_action_slot` collided with two unowned test files' `sys.modules`-injection mocks

WP04's own prompt requires `_resolve_action_slot` to swap its repository call from
`MissionTypeRepository.default()` to WP03's new `resolve_layered_mission_types` factory (not
argument-threading — a different callable entirely). Two pre-existing test files outside this WP's
`owned_files` (`tests/charter/test_mission_type_profiles.py`,
`tests/runtime/test_runtime_seam.py`) mock that internal call shape directly:

- `tests/charter/test_action_sequence_dispatch.py` (predates this mission — T035/WP05 of an
  earlier mission) injects a fake `doctrine.missions.mission_type_repository` module into
  `sys.modules` carrying only a `MissionTypeRepository` attribute, so `_resolve_action_slot`'s new
  `from doctrine.missions.mission_type_repository import resolve_layered_mission_types` raised
  `ImportError: cannot import name 'resolve_layered_mission_types' ... (unknown location)` — the
  fake module genuinely has no such attribute. Confirmed real (not a stale `__pycache__` artifact)
  by clearing every `__pycache__`/`*.pyc` under the tree and re-running before investigating
  further.
- `tests/charter/test_resolved_mission_type_context.py::TestResolvedTemplateSet::test_mapping_is_lazy_and_cached_per_bundle`
  primes `MissionTypeRepository.default()`'s cache (a `cls`-keyed `functools.cache`) to isolate the
  template-set slot's own `MissionStepRepository.default()` call count. WP04's action-sequence path
  no longer touches that cache at all — it resolves through `resolve_layered_mission_types`'s
  separate `(mission_types_dirs, pack_context)`-keyed cache (CL-001's whole point: the two caches
  must never be the same one), so priming the old cache no longer warms the one the action-sequence
  path actually uses, and the isolation assertion (`step_repository_default.call_count == 0`
  immediately after building the bundle, before touching `.template_set`) went from 0 to 4 (one
  `MissionStepRepository.default()` call per built-in mission-type YAML file loaded fresh through
  the now-cold layered-lookup cache).

Neither file is in WP04's `owned_files`, but per the same adjudication precedent WP05 recorded
above for `tests/charter/test_pack_manager_catalog.py` (a genuine, unavoidable collision between a
correct implementation and a pre-existing test's *mocking strategy*, not its asserted contract) —
both were fixed in place rather than left red:

- `test_action_sequence_dispatch.py`: the `sys.modules` injection helpers now expose
  `resolve_layered_mission_types` (a callable returning the same mock roster object, which already
  satisfies the `.get(id)` interface the real factory's return value needs) instead of
  `MissionTypeRepository`. No assertion's *meaning* changed — same registered/unregistered/extends
  scenarios, same expected results — only the shape of what gets mocked.
- `test_resolved_mission_type_context.py`: the priming call was changed from
  `MissionTypeRepository.default()` to a full `resolve_mission_type_context(tmp_path,
  mission_type="software-dev")` call (same `tmp_path`, so the same `PackContext` fields — frozen
  dataclasses compare equal by value, so a second, separately-constructed-but-equal `PackContext`
  still lands on the same cache entry). Deliberately does not touch `bundle.template_set` during
  priming, so that thunk stays cold for the assertions under test.

Both failures were first observed directly (not hypothesized): after landing T008/T009's
production edit, a full `tests/doctrine tests/charter` run showed exactly these two files newly
red — the `ImportError`/`assert 4 == 0` output quoted above is the actual pytest output from that
run, not a reconstruction. After applying the two test-file fixes described above, the same full
shard run showed zero failures beyond the pre-existing baseline.

## WP06 (FR-004/CL-003 loud-fail) — the layer-attribution message needs a lookup the roster factory doesn't return, plus a real gate-timing gotcha

FR-004's error message contract ("mission type `<id>` resolved from layer `<layer>` has an empty
action sequence") needs to name *which* layer resolved the type, but
`resolve_layered_mission_types` (WP03) returns a plain `dict[str, MissionType]` — the winning
layer's identity is not carried through to callers at all, only the final merged value. Extending
that factory's return shape to also carry provenance would have been the "real" fix (and is
probably what FR-006/FR-007/FR-008's `source_layer` CLI work, WP07, will eventually need too), but
`resolve_layered_mission_types` lives in `src/doctrine/missions/mission_type_repository.py`, which
is outside WP06's `owned_files` (`src/charter/mission_type_profiles.py` and its test file only).
Rather than reach outside scope, WP06 adds a small, local, read-only helper
(`_resolve_action_sequence_layer`) in the owned file that mirrors the factory's own
project > org > built-in-equivalent precedence by checking file existence directly — it never
re-parses or re-validates YAML, so it can't drift from what the factory already resolved, only
from *where* it looked. Flagging this as the more scalable fix a future mission (or WP07, if its
scope ends up needing per-id provenance for the CLI `source_layer` fields) should consider:
threading provenance through `resolve_layered_mission_types` itself rather than every caller
re-deriving it.

**Dead-symbol gate, decided proactively rather than hit red:** every other exception class in
`mission_type_profiles.py` (`UnknownMissionTypeError`, `CrossGrainDoubleDeclarationError`) is both
in the module's `__all__` and has a real non-test `src/` caller elsewhere in the codebase — the
dead-symbol gate (`tests/architectural/test_no_dead_symbols.py`) requires the latter for anything
declared in `__all__`. `MissionTypeEmptyActionSequenceError` has no such external caller yet (it is
raised and caught only within `mission_type_profiles.py` and its own tests), and adding one — e.g.
a dedicated `except` clause in the CLI's mission-create wrapper — would mean editing a file outside
WP06's `owned_files`. Left the class out of `__all__` entirely instead (still fully importable via
`from charter.mission_type_profiles import MissionTypeEmptyActionSequenceError`, exactly how this
WP's own tests and `UnknownMissionTypeError` are already imported) rather than trip the gate or
smuggle in an unrelated file edit. Verified clean:
`pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_golden_count_ban.py`
— 34 passed.

**Gate-timing gotcha, not a WP06 defect:** a full `tests/charter/ tests/doctrine/
tests/runtime/test_runtime_seam.py --cov=...` run (needed to regenerate `coverage.xml` for
diff-coverage) took 27 and then 26.5 minutes on this machine — 2.5–3x the ~10-minute baseline —
because two or three *other* missions' worktree test runs were hammering CPU concurrently for
unrelated work happening on the same host. One run surfaced a single failure,
`tests/charter/test_consistency_check.py::test_run_consistency_check_completes_within_budget`
(a documented wall-clock budget test: "Runs in the serial `timing-nfr-serial` gate (no parallel
cache contention)... elapsed < 3.0s"). Re-ran it alone immediately after (with the same other
missions' processes still active) — passed in 2.10s. Not attributable to this WP: WP06 never
touches `test_consistency_check.py` or anything on its call path; the test's own docstring already
documents itself as contention-sensitive. Recorded here rather than "fixed" because there was
nothing in this WP's diff to fix — it is host-load noise, not a regression, per the repo's baseline
-red-attribution policy (`AGENTS.md` § Test-run baseline-red gotcha, category 2/CI-environment
class).

## WP07 (FR-006/FR-007/FR-008 CLI fixes) — the doctrine census gate forced a facade widening outside the originally-planned owned_files

WP06's own tracer entry above already flagged this as the likely shape of WP07's problem, and it
landed exactly that way. `charter mission-type list` / `mission-type show` / `doctrine mission-type
list` all need the FR-001 layered roster's actual `MissionType` objects (display_name, extends),
not just an action sequence — `charter.mission_type_profiles` has no public function that returns
one. The only producer is `resolve_layered_mission_types` in
`src/doctrine/missions/mission_type_repository.py`, and that module is dispositioned `FACADE-ONLY`
in `tests/architectural/test_doctrine_census.py`'s `DISPOSITION` table — a `specify_cli` file may
only reach it through a `charter.*` door, never by importing `doctrine.missions.*` directly
(confirmed live: that census's `test_no_reached_file_is_orphaned` walks every file under
`src/specify_cli/` for a direct `from doctrine…` import and fails on any file not owned by a
*different* mission's migration WPs — a new direct import from a CLI command file would have
tripped it). `charter.missions` (the sanctioned door for this exact doctrine module) did not yet
re-export `resolve_layered_mission_types`, and neither `src/charter/missions.py` nor
`tests/architectural/test_charter_facades_reexport_doctrine.py` were in this WP's task-file
`owned_files` list. Widened both anyway — a two-line re-export plus one `_FACADE_TABLE` row — since
the alternative (duplicating the layer-precedence walk inside a CLI file to avoid an unowned-file
touch) would have forked a second, driftable copy of logic `charter.mission_type_profiles`'s own
`_resolve_action_sequence_layer` already implements, for no gain. Verified this was the intended
shape, not an improvisation: plan.md's "The Seam" section had already anticipated exactly this
under IC-01 as the "bare-function shape needs a new facade-table entry" branch, just without
naming which WP would end up needing it.

**mypy batch-vs-per-file cast redundancy — not a new defect class.** `mypy --strict src/specify_cli
src/charter src/doctrine` (the actual CI invocation, `ci-quality.yml`'s advisory mypy step) resolves
`charter.*` return types fully when checking the whole tree in one pass, so a `cast()` written to
work around the `charter.*` `follow_imports = "skip"` mypy override (needed when a file is
type-checked in isolation, e.g. `mypy --strict <one-file>`) shows as `redundant-cast` in the batch
invocation. This is not new: the batch run already carries this same inconsistency at multiple
pre-existing, already-approved call sites (`activate.py:109`/`139`, `deactivate.py:74`, three sites
in `tracker/local_service.py`, two in `tracker/saas_client.py`) — 18 pre-existing batch-mode errors
across 9 files, confirmed by running the identical `mypy --strict` invocation against the
pre-WP07 merge-base commit in a scratch worktree. WP07's new call sites in
`specify_cli/cli/commands/charter/mission_type.py` add 3 more instances of the *same two* already-
tolerated patterns (redundant-cast-in-batch, and the pre-existing `PackContext`/`_PackContextLike`
Protocol settable-attribute mismatch already present at `mission_type_profiles.py:661`/`675` from
WP04) — not a novel defect class. mypy is advisory in CI (`ci-quality.yml`'s own step name: "[INFO]
Run mypy report (advisory)"); left as-is rather than stripped, to keep the per-file `mypy --strict`
invocation (what this WP's own task instructions ask for) clean, which it is.
