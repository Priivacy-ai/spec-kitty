# Tracer: Design Decisions

Two decision forks, both resolved before spec authoring began and persisted verbatim (with evidence) into `spec.md`'s `## Clarifications` section. Recorded here in short form, cross-referenced to that section.

## Decision 1 — thread `PackContext`, or migrate to consumption-boundary sourcing?

**Resolved: thread it.** `template_set` already underwent a full, completed retirement off the `MissionType` model (mission `mission-step-creatability-01KXQA6R`) and now sources from a consumption-boundary resolver (`_resolve_template_set_slot`). `action_sequence` has had no equivalent migration — it is still a first-class validated model field read at eight call sites across the codebase, and its own docstring calls the raw-YAML fallback "C-007-retained, transitional" (i.e. still authoritative, not deprecated). No ADR authorizes an `action_sequence` migration. Threading `pack_context` through the existing seam mirrors the pattern `resolve_layered_mission_types` already uses successfully for the roster (#3397) and mirrors `_resolve_template_set_slot`'s own already-working, already-production-consumed pattern (confirmed stale-claim correction, SK-82). See `spec.md` § Clarifications, Decision 1, for the full evidence trail.

## Decision 2 — does the activation-gate fix belong in this mission?

**Resolved: no.** Issue #3701's Non-goals section names the activation-gate gap explicitly and points to #3702 (confirmed open, unassigned). SPEC-KITTY-LEDGER.md's SK-81 (verified first-hand) documents the operational consequence — `charter activate mission-type <T>` succeeds and writes the activation even when `<T>` resolves an empty sequence, so the failure only surfaces on the next invocation, after the project is already activated into a broken state — and is cited in `spec.md` as motivation for why this mission's projection defect matters, not as in-scope work. See `spec.md` § Clarifications, Decision 2.

## Plan-phase decision — one Implementation Concern, not several

Considered splitting the plan's Implementation Concern Map into per-function ICs (one per touched function in the four-function chain) to mirror C-007's own function-by-function enumeration, but rejected that shape: the four functions are not independent architectural areas, they are one call chain that must be threaded together as a single unit — a partial threading (e.g. only `_inject_projected_fields` and `_load_layered_mission_type_file` fixed, `resolve_layered_mission_types`'s call sites left unfixed) would still leave the defect live end-to-end. Used exactly one IC (IC-01) and said so explicitly in plan.md, per this mission's own instruction that a single-IC plan is acceptable and should be stated as a deliberate choice rather than an omission.

## Plan-phase decision — campsite-clean scope

Identified one real candidate for the opening campsite-clean (the near-duplicated per-file YAML-parse/validate block between `MissionTypeRepository._load()` and `_load_layered_mission_type_file`) but declined to fold it: extracting a shared helper would necessarily touch `_load()`'s body, which spec.md's own FR-005/C-001 require to stay untouched (threading a project-dependent value into `_load()`'s `cls`-keyed cache would poison it for later-resolved projects in the same process — the exact hazard FR-005 exists to prevent — and even a *non*-pack_context-related touch to `_load()` would still make it a fifth touched function under C-007's four-function bound). Recorded this as an explicit "not folded, flagged for a future mission" finding in plan.md's Campsite-clean section rather than silently skipping it or silently folding it anyway.

## Tasks-phase decision — one WP, not several

Per plan.md's own "PR shape" section (explicit instruction: "/spec-kitty.tasks should reflect
that as (most likely) a single WP, or at most a small number of WPs that still land in one PR"),
authored `wps.yaml` with exactly one WP (WP01) covering all of FR-001..FR-008, NFR-001..NFR-004,
and C-001..C-008. Considered and rejected splitting into e.g. a "production code" WP and a "test"
WP: red-first/ATDD discipline (C-011, spec.md SC-004) requires the red test to be authored and
witnessed red *before* the production-code fix lands, and both must be verified together (the
git-stash/rerun/stash-pop cycle) by the same actor in the same sitting — splitting across two WPs
would either force an artificial dependency (test-WP blocks code-WP, defeating the point of
parallelizable WPs) or break the stash/rerun witnessing requirement across two different
implementers who cannot literally `git stash` each other's uncommitted work. IC-01 is one seam,
one coherent change; the four touched functions and their three call-site edits are inseparable
(a partial threading leaves the defect live end-to-end, per plan.md's own IC-01 framing). One WP
is the honest decomposition — confirmed, not just carried forward by default.

## WP01 implementation phase (2026-08-24) — T004 findings (NFR-002/NFR-004 golden-parity extension)

**T004 step 5 vacuity self-check, performed empirically (not just reasoned about):** temporarily
reverted `mission_type_repository.py:559`'s `scan_mission_types_dir(base_dir,
pack_context=pack_context)` back to `scan_mission_types_dir(base_dir)` (T003's built-in-equivalent
layer edit only -- org/project layer edits left intact) and reran
`tests/runtime/test_runtime_seam.py::TestGoldenParityUnaffectedByPackContextThreading` (all 5
tests present at that point). Result: **all 5 still passed unchanged.** This is the honest, direct
answer to WP01's own question ("confirm the extended/new `action_sequence` parity assertion...
would actually fail in that state") — it does NOT fail. Root cause, verified rather than assumed:
`test_builtin_type_unaffected_by_real_pack_context_with_org_root`'s own fixture's org root declares
`mission_types/` but never writes a `mission-steps/<builtin-type>/...` override tree, so
`MissionStepRepository.resolve_all_for_mission_type("software-dev", pack_context=<real>)` and
`pack_context=None` resolve the byte-identical step set regardless of whether the base_dir
threading exists — there is nothing in this specific fixture the threading could possibly perturb.
This is a correct, expected property of an "unrelated org pack" fixture (matching the class's own
stated purpose: prove zero perturbation), not a defect to "fix" by artificially injecting
override content (T004 step 2 explicitly forbids conflating "unrelated pack" parity with "any pack
whatsoever" parity). Restored the line immediately after observing this (`git diff` confirmed zero
pending change on the file before continuing); this was never committed.

Because the byte-parity assertion is therefore provably unable to prove the base_dir call site is
even reached, T004 step 4's NFR-004 test (`test_builtin_layer_scan_receives_the_real_pack_context_once_per_type`)
is the test that actually closes this specific vacuity gap: it asserts by identity that the call
resolving `"software-dev"`'s step set received *this exact* real, non-`None` `pack_context`
instance -- something only reachable once T003's threading exists at all (pre-WP01,
`_inject_projected_fields` hardcoded `pack_context=None` unconditionally, so no call could ever
observe a real instance there). Verified this test's own red-first shape too: with T003's fix
present but the T004 test's spy watching the exact call, the test is a positive existence proof,
not a byte-difference proof — the correct instrument for a "this code path is live" claim when
the byte-difference instrument is, by design of the fixture, unable to move.

**Deviation from WP01's literal spy-shape instruction, found via actual test execution (not
assumed):** WP01 T004 step 4 specifies `instance = MissionStepRepository.default()` then
`unittest.mock.patch.object(instance, "resolve_all_for_mission_type",
wraps=instance.resolve_all_for_mission_type)`. Ran exactly this first. Result: `spy.call_count ==
0` even after resolving `"software-dev"` through the full seam — not a `TypeError`, a silent
zero. Traced why: `MissionStepRepository.default()` (`mission_step_repository.py:226-227`) is a
plain `@classmethod` with **no** `functools.cache` — unlike `MissionTypeRepository.default()`,
which is cached. It returns a **fresh instance** on every call. The seam's own internal
`_inject_projected_fields` call to `MissionStepRepository.default()` therefore constructs a
*different* object than the one the test pre-captured and patched, so the pre-captured instance's
patched method is never invoked. Switched to the plain-function class-attribute-spy shape already
proven correct elsewhere in this same file
(`TestMemoizedDefaultNoHotPathIO.test_default_does_not_rewalk_mission_steps_on_repeat_calls`,
pre-existing, not authored by this WP) -- a plain function (not a `Mock`) set as a class attribute
correctly binds `self` via Python's normal descriptor protocol regardless of which instance
invokes it, sidestepping the fresh-instance-per-call problem entirely. This is a different pattern
from what WP01 specified, not a contradiction of its underlying warning (WP01's own warning
about `Mock` not being a descriptor is exactly why a plain-function class-attribute spy is safe
where a `Mock`-based one would not be) — recorded here in full per this mission's own
"verify rather than trust" standard rather than silently swapping the pattern.
