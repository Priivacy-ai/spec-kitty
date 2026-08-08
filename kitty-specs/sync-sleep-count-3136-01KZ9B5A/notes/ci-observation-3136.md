**NON-GATING OBSERVATION — this is not evidence of the fix and can never be cited as a pass.** A clean `fast-tests-sync` run is the *pre-fix* outcome ~39% of the time (11 of 18 pristine-`main` jobs red on this class, including at `98198e980`). `SC-006` was retired for exactly this reason.

# CI observation — mission `sync-sleep-count-3136-01KZ9B5A`, WP07 (T040 / T041)

> **This note is NOT an acceptance arm and must not appear among them.** It is not cited as proof
> anywhere in the PR body, and a reviewer who finds it cited as proof should treat that as a defect.
> The mission's evidence is **structural**: the injection guard (`SC-004` / `SC-005`), the
> mechanism-keyed gate (`SC-007`), and the base-branch red — not a CI colour.

---

## The pull request

| Field | Value |
|---|---|
| **PR number** | **`#3252`** |
| **URL** | `https://github.com/Priivacy-ai/spec-kitty/pull/3252` |
| **Head SHA at open** | **`b0312a43890bc5a968ac24380ddf96828bfe8c7b`** |
| **Head ref** | `MOES-Media:pr/sync-sleep-count-3136` |
| **Base ref** | `Priivacy-ai:main` (at `709a59534`) |
| **`isDraft`** | **`true`** |
| **State** | `OPEN`, `MERGEABLE` |
| **Opened at** | `2026-08-07T07:02:38Z` |
| **Observation taken at** | `2026-08-07T07:11:06Z` |
| **Head SHA now** | **deliberately not frozen here — see the note below** |

> **The head advances after this note is written, so pinning "the current head" inside it would be
> false by the next push.** That is the self-measuring defect this mission has rejected four times;
> it is not re-committed here. What IS invariant, and what a reader actually needs, is stated as a
> **property with its reproducing command**:
>
> **Every commit after `b0312a438` on this branch touches `kitty-specs/**` and nothing else.**
> They add this note, the constraint transcripts, the closed `C-001` handshake and the
> `RL-040`…`RL-049` ledger entries — artifacts that describe the PR and therefore could not exist
> before it was opened. Verify, against whatever the head is when you read this:
>
> ```bash
> git diff --stat b0312a438 HEAD -- . ':(exclude)kitty-specs/**'     # MUST be empty
> git log --oneline b0312a438..HEAD                                  # dossier commits only
> ```
>
> **Every classification in this note is anchored to `b0312a438`**, the SHA the CI run observed. If
> the command above ever prints a non-empty diff, this note's classifications no longer describe the
> tree and CI must be re-observed. A reader who wants a same-head observation must re-run CI on the
> current head; this note does not pretend to be one.
>
> ### 🔴 THE TRIPWIRE ABOVE HAS FIRED — see the ADDENDUM at the end of this note
>
> As of `2026-08-07`, the command prints
> `tests/architectural/test_shared_module_object_patches.py | 14 ++++++++++++--`. **The invariant is
> broken and the stated consequence has been discharged**: CI was re-observed and the classification
> table below has been superseded. **Read the addendum before using any row in it.**

**The head SHA is the only reproducible handle.** This mission's predecessor branch moved twice and
every branch-name-anchored transcript became unreproducible; quote `b0312a438` rather than the branch
name. Verify with:

```bash
unset GITHUB_TOKEN
gh pr view 3252 --repo Priivacy-ai/spec-kitty --json number,isDraft,headRefOid,state
```

**Not merged. Not marked ready for review.** Un-drafting requires the operator's explicit go; merging
to the protected branch is the operator's action, never an agent's.

---

## Why a green shard would prove nothing — the `11/18` figure

`SC-006` was **retired**, not descoped, because it discriminated nothing. Pristine `main` reddens on
this class in **11 of 18** consecutive `fast-tests-sync` jobs — **including at `98198e980`** — so a
single clean run is the **pre-fix** outcome **~39%** of the time.

**`11/18` is NON-DISCRIMINATING.** A green `fast-tests-sync` on this PR would be consistent with the
fix working *and* with the fix not existing. It cannot separate the two hypotheses, which is the whole
reason the criterion was retired.

**Independently corroborated this session** by reading the last six `CI Quality` runs on pristine
`upstream/main` — an own-control rather than a restatement of the `11/18`:

```bash
gh run list --repo Priivacy-ai/spec-kitty --branch main --workflow "CI Quality" --limit 6 \
  --json databaseId -q '.[].databaseId' | while read R; do
    gh run view "$R" --repo Priivacy-ai/spec-kitty --json jobs \
      -q '.jobs[] | select(.name=="fast-tests-sync") | .conclusion'; done
```

| Job | pristine `main`, last 6 runs |
|---|---|
| `fast-tests-sync` | **failure 6 / 6** |
| `regression tests (blocking)` | **failure 6 / 6** |
| `integration-tests-status` | failure 5 / 5 (1 skipped) |
| `integration-tests-sync` | failure 5 / 5 (1 skipped) |
| `arch-adversarial (arch_shard_2)` | failure 4 / 6 |
| **`lint`** | **success 6 / 6** |

---

## ⚠ Two different claims — kept apart on purpose

**Claim A — the three targeted `tests/sync/tracker/` nodes (plus the fourth census node) go green.**
Achievable, and worth observing.

**Claim B — the whole board goes green.** **Not achievable, and this WP does not claim it.** The
`fast-tests-sync` job also carries pre-existing `tests/regression` inverted-red markers this mission
does not touch, and that job is **designed** to be red while open P0s exist.

**No sentence of the form "CI is green now" appears in this artifact or in the PR body.** It would be
a defect if it did.

### Per-node outcomes — SEPARATE from the job aggregate

These are the **local** runs on the composed tree, each node selected individually so no aggregate can
absorb it. They are Claim A, and nothing else:

| Node | `EXIT` | Result |
|---|---|---|
| `test_saas_client.py::TestPolling::test_exponential_backoff_intervals` | 0 | `1 passed in 44.91s` |
| `test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after` | 0 | `1 passed in 57.81s` |
| `test_saas_client.py::TestRetryBehaviors::test_429_defaults_to_5s_when_missing` | 0 | `1 passed in 46.25s` |
| `test_saas_client.py::TestPolling::test_timeout_after_5_minutes` (census node) | 0 | `1 passed in 46.26s` |
| `test_saas_client_origin.py::TestSearchIssues::test_429_retries_then_raises` (the CI victim) | 0 | `1 passed in 58.77s` |

**In CI's `fast-tests-sync` job on `b0312a438`, zero `tests/sync/tracker/` nodes failed**
(`2121 passed, 11 skipped, 3 warnings, 1 error`). The single `error` is a teardown leak on an
unrelated file — see the classification below.

---

## The job aggregate, and every failure classified

`gh pr checks 3252` at `2026-08-07T07:11:06Z`, head `b0312a438`: **27 pass · 7 fail · 36 skipping.**
**Superseded** — at `2026-08-07T10:42:54Z`, head `bf68b101b`: **28 pass · 6 fail · 36 skipping.** See the addendum.

Every failure is classified into exactly one of (a) pre-existing known red, (b) CI-environment,
(c) stale-install false red, (d) attributable to this diff. **Only (d) is this mission's.**

| Job | Result | Class | Basis |
|---|---|---|---|
| ~~**`lint`**~~ **SUPERSEDED — now `pass`** | *was* `Broken patch() targets (1 of 5087 checked)` | *was* **(d) THIS MISSION'S** | **FIXED by `bf68b101b`; see the addendum.** The row is kept struck rather than deleted because the classification method it demonstrates — controlling against `main` — is what identified it. → **`RL-048` (RESOLVED)** |
| `arch-adversarial (arch_shard_2)` | `2 failed, 628 passed, 3 skipped` | **mixed (a) + composition** | `test_routed_load_meta_floor` → **(a)**, reproduced red on a pristine `upstream/main` worktree (**`RL-047`**). `test_no_unregistered_baseline_keys_are_added` → the WP05-guard-vs-upstream-key **integration crossing** (**`RL-046`**), which is why `main` shows 4/6 not 6/6 |
| `fast-tests-sync` | `2121 passed, 11 skipped, 1 error` | **(a)** | `failure 6/6` on pristine `main`. The error is the **`FR-007` leak guard** on `test_issue_598_hang_fixes.py::TestBackgroundStopBounded::test_stop_acquires_lock_and_cancels_timer` — the `#3130` / `#3193` leak class, **out of scope per `C-003`**. **No `tests/sync/tracker/` node failed** |
| `integration-tests-sync` | `209 passed, 4 errors` | **(a)** | `failure 5/5` on pristine `main`. All four errors are the same **`FR-007` leak guard** class on `test_dual_write_integration.py` (×2) and `test_daemon_self_retirement.py` (×2) — `#3130` / `#3193`, **out of scope per `C-003`** |
| `integration-tests-status` | `1 failed, 236 passed` | **(a)** | `failure 5/5` on pristine `main`. The failing fixture reads **another mission's** `meta.json` (`coordination_branch: kitty/mission-review-cycle-verdict-seam-rebuild-01KZ2W7W`) — nothing to do with this diff |
| `regression tests (blocking)` | `2 failed, 10 passed, 36511 deselected` | **(a)** | `failure 6/6` on pristine `main`. Both are **inverted-red markers on open P0s** — `test_issue_2782_sync_strict_json_ingress_skip.py` and `test_issue_2804_merge_resets_gate_artifacts.py`. This job is *designed* red while those P0s are open |
| `quality-gate` | fail | **roll-up** | Aggregates the above; carries no independent signal |

### `C-003` — the leak `ERROR`s are named out-of-scope, wherever a count appears

The `#3130` / `#3193` leak `ERROR`s are **pre-existing and excluded**. They are counted with
`^ERROR tests/`, never `^ERROR `, and `-ra` is used, never `-rf`. They are **not** this mission's
failures and were **not** "fixed". They account for **1 of 1** errors in `fast-tests-sync` and
**4 of 4** in `integration-tests-sync`.

### Nothing was retried to green

No failing job was re-run to obtain a different colour. A pre-existing or flaky failure is
**classified**, never retried — and the one genuinely attributable failure (`lint` / `RL-048`) is
**disclosed in the PR body as the top landing risk**, not worked around.

### Killed or timed-out runs

**No run recorded in this note was killed or timed out.** Had one been, it would be recorded as
**neither a pass nor a failure**, in those words. One harness-level wrapper timeout did occur locally
while iterating over the targeted nodes; the two nodes that had already reported are quoted above, and
the remaining two were **re-run to completion** rather than reported from the truncated invocation.

---

## Summary for a later reader

*(as at `b0312a438`)* **One** of the seven failing CI jobs is attributable to this diff: `lint`, via
**`RL-048`** — a regex patch-target gate matching a docstring. Five are pre-existing reds reproduced on
pristine `main`, and one (`arch_shard_2`) is half pre-existing and half a genuine integration crossing
(**`RL-046`**) that needs the gate owner's ruling.

*(as at `bf68b101b`, current)* **ZERO of the six remaining failing jobs is attributable to this diff.**
`lint` is fixed and green. See the addendum.

**None of this is acceptance evidence.** It is an observation, recorded beside the PR because T041
requires the observation to exist and to be labelled for what it is.

---

# ADDENDUM — 2026-08-07, WP07 review cycle 2: re-anchored to `bf68b101b`

**This addendum supersedes every classification above.** It exists because the tripwire this note
defined for itself **fired**, and the note's own stated consequence — *"this note's classifications no
longer describe the tree and CI must be re-observed"* — had not been discharged.

## What broke the invariant, and why that is the right outcome

The note asserted: *"every commit after `b0312a438` on this branch touches `kitty-specs/**` and nothing
else."* Run verbatim, it now prints:

```
$ git diff --stat b0312a438 HEAD -- . ':(exclude)kitty-specs/**'
 tests/architectural/test_shared_module_object_patches.py | 14 ++++++++++++--
 1 file changed, 12 insertions(+), 2 deletions(-)
```

The cause is **`bf68b101b fix(sync-sleep-count): make WP05's gate docstring unmineable by
check_patch_targets`** — the fix for `RL-048`, the very red this note classified as category (d). A
source file changed, so the invariant is genuinely false. **The tripwire worked exactly as designed**;
what was missing was the follow-through, which is what this addendum is.

## Re-observation at the current head

| Field | Value |
|---|---|
| **Head SHA** | **`bf68b101b6b2b33ccd0b39ead7e975b74928743f`** |
| **Observed at** | `2026-08-07T10:42:54Z` |
| **Result** | **28 pass · 6 fail · 36 skipping** (was 27 · 7 · 36 at `b0312a438`) |
| **`isDraft`** | still `true` — unchanged, not un-drafted |

### The single delta: `lint` red → **green**

```
b0312a438 : lint = fail   ::error::Broken patch() targets (1 of 5087 checked):
                            tests/architectural/test_shared_module_object_patches.py:5:
                            cannot import any prefix of 'a.b.c'
bf68b101b : lint = pass   All 5086 patch() targets valid.
```

The corpus drops by exactly **1** — the phantom target, and nothing else. **No gate source was
changed**; the docstring now uses a brace placeholder (``patch("{mod}.attr")``) that the extractor's
regex cannot match. Full rationale, the rejected alternatives and the red-first proof are in `RL-048`'s
`### RESOLVED (2026-08-07)` section.

### The other six are unchanged, and none is attributable to this diff

| Job | at `b0312a438` | at `bf68b101b` | Class |
|---|---|---|---|
| `lint` | fail | **pass** | **RESOLVED** |
| `arch-adversarial (arch_shard_2)` | `2 failed, 628 passed` | `2 failed, 628 passed` | unchanged — `RL-047` pre-existing + `RL-046` crossing |
| `fast-tests-sync` | fail | fail | (a) pre-existing, `failure 6/6` on `main` |
| `integration-tests-sync` | fail | fail | (a) pre-existing |
| `integration-tests-status` | fail | fail | (a) pre-existing |
| `regression tests (blocking)` | fail | fail | (a) pre-existing, designed red while P0s are open |
| `quality-gate` | fail | fail | roll-up |

`arch_shard_2`'s two failures are **byte-identical** to the earlier run — `test_routed_load_meta_floor`
(`ROUTED_LOAD_META_FLOOR (128) … live routed count (133)`) and
`test_no_unregistered_baseline_keys_are_added` (`['test_verdict_seam_census']`). Both are the
pre-existing / crossing pair already filed; **neither was retried to green.**

## The new invariant, stated so it cannot go stale the same way

The previous formulation pinned a *property of the diff*, which a legitimate fix falsified. The
durable statement is about **attribution**, not about which files moved:

> **Every commit on this branch after `b0312a438` is either a `kitty-specs/**` dossier update or a
> fix for a red this note itself classified.** As of `bf68b101b` there is exactly one of the latter.

Re-derive the whole picture rather than trusting any frozen row above:

```bash
git log --oneline b0312a438..HEAD
git diff --stat b0312a438 HEAD -- . ':(exclude)kitty-specs/**'
unset GITHUB_TOKEN && gh pr checks 3252 --repo Priivacy-ai/spec-kitty | awk -F'\t' '{print $2}' | sort | uniq -c
```

**This addendum is still not acceptance evidence.** A green `lint` is a gate returning to its
pre-mission state, not proof the fix works; the mission's evidence remains structural.
