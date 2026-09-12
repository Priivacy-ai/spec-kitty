# How the measured tree was built, and why no single ref is mergeable as-is

> **Superseded ref — read this first.** The acceptance evidence was originally taken at
> **`dee9e29fd8`** (`wp/integration-probe-v2`). The pre-merge adversarial squad then found defects in
> six lanes — five mutation plugins and `tests/sync/conftest.py` — **and those are the proof
> instruments themselves**. A measurement taken with a broken instrument does not survive the
> instrument being fixed, so the probe was rebuilt at the corrected tips as
> **`87e0538ead`** (`wp/integration-probe-v3`) and the load-bearing measurements re-run there.
>
> Where an evidence string still names `dee9e29fd8`, it means that measurement was re-checked and its
> result was unchanged; where it names `87e0538ead`, it was re-taken. The recipe below is recorded for
> both.

Every one of the 17 acceptance criteria and 8 of the 9 negative invariants was verified on one of
these two refs. Nothing else in the dossier said what they are. This file says it, because a
measurement whose surface is unrecorded is a measurement nobody can repeat.

## The problem this solves

The mission's code lives on **12 lane branches**. The mission branch `feat/verification-trust-3115`
carries planning artifacts and no code. So:

- `feat/verification-trust-3115` — the current dossier, **none** of the nine code artifacts.
- any single lane — its own slice, none of the other eleven.
- `wp/integration-probe-v2` — all twelve slices, but a **dossier snapshot from when it was built**.

**No single ref is mergeable today.** The PR tree is *probe code + mission-branch dossier*, and
assembling it is a real step with a real failure mode, not a formality.

## The recipe

Built from `feat/verification-trust-3115` at `bbf65c399e`, merging each lane tip in order:

| lane | tip | lane | tip |
|---|---|---|---|
| a | `e442854cc0` | g | `d8d2d3ca2d` |
| b | `9bddb14705` | h | `ecd25b760d` |
| c | `0bc7c738e2` | i | `2fe038e00c` |
| d | `337cc6381b` | j | `ee98806965` |
| e | `f2710556c3` | k | `ba28d2d2c2` |
| f | `79990b6f01` | l | `7e46aa3e1e` |

**Zero code conflicts across all twelve.** Every conflict was in `kitty-specs/` status files, and
each was resolved `--ours` (keep the mission branch's version) before committing the merge.

### The rebuild — `87e0538ead`, from `feat/verification-trust-3115` at `03cc78888d`

Six tips moved when the squad's findings were fixed. Same procedure, zero code conflicts again:

| lane | tip | changed | what |
|---|---|---|---|
| a | `e442854cc0` | | |
| b | `96b71b1a99` | ✔ | `disable_render_seam` no longer raises from `sessionfinish` |
| c | `0bc7c738e2` | | |
| d | `337cc6381b` | | |
| e | `b47726a589` | ✔ | fingerprint by identity; marker completeness; teardown safety; per-marker flag |
| f | `f3d9496d69` | ✔ | `attribute_sleep_count` — monkeypatch reach, honest zero-report, two wrapper bugs |
| g | `1375621703` | ✔ | `neutralise_reset_token_manager` — patch the re-export, declare 14 sites |
| h | `ecd25b760d` | | |
| i | `2fe038e00c` | | |
| j | `bd1b28f244` | ✔ | binding assertion no longer tautological |
| k | `ba166a6933` | ✔ | same, kept byte-identical to lane-j |
| l | `7e46aa3e1e` | | |

**Why a rebuild rather than an argument that the fixes were additive.** Five of the six changed lanes
*are* the proof instruments. The sixth is the leak guard, which was measured blind to 20 of 21
injected leaks. Asserting that measurements taken with those instruments still hold, without re-taking
them, is the exact move this mission spent its whole length objecting to.

Verified present on the result: all five `scripts/mutants/*.py`, and
`tests/cli/commands/test_render_fold_not_repairable_3115.py`. Checked beforehand that
`nonterminating_dispatch_3115.py`, which lands on both lane-j and lane-k, is **byte-identical** on
both — so its double-landing is not a silent divergence.

## The known defect in this probe, stated so nobody measures the wrong thing on it

**The probe's `kitty-specs/` is corrupt.** Resolving twelve successive merges with `--ours` left six
literal `<<<<<<< ours` markers embedded *inside the `#3115` `evidence_ref` string value*, nested and
re-escaped once per merge.

The file still **parses cleanly** under `json.load` — which is the interesting part. A structural
validity check waves it straight through. It is valid JSON containing corrupt content, and that is
exactly the class of thing this mission exists to object to.

**Consequence, and the rule that follows:** measure **code** on the probe, measure **planning
artifacts** on `feat/verification-trust-3115`. NI-007 is the one invariant that touches a planning
artifact, and it is verified on the mission branch for this reason.

The corruption is probe-only. `grep -r '<<<<<<<' kitty-specs/verification-trust-3115-01KYVYWM/` on
the mission branch returns nothing.

## Rebuilding it

The recipe above reproduces `dee9e29fd8` from the listed tips. If any lane tip has moved since, the
result will differ and **the SHA in every evidence string will no longer name the tree that was
measured** — re-measure rather than assuming the delta is immaterial.

**`#3131` is a live threat to this**: `spec-kitty merge` deletes lane branches and worktrees. Once
that runs, the twelve tips above are unresolvable and this recipe becomes unrunnable. The tips are
therefore recorded by SHA rather than by branch name, so the recipe survives the branches.

## What still has to happen at landing

1. Assemble the PR tree — probe code plus the current mission-branch dossier, not the probe's stale
   copy of it.
2. Confirm the assembled tree still carries all nine code artifacts.
3. Push, and open the PR from the assembled ref.

Step 1 is the one with a failure mode: taking the probe wholesale ships a dossier missing every
correction made after the probe was built — including the terminal issue-matrix verdicts, the
re-verified negative invariants, and the filled acceptance criteria.
