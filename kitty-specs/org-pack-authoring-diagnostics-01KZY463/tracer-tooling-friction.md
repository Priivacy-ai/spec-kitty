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

## 2026-08-14 — WP01 implement — workspace allocation trap confirmed live, plus two more
   friction incidents needed to clear it (charter prerequisite chain, then the base-branch trap
   itself, then commit-refusal class again)

**Eighth sighting overall; the base-branch trap named in the WP01 brief reproduced exactly as
predicted.** Following the canonical loop (`spec-kitty next --agent claude --mission
org-pack-authoring-diagnostics-01KZY463`, then `spec-kitty agent action implement WP01 --agent
claude`), workspace creation failed twice before touching the base-branch issue at all:

1. `Error: charter_source stale; run \`spec-kitty charter sync\`` — resolved by running exactly
   that command (`spec-kitty charter sync --json`); it regenerated
   `.kittify/charter/metadata.yaml` (timestamp/hash only, no content drift) and reported
   `"stale_before": true`.
2. `Error: synthesized_drg missing; run \`spec-kitty charter synthesize\`` — resolved by running
   that command. `--dry-run` was used first to confirm blast radius: the repo has no
   `.kittify/charter/generated/` directory, so the command took the documented "fresh project
   seed" fallback (issue #839) and only materialized/refreshed two small metadata files
   (`.kittify/doctrine/PROVENANCE.md`, already byte-identical; `.kittify/charter/synthesis-
   manifest.yaml`, version-string drift only). No doctrine content was generated or altered.

Neither of these two commands is mentioned in the WP01 brief or the canonical two-command loop —
both had to be discovered live from the tool's own error text. Recording them here since a
documentation-only WP should not need to touch charter/doctrine machinery at all to reach its
lane worktree.

**Then the named trap**: `spec-kitty agent action implement WP01 --agent claude` proceeded past
those two gates, reached "Resolve execution workspace", and materialized
`.worktrees/org-pack-authoring-diagnostics-01KZY463-lane-a` on branch
`kitty/mission-org-pack-authoring-diagnostics-01KZY463-lane-a` — confirmed via `git branch
--show-current` inside that worktree. As the brief predicted, this lane is missing this
mission's artifacts entirely: `ls .../lane-a/kitty-specs/org-pack-authoring-diagnostics-01KZY463/
tasks/WP01-guide-correction-fr001.md` and the equivalent `spec.md` path both returned "No such
file or directory" — the worktree's top level only shows generic repo scaffolding (`AGENTS.md`,
`docs`, `packs`, ...), no `kitty-specs/org-pack-authoring-diagnostics-01KZY463/` at all. The same
command call also failed at its own final commit step with a byte-identical member of the
SK-12/13 commit-refusal family: `Failed to commit workflow status update for WP01: safe_commit:
worktree ... HEAD is 'feat/org-pack-authoring-diagnostics-3387', expected 'main'.` — ninth
sighting of that class.

**Remedy applied per the brief, exactly once**: `spec-kitty implement WP01 --mission
org-pack-authoring-diagnostics-01KZY463 --base feat/org-pack-authoring-diagnostics-3387`. First
attempt still failed — a *tenth* sighting of the commit-refusal class, this time phrased as
`Error: Planning artifacts must be committed on main. Current branch:
feat/org-pack-authoring-diagnostics-3387` — because the prior failed `agent action implement`
call had already (as an uncommitted side effect) written `agent`/`shell_pid` tracking fields into
`meta.json` and the WP01 task file's frontmatter, and this second command refuses to proceed
while those are dirty, using the same stale-`main`-assumption diagnostic text. Landed those two
tool-written files via the documented escape hatch (`spec-kitty safe-commit ... --to-branch
feat/org-pack-authoring-diagnostics-3387`), matching the pattern already established three times
earlier in this tracer. After that commit, worktree state showed `--base` had actually already
succeeded silently in the background on its first (reported-failed) invocation: a second, correct
lane worktree — `.worktrees/org-pack-authoring-diagnostics-01KZY463-lane-b` on branch
`kitty/mission-org-pack-authoring-diagnostics-01KZY463-lane-b` — was present, based on the
feat-branch tip, and does contain `kitty-specs/org-pack-authoring-diagnostics-01KZY463/tasks/
WP01-guide-correction-fr001.md` with the correct committed content. **Net effect: the reported
exit-1 failure was misleading — the workspace it needed had already been materialized correctly
before the error was raised**, an eleventh distinct friction sighting (commit-step failure
reporting overall command failure even though the higher-value side effect, correct workspace
creation, had already succeeded).

**A second, more troubling defect surfaced under closer inspection: the lane the runtime actually
used for WP01 does not match this mission's own committed lane plan.**
`kitty-specs/org-pack-authoring-diagnostics-01KZY463/lanes.json` (computed at tasks-finalize time,
`computed_at: 2026-08-13T23:16:05Z`, unchanged since) statically assigns `lane-a` → `["WP01"]`
with `write_scope: ["docs/guides/how-to/governance/create-an-org-doctrine-pack.md"]` — exactly
WP01's one owned file — and `lane-b` → `["WP02", "WP03", "WP04"]` with a disjoint write_scope
(`doctrine.py`, `pack_assembler.py`, `pack_validator.py`, test files, `CHANGELOG.md`). `lane-a` is
precisely the broken, wrong-base worktree from the named trap above; the `--base` remedy did not
repair or reuse `lane-a` — it minted a *new* worktree using the next sequential slot name,
`lane-b`, which per the mission's own plan belongs to WP02/WP03/WP04, not WP01. That explains the
WP02 side effect: materializing a worktree the runtime labeled `lane-b` apparently drove the
runtime to also write lane-assignment frontmatter (`base_branch`, `base_commit`, `created_at`,
`shell_pid`) into every WP `lanes.json` lists under that label — WP02 (confirmed diff), and
likely WP03/WP04 (not checked) — even though this session asked only for WP01, which `lanes.json`
does not associate with `lane-b` at all. `spec-kitty agent status lifecycle --mission
org-pack-authoring-diagnostics-01KZY463 --json` now reports `"active_wp_count": 2` although only
WP01 was requested. This session did not commit, revert, or otherwise touch the WP02 diff — left
exactly as the tool wrote it, for whoever owns WP02 to evaluate. Net assessment: the runtime's
live lane-slot allocator (sequential `lane-a`/`lane-b`/... naming on each fresh worktree
materialization) and the static `lanes.json` WP-to-lane plan (content-based write-scope
partitioning) are **two different, uncoordinated sources of lane identity** that happened to
collide names here. Practically this is low-risk for WP01 specifically — WP01's file
(`docs/guides/...create-an-org-doctrine-pack.md`) does not overlap `lane-b`'s planned write_scope,
so no write collision — but the mismatch means "lane-b" is not evidence of WP02-ownership and a
future WP02/WP03/WP04 agent may find its own `lane-a`/`lane-b` allocation similarly does not match
`lanes.json`'s plan. Not filed as a numbered ledger sighting since it is a distinct, newly observed
defect shape (dynamic lane-slot allocation diverging from the committed static lane plan), not a
corroboration of an existing one; recommend a follow-up issue against the `--base` lane-allocation
path to either reuse the WP's `lanes.json`-assigned lane_id or reconcile the naming scheme.

**Escalation — the lane-naming mismatch is not merely cosmetic: `lane-b` is live-occupied by a
concurrent WP02 session, making it unsafe to use.** Immediately before starting WP01's edit,
`git -C .../lane-b status --short` and `log` were re-checked as a final safety pass and found to
have moved since the `--base` remedy: HEAD is now `bfb152524` (`fix(pack-validator): recurse into
assets/ matching AssetRepository (FR-003)`, author `MOES-Media`), with two more commits ahead of
the fork point this session created it at (`86b072366`) — `9e8f3687c test(pack-validator): add
red AC-1 nested asset recursion regression (FR-003)` and `5960f75d6 chore(tracer): record SK-14
corroboration on WP02 workspace allocation` — plus a currently-uncommitted working-tree
modification to `tests/specify_cli/doctrine/test_pack_validator.py`. None of these three commits
or the pending test-file edit originate from this session. `git worktree list` timestamps
(directory mtimes) confirm this session's own `--base` call minted `lane-b` at `2026-08-14
00:41:51 UTC`; the FR-003/WP02 commits above are timestamped `02:41:48`–`02:43:38` **local**
(`+0200` = UTC+2, i.e. `00:41:48`–`00:43:38 UTC`) — within seconds to ~2 minutes of this
session's own allocation, and HEAD was observed to advance a second time between two consecutive
read-only checks made moments apart in this session, confirming the other agent's writes are
actively landing in real time, not a stale leftover. Conclusion: a separate, live WP02
implementer session resolved its own `lane-b` allocation to the **same worktree and branch** this
session's WP01 `--base` remedy had just minted (because `lane-b` is WP02/WP03/WP04's correct,
`lanes.json`-assigned name, and the runtime's sequential lane-slot allocator handed that same name
to this session's WP01 attempt only because `lane-a` was already occupied by the earlier
broken-base worktree). The two sessions are now sharing one worktree/branch with no isolation.

**Net remedy: none usable — reporting BLOCKED rather than writing into a live-shared worktree.**
`lane-a` lacks this mission's planning artifacts (confirmed above) and is therefore unusable.
`lane-b` does contain the artifacts but is concurrently occupied by another agent's in-flight
WP02 commits and an uncommitted WP02 test edit; writing WP01's guide correction there would land
in the same branch as unrelated, concurrently-authored WP02 work-in-progress and risks a race
against the other session's own git operations. No third worktree was created (the brief's
"do not create branches yourself" and "do not improvise any other base" both apply, and creating
one now would also mean guessing at a base ref not documented for this case). WP01's target file
(`docs/guides/how-to/governance/create-an-org-doctrine-pack.md`) was **not edited** in this
session — there is no safe, isolated worktree available for it right now. `.kittify/charter/
metadata.yaml` and `.kittify/charter/synthesis-manifest.yaml` (steps 1–2 above) and this tracer
file were committed to the primary checkout's `feat/org-pack-authoring-diagnostics-3387` branch
via `spec-kitty safe-commit --to-branch feat/org-pack-authoring-diagnostics-3387` as
tool-prerequisite housekeeping and process record — neither is WP01's owned file.
