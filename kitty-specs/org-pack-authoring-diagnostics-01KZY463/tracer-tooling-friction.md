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
