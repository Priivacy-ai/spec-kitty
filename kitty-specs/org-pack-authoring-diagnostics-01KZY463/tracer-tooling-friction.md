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
