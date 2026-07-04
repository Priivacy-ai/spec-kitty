---
title: 'Landing Contributor PRs: The Maintainer Runbook'
description: 'The maintainer workflow for landing contributor PRs: claim, isolated worktree, rebase, red classification, folds, red-first verification, squad review, push discipline, and hand-off.'
doc_status: active
updated: '2026-07-04'
related:
- docs/guides/index.md
- docs/guides/review-gates.md
- docs/guides/testing-flakiness.md
- docs/changelog/index.md
---
# Landing Contributor PRs: The Maintainer Runbook

**Audience**: Maintainers taking contributor PRs from "open with red CI" to
"merge-ready, evidence posted, operator merges".
**Issue**: [Priivacy-ai/spec-kitty#2341](https://github.com/Priivacy-ai/spec-kitty/issues/2341)
**Origin**: The 2026-07-04 landing pass (#2332, #2336, #2338, #2239, #2238),
where this workflow was run end-to-end and its friction points were logged.

The deliverable of a landing pass is never a merge. It is a PR that is green,
un-drafted, carries a full evidence trail in its comment thread, and states
any landing-order constraints — so the operator can merge it without
re-deriving the adjudication. The maintainer never merges
(see [step 11](#11-hand-off--the-operator-merges)).

## The workflow at a glance

1. [Claim before touching](#1-claim-before-touching)
2. [One isolated worktree per PR](#2-one-isolated-worktree-per-pr)
3. [Rebase onto current upstream/main first](#3-rebase-onto-current-upstreammain-first)
4. [Classify every red check](#4-classify-every-red-check)
5. [Folds: remediation commits on the contributor branch](#5-folds-remediation-commits-on-the-contributor-branch)
6. [Red-first verification for bugfix PRs](#6-red-first-verification-for-bugfix-prs)
7. [Review focus areas beyond CI](#7-review-focus-areas-beyond-ci)
8. [Adversarial squad for architectural or API-surface PRs](#8-adversarial-squad-for-architectural-or-api-surface-prs)
9. [Push discipline](#9-push-discipline)
10. [Post the remediation summary](#10-post-the-remediation-summary)
11. [Hand-off — the operator merges](#11-hand-off--the-operator-merges)
12. [Follow-up hygiene](#12-follow-up-hygiene)

## 1. Claim before touching

Post a claim comment on the PR **before** any rebase or review work: what you
are picking up, in which landing queue, and what you plan to do. One claim per
PR in the pass, posted first.

```bash
unset GITHUB_TOKEN   # keyring auth has full repo scope; a limited env token may not
gh pr comment <N> --repo Priivacy-ai/spec-kitty \
  --body "Claiming this PR for today's landing pass: rebase onto upstream/main, adjudicate red checks, fold fixes as needed. Evidence to follow."
```

Why: it prevents duplicated maintainer effort when several PRs are being
landed in parallel, and it means the contributor is never surprised by
maintainer commits appearing on their branch.

## 2. One isolated worktree per PR

Never touch the primary checkout — a mission session may own it. Give every
PR its own worktree:

```bash
git fetch upstream pull/<N>/head:pr-<N>-local
git worktree add .worktrees/pr-<N>-landing pr-<N>-local
cd .worktrees/pr-<N>-landing
```

Each worktree builds its own `uv` virtualenv on the first `uv run` — expect
roughly 40 seconds and some disk on that first command. That is normal, not a
hang.

## 3. Rebase onto current upstream/main first

Contributor branches are routinely 100+ commits behind. Every adjudication —
tests, gates, review — happens on the rebased tip, not the stale base:

```bash
git fetch upstream main
git rebase upstream/main
```

Changelog conflicts resolve in `docs/changelog/CHANGELOG.md`, which is the
canonical changelog. The root `CHANGELOG.md` is a symlink to it (since the
symlink cutover that rode #2338), so both paths reach the same file — resolve
the conflict once, in the canonical location.

## 4. Classify every red check

This is the core reviewer decision point. Diagnose each red check on the
rebased tip and classify it into exactly one of four bins:

| Classification | What it looks like | Action |
|---|---|---|
| **PR defect** | The PR's own change breaks a test or gate | Fix it on the branch (a "fold", [step 5](#5-folds-remediation-commits-on-the-contributor-branch)) |
| **Contract the PR legitimately crosses** | A seam move-set completeness gate, a census tolerance band | Re-pin the contract **in the same PR**, with a dated rationale in the pin |
| **Pre-existing main breakage** | The same red reproduces on an unrelated main-based branch | Prove it cross-branch, file an upstream issue (campsite-cleaning standing order); do **not** fix it inside the contributor PR and do **not** retry-to-green |
| **Perf-budget flake** | A budget gate trips without a correctness signal | Note it, watch for recurrence, tune the budget at the root if it repeats — never retry-to-green |

The cross-branch reproduction for the third bin is cheap and decisive:

```bash
git worktree add /tmp/repro-main upstream/main
cd /tmp/repro-main && PWHEADLESS=1 uv run pytest <failing test> -q
```

If it is red there too, the PR does not wear the failure — the filed issue
does. See the
[test-flakiness handling policy](testing-flakiness.md) for the
never-retry-to-green rule behind the fourth bin.

## 5. Folds: remediation commits on the contributor branch

Folds are maintainer commits pushed directly to the contributor branch. This
relies on `maintainerCanModify`, which is true by default on PRs from forks.

- Keep each fold small and single-purpose.
- Label the commit subject `landing fold: ...`.
- Explain every fold in the remediation summary comment ([step 10](#10-post-the-remediation-summary)).

Typical folds: canonical-source fixes (the changelog lives in
`docs/changelog/`), seam re-pins with dated rationale, retired-shim API
migrations, and doc/contract artifact sync.

## 6. Red-first verification for bugfix PRs

A fix whose test is green before and after the fix captures nothing. Prove
the PR's test actually witnesses the bug by swapping the pre-fix product file
back in:

```bash
git checkout upstream/main -- <product-file>
PWHEADLESS=1 uv run pytest <the PR's test> -q     # MUST FAIL
git checkout HEAD -- <product-file>
PWHEADLESS=1 uv run pytest <the PR's test> -q     # must pass again
```

Post the result on the PR. If the test never goes red, the fold is a better
test — not a green checkmark.

## 7. Review focus areas beyond CI

What the maintainer reads the diff for, beyond the checks:

- **Canonical sources** — does the change edit the source of truth, or a
  generated mirror/agent copy? (Agent directories under `.claude/`,
  `.amazonq/`, etc. are generated; sources live under `src/doctrine/`.)
- **SSOT / duplication** — does new code near-copy an existing canonical seam
  or resolver? Justified divergence must be adjudicated explicitly (name the
  contract difference), never assumed.
- **Contract artifacts** — a new command or field on a versioned surface must
  land in the machine contract (`upstream_contract.json`), the version
  ledger, and the human docs together, in the same PR.
- **Scope-vs-spec** — an apparent scope surprise may be required by the
  mission spec; check the FRs and constraints before flagging creep.
- **Error-handling nets** — best-effort helpers must catch the *actual*
  exception types their callees raise, not a guessed superset.
- **Terminology canon** — on any prose or doctrine touch, run the guard
  locally: `PWHEADLESS=1 uv run pytest tests/architectural/test_no_legacy_terminology.py -q`.

## 8. Adversarial squad for architectural or API-surface PRs

For changes to versioned contracts or shared seams, dispatch profile-loaded
review lenses in parallel — for example `architect-alphonso` for design and
contract adherence, `paula-patterns` for SSOT and duplication — with
read-only access to the landing worktree.

- Fold their MAJOR findings ([step 5](#5-folds-remediation-commits-on-the-contributor-branch)).
- File their MINORs and NOTEs as **one** follow-up issue, parented under the
  relevant functional epic.

## 9. Push discipline

Before any force-push to a fork branch, check for commits you have not seen —
Copilot-review commits and parallel-session commits get cherry-picked, never
clobbered:

```bash
git fetch <fork-remote> <branch>
git log <old-head>..FETCH_HEAD --oneline   # anything here? cherry-pick it first
LEASE_SHA=$(git rev-parse FETCH_HEAD)
git push <fork-remote> HEAD:refs/heads/<branch> --force-with-lease=<branch>:"$LEASE_SHA"
```

Two lease lessons from the 2026-07-04 pass, both worth internalizing:

1. **A bare `--force-with-lease` fails with `(stale info)` on fork branches
   you have never fetched** — the lease has no remote-tracking ref to compare
   against locally. The explicit `<branch>:<sha>` form above is the standard
   flow, not a workaround.
2. **The lease sha must come from `git rev-parse`, never retyped from a
   display.** Two pushes in the pass were rejected because a lease sha was
   retyped from a 9-character abbreviated prefix.

## 10. Post the remediation summary

After pushing folds, post one structured comment on the PR:

- the review verdict;
- each fold, with its why;
- squad verdicts, if a squad ran;
- local test evidence — counts, plus `ruff` / `mypy` results;
- pre-existing failures called out **with the filed issue number**;
- the state: e.g. "watching CI; merge-ready on green".

Contributor-education notes (for example, which file is the canonical
changelog) go in this comment too, addressed to the author.

## 11. Hand-off — the operator merges

The operator merges; the maintainer never runs `gh pr merge`. The hand-off
deliverable is:

- green CI;
- the PR un-drafted;
- the evidence trail on the PR;
- landing-order constraints stated explicitly — for example, a structural
  cutover riding one PR forces an order on the rest of the pass.

## 12. Follow-up hygiene

Everything discovered but out of scope gets a tracked home **the same day**:
filed, labeled, and parented under a functional epic (never a meta rollup).
New issues get processed by a triage pass immediately, so the next landing
pass starts from a clean queue.

## Gotchas

Field notes from the 2026-07-04 landing pass. Where the friction has since
been fixed, the end-state is stated instead of the trap.

- **The changelog has one canonical home.** `docs/changelog/CHANGELOG.md` is
  the canonical changelog; the root `CHANGELOG.md` is a symlink to it. Edits
  and conflict resolutions land in the canonical file either way — there is
  no longer a generated root mirror to trip docs-freshness.
- **`--force-with-lease` on never-fetched fork branches.** See
  [step 9](#9-push-discipline): use the explicit `<branch>:<sha>` lease form,
  and take the sha from `git rev-parse` — never retype it from an
  abbreviated display.
- **Pre-existing main breakage surfaces mid-pass.** One broken contract on
  main (#2339: dotted `migration_id` vs the dry-run JSON contract) turned
  local runs red on *every* rebased branch in the pass. Adjudication cost one
  cross-branch reproduction per PR until the issue was filed — file early;
  the filed issue is what lets subsequent PRs skip the reproduction.
- **Saturated tolerance bands trip on the next legitimate change.** The CLI
  visible-count census sat at the top of its band, so the next legitimate
  command (#2338) tripped it. A saturated band needs a re-pin with a dated
  rationale — the band was re-pinned 2026-07-04 at 236 visible (tolerance
  212–259) in `tests/docs/test_check_cli_reference_freshness.py`. That
  re-pin-in-the-same-PR pattern is the model for the second bin of
  [step 4](#4-classify-every-red-check).
- **Seam completeness gates are invisible to contributors.** Adding a `def`
  to `src/specify_cli/cli/commands/agent/tasks_move_task.py` also requires
  joining the `_MOVE_SET` pin in
  `tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py` and the
  re-export block in `agent/tasks.py`. Expect this as a fold on PRs that
  touch decomposed command modules.
- **CI-only architectural gates land late.** Repo-wide gates (terminology,
  shim retirement, seam boundaries) run in the
  `integration-tests-core-misc (architectural)` shard — a PR can pass every
  fast shard and fail ~40 minutes later. Run `tests/architectural/` locally
  on the rebased tip before declaring a branch green.
- **Shard path-filters mask pre-existing failures.** The `changes` filter
  skips shards like `fast-tests-cli` on PRs that do not touch those paths, so
  a pre-existing red only surfaces on the first PR that does — the innocent
  PR wears the failure. Classify it as pre-existing (bin three of
  [step 4](#4-classify-every-red-check)), not as the PR's defect.
- **`scripts/` invocations need `PYTHONPATH=.`.** The docs scripts import
  `scripts.docs.*` as a package; without it they crash with
  `ModuleNotFoundError: scripts`:

  ```bash
  PYTHONPATH=. uv run python scripts/docs/check_docs_freshness.py --ci
  ```

- **`build_cli_reference.py` defaults to the wrong output path.** Its
  defaults write `docs/reference/`, while the live canonical reference is
  `docs/api/cli-commands.md`. Always pass the outputs explicitly:

  ```bash
  PYTHONPATH=. uv run python scripts/docs/build_cli_reference.py \
    --output docs/api/cli-commands.md \
    --agent-output docs/api/agent-subcommands.md
  ```

- **Per-worktree venv rebuild.** The first `uv run` in a fresh landing
  worktree rebuilds the virtualenv (~40 s + disk). Budget for it; do not
  debug it.

## See also

- [Review gates: pre-PR / pre-review checklist](review-gates.md) — the
  contributor-side hygiene this runbook assumes.
- [Test-flakiness handling policy](testing-flakiness.md) — the
  never-retry-to-green rule and budget-gate tuning.
- [Guides index](index.md)
