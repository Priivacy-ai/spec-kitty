# Tooling Friction Tracer — org-pack-authoring-diagnostics-01KZY463

Seeded ahead of schedule (normally a plan-phase artifact per the sk overlay) because a
real, blocking tooling defect surfaced during the spec phase and the reflexive-failure
clause requires recording it here rather than losing it to a session transcript.

## 2026-08-13 — `spec-kitty spec-commit` refuses on this mission; canonical state machine
   never advances past `discovery` despite a complete, fully-reviewed spec

**What happened**: after a full R1→R6 adversarial squad (3 rounds; see `reviews/`) landed a
findings-free spec at commit `766766d38` and the review trail was committed via
`spec-kitty safe-commit` (commit `<see reviews-trail commit in git log>`), the design
pipeline's final step — `spec-kitty spec-commit` — was run to finalize the phase. It
refused every attempt:

```
spec-kitty spec-commit kitty-specs/org-pack-authoring-diagnostics-01KZY463/spec.md \
  --mission org-pack-authoring-diagnostics-01KZY463 \
  --message "spec(org-pack-authoring-diagnostics): finalize spec phase after R1-R6 adversarial squad (PASSED)" \
  --json

{"result": "error", "success": false, "committed": false, "placement_ref": "main",
 "error": "Refusing to commit planning artifacts to the protected branch 'main'.
Start a non-protected feature branch and commit there: 'spec-kitty mission
create --start-branch <feature-branch>' (or check out an existing feature
branch). Planning artifacts must land on a feature branch.
To retry after materialising the coordination worktree, run:
  spec-kitty spec-commit --mission org-pack-authoring-diagnostics-01KZY463 -m '...' <files>"}
```

`git branch --show-current` at the time of every attempt: `feat/org-pack-authoring-diagnostics-3387`
— NOT `main`. Adding `--target-branch feat/org-pack-authoring-diagnostics-3387` (the only
branch-naming flag `spec-commit --help` exposes) produced the byte-identical error —
`--target-branch` only affects the post-commit ff-advance per its own `--help` text, not
commit placement.

`spec-kitty agent mission branch-context --json` (the CLI's own documented canonical branch
resolver — "Use this deterministic branch contract during specify/plan prompts; do not
rediscover branch state inside the LLM") correctly resolves `current_branch`,
`target_branch`, and `base_branch` all to `feat/org-pack-authoring-diagnostics-3387` and
`recommended_strategy: stay`. `spec-commit` disagrees with the CLI's own canonical resolver
and reports `placement_ref: "main"` instead — sourced from `meta.json`'s `target_branch`
field, frozen at `specify` time before any branch existed, and never reconciled after
`safe-commit` minted `feat/org-pack-authoring-diagnostics-3387` on the first protected-branch
refusal.

**Confirmed blocking, not cosmetic**: `spec-kitty next --mission org-pack-authoring-diagnostics-01KZY463 --json`
reports `"mission_state": "not_started", "preview_step": "discovery"` — the canonical event
log has not advanced at all, despite a complete, adversarially-reviewed spec sitting
committed on the mission branch. `spec-commit`, not `safe-commit`, is apparently the sole
writer of that state transition for this artifact kind, and it cannot succeed here.

**This is the exact defect already filed as SK-12 / SK-13 in `SPEC-KITTY-LEDGER.md`** — a
third, independent corroboration, on `topology lanes` (matching SK-13's topology, not
SK-12's `coord`), same byte-identical error text, same stale-`meta.json`-over-live-HEAD root
cause. New information added to the ledger entry: `safe-commit` DOES have a working escape
hatch not previously documented (`--to-branch <branch>` matching live HEAD succeeds), while
`spec-commit` has no equivalent parameter — its only branch flag serves a different,
non-placement purpose.

**Action taken**: did NOT hand-edit `meta.json` or any status/event file. Did NOT attempt an
env-var bypass. All planning artifacts (`spec.md`, full `reviews/` trail) are safely
committed and git-reachable via `safe-commit` with an explicit `--to-branch` override — this
part of the phase's substantive work is complete and verifiable independent of
`spec-commit`'s failure. The phase agent reported **BLOCKED** to the orchestrator per the
reflexive-failure clause rather than improvising a further workaround, since the mission's
canonical state machine (`spec-kitty next`) cannot register phase completion through any
sanctioned path currently available.

**See**: `SPEC-KITTY-LEDGER.md` SK-12, SK-13 (this entry corroborates both; a fourth
consecutive mission-family sighting of the same class after SK-09/SK-10/SK-11 established
the "branch check is blind to live HEAD" pattern more broadly).

## 2026-08-13 — plan phase — same defect class reproduces on `spec-kitty plan --json`

Running the plan-phase tooling check as instructed (`spec-kitty plan --mission
org-pack-authoring-diagnostics-01KZY463 --json`), after `plan.md`, `tracer-approach.md`, and
`tracer-design-decisions.md` were already written with real content: the command correctly
reported `"plan_substantive": true` (confirming the plan is real, not template placeholders) but
`"commit_created": false"`, `"commit_status": "no_op_wrong_surface"`, with the byte-identical
diagnostic text SK-12 documents: `"Refusing to commit planning artifacts to the protected branch
'main'... placement_ref` sourced from stale `meta.json.target_branch` (`"main"`), while every
`branch_context` field in the same JSON payload correctly resolves `current_branch`,
`target_branch`, and `base_branch` to `feat/org-pack-authoring-diagnostics-3387` and
`branch_matches_target: true`. Same root cause as the spec-phase entry above: the auto-commit
path trusts stale `meta.json` over the CLI's own live branch resolution. No `spec-kitty
spec-commit`/auto-commit path was used to land the plan artifacts — per the mission brief's
explicit instruction, `safe-commit --to-branch <branch>` is used instead (the documented working
escape hatch). Fifth consecutive sighting of the same defect class in this mission family.

## 2026-08-14 — tasks phase — same defect class reproduces on `spec-kitty tasks --json`
   (`finalize_tasks`); PLUS a new, distinct silent-data-loss defect discovered as a byproduct

**Sixth sighting, same class**: `spec-kitty tasks --mission org-pack-authoring-diagnostics-01KZY463
--json` was run, as instructed, after `wps.yaml` and `tasks/WP01..WP04-*.md` were hand-authored.
Its help text ("Finalize tasks metadata after task generation") and a source read confirm this
top-level command and `spec-kitty agent mission finalize-tasks --json` are the **same underlying
function**, `finalize_tasks()` (`src/specify_cli/cli/commands/agent/mission_finalize.py:1783`).
Output:

```json
{"error": "Git commit failed: Refusing to commit planning artifacts to the protected branch
'main'. Start a non-protected feature branch and commit there: 'spec-kitty mission create
--start-branch <feature-branch>' (or check out an existing feature branch). Planning artifacts
must land on a feature branch."}
```

Byte-identical diagnostic family to SK-12/13 and this file's two prior entries; same root cause
(`_resolve_mission_target_branch` reads `meta.json`'s `target_branch: "main"` directly —
`src/specify_cli/core/paths.py:717`, whose own docstring at `:738-740` names this "the
finalize-tasks / implement-loop refusal-to-main bug, WP00 / FR-004" — so the defect is already
self-documented in the source, not merely inferred by this tracer). No workaround flag was used;
per the mission brief this is absolute. All planning artifacts were committed afterward via
`spec-kitty safe-commit --to-branch feat/org-pack-authoring-diagnostics-3387`.

**New finding, distinct defect — silent requirement-ref truncation**: `finalize_tasks` writes
several artifacts to disk *before* the commit attempt (confirmed by call-order trace:
frontmatter flush at `mission_finalize.py:1926`, `tasks.md` regeneration at `:1931`, dependency +
requirement-mapping validation at `:1937-1946`, `lanes.json` write inside `_run_commit_pipeline`
at `:1963`/`:1737-1748` — all strictly before the commit call that then fails). Comparing
`wps.yaml` (hand-authored, untouched by the run — still lists `requirement_refs: [FR-001, C-001,
SC-001]` for WP01, and the equivalent `SC-00x` entry for WP02/WP03/WP04) against each
`tasks/WP*.md`'s frontmatter *after* the run: every `SC-00x` reference was **silently dropped** —
WP01's flushed frontmatter reads `requirement_refs: [FR-001, C-001]` only, WP02 lost `SC-003`,
WP03 lost `SC-002`, WP04 lost `SC-004`. No warning, error, or log line reports this — the JSON
output contains only the unrelated commit-refusal message above; the dependency/requirement-ref
validation that runs at `mission_finalize.py:1937-1946` (before the commit attempt) apparently
completed without complaint, silently filtering `SC-*`-prefixed refs rather than accepting or
rejecting them explicitly. This is a live instance of this repo's own named dominant defect class
("silent success" — #3133, #3212, #3282, #3336, the class this very mission's FR-002/003/004 are
about) inside the tooling that authors missions like this one. **Not fixed here** — out of this
mission's scope (C-003, no fifth surface; this is a `mission_finalize.py` defect, not a
`pack_validator.py`/`pack_assembler.py`/`doctrine.py` one) and not something a tasks-phase agent
is chartered to patch. `wps.yaml` (the authoritative source per `tasks-outline.md`) retains the
full `SC-00x` refs; only the derived, machine-flushed WP frontmatter lost them. Every WP's prose
body still cites its `SC-00x` explicitly, so human/reviewer traceability is intact — only the
machine-readable frontmatter field is incomplete. Recommend a follow-up issue against
`mission_finalize.py`'s requirement-ref parser to either accept `SC-*` as a recognized prefix or
explicitly warn when dropping an unrecognized one, rather than silently truncating.

Seventh consecutive sighting (across spec/plan/tasks phases) of the commit-refusal class in this
mission family, plus one newly discovered sibling defect in the same subsystem.

## 2026-08-14 — WP02 workspace allocation hits `SK-14` (`synthesized_drg missing`), self-resolves
   without an improvised remedy

**What happened**: per this WP's brief, the canonical loop was run from the repo root
(`/home/jeroennouws/dev/SK-missions/3387`, checked out on `feat/org-pack-authoring-diagnostics-3387`
@ `07b12685c`): `spec-kitty next --agent claude --mission org-pack-authoring-diagnostics-01KZY463`
returned a query-mode result (no advance) and `spec-kitty agent action implement WP02 --agent claude
--mission org-pack-authoring-diagnostics-01KZY463` refused workspace creation with:

```
Error: synthesized_drg missing; run `spec-kitty charter synthesize`
```

This is **not** the documented "lane bases on `main`" trap the brief pre-armed — the failure was
earlier, at "Detect feature context" preflight, before lane resolution ran at all. It is instead
**`SK-14`** (`SPEC-KITTY-LEDGER.md`), already recorded from a sibling mission
(`org-pack-drg-root-graph-guard-01KZY0QT`, WP01): `implement`'s preflight forces `charter
synthesize`, whose fresh-project detector misfires on this populated repo.

Per the brief, the one documented remedy (`spec-kitty implement WP02 --mission
org-pack-authoring-diagnostics-01KZY463 --base feat/org-pack-authoring-diagnostics-3387`) was
tried once — it hit the byte-identical `synthesized_drg missing` error, since the underlying
cause (SK-14, not lane-basing) is unaffected by `--base`. Per the brief ("do not improvise another
base; do not create branches yourself" / gate commands that don't exist are BLOCKED, never an
improvised substitute), no workaround (e.g. hand-running `spec-kitty charter synthesize`) was
attempted.

**Self-resolved via shared-checkout concurrency, not by this WP's own action**: this mission's
lanes (WP01 on lane-a, WP02-04 on lane-b) share the same repo root as their common ancestor
checkout. Between the first and second `implement WP02` attempts, a concurrent process — almost
certainly WP01's own `implement` preflight run, evidenced by a new `chore(spec-kitty): status
transition batch WP01` commit appearing on `feat/org-pack-authoring-diagnostics-3387` and a
freshly-materialized `.worktrees/org-pack-authoring-diagnostics-01KZY463-lane-a` worktree — ran
`charter synthesize` (or an equivalent preflight) itself. This left `.kittify/charter/
metadata.yaml`, `.kittify/charter/synthesis-manifest.yaml`, and `.kittify/doctrine/` mutated on
the shared checkout: `synthesis-manifest.yaml`'s `adapter_version`/`synthesizer_version` moved
from `3.2.6` to `3.2.5` — the exact "downgrades the versions recorded in
synthesis-manifest.yaml" symptom SK-14 already names. Re-running the identical `implement WP02
--base ...` command afterward succeeded cleanly and materialized
`.worktrees/org-pack-authoring-diagnostics-01KZY463-lane-b` on
`kitty/mission-org-pack-authoring-diagnostics-01KZY463-lane-b`.

**New information for SK-14**: confirms the defect is not lane-specific (previously seen on WP01
of a different mission) and that a concurrent `implement` invocation elsewhere in the same
checkout is a de facto (undocumented, timing-dependent) workaround — which is exactly the kind of
non-deterministic behavior that makes SK-14 worth fixing rather than living with. Also confirms
the "shared repo root across lane implementers" execution model: agents working different lanes
of the *same* mission from the *same* checkout can observe and be affected by each other's
preflight side effects on shared governance state (`.kittify/charter/*`), including a manifest
version downgrade that isn't scoped to any one WP or lane.

**Action taken**: no hand-edit of any spec-kitty state file; no improvised `charter synthesize`
run; no alternate `--base` invented. Waited for the documented remedy to be tried exactly once
(per brief) and reported the result plainly rather than repeatedly retrying blind.

## 2026-08-14 — WP04 allocation hits the documented `stale_analysis_report` false positive
   (`analysis_report_required`); corroborated a third time, resolved per the documented recovery

**What happened**: per this WP's brief, canonical allocation was attempted from the repo root:
`spec-kitty next --agent claude --mission org-pack-authoring-diagnostics-01KZY463` returned a
query-mode result (no advance, `next_step: implement`, `0/4 done`), then `spec-kitty agent action
implement WP04 --agent claude --mission org-pack-authoring-diagnostics-01KZY463` was run and
refused with:

```
Branch: on 'feat/org-pack-authoring-diagnostics-3387', mission targets 'main'
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Reason: stale_analysis_report
  Stale inputs:
    - charter
  Run: /spec-kitty.analyze --mission org-pack-authoring-diagnostics-01KZY463
```

Per the WP brief's explicit instruction (this is a known, hash-verified false positive hit three
times already in this mission family; do NOT run the mission-wide `/spec-kitty.analyze` in
response), the mission-wide analyze command was **not** run. Instead, checked whether a valid
worktree had already materialized despite the refusal: `.worktrees/org-pack-authoring-diagnostics-01KZY463-lane-b`
was present, on branch `kitty/mission-org-pack-authoring-diagnostics-01KZY463-lane-b`, clean,
1 commit ahead of its own `origin` tracking ref, tip `617152291` ("reviews(wp03): record per-WP
review verdict for FR-002") — exactly the tip WP03's own review recorded as approved, carrying
WP02's and WP03's commits in `git log`. This is the same "stale-charter-hash false positive over
an already-materialized, correct worktree" shape the mission brief pre-armed. Proceeded directly
in that worktree rather than re-running or improvising around the gate.

**Action taken**: no `/spec-kitty.analyze` run; no hand-edit of any spec-kitty state file; no
alternate `--base` invented. Third corroboration (mission-wide) of this specific false-positive
class; documented here as instructed rather than silently routed around.
