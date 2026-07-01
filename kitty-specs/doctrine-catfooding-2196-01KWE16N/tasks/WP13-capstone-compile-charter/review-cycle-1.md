---
affected_files: []
cycle_number: 1
mission_slug: doctrine-catfooding-2196-01KWE16N
reproduction_command:
reviewed_at: '2026-07-01T12:44:19Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP13
---

# WP13 Review — Capstone: Compile the Spec Kitty Charter — CHANGES REQUESTED

Reviewer: reviewer-renata (opus). Review cycle 1.

The committed charter (`.kittify/charter/charter.md` v1.2.0) is reconciled and the
single contract-named non-shallow proof passes (`architectural-gate-non-vacuity`
resolves in `references.yaml`). However, a full audit of the acceptance surface
shows the capstone is **not** cleanly complete. Two blocking findings, one minor.

---

## BLOCKING 1 — Reference closure is incomplete (contract Acceptance / NFR-003 / SC-001)

The contract (`contracts/capstone-compile.md`) acceptance states, verbatim:

> Reference closure **non-shallow**: **every** activated catfooding artifact's
> `requires`/`suggests` edges resolve in `references.yaml` (not just direct
> interview selections).

The implementer verified only the ONE grep the contract names
(`architectural-gate-non-vacuity`) and declared the closure non-shallow. A full
audit of all 14 catfooding artifacts against the on-disk `references.yaml`
(85 entries, mtime 14:11, generated AFTER the finalized `answers.yaml` at 14:00 —
so this is not a staleness artifact) shows **6 activated + directly-selected
artifacts do NOT resolve in `references.yaml`**:

| Artifact | kind | in answers.yaml | in graph.yaml (node+edges) | in references.yaml |
|---|---|---|---|---|
| pr-agent-worktree-isolation | tactic | yes | yes | **NO** |
| ownership-map-leeway | tactic | yes | yes | **NO** |
| reviewer-implementer-role-separation | tactic | yes | yes | **NO** |
| planning-and-tracking | styleguide | yes | yes | **NO** |
| mission-tracer-files | procedure | yes | yes | **NO** |
| post-merge-arch-gate-adjudication | procedure | yes | yes | **NO** |

(The other 8 — 043/044/045, architectural-gate-non-vacuity, frozen-baseline,
canonical-source-unification, adversarial-squad-cadence, terminology-guard — DO
resolve.)

Why this blocks: these 6 span §3, §5b, §7, §8. They are directly selected in
`answers.yaml` and are full nodes in `src/doctrine/graph.yaml` with edges
(WP12 wiring is present — confirmed at graph.yaml lines 271/277/313/527/533/617
plus edges at 1990–2865). So the DRG authoring is done, yet `charter generate`
did not render them into the closure lockfile. The committed `charter.md`
contains them only because they were added by hand during the T062 reconcile —
which **masks** the gap. That is precisely the failure NFR-003 warns about
("if the closure is shallow, the DRG edge authoring in WP02-WP11 was for
nothing"): the catfooding payoff is that the doctrine ENGINE composes the
closure, not that a human patches `charter.md` to look complete.

Reproduce:
```bash
cd .worktrees/doctrine-catfooding-2196-01KWE16N-lane-m
for a in pr-agent-worktree-isolation ownership-map-leeway \
         reviewer-implementer-role-separation planning-and-tracking \
         mission-tracer-files post-merge-arch-gate-adjudication; do
  printf "%-42s refs=%s\n" "$a" "$(grep -c "$a" .kittify/charter/references.yaml)"
done   # all print refs=0
```

Fix direction (do not hand-edit references.yaml or charter.md to paper over it):
1. Root-cause why `charter generate` renders the 043/044-anchored tactics but
   NOT directly-selected §7/§8 tactics, the §8 styleguide, and both procedures.
   Two contributing causes are visible:
   - **`.kittify/config.yaml` has no `activated_procedures` and no
     `activated_toolguides` keys.** Only `activated_directives`,
     `activated_styleguides`, `activated_tactics` were written. The T059 steps
     `charter activate procedure mission-tracer-files`,
     `charter activate procedure post-merge-arch-gate-adjudication`, and
     `charter activate toolguide terminology-guard` did NOT persist an
     `activated_procedures`/`activated_toolguides` list. (terminology-guard
     still renders via built-in inclusion, but the procedures do not.) Confirm
     whether procedure/toolguide activation is expected to persist and, if the
     activate command silently no-ops for those kinds, that is an upstream CLI
     gap to file — not something to work around.
   - The 3 §7/§8 tactics + planning-and-tracking styleguide are activated and
     selected yet still absent, suggesting `charter generate`'s reference
     renderer only walks the directive-anchored closure and drops
     directly-selected artifacts that aren't directive-reachable. Investigate
     and fix so the generated `references.yaml` resolves ALL activated
     catfooding artifacts.
2. Regenerate and re-verify with a FULL matrix (all 14), not the single grep.
   Every activated catfooding artifact must resolve in `references.yaml`.
3. Record the full matrix (not just one grep) in the Activity Log.

If, after investigation, it is determined that some of these legitimately do not
belong in `references.yaml` by design, that contradicts the contract's
"every activated catfooding artifact resolves" wording — reconcile the contract
and get the discrepancy explicitly signed off rather than silently shipping a
partial closure.

---

## BLOCKING 2 — Dirty working tree reverts the v1.1.5 reconciliation (SC-003 / merge preflight)

`.kittify/charter/charter.md` has an **uncommitted** working-tree modification
(mtime 14:34, i.e. after the WP13 commit `d58a9475f`):

```
$ git status --porcelain
 M .kittify/charter/charter.md
```

The uncommitted diff is 90 insertions / 103 deletions. No section headers are
dropped, but it reverts the reconciliation formatting the commit established —
bold directive titles removed, docker sub-bullets de-indented, `ADR-12` text
re-linked, rule numbering changed. In effect it re-applies raw `charter generate`
output on top of the hand-reconciled committed version, degrading SC-003.

This blocks because (a) the mission merge preflight requires clean worktrees, so
a dirty lane tip will fail preflight, and (b) if this dirty state is committed as
delivered, the T062 reconciliation is partially undone.

Fix: decide intent. Either `git checkout -- .kittify/charter/charter.md` to
restore the committed reconciled v1.2.0 (if the 14:34 edit was an accidental
re-generate), OR, if the re-generate is intended, redo the T062 reconcile on top
of it and commit — but do not leave the lane dirty.

---

## MINOR — config.yaml activated_* completeness (criterion #3)

`.kittify/config.yaml` explicit `activated_*` lists cover directives, styleguides,
and tactics, but there is no `activated_procedures`, `activated_toolguides`, or
`activated_templates` key. Criterion #3 expects the 2 procedures + 1 toolguide
(+template) to be represented in the activated set. They are currently only
"active" by the all-built-in default. Tie this off as part of BLOCKING 1's
root-cause (the two are the same underlying activation-persistence question).

---

## What passed (for the record)

- Scope: the WP13 commit `d58a9475f` touches ONLY `.kittify/charter/charter.md`,
  `.kittify/charter/interview/answers.yaml`, `.kittify/config.yaml` — no
  `src/doctrine/` artifact or `graph.yaml` edit. (references.yaml is gitignored
  by `.gitignore:114`, correctly not committed.) PASS.
- Non-shallow proof (contract-named single invariant):
  `grep architectural-gate-non-vacuity references.yaml` → 2 matches. This tactic
  is only transitively reachable via DIRECTIVE_043's `suggests` edge, so its
  presence proves activate-preceded-generate. PASS.
- Version reconcile: committed `charter.md` is v1.2.0 (parent was v1.1.5), with
  an explicit reconciliation preamble; no v1.1.5 sections dropped in the commit. PASS.
- answers.yaml mirror: all 14 catfooding IDs present in the committed
  `answers.yaml` selected_* lists. PASS.
- `spec-kitty doctor doctrine --json`: healthy (18/18 profiles valid, 0 invalid,
  0 collision warnings). PASS.
- `spec-kitty charter list`: all 8 sections' artifacts show as activated. PASS.
- SC-005: `docs/development/quality-and-tech-debt-standing-orders.md` present and
  inventoried (1 hit in `3-2-page-inventory.yaml`). PASS (WP01 scope).

## Anti-pattern checklist
1. Dead code — N/A (doctrine/config artifacts, no new production symbols).
2. Synthetic-fixture test — N/A.
3. Silent empty return — N/A.
4. FR coverage (FR-014) — PARTIAL: the closure-completeness half of FR-014 is
   not met (BLOCKING 1).
5. Frozen surface — PASS (no frozen file touched).
6. Locked decision — FAIL: contract "every activated catfooding artifact
   resolves in references.yaml" is contradicted (BLOCKING 1).
7. Shared-file ownership — PASS (WP13 owns .kittify/charter + config.yaml alone).
8. Production fragility — N/A.

Verdict: **CHANGES REQUESTED** — resolve BLOCKING 1 (complete + machine-verified
closure) and BLOCKING 2 (clean the lane / re-reconcile), then re-verify with the
full 14-artifact matrix recorded in the Activity Log.
