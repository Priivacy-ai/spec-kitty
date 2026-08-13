# Tracer — tooling friction

Mission `mission-type-guard-registry-01KZY2FG` (issue #3386), base `main`, topology `lanes`.
Append as friction is hit. Every entry states whether it was **verified first-hand** or
**reported by a subagent**.

## 1. SK-09 reproduced — `specify` mints no branch, first commit refused

**Verified first-hand** (orchestrator), spec-kitty 3.2.5, checkout at `main` @ `ab0a0b9b5`.

`spec-kitty specify mission-type-guard-registry --mission-type software-dev --topology lanes
--json` scaffolded `kitty-specs/mission-type-guard-registry-01KZY2FG/` and left HEAD on
`main`, minting no branch. Already recorded as ledger **SK-09**; this mission is a second
first-hand reproduction, on a different topology (`lanes`, not the `coord` default) than the
3384 sighting — so the defect is not topology-specific.

Worked around as authorized: `git checkout -b
kitty/mission-mission-type-guard-registry-01KZY2FG`, the canonical name derived from
`meta.json`'s `mission_id` (`01KZY2FGYX2B90XXDD1DM3M95B` → mid8 `01KZY2FG`). Charter
§Agent Push Authorization sanctions this on this repo.

## 2. NEW — both canonical commit paths refuse, on contradictory grounds (ledger SK-11)

**Verified first-hand** (orchestrator). See `SPEC-KITTY-LEDGER.md` SK-11 for the full entry.

Standing on the mission branch, with `meta.json` carrying `target_branch: main`:

- `spec-kitty safe-commit <files> -m "..."` → refuses, demanding HEAD be `main`:
  `safe_commit: worktree ... HEAD is 'kitty/mission-mission-type-guard-registry-01KZY2FG',
  expected 'main'. Run 'git ... checkout main' first.`
- `spec-kitty spec-commit <files> -m "..."` → refuses, claiming the branch **is** `main`:
  `Refusing to commit planning artifacts to the protected branch 'main'. Start a
  non-protected feature branch and commit there.`

Both refusals were emitted while `git branch --show-current` returned the mission branch.
The two commands cannot both be satisfied: one demands `main`, the other refuses `main`.

Worked around with raw `git add` + `git commit` on the mission branch (commit `5c55d11ca`),
which bypasses no protection guard because HEAD is not `main`. Recorded rather than hidden.

## 3. Harness — subagent delegation lost, and org spend limit reached

**Verified first-hand** (orchestrator). **Not a spec-kitty defect** — Claude-harness /
billing, recorded here only so the mission's cost history is honest, and deliberately NOT
added to `SPEC-KITTY-LEDGER.md`, which is for defects in the tooling under review.

- The readiness probe dispatched two verification subagents; one never returned a result.
  Robbie disclosed this rather than presenting its unfinished work as findings, and
  re-verified four census sites himself. The issue body's "~22 sites" figure remains
  **unverified** and must not be restated as established fact.
- The spec phase agent and the R1 `arch` lens (`architect-alphonso`) both terminated on
  `You've hit your org's monthly spend limit`. The R1 `gov` lens (`planner-priti`) completed
  and its findings are committed. `verify` (`debugger-debbie`) never produced an artifact.

## 4. Review artifact filename deviates from the protocol contract

**Verified first-hand** (orchestrator).

The `gov` lens wrote `reviews/spec-gov.findings.yaml`. The review contract
(`~/.hermes/skills/sk/references/review-overlay.md` §Artifact paths) specifies
`<PHASE>.<group>.findings.yaml` — i.e. `spec.gov.findings.yaml`, dot-separated. The file was
left as written rather than renamed by the orchestrator: squad artifacts are not the
orchestrator's to edit. The resumed spec phase agent must correct the name and use the
contract spelling for the remaining groups, so R2 merge and downstream families stay
comparable across missions.

## 5. `finalize-tasks` (real run) refuses on a NEW, coherent ground — protected-branch
   bookkeeping commit, no coordination branch for this mission's `lanes` topology

**Verified first-hand** (tasks-phase subagent), spec-kitty 3.2.6rc2.

Sequence: `spec-kitty agent tasks map-requirements --batch ...` succeeded (11/11 FRs mapped,
`unmapped_functional: []`). `spec-kitty agent mission finalize-tasks --validate-only --json`
passed cleanly — zero ownership warnings, zero dependency cycles, `validation_passed`. It
previewed correcting both WPs' `planning_base_branch`/`merge_target_branch` from my
hand-authored guess (`kitty/mission-mission-type-guard-registry-01KZY2FG`, taken from
`spec-kitty agent mission branch-context --json`, which resolves differently) to `main` (read
from `meta.json`'s `target_branch` field) — a legitimate correction, not a defect.

The real run then failed:

```
$ .venv/bin/spec-kitty agent mission finalize-tasks --mission mission-type-guard-registry-01KZY2FG --json
{"error": "Bookkeeping refused: PROTECTED_BRANCH_REFUSED: Refusing to record 'status transition
WP01': destination ref 'main' is on this project's protected branch list. Bookkeeping commits
must target the coordination branch.", "spec_kitty_version": "3.2.6rc2"}
```

`meta.json` carries `"topology": "lanes"` and `"target_branch": "main"` — a `lanes` topology has
no coordination branch by design (per CLAUDE.md's own Execution Workspace Strategy section:
"Missions with no coordination topology (`SINGLE_BRANCH` / `LANES`) route everything to
primary"), yet this bookkeeping step demands one. This is a **different, single, internally
coherent** refusal (unlike SK-11's two commands refusing for *contradictory* reasons) — but it
still leaves a `lanes`-topology, `target_branch: main` mission unable to complete
`finalize-tasks` end-to-end via any documented path found so far (a `--target-branch` override
flag exists but was not used — deliberately not attempted here, since routing around a
BLOCKED condition is explicitly out of scope for this subagent's mandate; left for the
orchestrator to resolve or escalate).

**Partial-mutation side effect, left as-is (not reverted, not hand-fixed)**: before refusing,
the run already wrote local (uncommitted) state: appended `TasksStarted` / two `WPCreated` /
`TasksCompleted` events to `status.events.jsonl`, created
`kitty-specs/mission-type-guard-registry-01KZY2FG/issue-matrix.json` (a scaffold row for
`#3386`), and normalized both WP files' frontmatter (branch fields → `main`, dependency
parsing applied). None of this was committed (the refusal happens before the commit step).
This subagent did not revert or hand-edit any of it — reverting would itself be a form of
routing around the block by deciding, on this subagent's own authority, what the "clean" state
should be. `tasks.md` and both WP prompt files were committed via raw `git add`+`git commit`
(same SK-11-authorized pattern as entry 2) since they are this subagent's own authored
planning content, not tool-internal bookkeeping; `status.events.jsonl` / `issue-matrix.json`
were deliberately left uncommitted so the orchestrator sees the exact partial state and decides
how to proceed (retry with `--target-branch`, change topology, or something else).
