# Paula Patterns — Anti-Gaming / Fakeable-DoD / Vacuous-Proof Review (Mission B WP decomposition)

**Author:** paula-patterns (profile-loaded; DIR-001 owning-boundary, DIR-003 decision-documented,
DIR-030 test-quality-gate, DIR-032 conceptual alignment). Lens: anti-laziness / fakeable-DoD /
vacuous-proof.
**Date:** 2026-06-17
**Branch / HEAD:** `feat/write-side-context-factory-adoption` @ `eba2448d8` (re-verified live, not from inventory).
**Scope:** the 9 WP prompts + their DoDs vs the actual test/code surface on HEAD. The mission rests
entirely on **verification-by-deletion** + WP01's net being **non-vacuous**. My own prior finding (the
"live-evidence trap": the strongest write-path suite passes `repo_root=` everywhere, blind to the swap;
the FR-004 divergence has zero witness) is the central risk. I adversarially audited whether the WP DoDs
let an implementer satisfy "suite green after deletion" against fixtures that never hit the real path.

---

## Live-code verification (claims vs HEAD)

Confirmed before judging the prompts:

1. **`repo_root=` blindness is real.** `tests/specify_cli/coordination/test_status_transition.py` passes
   `repo_root=repo` at 9 call sites (lines 84,158,197,262,371,…). `_repo_root_for_feature`
   (`status_transition.py:49-54`) has `if repo_root is not None: return repo_root` — the explicit-root
   short-circuit. Confirmed: that suite cannot witness the root-walk swap. **A-1 / paula trap holds.**
2. **FR-004 divergence is real and at the named line.** `status_transition.py:291`:
   `destination_ref=coord_branch or _current_branch(repo_root)`. `_current_branch` =
   `git rev-parse --abbrev-ref HEAD` (CWD/checkout-dependent). Factory `destination_ref` for the
   flattened arm resolves `target_branch` via `get_feature_target_branch` → `resolve_primary_branch`
   (CWD-invariant). **The divergence is a correctness flip, not a no-op.**
3. **Private-helper-by-name tests exist where WP01/WP02 say.** `test_emit.py:302-306`
   (`_feature_status_lock_root` by name), `test_work_package_lifecycle.py:19,463-464`
   (`_repo_root_for_lock` imported + asserted by name). Confirmed (paula S-4/S-9).
4. **FR-006 deletion targets exist where WP07 says.** `prompt_source` and the `surface=` read-param
   are reachable as described in `reduction-census.md §5`.

So the prompts' premises are accurate. The defects are in **enforceability and ownership coverage**, and
in **one FR-004-fighting test that no WP owns** — discovered live, NOT in my prior census.

---

## BLOCKERS

### BLOCKER-1 — An FR-004-fighting test ENCODES THE BUG AS A CONTRACT, and no WP owns or updates it. The "FR-004 oracle flips green" claim (T002/WP05) is undermined; every status-suite green-after claim is at risk of a hidden RED.

**This is the single most important finding and it is NEW (not in my pre-refactor census, which said the
flattened arm has "ZERO witnessing test").** There IS a witnessing test, and it pins the *wrong* value:

`tests/unit/status/test_mission_status_aggregate.py::TestSaveReturnType::test_save_supports_identity_bearing_legacy_mission`
(~line 943):
- checks out `legacy-lane`, `monkeypatch.chdir(repo)`, mission meta has **no** `coordination_branch` and
  **no** `target_branch` → flattened arm;
- drives the real `save()` → `_identity_for_request` → `destination_ref` path;
- asserts `receipt.destination_ref == "legacy-lane"` and `git show legacy-lane:…/status.events.jsonl`.

This asserts the **current buggy behavior** (`_current_branch` = git HEAD = `legacy-lane`). When WP05 flips
`destination_ref` → `branch_ref.destination_ref`, the flattened legacy case resolves to the primary branch
(`get_feature_target_branch` → `resolve_primary_branch`, e.g. `main`), **not** `legacy-lane`. The test goes
**RED**, and the `git show legacy-lane:…` line will fail because the event now lands on `main`.

**No WP owns `tests/unit/status/test_mission_status_aggregate.py`** (grep of all `owned_files` and
`lanes.json`: zero hits). Consequences, all gaming-relevant:
- WP05's DoD "the FR-004 oracle actually flipped green" can be claimed satisfied via the WP01-authored
  oracle in `tests/specify_cli/write_side/` while this *other* test silently goes RED — the implementer's
  own owned suite is green, the mission suite is not. An implementer under "fix adjacent breakage" (C-008)
  might also just **flip the assertion to the new value with no analysis** — which is correct here, but
  must be an *explicit, reasoned* update tied to FR-004, not a silent edit, or it becomes the exact
  "retire a live-behavior test under cover of deletion-target" gaming WP07 is warned against.
- It directly contradicts the plan's framing that FR-004 has "zero witnessing test" — the planning
  research is stale on this point, so the implementer will not be looking for it.

**Remediation (concrete):**
1. Add `tests/unit/status/test_mission_status_aggregate.py` to **WP05's `owned_files`** (it owns the
   FR-004 flip; this is its blast radius).
2. Add a WP05 subtask + DoD line: *"T023a — Update
   `test_mission_status_aggregate.py::test_save_supports_identity_bearing_legacy_mission`: the flattened
   no-coord case now asserts `destination_ref == <primary/target branch>` (CWD-invariant), NOT the
   checked-out `legacy-lane`. This test pinned the FR-004 bug as a contract; updating it (with the
   reasoned before→after value) IS part of witnessing the fix. The `git show` must target the
   target/primary branch."*
3. Correct WP01 T002 and the plan's "zero witnessing test" wording: there is a flattened-arm test; the WP01
   oracle must be reconciled with it (assert the SAME post-fix value), or the two tests disagree.
4. WP05 reviewer-guidance add: *"Confirm no flattened-arm `destination_ref` assertion anywhere in
   `tests/` still asserts a git-HEAD/checkout-dependent branch after the flip (grep
   `destination_ref ==` across `tests/`)."*

### BLOCKER-2 — WP02 deletes private helpers that `test_worktree_topology.py` imports BY NAME, but no WP owns that file. WP02's "suite green after deletion" is provably false at merge time (ImportError), and the by-name retirement is incompletely scoped.

WP02 routes `_feature_status_lock_root` / `_repo_root_for_lock` to `workspace.primary_root` and (per T010)
retires the by-name tests in `test_emit.py` / `test_work_package_lifecycle.py`. But the **strongest**
topology-true by-name lock-root tests live in
`tests/specify_cli/coordination/test_worktree_topology.py:280,289,292,307,316,317,353,361` — they `from
specify_cli.status.emit import _feature_status_lock_root` and `from … work_package_lifecycle import
_repo_root_for_lock`. **This file is in NO `owned_files` list.**

If WP02 deletes the helpers, those imports raise `ImportError` and the whole module fails to collect —
WP02's own owned suite (`tests/status/`) can be green while `tests/specify_cli/coordination/` is RED. The
DoD "WP01 net + `tests/status/` suite green" is satisfiable *and still ships a broken suite*. This is a
classic scope-of-green gaming surface: the green claim is scoped to owned files, not the real blast radius
of a `def` deletion.

**Remediation (concrete):**
1. Add `tests/specify_cli/coordination/test_worktree_topology.py` to **WP02's `owned_files`**.
2. WP02 T010 reword from *"Retire the private-helper by-name tests in test_emit.py /
   test_work_package_lifecycle.py"* to: *"Retire/convert ALL private-helper-by-name lock-root tests that
   import `_feature_status_lock_root` / `_repo_root_for_lock` — across `tests/status/test_emit.py`,
   `tests/status/test_work_package_lifecycle.py`, AND
   `tests/specify_cli/coordination/test_worktree_topology.py` — repointing their behavioral intent at the
   WP01 public invariant. Grep `_feature_status_lock_root|_repo_root_for_lock` across `tests/` → ZERO
   surviving imports of the deleted symbols."*
3. WP02 DoD add: *"`grep -rn '_feature_status_lock_root|_repo_root_for_lock' tests/` returns no
   import/call of a deleted symbol; the full `pytest tests/specify_cli/coordination/ tests/status/` suite
   collects and is green (not just the owned files)."*
4. WP01 T006 caveat: the public lock-root invariant must cover the **coord-worktree vs primary same-lock**
   property that `test_worktree_topology.py:280-317` currently proves by name — otherwise retiring those
   loses real coverage (the two-process-same-lock concurrency invariant), which is gaming by coverage loss.

### BLOCKER-3 — "drive WITHOUT explicit `repo_root`" is the load-bearing non-vacuity rule but is NOT mechanically enforceable as written; an implementer can satisfy WP01's DoD with a net that still bypasses the swap.

WP01's whole value is "the net is forced non-vacuous." The DoD line is *"The net drives the write sites
WITHOUT explicit `repo_root=` (paula's trap closed)"* and the reviewer-guidance says *"grep the tests for
`repo_root=` — there should be NONE on the driven calls."* This is **under-specified for review** in three
ways that let a blind net pass:
- **`repo_root=` is not the only escape hatch.** `MissionStatus.load(repo_root=…)` (aggregate.py:196) is a
  *public* entry that takes `repo_root` and is the natural way to drive `save()` → `_identity_for_request`.
  A net can avoid the literal `repo_root=` on the *innermost* helper while still threading a caller-supplied
  root through `load(repo_root=…)`, so `_repo_root_for_feature` short-circuits at line 50 anyway. The grep
  "NONE on the driven calls" is ambiguous about which call layer.
- **Mocked paths / `monkeypatch` of the resolver** would also defeat the swap and aren't named.
- "Topology-true" and "no fabricated short ids" are asserted but there is **no positive forcing check**
  that the re-derivation arm actually executed (e.g. that `classify_worktree_topology` /
  `_current_branch` / the `.parent.parent` arm was reached on the driven path).

**Remediation (concrete):** Replace the WP01 DoD line and reviewer-guidance with a *positive* forcing
obligation, not just a negative grep:
- DoD: *"Each characterization test drives the write site via its real public entry from a CWD that is NOT
  the primary root (a coord-worktree CWD or a lane-branch checkout), and supplies NO caller `repo_root`
  anywhere in the call chain (neither on the helper nor on `MissionStatus.load`). For at least the FR-004
  oracle (T002) and the coord parity rows (T003), the test runs from a CWD whose `git HEAD` ≠
  `target_branch`, so a swap that silently changed the resolved value would change the asserted value."*
- DoD add: *"A test that, if the adoption swap were reverted to a hand-rolled `.parent.parent` /
  `_current_branch`, would STILL pass, is vacuous and rejected. The FR-004 oracle MUST flip
  (RED-on-HEAD → GREEN-post-WP05); the equivalence rows MUST be green-on-HEAD and stay green (these are
  the only ones allowed to be swap-insensitive)."*
- Reviewer-guidance: *"Mutation check — mentally (or actually) revert one adopted site to its
  `.parent.parent` / git-HEAD form; the net MUST go red. If reverting the swap leaves the net green, the
  net is blind. Confirm no `monkeypatch`/mock of `resolve_canonical_root` / `classify_worktree_topology` /
  `_current_branch` on the driven path."*

### BLOCKER-4 — T002's "RED-on-HEAD oracle" permits an `xfail`, which is exactly the silently-removable gaming vector the prompt is meant to close.

WP01 T002 says: *"Mark it clearly as the FR-004 oracle WP05 will flip to green. (If asserting the bug as
RED is cleaner than xfail, capture the current/wrong value as the documented baseline.)"* The parenthetical
**permits `xfail`**. An `xfail` that WP05 deletes-and-replaces is indistinguishable from the "silently
removed xfail" gaming the brief explicitly worries about — and an `xfail(strict=False)` that quietly starts
passing produces no signal at all.

**Remediation (concrete):** Forbid `xfail` for the oracle. T002 reword: *"Implement the FR-004 oracle as a
**hard assertion of the wrong (current) value** — `assert destination_ref == <git-HEAD branch>` with a
docstring `# FR-004 BUG WITNESS: flips to <target_branch> in WP05`. It MUST be RED-on-HEAD only after the
WP05 swap is in (i.e. on HEAD it documents the current value as a passing baseline that WP05 must CHANGE,
or it is a `@pytest.mark.xfail(strict=True, reason=...)` that WP05 converts to a positive assertion of the
NEW value — never a non-strict xfail, never a deletable skip). WP05's DoD references this exact test by
node-id; WP05 may not delete it, only flip its asserted value."*. WP05 T025 DoD add: *"the FR-004 oracle
(WP01 node-id `<…>`) is converted to assert the post-fix `target_branch` value — the node still exists and
is GREEN; it was not deleted."*

---

## SHOULD-FIX

### SF-1 — WP07 retirement scope is too narrow ("S-2/S-3 tests") vs my own census, risking an incomplete-deletion that fights mid-mission.

WP07 T033 says "Atomically retire the S-2/S-3 tests." My census S-3 names **four** distinct sites that
hard-code `PromptSourceFragment`/`prompt_source`:
`tests/architectural/test_mission_runtime_surface.py:59` (`_PUBLIC_SURFACE` ratchet),
`tests/architectural/test_execution_context_parity.py:1461,1779-1801`,
`tests/mission_runtime/test_context_fragments.py:21,171,180`, plus S-2's spy at
`test_execution_context_parity.py:2099-2156`. **WP07's `owned_files` lists only**
`resolution.py`, `context.py`, `aggregate.py` — **none of the test files**. So WP07 cannot atomically
retire the contract-encoding tests it is told to retire; they will go RED in files it does not own.

**Remediation:** Add to WP07 `owned_files`: `tests/architectural/test_mission_runtime_surface.py`,
`tests/architectural/test_execution_context_parity.py`,
`tests/mission_runtime/test_context_fragments.py`. T033 reword to enumerate the exact 4 sites (the
`_PUBLIC_SURFACE` entry, `test_promptsource_fragment_parity` + `_PROMPT_SOURCE_FRAGMENT`, the
`test_context_fragments` import/construction, the `surface=` spy at 2099-2156) and DoD: *"`grep -rn
'PromptSourceFragment|prompt_source|surface=' src/ tests/` returns no live reference to the deleted
scaffolding; full `pytest tests/architectural/ tests/mission_runtime/` green."*

### SF-2 — WP08 FR-005 ratchet allow-list can be gamed into a blanket escape; "optional" weakens the one form-coupled guard.

WP08 T037 seeds the ratchet allow-list "ONLY with genuinely-deferred sites (the S2 #1716 ladder)" but the
ratchet is marked **optional**, and there is no DoD check that the allow-list is *minimal* (an implementer
can add `status_transition.py` wholesale to the allow-list to dodge a real finding, since S2 lives in that
file). The reviewer-guidance says "its allow-list isn't a blanket escape" but gives no mechanical test.

**Remediation:** (1) Make the ratchet **required**, not optional (it is the only durable guard against the
re-derivation class recurring — DIR-001/DIR-030; an optional anti-regression guard is how the disease comes
back). (2) T037 DoD add: *"the allow-list entries are line/function-scoped (e.g.
`status_transition.py::_read_contract_from_transaction_target`), NOT file-scoped; a self-test plants a
`feature_dir.parent.parent` in an ADOPTED function and asserts the ratchet flags it (the ratchet bites)."*
Model on the existing `tests/architectural/test_no_worktree_name_guess.py` style.

### SF-3 — Every adoption WP's "suite green after deletion" scopes "green" to owned/named files, not the swap's real reachable callers — making the green claim satisfiable without topology-true exercise.

WP02/WP03/WP04/WP05/WP06 each end with "net + <named module> suite green." Because the WP01 net is the only
guaranteed topology-true driver and each WP names only its adjacent per-site module, an implementer can land
a deletion, run `pytest tests/status/test_emit.py tests/specify_cli/write_side/`, see green, and ship —
**without ever running the broader suite that actually exercises the deleted path through a real caller**
(e.g. the `tests/unit/status/` aggregate save path from BLOCKER-1, the `tests/specify_cli/coordination/`
suite from BLOCKER-2, `tests/merge/` for lanes). This is the structural enabler of BLOCKER-1/2.

**Remediation:** Add a uniform DoD line to WP02–WP06: *"Verification-by-deletion is proven by running the
FULL `pytest tests/status/ tests/specify_cli/ tests/unit/status/ tests/lanes/ tests/merge/
tests/architectural/` (the reachable-caller surface for the adopted site), not only the owned module + the
WP01 net. Any RED in that surface is in-scope to fix under C-008, not deferred."* This converts "green in my
file" into "green where the deleted code was actually reached."

### SF-4 — The mission acceptance-matrix is entirely stubbed; FR-004 has no binding mission-level proof.

`acceptance-matrix.json` has all 9 FRs as `"notes": "TODO: replace with a real acceptance criterion"`,
`pass_fail: pending`, `evidence: null`. There is no negative invariant for "status events never land on a
git-HEAD-dependent branch" (the FR-004 bug class). With the per-WP green-claims gameable (SF-3) and the
mission gate empty, nothing binds the FR-004 correctness flip at accept time.

**Remediation:** Before implement, populate at least FR-004, NFR-006, FR-001 with concrete test node-ids
(the WP01 oracle, the WP08 keystone, the WP05 idempotency test) as `proof_type: automated_test` evidence,
and add a `negative_invariants` entry: *"No flattened-topology status write resolves `destination_ref` to
`git rev-parse HEAD`; it resolves the declared target/primary branch (CWD-invariant)."*

---

## NITs

- **NIT-1 — WP06 title is truncated in frontmatter:** `title: Lanes/coord adoption (FR-008,` (trailing
  comma, unclosed paren). Cosmetic, fix the YAML title.
- **NIT-2 — WP04 T020 lets the implementer "leave a one-line note" for the `:304` DeprecationWarning.** Under
  C-008 (fix-don't-litigate, BINDING) "leave a note" is the litigation the directive forbids. Either it is
  due (fix it) or it is not (say nothing); reword to "fix if due; otherwise no action" — drop the note
  escape.
- **NIT-3 — WP01/WP05 cite `research/reduction-census.md §6` as the FR-004 authority, but that census
  classifies the write-target flip as `#1716-deferred, MUST NOT be in the now-cut`.** The plan's D-2 operator
  reversal pulls it IN. The prompts should note the reversal explicitly so an implementer reading the census
  does not conclude FR-004 is out of scope (conceptual-alignment / DIR-032; the cited source contradicts the
  task).

---

## Sequencing soundness (Q5)

WP01 → {WP02..WP07} → WP08 is correctly ordered for provability **in principle**: the net lands first, each
deletion runs against it, WP08 integration-tests last. The dependency edges (`WP08 depends on
WP02,03,04,05,06`) are correct. **But the guarantee is hollow given BLOCKER-2/3 and SF-3:** "the net is
green before each deletion" only proves the deletion safe if the net is (a) non-vacuous (BLOCKER-3) and (b)
the green surface covers the real reachable callers (SF-3), and if the deletion does not break an unowned
file (BLOCKER-2). The DAG is right; the *content* of "green" is gameable. Fix BLOCKER-2/3 + SF-3 and the
sequencing becomes genuinely sound.

---

## Verdict roll-up

| Severity | ID | WP | One-line |
|----------|----|----|----------|
| BLOCKER | B-1 | WP05 (+WP01) | FR-004-fighting `test_save_supports_identity_bearing_legacy_mission` (asserts `==legacy-lane`) is owned by no WP and will RED on the flip; "oracle flips green" is gameable. |
| BLOCKER | B-2 | WP02 (+WP01) | `test_worktree_topology.py` imports the deleted lock-root helpers by name but is owned by no WP; "suite green" is false at merge. |
| BLOCKER | B-3 | WP01 | "drive without explicit `repo_root`" not mechanically enforceable (load(repo_root=) / mocks not covered; no positive forcing/mutation check). |
| BLOCKER | B-4 | WP01/WP05 | T002 permits `xfail` — the silently-removable oracle gaming vector; forbid non-strict xfail, pin by node-id. |
| SHOULD-FIX | SF-1 | WP07 | FR-006 test-retirement targets (4 sites) not in `owned_files`; cannot retire atomically. |
| SHOULD-FIX | SF-2 | WP08 | FR-005 ratchet optional + allow-list file-scopeable = blanket-escape gaming; make required + line-scoped + bite self-test. |
| SHOULD-FIX | SF-3 | WP02-06 | "suite green" scoped to owned files, not reachable callers — structural enabler of B-1/B-2. |
| SHOULD-FIX | SF-4 | mission | acceptance-matrix all-stub; FR-004 has no binding mission-level proof / negative invariant. |
| NIT | N-1 | WP06 | truncated title YAML. |
| NIT | N-2 | WP04 | "leave a note" escape violates C-008. |
| NIT | N-3 | WP01/WP05 | cited census §6 contradicts D-2 reversal; note it. |

NEEDS-REMEDIATION
