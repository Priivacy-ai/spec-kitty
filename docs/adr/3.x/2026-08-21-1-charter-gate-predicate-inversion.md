---
title: 'ADR: Charter/runtime gates test the declared entity, not a coarse hardcoded set'
description: 'Five charter/runtime surfaces replace coarse-set membership with a predicate on the actually-declared entity; two deliberate behaviour reversals (non-bootstrap actions deliver; typo mission types hard-fail) ship under named red-by-design test reversals.'
status: Accepted
date: '2026-08-21'
---

## Context and Problem Statement

Five charter/runtime surfaces decide **delivery**, **tolerance**, or **gating** by testing membership in a **coarse hardcoded set** instead of a predicate on the **entity actually declared**. Each silently starves shipped configuration or fails open (verified against `main`, 2026-08-21):

1. **Action gate (#3596).** `BOOTSTRAP_ACTIONS` (a 4-token frozenset) short-circuits any other action to `mode=compact` before a doctrine bundle is built (`src/charter/context.py:255,484`). Shipped per-type action manifests (`software-dev/actions/tasks/index.yaml`, `documentation/actions/retrospect/index.yaml`) deliver **nothing**.
2. **Governance-slot probe (#3598).** `_resolve_governance_slot` tolerates an unregistered mission type whenever a **project-wide** `_project_has_doctrine_overrides` is true — so a typo'd type (`softwaer-dev`) resolves **silently** with fabricated provenance, no warning.
3. **`_KNOWN_ACTIONS` fold.** A third copy of the same 4-token set (`interview.py:34`) warn-drops declared `action:` entries outside the four.
4. **Artifact seam (#3599/#3597).** Artifact filenames are hardcoded literals at the gates while per-type `expected-artifacts.yaml` manifests gate nothing; a dead `mission_v1` guard registry means no per-type artifact gate executes; `worktree.py` creates a stray empty `spec.md` that satisfies existence gates.
5. **CLI guard family (#3407).** `_check_cli_guards` hardcodes `mission_family="software-dev"` (`runtime_bridge.py:797`), routing every mission type's CLI-guard evaluation around the per-type `_GUARD_TABLES` (including the already-existing `plan` table).

The unifying defect: a coarse set stands in for the declared entity (a DRG action node, a per-type governance profile, a per-type artifact-name manifest, the resolved mission family).

## Decision

**At each surface, replace the coarse-set membership test with a predicate on the actually-declared entity**, and unify the 4-token literal to one fast-path constant:

- #3596 — an action delivers `bootstrap` **iff** `f"action:{type}/{action}" in bundle.merged.node_urns()` (node-URN membership); the bundle is resolved **once** before the mode decision (single graph load, NFR-001).
- #3598 — tolerate an unregistered type **iff** a per-type `governance-profile.yaml` with a matching `id` exists at project, org, **or** built-in layer (via `MissionTypeProfileRepository`); else `UnknownMissionTypeError`.
- #3599/#3597 — resolve artifact filenames from the single per-type authority `expected-artifacts.yaml` `path_pattern`; make the presence gate per-type/keyed on mission family.
- #3407 — resolve the mission's actual family and route to `_GUARD_TABLES[family]` (do not rebuild the existing `plan` table).

### Two deliberate behaviour reversals (this is NOT a byte-identical refactor)

This ADR is the sign-off (C-002) for two intentional behaviour changes, safe because **M0 (`mission_type` backfill + fail-closed `doctor mission-type` census) has landed** and real projects are census-gated:

- **(A) Declared non-bootstrap actions begin delivering.** `tasks` (software-dev) and `retrospect` (documentation/research) now return their doctrine grain instead of short-circuiting to `compact`.
- **(B) Typo'd / unregistered mission types begin hard-failing.** A type with no matching per-type profile at any layer raises `UnknownMissionTypeError` instead of resolving silently with fabricated provenance.

### Red-by-design test reversals (each MUST be reversed, never "fixed back")

An implementer who restores the old assertion re-breaks the fix. The following tests flip RED by design and must be **reversed** with a reference to this ADR:

1. `tests/charter/test_every_load_delivery.py:197::test_json_non_bootstrap_action_is_explicitly_ruled_out` — reverse to assert `tasks` now delivers `bootstrap` + non-empty grain (reversal A).
2. `tests/charter/test_context_schema_version_ledger.py:104::test_non_bootstrap_action_carries_stamped_version` — same reversal (A); the `action="tasks"` call now resolves `bootstrap`.
3. `tests/charter/test_mission_type_profiles.py:260::test_project_with_overrides_does_not_hard_fail_for_unknown_type` — rewrite around the layered per-type predicate, seeding a real per-type `governance-profile.yaml` (reversal B); do not restore the project-wide tolerance.
4. `tests/git_ops/test_worktree.py:263::test_creates_empty_spec_when_no_template` — reverse: the stray empty `spec.md` is no longer created.

Plus any sibling `non-bootstrap → compact` / `directives == []` / stray-`spec.md`-presence assertions the red-first `tests/charter/` + `tests/git_ops/` run surfaces. The self-limiting invariant stays: an **undeclared** action node (any type) still resolves `compact` (`test_context.py:228` stays green).

Reversal (4) — deleting the stray empty `spec.md` — is a **bugfix, distinct from the two policy reversals (A) and (B)**: the empty file was unread and merely satisfied existence gates vacuously. Only the `else: spec_file.touch()` branch is removed; the template-copy path in the same block stays (its `test_copies_spec_template_when_exists` stays green). It is called out here so an implementer does not conclude only two behaviour deltas need guarding.

### Resolved design decisions (pushed here by the POST-SPEC squad)

- **Artifact-filename authority = `expected-artifacts.yaml` `path_pattern`** (single per-type source, 10/10 presence tags). **Not** `MissionStepTemplateRef.artifact_file` — a second authority for the same value would reintroduce the whack-a-field pattern this ADR removes. `MissionStepTemplateRef`/`resolve_configured_template` stay template-only.
- **FR-001 predicate is node-URN membership, not empty-grain.** `resolve_context` already degrades an undeclared node to empty grain; and action nodes are activation-filter-exempt while their `scope`-edge targets are not. A declared-but-activation-starved node therefore legitimately yields `bootstrap` + empty arrays — this is correct, not a bug; no downstream consumer may branch on `mode` expecting a non-empty payload.
- **Delivery carrier is direct `action:<type>/<step>` URN construction** + the node's own `scope` edges; the `mission_type → action requires` edge is an `action_sequence` artifact and is not load-bearing for delivery (the three `*/retrospect` nodes are sequence-orphans yet deliver).
- **Fold keeps two roles distinct.** The single 4-token constant is named for its **fast-path** role; the interview consults it **plus** a declared-node source, so the fast-path set never becomes the closed acceptance allowlist.
- **Third artifact kind: pin-and-defer.** No built-in third kind is introduced; the `_substantive.py` / `_ARTIFACT_TYPE_TO_KIND` boundary is pinned with a specific-raise test. `mission_v1` guard revival is rejected (dead in production; the live runtime has its own `artifact_exists`).
- **Custom-family gate mechanism = data-driven presence, not code registration.** A custom mission family gates on its own artifacts by shipping an `expected-artifacts.yaml` whose `path_pattern` filenames become its presence set (`gather_artifact_presence` consults the per-type set): present → gate passes, absent → gate blocks (AC-10). No entry is added to the `_GUARD_TABLES` code map for custom families. The `evaluate_guards_strict` `UnregisteredMissionFamilyError` strict-raise is **retained** for guard-table *dispatch* of a genuinely unregistered family — a distinct concern (WP-iteration guards cannot be evaluated for an unknown family), and the correct fail-closed default.
- **Layered tolerance (AC-5) does NOT override mission-type activation gating (operator ruling 2026-08-21).** The `#3598` per-type tolerance resolves the *unknown-type / typo* question — a genuinely-defined custom type (a matching per-type `governance-profile.yaml` at the **project or org** layer) tolerates; a typo with no matching profile hard-fails (AC-4). It is **orthogonal** to the shipped mission-type activation-subset gate: a canonical built-in type that a project has deliberately **not activated** still hard-fails with `UnknownMissionTypeError` (its `registered_ids` = the activated subset), exactly as before. The layered probe's "built-in layer" clause therefore does **not** tolerate a non-activated canonical type merely because a built-in profile exists — otherwise activation restriction would be silently defeated. `tests/charter/test_mission_type_activation_gating.py::test_resolve_context_raises_for_type_outside_activated_subset` stays GREEN; it is NOT a red-by-design reversal.
- **No memoization of `load_validated_graph`.** The single-graph-load budget (NFR-001) is satisfied by the per-call `_ActionDoctrineBundle.merged` carrier — `load_validated_graph` is called exactly once per `build_charter_context_json` and reused. Process-wide memoization is explicitly rejected: it would serve stale graphs when project/org overlays change mid-process. A red-first load-count test guards the budget.

## Consequences

- **Positive.** Non-canonical actions receive their action-scoped doctrine; typo'd types fail loud with honest provenance; custom mission types can declare and gate on their own artifact filenames; a `plan` mission's `review` step stops aliasing into the WP-iteration guard. One canonical authority per surface (charter Governing Principle).
- **Compatibility (NFR-003).** For the four built-in mission types, every converted artifact/guard site yields the same values as `main` **except** the two reversals above. A new red-first load-count test guards NFR-001's single-graph-load budget (the pre-existing `test_charter_import_time_io.py` cannot observe a runtime double-load).
- **Cost.** Genuinely non-bootstrap actions now pay one graph load (previously graph-free) to reach the membership predicate; the 4-token fast path spares the common case. Accepted.
- **Program interlocks.** Requires **M0** (landed). Forward-compatible with **M5** (`resolve_mission_type_key` will delegate to M5's `read_mission_type` when it lands; M3 adds no parallel reader). Coordinates with **M4** on `src/doctrine/missions/repository.py` at the function boundary (`get_expected_artifacts` vs M4's `get_action_index`).
- **Layer boundary (C-001).** `ExpectedArtifactManifest` relocates into `src/doctrine/missions/`; the charter bundle slot stays a bare `Mapping[str, Any]` (accepted mypy-strict typing cost on the charter boundary).

## Alternatives considered

- **Revive the `mission_v1` guard registry** to gate per-type artifacts — rejected: the cluster is dead in production and the live runtime already has its own `artifact_exists`; reviving re-introduces a parallel engine.
- **Source artifact names from `MissionStepTemplateRef.artifact_file`** — rejected: covers only 2 of 10 presence tags and duplicates the `path_pattern` authority.
- **Keep the project-wide override tolerance** but warn on typo — rejected: a project-wide probe cannot witness whether *this* type is defined; only a per-type id-matched profile can.
