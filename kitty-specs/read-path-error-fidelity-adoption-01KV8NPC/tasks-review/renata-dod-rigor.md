# Adversarial post-tasks review — DoD rigor + test integrity

**Reviewer:** reviewer-renata (profile-loaded: code-review-incremental, reverse-speccing,
test-scaffolding-as-design-smell, BDD scenario-lifecycle)
**Lens:** Definition-of-Done rigor + test integrity — anti-laziness, anti-gaming.
**Scope:** the 9 WP prompts of `read-path-error-fidelity-adoption-01KV8NPC` against `spec.md`,
`contracts/behavioral-contracts.md`, `research/live-repro.md`,
`research/investigation-2/debbie-reverify-missed.md`, and a spot-verification of the named
production code on HEAD.

**Verification performed (not static reading):** I read the actual code at every load-bearing
file:line the WPs cite — `resolution.py:739`/`:801-808` (mutator confirmed; `ExecutionContext`
is `@dataclass`, NOT frozen, `context.py:184`), `runtime_bridge.py:3129-3130` and `:3265-3274`
(both collapse sites confirmed), `_substantive.py:330-355` (two legs, no primary-target leg
confirmed), `workflow.py:1377-1381` (re-resolution + "no workspace" confirmed), `decision.py:86-107`
(walk + escape-check confirmed), `lanes/persistence.py:43,:78` + `workspace/context.py:798`
(`resolve_lanes_dir` = 0 hits confirmed; 3 ad-hoc joins confirmed), `orchestrator_api/commands.py:261`
+ `_read_path_resolver.py:352` (`and bool(mid8)` fail-closed gate confirmed),
`charter/_status_collectors.py:36,:39,:41` (two writes + `# noqa: BLE001` confirmed). The repros
hold and the line cites are accurate.

---

## Overall posture

These prompts are **above the median** for gaming resistance. The mission-wide spine is strong:
every behavioral WP names a topology-true fixture, demands TDD-first with an explicit "FAILS on HEAD"
validation step, and pins a verification-by-deletion proof. The "exact prompt text at fault" is
usually *present* — my findings are about **closing the last gaming gap**, not rebuilding.

That said, there are **3 BLOCKERs** where the DoD as written can be satisfied by a test that never
reproduced the bug, plus one BLOCKER-class **internal contradiction** between WP09 and the production
code it cites. Hardening required on **WP02, WP03, WP09** before implement; **WP08** is the
test-integrity exemplar (no change needed); WP01/WP04/WP05/WP06/WP07 need only SHOULD-FIX tightening.

**Highest-risk gaming vector (read this first):**
> **The "FAILS on HEAD" step is a prose instruction, not an enforced artifact.** Every TDD-first WP
> says "the test FAILS on HEAD" — but nothing in the DoD requires the implementer to **record the
> red** (the captured failure output / the asserted *wrong* value). An implementer who writes the
> test *after* the fix, or writes a test that asserts the post-fix value against a fixture that
> doesn't actually trigger the bug, produces an all-green DoD with **zero proof the bug ever
> reproduced**. WP08 is the only WP that closes this — via its falsification guard. The fix is to
> propagate WP08's pattern (assert the *broken* behavior, or capture the red) into every behavioral
> WP's DoD. See per-WP BLOCKERs below.

---

## WP01 — Single context factory + freeze + build-invariant

**Verdict: SHOULD-FIX (no BLOCKER). The most rigorous of the behavioral WPs.**

Strengths: the invariant test (`CONTEXT_INVARIANT_VIOLATION`) and the immutability test are *both*
required to fail on HEAD; the `:801-808` mutator deletion is a concrete, grep-checkable
verification-by-deletion; the "do NOT assert on `branch_name`" trap is called out twice. I confirmed
`ExecutionContext` is a plain `@dataclass` at `context.py:184` and the post-build mutator is live at
`resolution.py:801-808`, so both red tests are genuinely red.

### NIT → SHOULD-FIX-1: the invariant test is fakeable as a tautology
> T001: "drives `build_execution_context` … with inputs that yield
> `context.target_branch != branch_ref.target_branch` and asserts it raises".

There is no production call site that *naturally* produces the mismatch (the whole point of FR-009 is
that the resolver builds them consistent). So the only way to drive the mismatch is to **hand-craft
divergent inputs to the factory** — which means the test proves "if I pass A≠B, it raises", a
near-tautology of the assertion itself. That is acceptable as a guard, but it does **not** prove the
factory rejects a *realistically reachable* split-brain.

**Remediation:** add to T001 a second case that constructs the **WP-bearing** context (the
`:801-808` path) end-to-end through `resolve_action_context` on a lane-branch fixture where
`branch_name` legitimately differs, and assert it **succeeds** (does not raise
`CONTEXT_INVARIANT_VIOLATION`). This guards the live FR-009 contradiction the spec warns about
(asserting on `branch_name` would break lane branches) — i.e. prove the invariant is *narrow*, not
just *present*. Without it an implementer can satisfy DoD with an over-tight invariant that breaks
every real lane-branch context, and the pure tautology test would still pass.

### NIT → SHOULD-FIX-2: "freeze surfaces hidden mutators" has no failure budget
T006 says "fix any mutator the freeze surfaces." This is open-ended scope that could balloon the WP
or tempt the implementer to re-introduce mutability behind a guard (the prompt forbids this in prose
but the DoD has no detector). **Remediation:** add a DoD line: "a repo-wide grep for assignment to a
built `ExecutionContext` attribute (`\.target_branch =`, `\.wp_id =`, etc.) returns only the factory
internals." This makes "sole construction door" objectively checkable, matching the WP05/WP06
grep-assertion pattern already used elsewhere in this mission.

---

## WP02 — `next` typed-error pass-through (+ M1)

**Verdict: BLOCKER. The DoD can be satisfied without proving fidelity, and there is a live
comment-vs-intent contradiction in the very code being edited.**

### BLOCKER-1: the red is only described, not enforced — and the fixture can pass vacuously
T007 says the test "FAILS on HEAD (emits `MISSION_NOT_FOUND`)". But the DoD assertion is purely
**positive** ("emits the resolver's real code … checked paths … read-path remediation"). An
implementer can:
- write the test after the fix, or
- build a fixture where the resolver returns the *generic* path so `next` happens to emit something
  non-`MISSION_NOT_FOUND` that isn't actually the typed `COORDINATION_BRANCH_DELETED` code.

I confirmed on HEAD that the live resolver emits `COORDINATION_BRANCH_DELETED` (a
`STATUS_READ_PATH_NOT_FOUND` subclass) on the `/tmp/debbie-coord` topology. The DoD must pin **that
exact code**, not "the resolver's real code" (which an implementer can satisfy by surfacing *any*
non-mission-not-found code).

**Remediation:** make T007's assertion concrete and add a negative anchor:
1. Assert `error_code == "COORDINATION_BRANCH_DELETED"` (the witnessed code) on the
   coord-declared-no-worktree fixture, AND assert the payload `checked_paths` is non-empty and
   contains the coord candidate path.
2. Add an explicit assertion that the pre-fix value would be `MISSION_NOT_FOUND` — either by
   capturing the red (run the test against `git stash`-ed source, paste the red into the Activity
   Log) or, better, a parametrized "broken-baseline" expectation comment so the reviewer can see the
   delta. (Mirror WP08's falsification discipline at WP-grade.)
3. The DoD bullet currently reads "emits the resolver's real code (`STATUS_READ_PATH_NOT_FOUND` /
   `COORDINATION_BRANCH_DELETED`)". The `/` makes it satisfiable by the *parent* code; require the
   **most-specific** code the live resolver produces for the fixture.

### BLOCKER-2: live comment-vs-intent contradiction at the edit site (will mislead the implementer)
At `runtime_bridge.py:3129-3130` the collapse is annotated:
```python
    except ActionContextError as exc:
        # Mission directory not found — raise fail-closed (FR-004 / WP03).
        raise MissionNotFoundError(mission_slug) from exc
```
The in-code comment attributes this collapse to **FR-004 / WP03**, but WP02 (FR-001/002) owns the
deletion of this exact collapse. An implementer reading the comment may believe the collapse is
*intentional fail-closed behavior owned by another WP* and leave it, or wire a half-fix. The same
"FR-004 / WP03" comment is on the `:3132-3134` `not feature_dir.is_dir()` branch — which WP02 does
**not** mention at all.

**Remediation:** WP02 must explicitly instruct: (a) replace the `:3129-3130` comment as part of the
deletion so it no longer claims FR-004/WP03 ownership; and (b) **decide and state** what happens to
the sibling `:3132-3134` "resolved path does not exist on disk → `MissionNotFoundError`" branch —
is that *also* a fidelity loss (a real read-path miss masquerading as MISSION_NOT_FOUND), or is it a
legitimately-missing mission? The prompt is silent on it; left as-is it is a second collapse site the
deletion proof will not cover, and C-IC02 says "removing the … collapse at the **three** catch-sites"
— the prompt enumerates `:3128-3130`, `:3265-3274`, `next_cmd.py:355-361`, but the disk-existence
branch is a fourth path that re-raises `MissionNotFoundError`. Reconcile "three catch-sites" against
the actual four `MissionNotFoundError`-raising sites in scope.

### SHOULD-FIX-3: the decision-answer path (T009) has no asserted code value
T009 says "a decision-answer … surfaces the same typed code as the query path" but the DoD bullet is
"preserves the code identically." The note at `:3265-3274` raises `MissionRuntimeError` (a *different*
error class than the query path's `MissionNotFoundError`), so "identically" is doing heavy lifting.
**Remediation:** T009 must assert the decision-answer surface emits the **same `error_code` string**
as T007's query path on the **same fixture** — a direct equality assertion between the two payloads,
not two independent positive checks (which could both pass while differing).

---

## WP03 — `mission.py` planning-entry adoption

**Verdict: BLOCKER. The #7 fixture is the exact NFR-002 trap, and one DoD leg can pass vacuously.**

This WP is well-scoped and the surface-specificity of #7 is called out three times (good). The
BLOCKER is that the prompt *describes* the trap but the **DoD does not include a guard that the
fixture is non-vacuous**.

### BLOCKER-3: the #7 regression can pass against a fixture that doesn't reproduce the bug
The live-repro caveat (and the prompt) state plainly: when the coord worktree does **not** carry the
mission dir, `_find_feature_directory` resolves to the *primary* dir and `is_committed` already
returns `True` on HEAD. So a fixture that builds the coord worktree **without** the mission dir, or
commits the spec on **both** branches, makes T015 **pass on HEAD before the fix** — a green that
proves nothing. T015's only red-guard is the prose "test FAILS first."

**Remediation (make the trap detectable in DoD, not just prose):**
1. T015 must assert the **pre-fix** value: add a sub-assertion (or a captured-red Activity-Log
   requirement) that on HEAD `is_committed(resolved_coord_spec, COORDINATION) == False` for *this*
   fixture — i.e. prove the fixture actually triggers the false-negative before fixing it. If the
   fixture is wrong (mission dir absent on coord, or spec on both branches) this pre-check fails and
   the implementer is forced to build the real topology.
2. Add a DoD assertion that the resolved spec path is **under `.worktrees/…-coord/`** (not the
   primary dir) — proving the coord surface is the one being checked. Without this, T016's "primary
   leg ORed in" can be satisfied while the test silently exercises the primary path.
3. The T016 guard ("existing single-repo `spec_committed:true` case still passes — add a guard test
   if not already covered") is written as optional ("if not already covered"). Make it
   **mandatory**: the OR-leg must not flip a genuinely-uncommitted spec to `True`. Require an
   explicit negative case: spec absent on *all* surfaces → `is_committed == False` after the fix.
   Otherwise the cheapest way to make T015 green is to make `is_committed` return `True`
   unconditionally for the coord surface.

### SHOULD-FIX-4: FR-004 Case B (>1) ambiguity code is under-pinned
T013 Case B asserts "the structured `MISSION_AMBIGUOUS_SELECTOR` / detection error." The live repro
shows HEAD emits `PLAN_CONTEXT_UNRESOLVED` / "1 missions found … disambiguate" for n==1. For n>1 the
DoD says `MISSION_AMBIGUOUS_SELECTOR` **or** "detection error" — the `or` lets an implementer keep
the old `PLAN_CONTEXT_UNRESOLVED` for n>1 and still pass. **Remediation:** pin the exact error_code
required for n>1 (`MISSION_AMBIGUOUS_SELECTOR` per FR-004/C-IC04) and forbid the n>1 path from
emitting the n==1 "disambiguate" string. Add an n==0 case too (no missions) so the auto-select gate
is proven to fire **only** at exactly-one.

### SHOULD-FIX-5: T017 "genuine-unchanged stays benign" has no observable assertion
The three #7-secondary cases are good, but "genuine-unchanged stays a benign no-op" needs a concrete
observable (e.g. `commit_created` is `None` AND no typed diagnostic is emitted AND exit 0) so the
implementer can't collapse all three cases into "always emit a diagnostic." Pin the distinguishing
JSON shape for each of the three classes.

---

## WP04 — `decision` single authority

**Verdict: SHOULD-FIX (no BLOCKER). The traceback-vs-structured distinction is the integrity risk.**

The dual-authority analysis is correct (I confirmed the walk at `decision.py:86-97` and the escape
check at `:101-109`), and Case B (traversal token still rejected) is a real security regression guard.
The TDD red is genuine: `:103` raises uncaught on the coord fixture.

### SHOULD-FIX-6: "no raw traceback" is hard to assert without a concrete handle
T020 Case A asserts "no raw `ActionContextError` traceback" and Case C asserts "structured typed
error." A test driving the CLI via a runner can satisfy "no traceback" simply because the test
harness catches the exception — i.e. the assertion can pass without the *production* code path being
fixed. **Remediation:** assert on the **`--json` envelope contents**: Case C must assert
`response["error_code"] == "COORDINATION_BRANCH_DELETED"` (the witnessed code) and that the process
exit is the structured-error exit, AND assert the stderr/stdout does **not** contain a Python
traceback marker (`Traceback (most recent call last)`). Pin the exact code, not "a structured typed
error."

### SHOULD-FIX-7: Case A success criterion is ambiguous on a no-worktree topology
The repro #8 fixture is **coord-declared-no-worktree** — on that topology the resolver legitimately
*cannot* resolve (the read-path is genuinely missing), so "Case A: coord handle **succeeds**" and
"Case C: read-path miss surfaces structured error" appear to use the same fixture with opposite
expected outcomes. The prompt says Case A "resolves through the single canonical authority" but on
the no-worktree topology that resolution may itself be a typed miss. **Remediation:** clarify Case A's
fixture must be a coord topology where the resolver **does** resolve (coord worktree materialized with
the mission dir) so "succeeds" is well-defined; reserve the no-worktree topology for Case C. As
written, an implementer could conflate the two and ship a fix where *every* coord handle returns a
structured error (Case C green) while Case A never actually succeeds.

---

## WP05 — implement single-resolution + #1993 lanes seam

**Verdict: SHOULD-FIX (no BLOCKER). Verification-by-deletion is concrete; one fakeable test.**

I confirmed `resolve_lanes_dir` has **0 hits** and the 3 ad-hoc joins exist exactly as cited
(`persistence.py:43,:78`, `workspace/context.py:798`). The grep-assertion DoD ("no remaining ad-hoc
join") is the right kind of objective check. The #1832 deletion proof (remove re-resolution at
`:1377-1381`) is concrete.

### SHOULD-FIX-8: T024 can pass via a re-resolution that happens to succeed
T024's risk is named in the prompt ("not a re-resolution that happens to succeed") but the DoD does
not enforce it. The test asserts implement "succeeds and does NOT raise 'no workspace could be
resolved'." On a healthy fixture, the *current* re-resolution at `:1377` also succeeds — so the test
is green on HEAD and proves nothing. **Remediation:** the test must construct a fixture where
**re-resolution would fail but the claim's context is valid** (the verified-read-path case the prompt
mentions but does not pin). Concretely: a topology where `resolve_workspace_for_wp` called fresh
returns `exists=False` (the `:1379` branch) yet the claim already resolved a valid workspace. Then
the red is real (HEAD raises "no workspace"), and the green proves consumption of the claim's context.
If such a fixture can't be built, the deletion-proof alone (remove `:1377-1381`, suite green) is the
only honest evidence — say so explicitly and drop the misleading "test FAILS first."

### SHOULD-FIX-9: T028 "grep/shape check" should be a real test, not a manual grep
T028 says "grep assertion or a code-shape test." A manual grep run by the implementer is not a
regression guard. **Remediation:** require an automated test (an `ast`/source scan, or import-and-
introspect) that fails if a new ad-hoc `feature_dir / "lanes.json"` join is added — this is the only
way the "exactly one derivation" invariant survives future edits. (Matches the mission's stated
preference for testable extractions.)

---

## WP06 — root-resolver submodule unification

**Verdict: SHOULD-FIX (no BLOCKER). The strongest topology-true discipline of the code WPs.**

This is exemplary on the topology trap: T029 demands a **real `git submodule add`** (`.git` FILE),
the risk section requires the reviewer to "assert the child `.git` is a FILE, not a dir, and that
`_read_worktree_gitdir` returns `None`", and T029.5 requires capturing the pre-fix red (resolves the
parent). I confirmed the root cause at `paths.py:284-288`. The equivalence test (T031) over
{primary, coord, submodule} directly satisfies NFR-001.

### SHOULD-FIX-10: the `.kittify` vs `kitty-specs` marker is left ambiguous
T030 says mirror `locate_project_root`'s check "(`.kittify` dir present … honour the spec's
`kitty-specs` mention if `locate_project_root` consults it)". This hedge is a correctness hazard: if
the implementer picks the wrong marker the fix could stop at the wrong boundary (e.g. a submodule
with `kitty-specs/` but no `.kittify/`, or vice-versa). **Remediation:** the prompt should pin the
**exact predicate `locate_project_root` uses** (I'd resolve this at task time, not leave it to the
implementer) so "agree" is structural. The DoD already says "uses the SAME predicate as
`locate_project_root`" — make T030 state that predicate verbatim rather than offering a choice.

### NIT: T031 pre-fix assertion is good — make it a DoD line
T031.3 ("running against pre-fix `paths.py` shows ONLY the submodule case diverging") is excellent
evidence but lives only in the subtask body. Promote it to a DoD checkbox so the captured red for the
equivalence test is required, not optional.

---

## WP07 — charter status side-effect-free + JSON-safe

**Verdict: SHOULD-FIX (no BLOCKER). The no-op proof is real; one mock-escape hatch.**

I confirmed the two writes (`ensure_charter_bundle_fresh` at `:36`, `generate_all()` at `:39`) and
the `# noqa: BLE001` at `:41`. The `git status --porcelain` before/after snapshot (T032) is the right
real-tree assertion, and the risk section explicitly forbids the mock-stub escape ("A mock-based test
that stubs the renderer hides the write").

### SHOULD-FIX-11: the no-op assertion can pass vacuously if the fixture has nothing to write
The write side-effect only manifests when there *are* glossary entities to render / a stale bundle to
regenerate. A minimal fixture (empty glossary, fresh bundle) produces **no diff even on HEAD** — so
T032 is green pre-fix and proves nothing. **Remediation:** the fixture must guarantee the writes
*would* fire on HEAD: include at least one glossary entity that `generate_all()` would render to a new
file, and/or a deliberately stale bundle so `ensure_charter_bundle_fresh` rewrites. Add a pre-fix
captured-red requirement: on HEAD, `git status --porcelain` is **non-empty** after a status run for
this fixture. Without this the "side-effect-free" green is unfalsifiable.

### NIT: `current_hash`/`stored_hash` → "one normalized hash" mapping is under-specified
The collector returns two hash fields (`:94-95`) but FR-010/T034 say "one normalized hash." Clarify
whether both fields are normalized-but-kept (two strings) or collapsed to one — otherwise "one
normalized hash" is ambiguous and the JSON round-trip assertion can pass while the contract intent
(single canonical value) is unmet.

---

## WP08 — #1827 baseline regression (test-only)

**Verdict: PASS — the test-integrity exemplar. No change required.**

This WP is the benchmark the others should match:
- The **falsification guard (T036) is a hard DoD requirement**, not optional: "If the guard does not
  raise `BaselineMergeCommitError`, the harness is not exercising the ordering … reviewer should
  treat a non-raising guard as a blocking defect." This is exactly the anti-vacuous-green discipline
  the other behavioral WPs lack.
- The "no code fix" boundary is **explicit and enforced**: owned_files is a single test file, the
  DoD requires `git diff` to touch only the test tree, `merge.py` is named as untouchable, and the
  "no fiction fix" risk is spelled out.
- The resume leg (advance HEAD past baseline, re-run) is required and justified against the
  circular-failure mode — a pure unit assertion is explicitly called insufficient.
- Topology-true: real git repo, full ULID, real HEAD-advance, no stubbed helpers.

I verified the cited helpers exist in `merge.py` (`_record_baseline_merge_commit`,
`_assert_baseline_merge_commit_on_target`, `_recorded_baseline_from_working_meta`,
`BaselineMergeCommitError`) and that live-repro confirms DOES-NOT-REPRODUCE. The disposition
(verified-already-fixed → test-only lock) is faithful to FR-012/C-003.

**One NIT:** T036 asserts the substring `"baseline_merge_commit is missing from committed"` + `meta.json`
+ `on main`. If a future refactor reworded the error, the guard would silently stop matching and pass
as "broken order didn't raise the *expected* string" — pin the assertion to
`raises(BaselineMergeCommitError)` as the primary gate and treat the substring as a secondary check,
so a reworded-but-still-raised error doesn't turn the guard into a false pass.

---

## WP09 — orchestrator-api typed-error + fail-closed (M2 + M3)

**Verdict: BLOCKER. M3's premise is directly contradicted by a comment in the code being edited —
this must be resolved at task time, or the implementer will be unable to write a red test (or will
write a fiction-green).**

### BLOCKER-4: M3 vs. the in-code comment at `commands.py:258-260` — a load-bearing contradiction
The prompt's M3 premise: the empty-mid8 seed at `commands.py:261` **suppresses** the coord-aware
fail-closed guard (`_read_path_resolver.py:352 and bool(mid8)`), so the orchestrator reads stale
primary status. I confirmed the gate: `fail_closed = (… and bool(mid8))`, so empty `mid8` → `fail_closed`
is `False` → guard suppressed. **The mechanism is real.**

BUT the production code at `commands.py:258-260` carries a comment asserting the **opposite**:
```python
    # handle the empty mid8 is byte-identical here: the resolver's compose is
    # idempotent on an embedded slug and its canonical-handle fallback re-derives
    # the real mid8 when the literal path misses.
    mid8 = resolve_mid8(mission_slug, mission_id=None)
```
This comment claims the empty seed is **safe / byte-identical**. It reasons only about the *literal
path compose* and the *canonical-handle fallback* — it does **not** account for the `bool(mid8)`
fail-closed gate, which never re-derives mid8 (it just evaluates `False`). So either:
- the comment is **wrong** (M3 is a real bug, and the comment is the rationalization that planted it
  — likely, given the live evidence in investigation-2 §3 "M3 is the live-confirmed harm"), or
- the comment is **right** for some path the prompt's M3 analysis missed.

An implementer who reads this comment will be told the bug they're fixing "is byte-identical / safe."
The most likely outcomes are (a) they leave `:261` alone trusting the comment (M3 unfixed, DoD
gameable via a fixture where the fallback happens to re-resolve), or (b) they delete the seed but the
comment's claimed "canonical-handle fallback" re-introduces the stale read on a different path.

**Remediation (BLOCKER — resolve before implement):**
1. The prompt must **explicitly call out and refute** the `:258-260` comment, instructing the
   implementer to delete/replace it as part of T042 (it is the rationalization that masks M3). State
   that the comment reasons only about literal-path compose, NOT the `bool(mid8)` fail-closed gate.
2. T041's red must be pinned to the **gate**, not just "stale read succeeds": assert that on HEAD,
   for the coord fixture, `_read_path_resolver`'s `fail_closed` evaluates `False` (because mid8 is
   `''`) and the read returns the stale primary; after the fix `mid8` is non-empty and `fail_closed`
   fires. Without pinning to the gate the implementer can build a fixture where the "canonical-handle
   fallback" the comment describes happens to re-resolve, masking the gate behavior — a fiction-green.
3. Verify the prompt's claim that resolving real `mission_id` from meta (à la `decision.py:421`)
   produces a non-empty mid8 on the coord-only topology — investigation-2 M5 notes that the same
   primary-only `load_meta` pre-read on a **coord-only** topology returns *empty meta* → `mission_id=None`
   → empty mid8 *anyway*. If the meta lives only on the coord surface, "resolve mission_id from meta"
   may itself return empty on the coord-deleted case, and the fix wouldn't fire the guard. The prompt
   must state **which surface** the `mission_id` is read from and prove it is populated on the M3
   fixture — otherwise T042 is unimplementable as written.

### SHOULD-FIX-12: M2 endpoint coverage — "at least one of the 8" is too weak
T039 drives "at least one of the 8 endpoints." The fix touches a shared helper (`_resolve_mission_dir`)
but each of the 8 endpoints has its own `_fail("MISSION_NOT_FOUND", …)` call site. Fixing the helper
to *return* the typed code does nothing unless each endpoint is also updated to *surface* it — and
testing one endpoint leaves 7 unverified. **Remediation:** require the test to parametrize over **all
8** endpoints (the line numbers are enumerated — `:587,:652,:735,:870,:997,:1066,:1164,:1268`), or
explicitly justify why the shared-helper fix makes per-endpoint tests redundant (it does not, given
the per-endpoint `_fail` calls). As written, an implementer can fix one endpoint, green the test, and
leave 7 endpoints flattening.

### SHOULD-FIX-13: the legacy-grammar guard is prose-only
The `:484` / `:787` "do not touch" boundary is well-explained, but the DoD's only enforcement is
"diff shows only `:261` moved" — a manual reviewer check. **Remediation:** since these are the exact
trap, add a captured-diff requirement to the Activity Log (paste the `git diff` of `commands.py`
showing `:484`/`:787` unchanged), or an automated assertion that those two call sites still pass
`mission_id=None`. Manual diff inspection is the weakest possible guard for the single most likely
regression.

---

## Verdict — which WPs need DoD hardening before implement

| WP | Verdict | Must-fix before implement |
|----|---------|---------------------------|
| **WP02** | **BLOCKER** | Pin the exact witnessed code (`COORDINATION_BRANCH_DELETED`) + require captured red; reconcile the "three catch-sites" vs the fourth `not feature_dir.is_dir()` collapse; fix the misleading `FR-004/WP03` comment at the edit site; equality-assert query-vs-decision-answer codes. |
| **WP03** | **BLOCKER** | T015 must assert the **pre-fix `False`** on the coord-worktree-with-mission-dir fixture (prove non-vacuous) + assert the resolved spec is under `.worktrees/…-coord/`; make the negative `is_committed==False` guard mandatory; pin the n>1 code to `MISSION_AMBIGUOUS_SELECTOR` (drop the `or detection error`). |
| **WP09** | **BLOCKER** | Refute/replace the `commands.py:258-260` "byte-identical" comment that contradicts M3; pin T041's red to the `bool(mid8)` gate; prove `mission_id`-from-meta is populated on the M3 coord fixture (M5 warns it may be empty on coord-only); parametrize M2 over all 8 endpoints. |
| **WP01** | SHOULD-FIX | Add the WP-bearing-success case to T001 (prove the invariant is *narrow*); add grep-DoD for sole construction door. |
| **WP04** | SHOULD-FIX | Assert on `--json` envelope code + no-traceback marker (not "no traceback" via harness catch); disambiguate Case A (resolvable coord) vs Case C (no-worktree miss) fixtures. |
| **WP05** | SHOULD-FIX | T024 fixture must make re-resolution fail while claim-context is valid (else green proves nothing) — or drop "FAILS first" and rely on the deletion proof; make T028 an automated scan, not a manual grep. |
| **WP06** | SHOULD-FIX | Pin the exact `locate_project_root` marker predicate (kill the `.kittify`/`kitty-specs` hedge); promote the T031 pre-fix-divergence red to a DoD line. |
| **WP07** | SHOULD-FIX | Fixture must guarantee writes *would* fire on HEAD (entity to render / stale bundle) so the no-op green is falsifiable; clarify one-vs-two hash fields. |
| **WP08** | **PASS** | None. Test-integrity exemplar — propagate its falsification-guard pattern to WP02/WP03/WP06/WP07/WP09. |

**Highest-risk gaming vector (single sentence):** across every behavioral WP the "FAILS on HEAD"
red is a *prose instruction with no required artifact* — an implementer can write the test after the
fix (or against a vacuous fixture) and produce an all-green DoD that never reproduced the bug; only
WP08 closes this, and its **falsification-guard / captured-red discipline must be lifted into the DoD
of WP02, WP03, WP06, WP07, and WP09** (the topology-trap WPs where a wrong fixture passes silently).

**Second-highest vector:** WP09's M3 is actively contradicted by a comment in the code being edited
(`commands.py:258-260` claims the buggy empty-mid8 seed is "byte-identical / safe"); unless the prompt
refutes that comment and pins the red to the `bool(mid8)` fail-closed gate, the implementer will
either trust the comment and leave the bug, or write a fiction-green against the "canonical-handle
fallback" path the comment describes.
