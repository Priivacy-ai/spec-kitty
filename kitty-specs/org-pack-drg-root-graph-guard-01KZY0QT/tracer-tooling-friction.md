# Tracer: tooling friction — org-pack-drg-root-graph-guard

Charter standing order 3. Every place the tooling fought this mission, so it feeds the
tooling-gap backlog — seeded at plan time with three known-broken surfaces this mission hit
first-hand while driving the plan phase (all three are already documented in
`/home/jeroennouws/dev/SK-missions/SPEC-KITTY-LEDGER.md`; restated here in public-repo-safe,
class-level terms, no private downstream detail).

## SK-09 — nothing mints the mission branch during `specify`

`safe_commit`'s prescribed remedy when it refuses a commit is `spec-kitty mission create
--start-branch` — a flag that does not exist on this checkout. Nothing in the `specify` phase
actually creates the mission branch for you; an agent following the tool's own suggested
recovery path hits a second wall (an unrecognised flag) instead of an unblock.

## SK-09b — `spec-commit` refuses on the resolved placement ref, not on `HEAD`

`spec-commit` checks `meta.json`'s own `target_branch` (here, `main` — a protected primary)
before deciding whether to refuse, rather than checking the branch actually checked out
(`HEAD`, the mission lane branch). Under `lanes` topology with a protected primary, this makes
`spec-commit` structurally unusable no matter which branch is checked out at invocation time —
refusing on the *placement* ref means it refuses even when `HEAD` is the correct, unprotected
mission branch. `spec-kitty safe-commit` is the working path and was used throughout this
phase (see the commit at the end of this plan phase).

## SK-10 — `branch-context`/`setup-plan` branch fields derive from `HEAD`, not from `meta.json`

Live-verified during this plan phase: `spec-kitty plan --mission
org-pack-drg-root-graph-guard-01KZY0QT --json` returned `target_branch`,
`base_branch`, `planning_base_branch`, and `merge_target_branch` **all equal to the current
branch name** (`kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT`) — even though this
mission's own `meta.json` declares `"target_branch": "main"`. `branch_matches_target` was
reported `true` by construction, not because the branches actually agree. This means
`spec-kitty agent mission branch-context --json` (and the equivalent fields surfaced by
`plan`/`setup-plan`) **cannot ever report a genuine target-branch mismatch** — it derives every
branch field from whatever is currently checked out rather than reading `meta.json`'s own
`target_branch`. This plan's own branch-contract statement (top of `plan.md`) was written by
reading `meta.json` directly instead of trusting this command's branch fields, precisely
because of this defect.

## SK-11 — canonical `plan-template.md` still carries the prohibited "Feature specification" wording

Live-verified during the plan-phase R4 fix round: `plan.md:4`'s "**Input**: Feature
specification from ..." line is verbatim canonical-template boilerplate —
`packs/built-in/missions/software-dev/templates/plan-template.md:4` carries the identical
phrase, character-for-character. The Terminology Canon prohibits `Feature`/`Features` in
canonical, operator, and user-facing language ("Mission specification" is correct here), but
the defect is upstream, in the template itself, not in this mission's copy: hand-editing only
this plan's instance would create non-canonical drift from the template every other mission
inherits. Left unfixed in `plan.md` deliberately (not silently ignored — recorded here) pending
an upstream doctrine fix to `plan-template.md` (and any sibling mission-type templates using
the same phrase) that replaces "Feature specification" with "Mission specification" at the
source.

## SK-12 — `check-prerequisites`'s `branch_matches_target` is a false positive on a mid-flight `lanes`-topology mission

Live-verified during this tasks phase: `spec-kitty agent mission check-prerequisites --json
--paths-only --include-tasks --mission org-pack-drg-root-graph-guard-01KZY0QT` reported
`branch_matches_target: false` while HEAD was `762f6f362` on
`kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT` — the exact, correct branch this
mission's spec and plan phases already committed to. `target_branch`/`planning_base_branch`/
`merge_target_branch` were all reported as `"main"` (correctly read from `meta.json`'s own
`target_branch` field, unlike SK-10's HEAD-derived defect), but the command then compares the
*current checked-out branch* against that literal value to compute `branch_matches_target`,
with no allowance for `lanes` topology's actual planning model: per `meta.json`
(`"topology": "lanes"`) and AGENTS.md's Execution Workspace Strategy, a mid-flight mission's
planning artifacts (spec.md, plan.md, and now tasks.md) land on the mission branch itself, not
literal `main` — `main` is only the eventual PR merge target, reached at mission close, not the
branch planning commands should be checked out on mid-mission. Verified by checking that `main`
does not contain this mission's `kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/spec.md` at
all (`git show main:kitty-specs/.../spec.md` → `fatal: ... exists on disk, but not in 'main'`),
while the mission branch already carries four committed spec/plan-phase commits. Following the
canonical prompt's literal instruction ("if `branch_matches_target` is false, stop") would have
incorrectly halted valid, already-in-progress work on the one correct branch. Not worked around
by switching branches (there is nowhere correct to switch *to* — `main` lacks this mission's
own planning artifacts); tasks authoring proceeded on the verified-correct mission branch
instead, with this entry recording the false-positive field rather than silently ignoring it.
Same root family as SK-10 (branch-field/topology confusion), but the opposite failure
shape: SK-10's fields are wrong (HEAD-derived); here the raw `target_branch` value is right, but
the derived boolean comparing it against the working branch is wrong for `lanes` topology
mid-mission.

## SK-13 — `finalize-tasks`'s own auto-commit refuses on the resolved placement ref, same shape as SK-09b

Live-verified during this tasks phase: `spec-kitty agent mission finalize-tasks --mission
org-pack-drg-root-graph-guard-01KZY0QT --json` (the mutating command, run only after
`--validate-only` passed cleanly) performed all of its file-writing work correctly — WP01
frontmatter normalized with `requirement_refs`/`dependencies`/`planning_base_branch` etc.,
`lanes.json` computed (1 lane, disjoint write-scope), `issue-matrix.md` and
`acceptance-matrix.json` generated, and even a separate `status.events.jsonl` bootstrap commit
(`chore(spec-kitty): status transition WP01`) landed successfully — but then failed with exit
code 1 on its own commit of `tasks.md`/the WP file/`lanes.json`/etc.:
`{"error": "Git commit failed: Refusing to commit planning artifacts to the protected branch
'main'. ..."}`. HEAD at the time was `kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT` (the
correct, unprotected mission branch), not `main` — confirmed via `git branch --show-current`
immediately after the failure. This is the exact SK-09b shape (`spec-commit` refusing on
`meta.json`'s resolved *placement* ref, `target_branch=main`, rather than on the branch actually
checked out, `HEAD`) now confirmed to also affect `finalize-tasks`'s internal auto-commit call,
not just the standalone `spec-commit` command SK-09b originally documented. **Recovery used**:
per this mission's own tasks-phase brief, `spec-kitty safe-commit <files> --to-branch
kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT --message "..."` committed the six
already-written files finalize-tasks left staged-but-uncommitted; a follow-up
`finalize-tasks --validate-only` afterward returned `"would_modify": [], "unchanged": ["WP01"]`,
confirming the recovery fully captured finalize-tasks's intended output with no drift. This
is the sanctioned recovery path this mission's brief names for exactly this situation
("`safe-commit` is the correct recovery tool ONLY if you need to commit something
`finalize-tasks` didn't") — not a hand-rolled workaround.

## SK-06-adjacent — `record-analysis` returns `success: true` and silently records `verdict:
unknown` when the input body is missing its leading `---` fence, distinct trigger from SK-06

Live-verified during this analyze phase, not a re-file of SK-06 (ledger SK-06 is specifically
the legacy `schema_version`/`artifact_type` carrier shape). The analyze subagent's first
`record-analysis` call used an input file whose first line was `schema: analysis-findings/v1`
directly — the correct schema key, but with **no opening `---` fence** before it. `_split_carrier`
(`src/specify_cli/analysis_report.py:243`) requires `body.startswith("---")` before it will even
attempt to parse a carrier; without it, it returns `(None, body)` unconditionally, so
`parse_structured_findings` (line 358) returns `None` and `write_analysis_report` falls to the
`verdict = VERDICT_UNKNOWN` branch (line 411) — the exact same silent-fallback branch SK-06
documents, reached by a different proximate cause (missing fence vs. wrong schema key). The CLI
call still returned `{"success": true, ...}`; nothing in that JSON response distinguished a fully
parsed `analysis-findings/v1` carrier from the silent legacy fallback. Persisted
`analysis-report.md` carried `verdict: unknown`, `issue_counts` all `null`, `findings: []` in its
outer frontmatter, while the correctly-formed inner carrier (`verdict: ready`, `findings: []`)
survived intact in the document body below it — because `_split_carrier` never touched it, it
was never stripped out either.

**Recovery**: re-wrote the same content with a leading `---` line added, removed the stray
untracked `analysis-report.md` from the first attempt (required — `record-analysis` refuses with
`DIRTY_WORKTREE` on a pre-existing untracked report at the same path), and re-ran
`record-analysis` with the fenced input. Read back the result directly (not the command's exit
status): `verdict: ready`, `issue_counts` all `0`, `findings: []` — confirmed correct. No mission
artifact content was changed; this was a carrier-formatting correction only, not a fix to spec,
plan, tasks, or WP01.

**Class-level note for the operator**: this confirms the failure mode SK-06 names — "an analyze
agent can appear to record a verdict while recording nothing usable" — is not limited to the one
malformed-shape trigger SK-06 documents. Any input body that does not open with a literal `---`
on line 1 hits the identical silent fallback, with `success: true` giving no signal either way.
Worth folding into SK-06 as a second trigger, or filing as its own sibling entry — operator's call.

## SK-14 — `implement WP01` preflight demands `charter sync` + `charter synthesize` before
workspace creation, and `synthesize`'s "fresh project" detector misfires on a real project

Live-verified during WP01's `implement` invocation, before any of this WP's own code changed.
`spec-kitty agent action implement WP01 --agent claude --mission
org-pack-drg-root-graph-guard-01KZY0QT` refused workspace creation twice in sequence, on two
different preflight checks, neither related to WP01's own change:

1. First refusal: `Error: charter_source stale; run \`spec-kitty charter sync\`` — resolved by
   running that exact command, which rewrote `.kittify/charter/metadata.yaml`'s
   `extracted_at`/`charter_hash`/`sections_parsed` fields (no `charter.md` content had actually
   changed since the last sync; the cache was simply stale).
2. Second refusal, immediately after: `Error: synthesized_drg missing; run \`spec-kitty charter
   synthesize\`` — resolved by running that command, which reported "Charter synthesis (fresh
   project): minimal .kittify/doctrine/ materialized" and rewrote
   `.kittify/charter/synthesis-manifest.yaml`.

The second command's own "fresh project" framing is a misdiagnosis on this checkout:
`.kittify/doctrine/` already contains real, populated `directive/`, `overlays/`, `procedure/`,
`tactic/` subdirectories (this is the live spec-kitty dev repo, not an empty scaffold), yet the
synthesize command took the fresh-project short-circuit path anyway. Its rewrite of
`synthesis-manifest.yaml` **regressed** `adapter_version`/`synthesizer_version` from `3.2.6` to
`3.2.5` and **dropped** the `bundle_content_hash` key entirely — a downgrade, not a refresh,
suggesting the fresh-project seed template itself is pinned to a stale synthesizer version.
Neither rewritten file (`metadata.yaml`, `synthesis-manifest.yaml`) is in WP01's own blast
radius (C-001); both were committed separately via `spec-kitty safe-commit` (see SK-15) as
tool-driven administrative state, not hand-edited.

## SK-15 — same SK-09b/SK-13 branch-mismatch shape, now hit inside `implement`'s own
auto-commit of the WP claim/status-transition

Live-verified immediately after SK-14's two preflight fixes: `implement WP01` proceeded to
create the lane worktree successfully (`.worktrees/org-pack-drg-root-graph-guard-01KZY0QT-lane-a`,
HEAD `eeb027b50`, matching the captured baseline) and appended the `planned`→`claimed`→
`in_progress` events to `status.events.jsonl` on disk, but then failed its own follow-up commit
of that status change with: `Failed to commit workflow status update for WP01: safe_commit:
worktree /home/jeroennouws/dev/SK-missions/3384 HEAD is
'kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT', expected 'main'.` — reported as "Event
log rolled back to pre-emit state" even though the JSONL events were, in fact, still present on
disk afterward (verified by re-reading `status.events.jsonl` directly). Same root family as
SK-09b/SK-13: the auto-commit path checks the mission's resolved *placement* ref
(`meta.json.target_branch = "main"`) rather than the branch actually checked out
(`kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT`, the correct mission branch for a
mid-flight `lanes`-topology mission). **Recovery**: `spec-kitty safe-commit
.kittify/charter/metadata.yaml .kittify/charter/synthesis-manifest.yaml
kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/meta.json
kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/tasks/WP01-org-pack-drg-root-graph-guard.md
--to-branch kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT -m "..."` from the repo-root
checkout committed all four pending tool-written files cleanly; a subsequent
`implement WP01` re-invocation then proceeded past workspace creation with no further error.

## SK-16 — `spec-kitty charter status --json` throws a raw Python `AttributeError`, unrelated
to WP01's change

Live-verified while investigating SK-14: `spec-kitty charter status --json` (no other flags)
returned `{"error": "'str' object has no attribute 'get'", "result": "error", "success":
false}` both before and after the SK-14 fixes — an internal `AttributeError` leaking through the
CLI's error envelope rather than a structured diagnostic. Not investigated further (out of
WP01's blast radius entirely — C-001 confines this WP to `src/charter/_drg_helpers.py`,
`src/charter/action_doctrine_bundle.py`, and the new test file), but recorded here since it
blocked a normal diagnostic step (checking charter health before proceeding) and forced falling
back to reading `.kittify/charter/*.yaml` directly instead.

## Baseline-capture record (T001 / plan.md Baseline step 5)

<!-- Populated once, by WP01's T001, before this mission's first RED commit lands. Per
     plan.md's Baseline procedure step 5 ("committed to the mission's tracer notes"): run
     `pytest tests/charter/ tests/architectural/ -q` on `planning_base_branch` before any of
     this WP's commits, then record the resulting red test IDs + failure summaries verbatim
     below. Distinct from — and precedes — the per-FR ATDD red-first discipline; this capture
     happens once for the whole mission, not per WP. -->

WP01's T001, run in the lane worktree (`.worktrees/org-pack-drg-root-graph-guard-01KZY0QT-lane-a`,
HEAD `eeb027b50`, matching the orchestrator-captured baseline exactly) before any of this WP's
commits:

```
uv run --extra test --extra lint pytest tests/charter/ tests/architectural/ \
  -q -p no:cacheprovider -n auto --dist loadfile
→ 3612 passed, 6 skipped, 2 xfailed, 24 warnings in 128.99s (0:02:08)
```

**Zero failures.** (One more `passed` than the orchestrator brief's stated `3611` — collection-count
variance only, not a red; both runs report 0 failed / 0 errors.) There is no pre-existing red
test on this WP's targeted surface (`tests/charter/`, `tests/architectural/`) to exclude —
every red this WP's own gate runs subsequently show is therefore introduced by this WP, with no
baseline to diff against.

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->
- 2026-08-13 — `spec-kitty plan --mission <handle> --json` scaffolded `plan.md` from the
  template and reported `blocked` (Technical Context not yet substantive) on first invocation,
  as expected/documented behavior — not a defect, just confirms the scaffold-then-fill
  two-step is real and the tool's blocked-reason message is accurate and actionable.
