---
affected_files:
- path: src/specify_cli/missions/_read_path_resolver.py
- path: src/specify_cli/retrospective/writer.py
- path: src/mission_runtime/resolution.py
- path: tests/specify_cli/missions/test_primary_read_delegation.py
- path: tests/specify_cli/cli/commands/test_coord_status_commit_2155.py
- path: kitty-specs/read-side-seam-primary-primitive-closure-01KYKMMT/research/expected-reds.md
cycle_number: 1
mission_slug: read-side-seam-primary-primitive-closure-01KYKMMT
reproduction_command: 'grep -n "resolve_retrospective_home" src/mission_runtime/resolution.py
  && grep -n "primary_feature_dir_for_mission" src/specify_cli/retrospective/writer.py
  # then trace read_dir(RETROSPECTIVE) with sys.setprofile on primary_feature_dir_for_mission.__code__
  over the six quickstart.md 4 fixtures; expect 1 wrapper frame per call (see B1)'
reviewed_at: '2026-07-28T16:05:00Z'
reviewer_agent: reviewer-renata
verdict: changes_requested
wp_id: WP03
---

# WP03 Review — CHANGES REQUESTED (one structural defect + two recording gaps)

Commit `77226250f`. Recovered work from an implementer that died mid-flight; I generated all
evidence from scratch rather than checking a report, because no report exists.

Most of this WP is correct and I verified it independently — the extraction is genuinely
behaviour-neutral, the backfill pin is genuinely red-first, the Class-C harness is genuinely
non-vacuous. All of that is recorded under **Verified** so cycle 2 does not re-litigate it.

**One thing blocks**, and it is precisely the item T016 step 3 told the implementer to verify
and the Reviewer Guidance told me to re-check: *"Is the `read_dir` → leaf trace written down,
and does it actually hold when you follow it in the code?"* It is written down. **It does not
hold.**

---

## BLOCKING — B1. There IS a path from `read_dir` to the public wrapper. NFR-009 is violated and the commit body records the opposite

**The path** (captured live, not read off the source):

```
mission_runtime/resolution.py:1462      read_dir(kind=RETROSPECTIVE)
  → specify_cli/retrospective/writer.py:85   resolve_retrospective_home()
    → _read_path_resolver.py:1307             primary_feature_dir_for_mission()   ← THE PUBLIC WRAPPER
      → placement_seam(repo_root, slug).read_dir(PRIMARY_METADATA)                ← BACK INTO read_dir
```

`read_dir` has a **kind-specific chokepoint** at `resolution.py:1454-1464`: `RETROSPECTIVE`
does not go through `resolve_artifact_surface` at all — it calls out to
`specify_cli.retrospective.writer.resolve_retrospective_home`, which calls the public wrapper
at `writer.py:85`. T016 only traced the `resolve_artifact_surface → resolve_planning_read_dir`
leg. That leg is clean. This one is not.

**How I proved it.** `sys.setprofile` recording every frame entry whose code object is
`primary_feature_dir_for_mission.__code__` — this catches the wrapper regardless of which
module binding calls it, so module-top `from … import` bindings cannot hide. Run over **six
real git-repo fixtures** (flat, coord+materialized, coord husk, coord branch deleted, coord
worktree empty, backfilled) × **every** `MissionArtifactKind` member:

| kind | fixtures | wrapper frames entered |
|---|---|---|
| `RETROSPECTIVE` | all 6 | **1 per call** |
| every other kind | all 6 | 0 |

**Why no `RecursionError` fired.** The wrapper delegates with a hard-coded `PRIMARY_METADATA`,
and `PRIMARY_METADATA`'s leg does not re-enter the wrapper. Termination is a property of that
one constant, not of the call graph. The WP's designated stop-everything signal is therefore
silent on a cycle that exists. That is the shape the WP explicitly forbids — *"Do not work
around it by adding a guard flag or a recursion depth check — find the uncovered path"* — and
`PRIMARY_METADATA` is functioning here as an accidental guard constant.

**Against the requirements**, verbatim:

- **T016 step 3**: *"Verify **no path** from `read_dir` reaches the public wrapper."* — false as
  implemented.
- **NFR-009** (spec.md:336): *"No change introduces a cycle in the `read_dir` call graph."* — a
  `read_dir` → `read_dir` cycle now exists and did not before this commit (pre-WP03 the wrapper
  was a pure leaf).
- **Definition of Done**: *"no path from `read_dir` reaches the public wrapper; no new cycle."*
- The commit body states the trace as verified evidence that Half B is safe. It is not.

**Fix**: re-point `specify_cli/retrospective/writer.py:85` at `_compose_primary_feature_dir`,
exactly as T016 did for the four `resolution.py` callers and the seven in-module ones. It is
the same one-line call-name substitution and the same rationale comment. Then re-run the trace
harness and confirm zero wrapper frames for every kind on all six fixtures. This adds a file
outside `owned_files`; note it in the move-task reason — the coupling is structural, same class
as the WP01 allow-list edits already adjudicated as forced.

---

## BLOCKING — B2. The same site is a latent *infinite* recursion for a downstream WP, and nothing records it

`retrospective/writer.py` is listed in `tasks.md:368` as an **in-scope call site to be routed**
by a later WP, and it is **not** one of FR-005's four named foundation sites
(`core/paths.py` ×2, `core/git_ops.py:444`, `coordination/surface_resolver.py:739`).

But it sits *beneath* `read_dir`'s `RETROSPECTIVE` arm. So the obvious migration —
`placement_seam(...).read_dir(RETROSPECTIVE)` — is unbounded recursion, not a refactor.
`tasks.md:370` already flags a soft risk here (*"`retrospective/writer.py` has a dedicated home
resolver"*); it does not name the recursion.

WP03 is the WP whose stated purpose is *"break the recursion path before it can exist"* (T016).
Leaving this undocumented hands a live cliff to whichever WP routes that site.

**Fix**: record `retrospective/writer.py:85` as a **fifth foundation site** in the FR-005 /
SC-014 shape — by name, with its recursion rationale — in the `## WP03` section of
`research/expected-reds.md`. If instead the planning intent is that it *should* be routed, that
is a plan-level finding to escalate, not something to leave silent.

---

## BLOCKING — B3. An unattributed behavioural delta landed on a WRITE leg

`resolve_retrospective_home` is documented in its own body as *"FR-011 **write leg**
(#2136/#2164)"* and is what `canonical_record_path` uses to decide where `retrospective.yaml`
is **written**.

Because it calls the wrapper, it now inherits the seam's backfill recovery. On my backfilled
fixture it returns the recovered bare-slug dir where the pre-WP03 body returned the composed,
non-existent one. It also now double-folds the handle: `writer.py:83` canonicalizes, then the
wrapper re-enters the seam and canonicalizes again (`leaf=7 / planning=2` frames on the
backfilled fixture vs `leaf=6 / planning=2` for every other kind).

The recovered answer is plausibly the *better* one. That is not the point. **NFR-001 scopes the
accepted delta to routed reads**, and T020 requires *every* divergence attributed to exactly one
of anchoring / backfill recovery / husk / raising in a named artifact. This one is on a write
path, is unpinned, and is unrecorded.

**Fix**: if B1 is fixed by re-pointing `writer.py:85` at the leaf, this delta disappears and the
note becomes "no divergence". If it is fixed some other way, pin the retrospective write leg
explicitly and attribute the delta.

---

## BLOCKING — B4. The `## WP03` section of `research/expected-reds.md` was never authored

Definition of Done, verbatim: *"Every divergence attributed in a **named artifact** — append a
`## WP03` section to `kitty-specs/…/research/expected-reds.md` … **'In writing' with no location
is not reviewable.'"*

The file has exactly two sections — `## WP02` and `## WP01` — on the lane, on
`kitty/mission-…-01KYKMMT`, and on `fix/read-side-seam-primary-primitive-closure`. Zero
occurrences of `WP03`.

The attribution content *does* exist, but scattered across the wrapper docstring and the test
module docstring, which is what the DoD sentence above exists to prevent. (The
`kitty-specs`-on-a-lane guard is separately adjudicated — the orchestrator lands the file on the
planning branch — but the content still has to be written.)

The section must carry: the seven equal cells, the one backfill-recovery divergence, the
"raising" note about `MissionSelectorAmbiguous` now being reachable through this primitive, the
T020 step-3 latent shape at `status/aggregate.py:543`, and (per B2) the fifth foundation site.

---

## NON-BLOCKING — record and fix opportunistically

**N1. `test_backfill_recovery_pin_is_red_under_the_pre_delegation_wrapper_body` does not prove
what it claims.** It patches
`_read_path_resolver.primary_feature_dir_for_mission` and then calls *through that same patched
attribute*, so the `patch` is a no-op indirection: the assertions reduce to
`_compose_primary_feature_dir(...) == composed_dir`. It never re-executes the real pin under a
reverted body.

The property nonetheless **holds** — I verified it by rebinding every live reference to the
wrapper (module attribute plus one other importing module) to the pre-T019 body via a pytest
plugin and re-running the file: `test_backfill_recovery_is_the_one_accepted_divergence` fails on
`assert seam == wrapper == bare_dir` (10 passed / 1 failed). So the pin is genuinely red-first;
only the in-repo *proof* of it is circular. Consider replacing it with a
`monkeypatch`-of-the-test-module-binding form that re-runs the real assertion.

**N2. The Class-C `stubs` dict cannot distinguish the wrapper from the leaf.** One `MagicMock`
is bound to *both* `primary_feature_dir_for_mission` and `_compose_primary_feature_dir`, so
`stubs["primary_feature_dir_for_mission"].call_count == 3` is true whichever name the PRIMARY
leg calls. The harness would therefore stay green if the leg regressed back to the wrapper —
which is exactly the recursion cliff this WP exists to prevent. Bind two distinct mocks and
assert `wrapper.call_count == 0` / `leaf.call_count == 3`. (The assertion is *non-vacuous* as
shipped — see V4 — this is a specificity loss, not a correctness one.)

**N3. Stale docstring.** `_read_path_resolver.py:1442` still says the PRIMARY-partition kind
resolves *"via the topology-blind `primary_feature_dir_for_mission` primitive"*. It now calls
`_compose_primary_feature_dir`. The inline comment 40 lines below is correct; the docstring
above it contradicts it.

---

## Verified — settled, do not re-litigate in cycle 2

**V1. Half A is behaviour-neutral, and the lost commit split is NOT material.** I established
equivalent confidence three ways:

- *Structural*: the leaf's body is the pre-WP03 wrapper body moved verbatim (comment, local
  import, `assert_safe_path_segment`, the join, the `return` — five lines, unchanged). Every
  other Half-A edit is a pure callee-name substitution with an identical argument list, at 7
  in-module sites and 4 in `resolution.py`.
- *Census*: re-derived with the gate's own alias-resistant `scan_canonicalizer_call_sites`
  against **both** trees. Pre-WP03 (`77226250f^`, scanner target
  `primary_feature_dir_for_mission`): **46 total / 43 routed / 3 unrouted**. Post-WP03 (targets
  `{primary_feature_dir_for_mission, _compose_primary_feature_dir}`): **46 / 43 / 3**, the same
  three unrouted sites under the same enclosing qualnames
  (`_canonicalize_bare_modern_handle`, `read_primary_meta`, `MissionStatus._find_meta_path`).
  Matches the recorded expectation exactly. Zero call-site changes outside the two resolver
  modules — `git show --stat` lists only those two under `src/`.
- *Differential*: reverting **only** the wrapper body at runtime leaves 10/11 delegation tests
  green and reds exactly one assertion — the Half-B backfill delta. That is the same
  information the separate Half-A commit would have carried.

The split was a real process deviation and the commit body is right to record it as costly. It
is not worth a rejection when the safety property is recoverable, and it is.

**V2. Census / SC-003**: **46 total / 43 routed**, before and after. See V1.

**V3. The leaf is importable but unexported.** `_compose_primary_feature_dir` is absent from
`__all__` (`_read_path_resolver.py:1690-1704`) and imports cleanly by qualified name — the new
test module already does `from specify_cli.missions._read_path_resolver import
_compose_primary_feature_dir`. WP07 T034 can re-point the four FR-005 foundation sites at it.

**V4. Class-C per-stub reached/not-reached verdicts** — proved by instrumenting all five names
with **distinct** mocks (the shipped fixture shares one) and replaying the exact call sequences:

| stub | coord (3 calls) | flat (2 calls) | verdict |
|---|---|---|---|
| `_compose_primary_feature_dir` | 3 | 2 | **REACHED** |
| `_canonicalize_primary_read_handle` | 3 | 2 | **REACHED** |
| `primary_feature_dir_for_mission` | 0 | 0 | **NOT REACHED** (post-T016 the leg calls the leaf) |
| `candidate_feature_dir_for_mission` | 0 | 0 | **NOT REACHED** — pre-existing, `TASKS_INDEX` is PRIMARY-partition |
| `resolve_feature_dir_for_mission` | 0 | 0 | **NOT REACHED** — same, pre-existing |

The harness is **not vacuous**: the shipped counts (3 and 2) are exactly the leaf's real call
counts, so the assertion bites; and the convergence assertion still exercises the real
kind→partition dispatch, so a regression routing `TASKS_INDEX` through the kind-blind leg would
red it. The two zero-count stubs were already unreached pre-WP03 (the diff changes one line
inside `resolve_planning_read_dir`, on the PRIMARY leg only) — the fixture's claim that this is
"pre-existing, unrelated to WP03" is accurate.

**V5. T017 — zero collection errors.** `tests/architectural/test_single_mission_surface_resolver.py`
+ the three other touched test modules: **77 passed**, no collection errors. The
`ContentDescriptor` re-author onto `_compose_primary_feature_dir` lands in the same commit as
T015/T016, as required.

**V6. NFR-002 — no new raises.** Across 6 fixtures × every `MissionArtifactKind`, a
PRIMARY-partition read never raised — including husk, empty coord worktree and deleted coord
branch.

**V7. Gates and lint.** `test_resolution_authority_gates.py` + `test_no_read_side_bypass.py`:
72 passed. `ruff check` on all seven changed files: exit 0.

**V8. Out-of-map edits to WP01's two files are NOT held against this WP.** The allow-list pins
the literal token text of sanctioned call sites, and T016 necessarily changes those tokens, so
T016 cannot be done without them. The per-entry rationale is complete: it names the mission, the
WP, the subtask, the old and new callee, and preserves the semantic sanction (same raw-probe
intent). The `line:` corrections (453→464, 819→845) are true fixes — the base tree's values were
already stale. Extending `CANONICALIZER_PRIMITIVE_NAMES` to a frozenset of both names is the
right move and is what keeps the census at 46/43. This is a planning gap in `owned_files`.

---

## Anti-pattern checklist

| # | Item | Verdict |
|---|---|---|
| 1 | Dead code | PASS — the leaf has 11 production callers |
| 2 | Synthetic-fixture test | PASS — real git repos, no resolver patched in the equivalence cells |
| 3 | Silent empty return | PASS — no new swallowing arm |
| 4 | FR coverage | PASS for FR-002/FR-003/FR-021; **FAIL for NFR-009** (B1) |
| 5 | Frozen surface | PASS |
| 6 | Locked decision | **FAIL** — NFR-009's "no cycle in the `read_dir` call graph" (B1) |
| 7 | Shared-file ownership | PASS — WP01's files carry an explicit per-entry rationale |
| 8 | Production fragility | **FAIL** — termination of the `read_dir`↔wrapper cycle depends on the hard-coded `PRIMARY_METADATA` constant, not on structure (B1) |

---

## What cycle 2 needs

1. Re-point `retrospective/writer.py:85` at `_compose_primary_feature_dir`; re-run the trace and
   report **zero** wrapper frames for every kind across the six fixtures (B1).
2. Record `retrospective/writer.py:85` as a fifth FR-005-shaped foundation site with its
   recursion rationale, or escalate the routing question as a plan-level finding (B2).
3. Confirm the retrospective write leg carries no unattributed delta after the fix (B3).
4. Author the `## WP03` section of `research/expected-reds.md` (B4).
5. Optionally N1–N3.

Nothing else. V1–V8 are settled.
