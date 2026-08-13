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
