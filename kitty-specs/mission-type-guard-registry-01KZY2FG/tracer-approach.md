# Tracer — approach

Mission `mission-type-guard-registry-01KZY2FG` (issue #3386), plan phase, 2026-08-13.
Seeded at planning per charter Standing Order #3 (mission tracer files); this is a real
account of how the plan was produced, not a placeholder.

## What this plan does, in one pass

Closes the guard-evaluation fall-through in `evaluate_guards`
(`src/runtime/next/runtime_bridge_cores.py:351-374`) by replacing its
`if research / if documentation / else software-dev` chain with an explicit
`_GUARD_TABLES` registry; gives `plan`-type missions their own guard table so
their `review` step stops silently borrowing software-dev's work-package-iteration
message; splits the single shared `_cores.evaluate_guards(snapshot)` call (used
identically by both the legacy path and the composed path today) into a strict
lookup the legacy path calls directly and a tolerant, WARNING-logging wrapper the
composed path calls directly; and ships `spec-kitty doctor mission-type --json
[--fail-on <states>]`, modeled directly on the verified `doctor identity` shape,
so the same unregistered/unresolvable-type class is discoverable proactively
instead of only via a log line during a live run.

## How the plan was produced — verification-first, not spec-trust

The orchestrating brief was explicit that the spec's own review trail
(`reviews/spec.confirmed.yaml`) had already caught one stale line-number citation
and required me not to propagate more by trusting spec.md's citations blindly. I
treated this as a hard requirement, not a suggestion, and re-derived every load-bearing
citation directly against the actual checkout before writing a single line of plan.md:

- Opened `runtime_bridge_cores.py`, `runtime_bridge.py`, and
  `runtime_bridge_composition.py` directly and confirmed, by reading the code (not
  grepping for a function name and trusting the first hit), that `evaluate_guards`
  is at lines 351-374, `_check_cli_guards` at 680-698, `_check_composed_action_guard`'s
  real implementation is at `runtime_bridge_composition.py:427-486` (with
  `runtime_bridge.py:878-891` as a thin compat delegate forwarding to it), and that
  `_evaluate_documentation_guards`'s terminal-step precedent is the exact two lines
  the spec cites (455-456). All of spec.md's citations for these functions were
  confirmed accurate — no corrections were needed there (see
  `tracer-design-decisions.md` for the one genuine finding this verification pass
  DID surface, which is not a citation error but a missing implementation detail).
- Confirmed `doctor identity`'s command shape (`doctor.py:396-444`) by reading
  the shell itself, and confirmed the report-builder pattern is split across
  two modules by reading both in full, not just their docstrings:
  `cli/commands/_identity_audit.py` (346 lines — the CLI report-builder:
  `run_identity_audit`, `_build_identity_json`, `_compute_fail_on`) and its
  domain-layer collaborator `specify_cli/status/identity_audit.py` (361
  lines — `classify_mission`, `audit_repo`, `IdentityState`, `summarize`).
  This two-module split is what let the plan specify `doctor mission-type`'s
  design as combining both precedent shapes into one sibling module, instead
  of a vague "model it on identity" gesture.
- Confirmed `_canonical_meta_mission_type` (`specify_cli/mission.py:542-556`) and
  the shared `canonical_mission_type_key` primitive it calls
  (`charter/mission_type_key.py:24-49`) by reading both functions in full, which is
  what surfaced the important distinction the plan had to make explicit: FR-008's
  `doctor mission-type` taxonomy reuses the shared canonicalization *primitive*,
  but deliberately does NOT call `_canonical_meta_mission_type` itself, because that
  function collapses "which key produced this value" — exactly the fact
  `legacy-key-only` needs to keep visible.
- Ran the actual targeted test surface (not just read test file names off the spec)
  to capture a real, first-hand baseline before writing the Baseline & Reflexivity
  section: `tests/runtime/test_bridge_cores.py` + `test_bridge_composition.py` (71
  passed) and `tests/next/` + `tests/specify_cli/next/` +
  `tests/integration/test_custom_mission_runtime_walk.py` (713 passed), both at
  commit `7deadff0a4f3dfd2744b5e1e35680c0d70f4565e`. This directly answers
  SPEC-VERIFY-005's "captured baseline, not unconditional all-green" requirement
  with an actual number rather than a restated hedge.
- Traced the live production call chain end-to-end for the `plan`-mission defect
  (not just cited the readiness probe's trace) — `_dn_composition_dispatch`
  (`runtime_bridge.py:1531`) passes `mission=mission_type` through
  `_dispatch_via_composition` to `_check_composed_action_guard`, which passes it as
  `mission_family` into `gather_artifact_presence`, which becomes
  `snapshot.mission_family` inside `evaluate_guards`. Confirming this chain
  first-hand is what grounds the plan's claim that a `plan`-type mission's
  `review` step really does reach the fall-through today, not just "the spec says
  so."
- Checked the architectural layer rules (`tests/architectural/test_layer_rules.py`)
  before proposing that `_mission_type_audit.py` import from `charter` and
  `doctrine` — confirmed `specify_cli -> charter -> doctrine -> kernel` is the
  declared, enforced direction, and that `specify_cli/mission.py` already imports
  `charter.activation.mission_type_key` today, so the new sibling module's import shape has
  a direct, live precedent rather than being a novel architectural decision.

## Sequencing decisions

The plan sequences work as: ATDD red-first pins for the live defect and the
uncovered fall-through (charter C-011) → the registry/split/plan-table
implementation commit(s), landed together because they are one small, coherent
change (see `tracer-design-decisions.md` for why no separate campsite-clean commit
was needed) → the `doctor mission-type` command and its own ATDD pin → the
golden-CLI-surface-contract update, folded into the `doctor` commit because it is
a mechanical, not independently-motivated, consequence of that command existing.

One PR for the whole mission (spec-kitty's own default, not Team Kitty's per-WP
convention) — the touched-file set is small (6 production files, 4 test files
including the golden-contract test) and the change is one conceptual unit.
