# Landing handoff — `chain-b-consent-bypass-3167-01KZ63HK`

**State: mission complete, pre-merge squad run and remediated, NOT YET LANDED.**
**Branch:** `feat/chain-b-consent-bypass-3167` · **Merge base:** `abca7ec96` · **Current `upstream/main`:** `96494e5ec`

## Why this stops here rather than opening the PR

The landing process was not run. The `pr-landing` skill is mandatory and a PreToolUse hook blocks
`gh pr create` unless it has; `SKPRLANDING=1` exists to **attest that you ran it**, never to skip it.
Attesting without running would be precisely the manufactured green this programme exists to close — on
the one step that is outward-facing and hard to reverse. So the work stops at the last honest point.

Everything below is verified. Nothing here is a plan; it is a state description.

## What is done

- **All four work packages implemented, independently reviewed, and `approved`.** WP01 (frozen deletion
  manifest), WP02 (the atomic retirement), WP03 (unblinding the cone), WP04 (the record and the tracker).
- **Pre-merge squad run** — three lenses (evidence / code / completeness). Two returned SAFE TO LAND; the
  completeness lens returned BLOCK on three items. **All three are remediated** in the commit
  `fix(consent): remediate the pre-merge squad's findings`.
- **13 issues filed, all OPEN, none absorbed:** `#3188`, `#3190`, `#3191`, `#3192`, `#3193`, `#3196`–`#3203`.
- **`#3167`'s issue-matrix verdict is terminal** — `deferred-with-followup`, deliberately not `fixed`.
- **`#3130` carries the C-005 handoff comment** with the pin renumbering, un-pin status, the error
  distribution, and the two measurement footguns.

## What remains, in order

1. **Compact the history.** 94 commits, of which ~24 are `chore(spec-kitty): status transition`. Directive
   `046-readable-consistent-prs` wants linear and compacted; the brief's shape is **two commits — the
   dossier bunched, then the code** — with landing folds *amended into the code slice*, never stacked.
   **Never mix `kitty-specs/` with code in one commit.**
2. **Rebase onto `96494e5ec`.** Verified: **zero collision** — none of the 93 intervening commits touches
   any file this mission owns (`git log abca7ec96..upstream/main --name-only` restricted to the owned set
   returns empty). Re-check, because the base has already moved twice during this programme.
3. **Run CI's gates locally**, with a red-first proof.
4. **Lease-push to the MOES-Media fork.** ⚠️ `MOES-Media/main` is **NOT** a fast-forward of
   `upstream/main` — it carries ~78 commits of separate mission work. The landing skill says to
   fast-forward it; **do not**. Force-pushing destroys real work. Skip the intermediate fork PR and open
   the cross-fork draft directly; its range is measured against `upstream/main` anyway.
5. **Open a cross-fork DRAFT PR** to `Priivacy-ai:main`, then **read the state back** —
   `gh pr view <N> --json isDraft,state`. The `--draft` flag has been accepted while GitHub recorded
   `isDraft: false`.
6. **Post the remediation-summary comment.** **Never `gh pr merge`** — the operator merges, and do not
   un-draft without an explicit go.

**Commitlint runs on the range:** `type(word-scope): subject`, scope is a word not `#NNNN`, subject ≤100
chars, **body lines ≤100 chars**. `landing fold:` is **not** a valid type even though upstream's own head
uses it. Verify with a real exit status: `npx --yes commitlint --from upstream/main --to HEAD; echo $?` —
do not read it through a pipe.

## What the PR body must disclose

A draft exists nowhere — an earlier attempt was written to a scratchpad path keyed to a previous session id
and no longer exists. That is itself worth knowing: **do not trust `/tmp/claude-*/…/scratchpad` to survive.**

It must say, without softening:

- **`#3167` was not delivered as asked.** One of its two sites had **no production caller**, so it was
  **retired rather than migrated**; the other, `sync/runtime.py:106`, is **deliberately unchanged** per
  operator decision D-M5a-1=a, with the defence-in-depth residual filed as `#3199`.
- **The `tests/sync` error count is a distribution, not a number** — `{5,5,6,6,6}` at the merge base,
  `{5,6}` after, n=7 across two measurers. The volatile band is one shape (`live thread … target=None`)
  produced by `_ChainedTimer`/`threading.Timer`, attributed by the leak guard's `after − before` difference
  to whichever test spans the thread's lifetime. **The observer moves; the leak does not.** No error in any
  run implicates a file this mission owns. Filed as `#3193`. **Neither measurer asserts this diff had zero
  influence** — both assert the class pre-exists.
- **Pre-existing marker reds** in `tests/runtime/test_runtime_bridge_identity.py` — `#3188`, not fixed here.
- **Three live-path branches lost their only pin** (singular `details[*].detail`, per-event
  `accepted`/`warning`/`queued`). Their pins tested symbols in the frozen dead set, so keeping them was
  impossible. `#3192`, and three manifest rows say "partial only" rather than claiming coverage.
- **A per-event forbidden-key screen is still owed** — checked, not assumed. `#3191`.
- **No `CHANGELOG.md` entry** despite 1105 lines removed from `sync/batch.py`, and the out-of-tree-importer
  gap (`specify_cli` ships on PyPI; only in-repo reach was closed). Name both.
- **The eight filed residuals use `owner/repo#NNNN`**, which the matrix parser does not match, so the
  completeness gate **cannot fail** for them. All eight were verified OPEN by hand instead. Disclosed, not
  papered over.
- **`scripts/` is outside CI's linted set** (`ruff check src tests`), which is why the closure script's two
  `C901`s (`#3190`) are not CI-blocking. The dossier did not say this; the PR body should.

## Cross-mission consequences the next author needs

- **Hazard H4:** this mission removed the `E15` allowlist entry and changed `_baselines.yaml` 28→27, both
  in `tests/architectural/` — which **M1 also opens**. M1's architectural window must not overlap.
- **M3's inputs moved:** pins renumbered to `:420`/`:442`/`:452`, and the registry is
  `_leak_guard.py:376-479`, not the `:333-423` the programme plan recorded. The plan's M3 row now names
  `contracts/cone-attribution.md` as a required input; `#3130` carries the same handoff.
- **The lane worktrees never existed.** All four WPs ran in the root checkout on the target branch.
  Harmless here because this is genuinely one lane, but the isolation the lane model implies was not
  present, and a mission with real parallel lanes would have had two agents writing one tree.

## Reading order for whoever picks this up

`analysis-report.md` first — it records what this mission got **wrong** and how, which is more useful than
what it got right. Then `contracts/deletion-manifest.md` (the frozen contract the diff is checked against),
then `contracts/cone-attribution.md` (every measurement, including the ones that were corrected).
`research.md` carries two wrong findings marked inline rather than edited away.
