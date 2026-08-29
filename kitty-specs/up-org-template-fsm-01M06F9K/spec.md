# Mission Specification: Org Doctrine-Pack Tier for the Template Resolution Chain and FSM Discovery

**Mission Branch**: `up-org-template-fsm`
**Created**: 2026-08-17
**Status**: Draft
**Input**: User description: "Add an org doctrine-pack tier to the template resolver and FSM mission discovery, after converging the two forked template resolvers, fixing issue #3523."

## Provenance

Fixes [issue #3523](https://github.com/Priivacy-ai/spec-kitty/issues/3523). A completed research
spike (held in the authoring team's own research workspace, not in this repository — verified
against `main@4a2367539`)
already answers the design questions a specify phase would otherwise raise, and recommends
**Option A2**. This spec independently re-verifies every load-bearing claim against this
checkout's tip (`main@2cffc248f`) during authoring. Several files changed between the spike's
commit and this one (`src/doctrine/drg/org_pack_config.py`, `src/specify_cli/cli/commands/charter/list_cmd.py`,
`src/charter/activation/resolver.py`, `src/specify_cli/core/mission_creation.py`,
`tests/architectural/test_built_in_location_authority.py`); none of the changes touch the two
resolver `_resolve_asset` functions, `resolve_mission`, the FSM discovery walks, or the 3-kind
carve-out. One spike-cited line range had gone stale by the time of this re-verification
(`mission_creation.py`'s `resolve_configured_template` call site moved from `:354,383` to
`:548,577` — three unrelated commits landed in between); this spec cites the current location.
Every `file:line` citation below was read directly in this checkout this session, not inherited
from the spike.

## Decisions Log

Binding decision records for this mission, each independently re-verified against the live
codebase this session. Not open for re-litigation by an implementer; flag drift instead of
silently reinterpreting.

### DEC-001 — Adopt Option A2: org tier in both chains, sourced from `resolve_org_roots()`, preceded by converging the forked `_resolve_asset`s

**Still endorsed after checking current `main`.** `src/doctrine/resolver.py:145-179` (Tier 1,
mission-scoped override) and `src/specify_cli/runtime/resolver.py:260-286` (Tier 1, no
mission-scoped probe) remain forked with the identical drift the spike found — confirmed by direct
read this session, not carried over. `src/doctrine/resolver.py:303-361` and
`src/specify_cli/runtime/resolver.py:577-641` (`resolve_mission`, the `mission.yaml` config walk)
are still byte-for-byte identical 4-tier implementations, both missing an org tier equally — so no
drift exists there to converge, only the tier to add.

**Rejected alternative B — sanction `mission_packs:` as the bridge.** Re-confirmed today:
`raw.get("mission_packs", [])` on a bare `yaml.safe_load` remains the whole implementation at both
`src/runtime/next/_internal_runtime/discovery.py:178-187` (propagates malformed-YAML exceptions)
and `src/runtime/next/runtime_bridge_io.py:249-260` (swallows them, bare `except Exception: return
[]`) — still two divergent readers, still zero pydantic model, zero `doctor` check, zero writer.
Sanctioning it costs strictly more than the org tier. **Rejected, unchanged.**

**Rejected alternative C — project-tier-only, drop the org tier.** Re-confirmed today: Step 0 (the
`_resolve_asset` convergence) is needed regardless of whether the org tier ships, because the
project tier's mission-scoped override does not work on the production path
(`specify_cli.runtime.resolver`) today — verified directly, not inherited (see DEC-002). Having
paid that convergence cost, the org tier itself is the smaller remaining increment. **Rejected,
unchanged.**

### DEC-002 — Step 0 (convergence) is additive-only; never merge the two `_resolve_asset` modules

`src/specify_cli/runtime/resolver.py:283-286` currently has no mission-scoped override probe;
`src/doctrine/resolver.py:172-179` does. Step 0 adds the missing probe (mirroring
`doctrine/resolver.py:177-179` verbatim) to the `specify_cli` module — it does not delete, import,
or otherwise unify the two modules. `tests/architectural/test_charter_sole_door_resolver_imports.py:1-20`
gate-mandates that `doctrine.resolver`'s tier functions stay reachable, from outside
`src/charter/**`/`src/doctrine/**`, only via `charter.activation.resolver.DoctrineService` — a real merge
would make `specify_cli/runtime/resolver.py` import `doctrine.resolver` directly and red this gate
immediately (zero-tolerance, no allow-list, confirmed at the same citation).

### DEC-003 — Route the org tier's root resolution through the sanctioned `charter.drg.resolve_org_roots` facade wherever the caller lives under `src/specify_cli/**`

`src/specify_cli/runtime/resolver.py` is scanned in full by
`tests/architectural/test_runtime_charter_doctrine_boundary.py:16-17`
(`_RUNTIME_ROOT = src / specify_cli`, no subtree exclusion beyond
`src/specify_cli/doctrine/`) for **both** module-level and lazy (function-body) `doctrine.*`
imports (`test_runtime_has_no_direct_doctrine_imports` at `:64`,
`test_runtime_has_no_new_lazy_doctrine_imports` against an only-shrink baseline). A raw
`from doctrine.drg.org_pack_config import resolve_org_roots` there — even nested inside a
function, mirroring the existing lazy tier-5 pattern at `specify_cli/runtime/resolver.py:250-257` —
would be a *new* lazy doctrine importer not in the baseline and would fail that gate in the "grow"
direction.

The correct route already exists and is already load-bearing: `charter.drg.resolve_org_roots` is a
sanctioned, identity-verified re-export of `doctrine.drg.org_pack_config.resolve_org_roots`
(`tests/architectural/test_charter_facades_reexport_doctrine.py:86`; re-exported at
`src/charter/drg.py:97,152`). Five existing `src/specify_cli/**` modules already call it via the
exact `from charter.drg import resolve_org_roots` lazy pattern this mission should copy:
`src/specify_cli/cli/commands/charter/_layer_roots.py:16,31`,
`src/specify_cli/cli/commands/_doctrine_asset.py:87,90`,
`src/specify_cli/cli/commands/_doctrine_collect.py:239,339,497,946`,
`src/specify_cli/cli/commands/profiles_cmd.py:106,108`, and
`src/specify_cli/invocation/org_profiles.py:63,66`. `src/doctrine/resolver.py` itself needs no
facade — it is already inside the doctrine layer and may import
`doctrine.drg.org_pack_config.resolve_org_roots` directly, same as its sibling `doctrine.base`
module.

### DEC-004 — For `src/runtime/next/**` (FSM discovery), also route through `charter.drg.resolve_org_roots`, even though no architectural gate currently scans that tree

`test_runtime_charter_doctrine_boundary.py`'s `_RUNTIME_ROOT` is hardcoded to `src/specify_cli`
(`:16-17`, re-verified this session) — it does **not** scan `src/runtime/next/**` at all. This is
the gap the mission brief names as filed under #3522: passing this gate is not proof of
compliance for `discovery.py` / `runtime_bridge_io.py`. Absent a gate, `src/runtime/next/**`
already shows both patterns in production: module-level `charter.*` imports
(`src/runtime/next/prompt_builder.py:23-31`), lazy `charter.*` imports (`runtime_bridge_io.py:106,582,641,681`),
and one **direct** `doctrine.missions.step_contracts` import bypassing charter entirely
(`src/runtime/next/runtime_bridge_composition.py:266`, an existing, ungated precedent in a sibling
file of the same package). This mission deliberately does **not** add a second direct-doctrine
precedent to the FSM discovery files it touches: `discovery.py` and `runtime_bridge_io.py`
(Walk A / Walk B) both source org roots via `charter.drg.resolve_org_roots`, matching DEC-003's
discipline, even though nothing currently enforces it there. A reviewer should not read a green
CI run as proof this holds for `src/runtime/next/**` — it holds only by code-review confirmation
until #3522 is fixed.

### DEC-005 — Do not wrap `resolve_org_roots()` calls in a broad `except Exception`

Two distinct failure classes exist inside the `resolve_org_roots` call graph
(`src/doctrine/drg/org_pack_config.py`), verified by direct read:

1. **Malformed / unreadable `.kittify/config.yaml`, or a `ValidationError`/`ValueError` while
   building the `PackRegistry`.** `load_pack_registry` (`:380-427`) already fail-softs this
   internally — it warns and returns an empty `PackRegistry()` (`:396-397,416-422`). This is what
   satisfies the T019 fail-closed concern recorded at `specify_cli/runtime/resolver.py:231-242`
   ("a project could then no longer resolve the templates its repair commands need") — and it is
   **pre-existing**, not something this mission's code needs to add a second layer of
   `try/except` around.
2. **`OrgPackSubdirEscapeError` / `OrgPackEnvVarUnsetError`** (`org_pack_config.py:48,58`, both
   `ValueError` subclasses), raised from `OrgPackConfig.effective_root` during the list
   comprehension inside `resolve_org_roots` itself (`:458-466`) — **after** the registry already
   parsed cleanly. `tests/doctrine/test_org_pack_subdir.py::test_escape_is_not_swallowed_to_empty_registry`
   asserts these propagate **out of** `resolve_org_roots`, by name, deliberately (a subdir escape
   or an unresolved `${VAR}` is a security/config-correctness signal, not a "malformed YAML" case).

A blanket `except Exception: org_roots = []` around the org-tier's `resolve_org_roots()` call would
re-swallow class 2 — a real regression against an existing, tested invariant. Most existing
`src/specify_cli/**` callers already call `resolve_org_roots` with **no** wrapping try/except at
all (`_doctrine_asset.py:90`, `profiles_cmd.py:108`, `_layer_roots.py:31`); only
`invocation/org_profiles.py:63-66` wraps broadly ("org-root discovery stays best-effort" — a
documented, narrower-scoped exception for that one profile-discovery surface). The template/FSM
org tier this mission adds follows the majority pattern: call `resolve_org_roots(project_dir)` /
`resolve_org_roots(repo_root)` directly, with no additional try/except layered on top. The T019
property (a malformed `config.yaml` still resolves built-in templates) holds automatically because
`load_pack_registry`'s own internals already provide it — verified as NFR-001 / SC-004 below.

### DEC-006 — Three production wiring sites for Walk A's `org_roots`, not two

The spike's Step 5 sketch names only `discovery.py`'s `_build_tiers` and
`runtime_bridge_io.py:231-241` (Walk B). Direct grep for production `DiscoveryContext(...)`
constructors this session found a **third**: `src/specify_cli/mission_loader/command.py:187-200`
defines its own `_build_discovery_context`, whose docstring says explicitly *"Mirror
`runtime_bridge._build_discovery_context`... we duplicate the construction here so this module
does not depend on a private surface."* This is the real production entry point for `mission run
<key>` (`run_custom_mission` at `:73-99`, which calls it at `:94`) — the exact command exercised by
`tests/integration/test_mission_run_command.py`, one of the two suites the mission-loader `>=90%`
coverage gate runs (`.github/workflows/ci-quality.yml:1437-1462`). Walk A's org tier is invisible
to `mission run` unless this third site also populates `org_roots`. `src/runtime/next/_internal_runtime/engine.py:176`'s
bare `DiscoveryContext()` (a drift-detection fallback when no context is supplied) is explicitly
**out of scope** — it has no `repo_root` to resolve org packs against.

### DEC-007 — `list_cmd.py`'s org-path fix needs no new architectural allow-list entry

Checked directly against the two gates a `<org_root> / "missions"` join could plausibly trip:
`tests/architectural/test_charter_path_literal_authority.py` polices only `.kittify` /
`charter.{yaml,md}` literal joins (confirmed by reading its docstring and clause list) — unrelated.
`tests/architectural/test_built_in_location_authority.py`'s join-only AST ratchet
(`_KNOWN_JOIN_ALLOWLIST`, `:136-167`) polices only joins against the literal `"built-in"` segment —
also unrelated; the fix changes `org_root / "doctrine" / "missions"` to `org_root / "missions"`,
composing against the already-resolved `org_root`, never `"built-in"`.

### DEC-008 — `charter.activation.template_resolver.CharterTemplateResolver._tier_to_origin` is a fourth place needing an `ORG` label

`src/charter/activation/template_resolver.py:166-174`'s `tier_prefix` dict maps `ResolutionTier` members to a
display prefix via `.get(tier, "unknown")`. Without an `ResolutionTier.ORG` entry, an org-tier
resolution reached through this class would silently render its origin string as
`"unknown/<mission>/<asset_type>/<filename>"` — the exact silent-wrong class this program is
closing elsewhere. Grep this session found **zero production callers** of the two methods
(`resolve_command_template` / `resolve_content_template`) that invoke `_tier_to_origin` — only the
module's own `__all__` export and `tests/charter/test_template_resolver.py`. Folded in as a small,
low-priority consistency fix (FR-012) rather than a user-visible defect, so the public `charter`
surface stays honest even though nothing in production exercises it today.

### DEC-009 — `list_cmd.py`'s PROJECT-tier template path is a separate, pre-existing mismatch — out of scope

`_template_tier_roots` (`list_cmd.py:48-76`) resolves its **project** tier at
`project_root / "doctrine" / "missions"` (i.e. `.kittify/doctrine/missions/`). That path matches
none of the resolver's project-facing tiers (`.kittify/overrides/missions/<m>/templates/` or
`.kittify/missions/<m>/templates/`). This is a second, adjacent oddity noticed during
verification — issue #3523 diagnoses only the ORG gap and the resolver drift, not this path. Not
touched by this mission; recorded so a reviewer does not conflate it with this mission's scope
(see C-004).

### DEC-010 — `test_org_activation_seam.py` does not constrain this mission

Read directly: that gate polices only `AgentProfileRepository(..., org_dirs=resolve_org_roots(...))`
construction (the raw-splice bypass around agent-profile activation gating). `template` and
mission-FSM content are not charter-activation-gated at all — `template` is a member of
`_NON_AUGMENTATION_ELIGIBLE_KINDS` (`src/doctrine/artifact_kinds.py:247-249`) and has no activation
list in `config.yaml`. Ruled out; no interaction.

### DEC-011 — The 3-kind carve-out (`has_built_in_content_dir`) is unaffected, confirmed again today

`src/doctrine/artifact_kinds.py:65-92`'s `_HAS_BUILT_IN_CONTENT_DIR` map still marks `template`,
`mission_step_contract`, and `anti_pattern` `False` — a **location** statement about the built-in
tier's flat per-kind directories (governing ADR `docs/adr/3.x/2026-07-26-2-doctrine-artefact-pack-layout-convention.md`,
§5 point 5, re-read this session, unchanged), not an overridability statement. This mission never
creates `packs/built-in/templates/`, never touches `has_built_in_content_dir` or `built_in_dir`,
and never joins against the `"built-in"` literal (DEC-007). Zero interaction, confirmed again
against current `main`, not merely carried over from the spike.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An org-pack template resolves through the production mission-create path (Priority: P1)

An operator has activated an org doctrine pack (`doctrine.org.packs[].local_path` in
`.kittify/config.yaml`) that ships its own `spec-template.md` for an existing **built-in** mission
type (e.g. `software-dev`) — no custom mission type required. Today, nothing between LEGACY and
GLOBAL_MISSION resolves it; `mission create` silently falls through to the built-in default.

**Why this priority**: This is the mission's core defect — an org pack can already ship every
other artifact family through `resolve_org_roots()`, but not a template, and this is the entry
point that already caused a downstream pack's `TemplateConfigurationError`.

**Independent Test**: Author an org-pack `spec-template.md` at `<org-pack>/missions/software-dev/templates/spec-template.md`,
declare only `doctrine.org.packs[].local_path`, and call `resolve_configured_template("spec", ...)`
— the exact function `mission create` calls (`specify_cli/core/mission_creation.py:577`) — through
the **production** lane, not `doctrine.resolver` directly. Confirm it resolves the org-pack file at
tier `ORG` and loses to a project override placed at `.kittify/overrides/missions/software-dev/templates/spec-template.md`.
Requires no `qa` mission type and no `up-mission-type-seam` — this test is expressible today.

**Acceptance Scenarios**:

1. **Given** an org pack declaring `spec-template.md` under `missions/software-dev/templates/` and
   no project override, **When** `resolve_configured_template("spec", project_dir, ctx)` is called
   with `mission_type="software-dev"`, **Then** it returns the org-pack file with `tier ==
   ResolutionTier.ORG` (not `PACKAGE_DEFAULT`).
2. **Given** the same org pack AND a project override at `.kittify/overrides/missions/software-dev/templates/spec-template.md`,
   **When** the same call is made, **Then** the project override wins (`tier ==
   ResolutionTier.OVERRIDE`), proving org sits below project, above package-default.
3. **Given** the same fixture, **When** `charter list --all` is run, **Then** it reports the
   template's tier as `ORG` (not a borrowed `GLOBAL_MISSION` label) at the flat
   `<org_root>/missions/software-dev/templates/` path (not the nested
   `<org_root>/doctrine/missions/` path it reports today).

---

### User Story 2 - A mission-scoped project override resolves identically through both resolver implementations (Priority: P1)

A project has installed a template at `.kittify/overrides/missions/<mission>/templates/<name>`
(the mission-scoped override path `doctrine.resolver` already documents and supports). Today this
resolves for `charter list` / `show-origin` (which go through `doctrine.resolver`) and **fails**
for `mission create` / plan setup (which go through `specify_cli.runtime.resolver`) — the exact
defect that produced a downstream pack's `TemplateConfigurationError`.

**Why this priority**: This is Correction 7.1 from the spike, and it is the prerequisite the org
tier is built on top of — shipping an org tier onto a project tier that is already broken on the
production path would compound rather than fix the confusion.

**Independent Test**: Place a fixture at `.kittify/overrides/missions/software-dev/templates/spec-template.md`.
Before the fix, calling `specify_cli.runtime.resolver.resolve_template("spec-template.md",
"templates", project_dir, "software-dev")` raises `FileNotFoundError`. After the fix, it resolves
the same path at `tier == ResolutionTier.OVERRIDE`, identically to what
`doctrine.resolver.resolve_template` already returns for the same fixture.

**Acceptance Scenarios**:

1. **Given** a mission-scoped override fixture and pre-fix code, **When**
   `specify_cli.runtime.resolver.resolve_template` is called, **Then** it raises `FileNotFoundError`
   (the documented, reproduced regression) while `doctrine.resolver.resolve_template` succeeds on
   the identical fixture in the same test.
2. **Given** the same fixture and post-fix code, **When** both resolvers are called, **Then** both
   return the identical `path` and `tier` for the identical input — a single parametrized test
   asserting result equality across both modules.

---

### User Story 3 - An org pack's own mission-FSM content is discovered by `spec-kitty next` without a second declaration (Priority: P2)

An org pack ships mission-FSM content — a runtime-schema `mission.yaml` (`mission.key` required,
`steps: [...]`) — at `<org-pack>/missions/<type>/mission.yaml`, declared only via
`doctrine.org.packs[].local_path`. Today, neither FSM discovery walk has a tier between the
project layer and the machine-global (`~/.kittify`) layer, so the org pack's own mission content is
invisible unless it is separately re-declared under the unrelated, unschema'd top-level
`mission_packs:` key.

**Why this priority**: This is the second half of the compounding defect in #3523 — the same gap,
mirrored in FSM discovery. It depends on the `ResolutionTier.ORG` enum member (User Story 1) but is
otherwise independently testable and does not require a custom mission type to exist in the
roster (`up-mission-type-seam`'s territory) — a runtime-schema template for an existing built-in
type name exercises the whole new tier.

**Independent Test**: Author a runtime-schema `mission.yaml` (`mission.key: software-dev`,
non-empty `steps`) at `<org-pack>/missions/software-dev/mission.yaml`, declare only
`doctrine.org.packs[].local_path`, no `mission_packs:` entry. Confirm both
`discover_missions_with_warnings` (Walk A) and `_runtime_template_key` (Walk B) select it at the
org tier, and that project/legacy tiers still outrank it while `~/.kittify` and built-in still
rank below it.

**Acceptance Scenarios**:

1. **Given** the org-pack fixture above and no `.kittify/overrides/missions/`, no
   `.kittify/missions/`, **When** Walk A (`discover_missions_with_warnings`) runs, **Then** the
   mission is discovered at tier `"org"`, `selected=True`.
2. **Given** the same fixture, **When** Walk B (`_runtime_template_key("software-dev", repo_root)`)
   runs, **Then** it returns the org-pack's `mission.yaml` path, not the built-in
   `mission-runtime.yaml`.
3. **Given** the same fixture AND a `.kittify/missions/software-dev/mission.yaml` project-legacy
   file, **When** either walk runs, **Then** the project-legacy file wins over the org-pack file in
   both walks (position parity — the org tier sits at the same relative position in both).
4. **Given** the same fixture called through `mission run <key>` (`run_custom_mission`,
   `src/specify_cli/mission_loader/command.py:73`), **Then** it is also discovered at tier `"org"`
   — proving the third wiring site (DEC-006) is live, not just the generic engine.

---

### User Story 4 - A malformed org-tier FSM template fails loudly instead of silently vanishing (Priority: P3)

An org pack ships a `mission.yaml` at the org tier that is malformed, mis-keyed, or fails
`MissionTemplate` schema validation. On Walk A this already produces a `DiscoveryWarning`; on Walk
B (`_template_key_for_file`, `runtime_bridge_io.py:294-299`), it is currently swallowed by a bare
`except Exception: return None`, and `_runtime_template_key` silently falls through to returning
the bare `mission_type` string with no warning anywhere.

**Why this priority**: Lower priority than the resolution gap itself, but adding a new tier to a
code path that already silently swallows load failures multiplies the exact silent-success surface
this program is elsewhere closing, if left unaddressed.

**Independent Test**: Place a syntactically-invalid or schema-invalid `mission.yaml` at the new org
tier. Before the fix, Walk B produces zero warnings anywhere and falls through silently. After the
fix, a named warning identifying the offending path and tier is emitted through the same
`DiscoveryWarning`-shaped channel Walk A already uses.

**Acceptance Scenarios**:

1. **Given** a malformed `mission.yaml` at the org tier, **When** Walk B resolves the mission type,
   **Then** a named warning is recorded (not silence), identifying the file path and tier.
2. **Given** an org-tier directory shipping both `mission.yaml` and `mission-runtime.yaml` for the
   same key (as every built-in mission directory already does today,
   `src/specify_cli/missions/{plan,research,documentation,software-dev}/`), **When** discovery
   runs, **Then** no error is raised (both files legitimately coexist) but a named diagnostic is
   emitted only when a **non-built-in** tier supplies both — built-in behavior is unchanged.

---

### Edge Cases

- **Malformed `.kittify/config.yaml`** (unreadable, invalid YAML, invalid `doctrine.org.packs[]`
  shape): `load_pack_registry` already fail-softs this to an empty `PackRegistry()` with a warning
  (`org_pack_config.py:396-397,416-422`, pre-existing) — built-in template and FSM resolution MUST
  continue to work with zero org roots contributed (DEC-005, NFR-001).
- **`OrgPackSubdirEscapeError` / `OrgPackEnvVarUnsetError`**: MUST propagate out of the new tier's
  `resolve_org_roots()` call, not be swallowed (DEC-005) — these are deliberate, tested,
  security-relevant loud failures.
- **Two org packs both declare the same `<mission>/templates/<name>`**: `resolve_org_roots` returns
  packs in declaration order (`org_pack_config.py:458-466`); the org tier's own per-root loop uses
  the same first-match-wins semantics every other tier in `_resolve_asset` already uses — no new
  precedence rule to invent.
- **Org root resolves but the `missions/<mission>/templates/` subdirectory does not exist**: the
  tier's `candidate.is_file()` check returns `False` and resolution falls through to the next tier
  — no exception, matching every existing tier's behavior.
- **Project and org both declare the same mission-FSM key**: project wins (built-in → org →
  project precedence, matching `BaseDoctrineRepository`'s documented loading order at
  `src/doctrine/base.py:82-90` and the three-layer model in `docs/architecture/org-doctrine-layer.md:24-34`)
  — not a new merge/override semantic invented by this mission.
- **`engine.py:176`'s bare `DiscoveryContext()` fallback** (drift-detection path with no
  `repo_root`): stays out of scope — there is no project root to resolve org packs against there
  (DEC-006); `org_roots` stays empty by construction, not a regression.
- **A built-in mission directory shipping both `mission.yaml` and `mission-runtime.yaml`** (already
  true today for all four built-ins): MUST NOT start emitting the new sidecar warning — the
  warning is scoped to non-built-in tiers only (User Story 4, AC2).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Step 0: mission-scoped override tier in the production resolver | As an operator who installs a template at `.kittify/overrides/missions/<mission>/<subdir>/<name>`, I want `specify_cli/runtime/resolver.py`'s `_resolve_asset` (`:260-286`) to probe that path first, mirroring `doctrine/resolver.py:172-179` verbatim, so that `mission create` and plan setup (the production lane) resolve it identically to `charter list`/`show-origin`. | User Story 2 | High | Open |
| FR-002 | New `ResolutionTier.ORG` enum member | As a resolver consumer, I want a real `ORG` member on `ResolutionTier` (`doctrine/resolver.py:47-52`), re-exported identically through the existing `charter.resolution` facade, so that org-tier resolutions can be reported honestly instead of borrowed under `GLOBAL_MISSION`. | User Story 1, 3 | High | Open |
| FR-003 | Org tier in `doctrine/resolver.py`'s `_resolve_asset` | As an org-pack author, I want a tier between LEGACY and GLOBAL_MISSION in `doctrine/resolver.py:_resolve_asset` that probes `<org_root>/missions/<mission>/<subdir>/<name>` for each root returned by `doctrine.drg.org_pack_config.resolve_org_roots(project_dir)` (same-layer import, no facade needed), so that `charter list`/`show-origin`/`template_catalog.resolve_template_by_id` resolve org-pack templates. | User Story 1 | High | Open |
| FR-004 | Org tier in `specify_cli/runtime/resolver.py`'s `_resolve_asset`, routed through the charter facade | As an operator running `mission create` against an activated org pack, I want the same org tier added to `specify_cli/runtime/resolver.py:_resolve_asset` at the same relative position, sourced via the lazy `from charter.drg import resolve_org_roots` facade (DEC-003) — never a direct `doctrine.*` import — so that the production lane resolves org-pack templates too. | User Story 1 | High | Open |
| FR-005 | Mirror the org tier into `resolve_mission` in both modules | As an org-pack author shipping a `mission.yaml` mission config (distinct from a template), I want the same org tier mirrored into `doctrine/resolver.py:resolve_mission` (`:303-361`) and `specify_cli/runtime/resolver.py:resolve_mission` (`:577-641`) at the same relative position, so that mission-config resolution gets the identical guarantee templates do. | User Story 1 | High | Open |
| FR-006 | `list_cmd.py` reports the org tier honestly, at the flat path | As an operator running `charter list --all`, I want `_template_tier_roots`'s org branch (`list_cmd.py:76-86`) to resolve `<org_root>/missions` (flat, not the currently-nested `<org_root>/doctrine/missions`) and tag it `ResolutionTier.ORG` (not the borrowed `GLOBAL_MISSION`), so the listing stops advertising a path the resolver does not read and a tier that does not describe what actually resolved. | User Story 1 | Medium | Open |
| FR-007 | FSM discovery Walk A: `org_roots` on `DiscoveryContext` + tier insertion | As an org-pack author shipping mission-FSM content, I want `DiscoveryContext` (`discovery.py:90-97`) to carry an `org_roots: list[Path] = Field(default_factory=list)` field, and `_build_tiers` (`:201-245`) to insert an `("org", ..., context.org_roots)` tier immediately after `project_legacy` and before `user_global`, so the core loader's precedence order gains the org layer at the position the doctrine three-layer model prescribes. | User Story 3 | High | Open |
| FR-008 | FSM discovery Walk A: wire `org_roots` at all real production construction sites | As an operator running either `spec-kitty next` (generic engine) or `mission run <key>` (custom-mission execution), I want `org_roots` populated via `charter.drg.resolve_org_roots(repo_root)` at **both** production `DiscoveryContext` construction sites — `discovery.py`'s own tier-building callers and `src/specify_cli/mission_loader/command.py:187-200`'s `_build_discovery_context` (DEC-006) — so the org tier is live for both consumers, not just the generic engine. | User Story 3 | High | Open |
| FR-009 | FSM discovery Walk B: org tier in `_runtime_template_key` | As an org-pack author, I want `runtime_bridge_io.py`'s `_build_discovery_context` (`:231-241`) to populate `org_roots` via `charter.drg.resolve_org_roots(repo_root)`, and `_runtime_template_key`'s `project_tiers` list (`:338-343`) to insert the org tier at the same relative position as Walk A (immediately after the existing `.kittify/missions` entry, before `user_global`/`builtin`), so both walks agree on where the org layer sits (NFR-003). | User Story 3 | High | Open |
| FR-010 | De-silence Walk B's swallowed template-load failures | As an org-pack author who ships a malformed or mis-schema'd `mission.yaml`/`mission-runtime.yaml`, I want `_template_key_for_file`'s bare `except Exception: return None` (`runtime_bridge_io.py:294-299`) to route the failure into a named warning (the same `DiscoveryWarning`-shaped channel Walk A already uses at `discovery.py:266-273`) instead of silently returning `None` and falling through to the bare `mission_type` string, so a broken org-tier template is diagnosable instead of invisible. | User Story 4 | Medium | Open |
| FR-011 | Named diagnostic for a non-built-in tier shipping both sidecar files | As an org-pack author whose tier supplies both `mission.yaml` and `mission-runtime.yaml` for the same key, I want a named warning (not a hard error, and not emitted for the four built-in directories that already legitimately ship both) when a **non-built-in** tier does this, so a stale sidecar shadowing its sibling is diagnosable rather than silently resolved by the existing intra-directory preference (`_resolve_runtime_template_in_root`, `runtime_bridge_io.py:302-319`). | User Story 4 | Medium | Open |
| FR-012 | `CharterTemplateResolver._tier_to_origin` gains an `ORG` label | As a maintainer of the public `charter` package surface, I want `template_resolver.py:167-172`'s `tier_prefix` dict to include `ResolutionTier.ORG: "org"`, so an org-tier resolution reached through `CharterTemplateResolver` does not silently render as `"unknown/..."` in its origin string (DEC-008). | — | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Fail-soft/propagation semantics preserved exactly | The new org tier MUST NOT add any `try/except` broader than what `resolve_org_roots`/`load_pack_registry` already provide (DEC-005). Measured by: (a) `tests/doctrine/test_org_pack_subdir.py`'s existing "not swallowed" assertions for `OrgPackSubdirEscapeError`/`OrgPackEnvVarUnsetError` continue to pass unmodified; (b) a new regression test proves a malformed `.kittify/config.yaml` still resolves built-in templates AND built-in FSM discovery, before and after the fix (the fix changes nothing about this property — it already held). | Reliability | High | Open |
| NFR-002 | Layer boundary preserved for `src/specify_cli/**` | Zero new module-level or lazy `doctrine.*` imports in any `src/specify_cli/**` file this mission touches. Measured by `tests/architectural/test_runtime_has_no_direct_doctrine_imports` and `test_runtime_has_no_new_lazy_doctrine_imports` (`test_runtime_charter_doctrine_boundary.py`) continuing green with **no new allow-list entries**, and by `test_charter_sole_door_resolver_imports.py` continuing green (DEC-002, DEC-003). | Architecture | High | Open |
| NFR-003 | `src/runtime/next/**` follows the same facade discipline, by convention | `discovery.py` and `runtime_bridge_io.py` source org roots via `charter.drg.resolve_org_roots`, never a direct `doctrine.*` import, even though no architectural gate currently scans `src/runtime/next/**` (#3522, DEC-004). Verified by code review at PR time, not by an automated gate — the PR description MUST say so explicitly per this mission's own diligence bar. | Architecture | High | Open |
| NFR-004 | Position parity across all four org-tier insertion points | The org tier sits at the identical relative position — immediately after the project/legacy tier(s), immediately before the machine-global tier — in `doctrine/resolver.py`, `specify_cli/runtime/resolver.py`, FSM Walk A, and FSM Walk B. Measured by one parametrized test asserting position parity across all four (spike Risk R3: landing it in one walk only would create a third precedence divergence). | Reliability | High | Open |
| NFR-005 | Zero behavior change with no org pack configured | For any project with no `doctrine.org.packs[]` entries, every resolver/discovery code path this mission touches MUST return byte-identical results (`path`, `tier`, discovery order, warning list) to pre-mission behavior. Measured by the existing template/discovery test suites passing unmodified except for this mission's new tests, excluding any test already red on the mission's `planning_base_branch` for unrelated reasons (AGENTS.md § Test-run baseline-red gotcha). | Reliability | High | Open |
| NFR-006 | Coverage floors that actually gate the touched surface | `src/doctrine/*` and `src/runtime/next/*` are enforced **diff-coverage critical paths** (`.github/workflows/ci-quality.yml:3349`, `--fail-under=90` on changed lines) — FR-002, FR-003, FR-005, FR-007, FR-008 (partially), FR-009, FR-010, FR-011 fall under this gate. `src/specify_cli/mission_loader/command.py` (FR-008's third wiring site) falls under the separate, always-enforced `mission-loader-coverage` job (`ci-quality.yml:1437-1462`, `--cov-fail-under=90`, scoped to `src/specify_cli/mission_loader`). `src/specify_cli/runtime/resolver.py` and `src/specify_cli/cli/commands/charter/list_cmd.py` (FR-001, FR-004, FR-006) are **not** in the diff-coverage critical-path list — those changes are covered only by the advisory full-diff step, so they still need focused unit tests per the repo's Sonar new-code-coverage expectation (AGENTS.md § Sonar Expectations), not because a numeric gate demands it. `src/kernel/**` and `src/specify_cli/mission_loader/**`'s own ≥90% floors (`module-kernel.yml`, `ci-quality.yml:1437`) are otherwise **not** touched by this mission except for the one FR-008 site. | Process | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No merge of the two resolver modules | `doctrine/resolver.py` and `specify_cli/runtime/resolver.py` stay two modules. The tier-5 charter-facade split is gate-mandated (`test_charter_sole_door_resolver_imports.py`) — DEC-002. | Architecture | High | Open |
| C-002 | The 3-kind built-in carve-out is untouched | No change to `has_built_in_content_dir`, `built_in_dir`, `packs/built-in/templates/` (which must not be created), or any `"built-in"` path join. Confirmed unaffected — DEC-011. | Technical | High | Open |
| C-003 | `mission_packs:` is kept, not sanctioned or removed | Document it as the local escape hatch it already is; do not add schema, a writer, or a `doctor` check for it (DEC-001, Alternative B). | Technical | Medium | Open |
| C-004 | `list_cmd.py`'s PROJECT-tier template path is out of scope | The `project_root / "doctrine" / "missions"` mismatch noted in DEC-009 is not fixed by this mission. | Technical | Low | Open |
| C-005 | FSM sidecar preference mechanics stay as-is | `mission-runtime.yaml` outranking `mission.yaml` intra-directory (`_resolve_runtime_template_in_root`) is unchanged; this mission only adds the named diagnostic (FR-011), not a new preference rule. | Technical | Medium | Open |
| C-006 | `ArtifactKind`/mission-type roster work is out of scope | This mission does not touch `MissionTypeRepository`, `resolve_mission_type_context`, or any activation roster — confirmed independent per the spike's file-overlap check; that is `up-mission-type-seam`'s territory (its own spec's C-004 names this mission's territory as explicitly out of *its* scope, symmetrically). | Technical | Medium | Open |

### Key Entities

- **`ResolutionTier.ORG`** (new): the sixth member of the template/mission-config resolution
  enum (`doctrine/resolver.py:47-52`), sitting between `LEGACY` and `GLOBAL_MISSION` in
  precedence. Re-exported by identity through `charter.resolution` — no separate declaration
  needed there.
- **Org root** (existing, reused): a `Path` returned by `resolve_org_roots(repo_root)` —
  `pack.effective_root(repo_root)` for each configured `doctrine.org.packs[]` entry, already
  carrying `~`/`${VAR}` expansion and the `subdir:` containment seam. This mission adds no new
  path-normalization logic; it composes `<org_root> / "missions" / <mission> / <subdir> / <name>`
  against the existing seam.
- **`DiscoveryContext.org_roots`** (new field): a `list[Path]`, empty by default, feeding the new
  `"org"` tier in `_build_tiers`. Mirrors the shape of the existing `builtin_roots` field.
- **`DiscoveryWarning`** (existing, reused): the structured warning model (`discovery.py:59-66`)
  Walk A already emits on load failure; FR-010/FR-011 route Walk B's swallowed failures and the
  new sidecar diagnostic into the same shape rather than inventing a second warning type.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An org-pack `spec-template.md` for a **built-in** mission type, declared only via
  `doctrine.org.packs[].local_path`, resolves through `resolve_configured_template` (the
  production lane) at `tier == ResolutionTier.ORG` — proven by a test that fails before FR-003/FR-004
  land (falls through to `PACKAGE_DEFAULT`) and passes after.
- **SC-002**: `.kittify/overrides/missions/<m>/templates/<n>` resolves to the identical `(path,
  tier)` through `doctrine.resolver.resolve_template` and `specify_cli.runtime.resolver.resolve_template`
  — proven by a test that fails before FR-001 (the `specify_cli` resolver raises
  `FileNotFoundError` on the identical fixture) and passes after.
- **SC-003**: An org-pack runtime-schema `mission.yaml`, declared only via
  `doctrine.org.packs[].local_path` with **no** `mission_packs:` entry, is discovered by Walk A,
  Walk B, and `mission run <key>` (the third wiring site) at the org tier — proven by a test that
  fails before FR-007/FR-008/FR-009 (all three report "not found" or fall through to a lower
  tier) and passes after.
- **SC-004**: A malformed `.kittify/config.yaml` still resolves built-in templates and built-in
  FSM discovery, both before and after this mission's changes — a regression guard proving
  NFR-001's fail-soft property was never broken by the new tier (not a before/after delta, since
  the property is pre-existing per DEC-005).
- **SC-005**: Walk B surfaces a named warning for a malformed org-tier `mission.yaml` — proven by a
  test that fails before FR-010 (zero warnings anywhere, silent fallthrough) and passes after.
- **SC-006**: `charter list --all` reports the org template tier as `ORG` at the flat
  `<org_root>/missions/` path — proven by a test that fails before FR-006 (reports
  `GLOBAL_MISSION` at the nested `<org_root>/doctrine/missions/` path) and passes after.
- **SC-007**: Zero behavior change for the four built-in mission types and any project with no org
  pack configured — the existing template/discovery test suites pass unmodified except for this
  mission's new tests (NFR-005), excluding pre-existing baseline reds per the repo's attribution
  policy.
- **SC-008**: One parametrized test asserts the org tier sits at the identical relative position
  in all four resolver/discovery call sites (NFR-004) — proven green only after FR-003, FR-004,
  FR-007, FR-009 all land, catching a position mismatch if any one of the four drifts from the
  others.

## Out of Scope

Deliberately **not** part of this mission:

- `mission_packs:` sanctioning, schema, writer, or `doctor` check (C-003, DEC-001 Alternative B).
- The 3-kind built-in carve-out, `packs/built-in/templates/`, `has_built_in_content_dir`,
  `built_in_dir` (C-002, DEC-011).
- `list_cmd.py`'s PROJECT-tier template path mismatch (C-004, DEC-009) — a separate, pre-existing
  defect noticed during verification, not diagnosed by issue #3523.
- The FSM sidecar preference mechanics themselves (`mission-runtime.yaml` outranking `mission.yaml`
  intra-directory) — only the missing diagnostic is added (C-005).
- Mission-type roster / `ArtifactKind` promotion / `up-mission-type-seam`'s territory (C-006).
- The stale `#3091` pointers in `pack_paths.py:112,121` and `artifact_kinds.py:72,164` (confirmed
  still present, still stale, this session) — a documentation-only cleanup, unrelated to this
  mission's resolution-chain behavior; worth a separate small ledger entry, not this mission.
- Fixing #3522 itself (the architectural boundary tests' scan-root gap for `src/runtime/next/**`)
  — this mission works around it by convention (NFR-003), it does not close the gate gap.

## Mission Sizing

**Size class: M, upper edge.** The spike estimated ~105 production LOC / ~300 test LOC for a
two-site FSM wiring (generic engine + Walk B). This spec's independent re-verification found a
**third** required Walk A production wiring site (`mission_loader/command.py`, DEC-006) and one
additional small consistency fix (`CharterTemplateResolver._tier_to_origin`, FR-012), which were
not in the spike's estimate. Revised estimate:

| Slice | Production LOC | Test LOC |
|---|---|---|
| FR-001 (Step 0 convergence) | ~6 | ~40 |
| FR-002–FR-006 (template chain org tier + `list_cmd.py`) | ~60 | ~130 |
| FR-007–FR-009 (FSM org tier, all three wiring sites) | ~35 | ~110 |
| FR-010–FR-011 (de-silencing) | ~20 | ~50 |
| FR-012 (`_tier_to_origin` label) | ~2 | ~10 |
| Docs (6+ docstrings, `docs/api/missions.md` precedence table, "5-tier"→"6-tier" prose sweep across the sites this session confirmed still say "5-tier") | prose | — |
| **Total** | **~123** | **~340** |

## Terminology Note

This mission is about the **template resolution chain** and **FSM mission discovery** — the
tiered filesystem lookup that decides which file answers "what is the `spec` template for mission
type `X`" or "what is the mission-FSM definition for key `Y`." It is not about mission *lifecycle*
(status, lanes, WPs) and does not touch the mission-type *roster* (which type ids exist and are
activated) — that is `up-mission-type-seam`'s territory (C-006).
