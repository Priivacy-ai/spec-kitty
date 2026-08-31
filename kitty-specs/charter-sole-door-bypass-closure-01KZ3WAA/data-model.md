# Phase 1 Data Model: Charter as Sole Door: Close Bypass Access Paths

This mission has no user-facing data entities; the "model" is the access-path/gating-ownership map that
FR-001-006 change, plus the three contracts that must not regress while changing it.

## ArtifactKind → gating owner (post-mission)

| Kind | Pre-mission gating owner | Post-mission gating owner | Shape of change |
|---|---|---|---|
| `paradigm` | `charter.resolver.DoctrineService.paradigms` | unchanged | none |
| `procedure` | `charter.resolver.DoctrineService.procedures` | unchanged | none |
| `agent_profile` | `charter.resolver.DoctrineService.agent_profiles` | unchanged (+ new lineage/mutation accessor, R5) | additive |
| `directive` | none (`__getattr__` passthrough) | `charter.resolver.DoctrineService.directives` (new) | FR-005, mechanical |
| `tactic` | none (`__getattr__` passthrough) | `charter.resolver.DoctrineService.tactics` (new) | FR-005, mechanical |
| `styleguide` | none (`__getattr__` passthrough) | `charter.resolver.DoctrineService.styleguides` (new) | FR-005, mechanical |
| `toolguide` | none (`__getattr__` passthrough) | `charter.resolver.DoctrineService.toolguides` (new) | FR-005, mechanical |
| `mission_step_contract` | none (`__getattr__` passthrough) | `charter.resolver.DoctrineService.mission_step_contracts` (new) | FR-005, mechanical |
| `glossary_pack` | none (`__getattr__` passthrough) | `charter.resolver.DoctrineService.glossary_packs` (new) | FR-005, mechanical |
| `mission-type` (token) | none (lives outside `DoctrineService` entirely) | `resolve_mission_type_context()` only (new filtering; `MissionTypeProfileRepository`'s own file is explicitly untouched — WP06 ownership boundary) | FR-006, non-mechanical |

`TEMPLATE`, `ASSET`, `ANTI_PATTERN` remain outside this table — they are the pre-existing
`_NON_AUGMENTATION_ELIGIBLE_KINDS` carve-out and are not charter-activatable; unaffected by this mission.

## The three-state activation contract (must not regress)

Every mechanical kind (existing 3 + new 6) resolves its activation state through this contract, read from
`PackContext.activated_<kind>: frozenset[str] | None`:

| State | Meaning | Resolver behaviour |
|---|---|---|
| `None` | No pack tier authored a selection | Return the full built-in catalog default (bare-project case) |
| `frozenset()` (empty) | An explicit opt-out was authored | Return nothing for this kind |
| `frozenset({ids})` | A selection was authored | Return only the named ids |

**`mission-type` does NOT follow this contract** — `PackContext.activated_mission_types` is always a
concrete `frozenset[str]`, never `None`; the "no selection authored" case is already collapsed to
`builtin_mission_type_id_set()` inside `PackContext.from_config()` before any resolver runs. FR-006's gating
is binary (filtered vs. not), not three-state; a bare project's default is proven by asserting the built-in
set resolves when `PackContext` was constructed from a config with no `mission-type` key, not by asserting a
`None` passthrough.

## The unified builder contract (FR-008)

Both former call sites must produce identical output through one function after unification:

| Input | `charter` builder (pre) | `specify_cli` builder (pre) | Unified (post) |
|---|---|---|---|
| `repo_root` | required | required | required |
| `active_languages` | `infer_repo_languages(repo_root)` | omitted (not passed to inner service) | `infer_repo_languages(repo_root)` — always computed |
| `org_roots` | optional, defaults to `None` (no org layer) | always self-resolved via `resolve_org_roots` | always self-resolved via `resolve_org_roots` |

The unification must pick the *more complete* behaviour on each axis (compute `active_languages`; always
self-resolve `org_roots`) rather than an arbitrary pick — silently dropping either would be a regression for
whichever call site previously got the fuller behaviour.

**Sequencing note superseded (post-tasks squad)**: the post-plan squad's original note here said the
regression test's assertion surface was bounded by what's gated when it runs — before FR-005 lands, only 3
of 9 kinds exist on the factory, so the unification proof would need to be extended later. That staging no
longer applies: the post-tasks squad merged FR-005's 6-kind work into the same work package (WP01) as the
builder unification, so the proof is written once against the full 9-kind surface, in one unstaged pass.

**Also unified (post-plan squad, FR-002/FR-008)**: `org_layer.py:244,275` and `generate.py:56` each
reimplement the same "build raw `DoctrineService`, then conditionally wrap with `charter.resolver.
DoctrineService` if `pack_context` is given" pattern inline, rather than calling either named builder.
`org_layer.py:252-253`'s `except ImportError: pass` silently returns the *unwrapped* `inner` on import
failure — a fail-open bypass of the entire activation-gating mechanism. All three inline sites collapse onto
the one unified builder; the fail-open branch becomes fail-closed (the operation fails or raises, it does not
silently degrade to an unfiltered service).

## The unfiltered-diagnostic contract (FR-002, R4)

`charter.resolver.DoctrineService(inner, pack_context=None)` is a sanctioned, explicit construction shape for
diagnostic/health call sites that need the full unfiltered catalog. It is still the one factory class
(satisfies C-001); it is distinguished from the normal activation-aware construction only by the explicit
`pack_context=None` argument, not by a different class or a raw `doctrine.service.DoctrineService(...)`
construction. Call sites using this mode must carry an inline comment naming why (diagnostic completeness),
per FR-002.
