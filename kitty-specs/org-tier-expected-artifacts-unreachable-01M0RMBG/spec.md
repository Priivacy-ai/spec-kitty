# Mission Specification: Org-Tier `expected-artifacts.yaml` Resolver Anchor Fix

**Mission Branch**: `fix/org-tier-expected-artifacts-3703`
**Created**: 2026-08-24
**Status**: Draft
**Input**: GitHub issue [#3703](https://github.com/Priivacy-ai/spec-kitty/issues/3703) — "Org-tier `expected-artifacts.yaml` is unreachable: the resolver anchors at `<org_root>/<type>/` while every other org mission asset anchors at `<org_root>/missions/<type>/`"

## Clarifications

**Q (asked of operator, 2026-08-24)**: Should this mission also add an authoring-time `pack_validator` reachability gate for org-pack `expected-artifacts.yaml`, alongside the resolver fix — the issue's own "Suggested shape" section raises this as one of two things "worth considering in the same PR" and explicitly calls it "a maintainer call"?

**A (operator decision, 2026-08-24)**:

> **Resolver fix only — no validator gate.** Change the path join, the docstring, and the two test fixtures; nothing else. Fast, low-risk, matches the issue's own P1/kernel-defect framing and its explicit Non-goals (defers runtime-gate wiring to #3704).

**Consequence for scope**: adding a `pack_validator` reachability gate for org-pack `expected-artifacts.yaml` is explicitly **OUT OF SCOPE** for this mission — named here as a deliberate deferral, not an oversight. Ledger SK-75's broader "resolve every path at its tier-correct anchor" ask spans asset manifests generally (a different resolver family than the one this mission touches) and is likewise explicitly deferred, not part of this mission.

Also settled and folded in as facts (not re-derived here):

- **No sibling-fallback.** The fix does NOT keep `<org_root>/<mission_type>/` (the current, wrong location) as a legacy fallback after the fix lands. That location has zero possible existing consumers — it has been unreachable since the feature shipped (see #3516, closed, which introduced this file) — and every sibling org-tier resolver in `resolver.py` checks exactly one location, not two. Keeping a fallback would be new, unmatched asymmetry, not conservatism.
- **Related issues do not own or overlap this fix**: #3516 (closed, introduced this file), #3526/#3530 (epic/tracking issues, no code), #3701/#3702 (disjoint files — `mission_type_repository.py` and `charter activate` respectively).
- **Ledger SK-78 does not bear on this mission** — it names a different code path (`_GUARD_TABLES` custom mission-type family gap), not this resolver.

## User Scenarios & Testing *(mandatory)*

This is a kernel/tooling defect fix in spec-kitty's own doctrine resolution machinery, not a user-facing feature. The "user" is an org-pack author extending spec-kitty's mission-type system for their organization.

### User Story 1 - Org-pack author's manifest override is honored (Priority: P1)

An org-pack author lays out their pack's mission assets the only way the codebase demonstrates: mirroring the built-in pack's `packs/built-in/missions/<type>/` structure, i.e. `<org_root>/missions/<type>/mission.yaml`, `<org_root>/missions/<type>/templates/`, and `<org_root>/missions/<type>/expected-artifacts.yaml`. They configure the pack via `doctrine.org.packs[].local_path` and expect their `expected-artifacts.yaml` override (e.g. an extra required artifact, or a wholly custom mission type's manifest) to take effect.

**Why this priority**: This is the entire defect. Today the author's manifest is silently ignored — `resolve_org_expected_artifacts` (`src/charter/org_expected_artifacts.py:81-82`) joins `org_root / mission_type / "expected-artifacts.yaml"`, a location with no other org-tier or built-in precedent, while `MissionTemplateRepository.get_expected_artifacts` (the built-in reader this org tier mirrors) and every sibling org-tier resolver in `src/specify_cli/runtime/resolver.py` (`_resolve_asset` at line 378, `_resolve_mission_config` at line 817) join `org_root / "missions" / <mission> / ...`. An author who copies the demonstrated layout — the only layout the codebase shows — gets silent failure with no warning, because a missing file at the wrong location is indistinguishable from "no override intended."

**Independent Test**: Write a pack's `expected-artifacts.yaml` at `<org_root>/missions/<type>/expected-artifacts.yaml`, call `resolve_org_expected_artifacts(org_roots, mission_type)` and `ManifestRegistry.load_manifest(mission_type, repo_root=...)`, and confirm both return the parsed override instead of `None`.

**Acceptance Scenarios**:

1. **Given** an org pack with `expected-artifacts.yaml` at `<org_root>/missions/<type>/expected-artifacts.yaml` (the built-in-mirroring layout), **When** `resolve_org_expected_artifacts` is called with that org root and mission type, **Then** it returns the parsed manifest mapping instead of `None`.
   - *Currently*: it returns `None` — the resolver only checks `<org_root>/<type>/expected-artifacts.yaml`, a path the correctly-laid-out pack never populates.
2. **Given** the same pack configured via `doctrine.org.packs[].local_path`, **When** `ManifestRegistry.load_manifest(<type>, repo_root=...)` is called, **Then** it returns the org override, not the built-in manifest, and does not silently fall through with no warning.
   - *Currently*: `load_manifest` returns the built-in manifest (or `None` for a wholly custom type with no built-in baseline), because `_resolve_expected_artifacts_slot`'s only source for an org override — `resolve_org_expected_artifacts` — never finds the file.

---

### Edge Cases

- **Malformed file at the new, correct location** (`<org_root>/missions/<type>/expected-artifacts.yaml` exists but fails to parse as YAML, or parses to a non-mapping): must still log a `logging.warning` naming the offending path and the parse failure, and fall through as "no match" for that root — exactly the fail-closed-with-warning behavior `_read_yaml_mapping` already implements today, just reachable at the corrected path. This is not new behavior to build; it is existing behavior that must keep working once the anchor moves.
- **Multiple `org_roots` entries, corrected anchor.** With two or more configured org packs each shipping `missions/<type>/expected-artifacts.yaml`, last-EXISTING-match-wins precedence (NFR-003, contract C-4) must hold exactly as it does today at the corrected anchor: a later root's file (if present and parseable) overrides an earlier root's; a later root with no matching file does not clear an earlier match; a later root's malformed file does not clobber an earlier root's good match.
- **A pack with a file ONLY at the old, wrong location** (`<org_root>/<type>/expected-artifacts.yaml`, no `missions/` segment). Post-fix, this must correctly resolve to `None` (or fall through to the built-in manifest) — this is intended behavior, not a regression, since the old location has never actually worked for any consumer (see Clarifications: no sibling-fallback, zero possible existing consumers).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Correct the org-tier path join | As an org-pack author, I want `resolve_org_expected_artifacts` to check `<org_root>/missions/<mission_type>/expected-artifacts.yaml` (matching every sibling org-tier resolver and the built-in layout it mirrors) instead of `<org_root>/<mission_type>/expected-artifacts.yaml`, so my correctly-laid-out pack's manifest is actually found. | High | Open |
| FR-002 | Correct the module/function docstring | As a future reader of `src/charter/org_expected_artifacts.py`, I want its docstring to state the correct on-disk location (`<org_root>/missions/<mission_type>/expected-artifacts.yaml`) rather than the current, wrong location it documents today, so the mismatch between the docstring's precedence/merge-semantics detail and the actual path can never again be invisible to a reader of one side alone (the exact defect the issue's own "Suggested shape" section calls out). | High | Open |
| FR-003 | Update `tests/charter/test_org_expected_artifacts.py` fixture helper | As a maintainer, I want the `_write_org_expected_artifacts` helper (`tests/charter/test_org_expected_artifacts.py:31-43`) to write fixtures to `<org_root>/missions/<mission_type>/expected-artifacts.yaml` instead of `<org_root>/<mission_type>/expected-artifacts.yaml`, with the existing test matrix (empty-cases, single-root, declared-order precedence, malformed-file with/without warning, custom-mission-type-no-builtin-baseline — classes at lines 46, 65, 93, 151, 271) kept intact and passing against the corrected anchor. | High | Open |
| FR-004 | Update `tests/charter/test_mission_type_profiles.py` fixture helper | As a maintainer, I want the duplicated `_write_org_expected_artifacts` helper (`tests/charter/test_mission_type_profiles.py:996-1010`, used by `TestOrgTierExpectedArtifactsThreading` at line 1014) to write fixtures to `<org_root>/missions/<mission_type>/expected-artifacts.yaml` instead of `<org_root>/<mission_type>/expected-artifacts.yaml`, with its existing before/after threading-through-`resolve_mission_type_context` coverage (required_always count delta, whole-file-replacement-not-field-merge) kept intact and passing against the corrected anchor. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | ATDD-first (charter C-011) | Each of FR-001/FR-002 (paired with its test coverage) is committed as its own failing-first test pinning the user-observable behaviour BEFORE the implementation commit that makes it pass; the reviewer verifies RED at the planning base and GREEN at the final commit. The RED state to pin: currently, `resolve_org_expected_artifacts` returns `None` (and `ManifestRegistry.load_manifest` / `_resolve_expected_artifacts_slot` fall through to the built-in manifest with no warning) for a pack laid out at `<org_root>/missions/<type>/expected-artifacts.yaml`, because the resolver checks `<org_root>/<type>/expected-artifacts.yaml` instead. | Process | High | Open |
| NFR-002 | No new silent-failure mode | The fix must not introduce a new silent-failure mode. Post-fix, `resolve_org_expected_artifacts` still legitimately returns `None` when truly no org override exists at the corrected anchor for a given mission type — that is correct "no override" semantics, not a bug. A malformed file that DOES exist at the corrected anchor must still log a `logging.warning` naming the file and the parse failure, matching the existing (pre-fix) malformed-file handling documented in the function's own docstring (`_read_yaml_mapping`, `src/charter/org_expected_artifacts.py:89-120`) — that logging behavior is unchanged by this fix, only its reachable path is corrected. | Reliability | High | Open |
| NFR-003 | Declared-order precedence preserved | Last-EXISTING-match-wins precedence across multiple `org_roots` entries (contract C-4, NFR-003) must hold identically at the corrected anchor — verified by the existing precedence test classes, not re-derived. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Smallest-viable-diff picks the file set | Per the charter's `RECONCILE_CHANGE_SCOPE_TENSIONS` reconciler, the file set for this mission is fixed at exactly three files: `src/charter/org_expected_artifacts.py`, `tests/charter/test_org_expected_artifacts.py`, `tests/charter/test_mission_type_profiles.py`. Boy Scout Rule cleanup, if any, stays strictly inside this file set, domain-matched to the path-join/docstring defect — no files are added to the set for opportunistic cleanup. Locality of Change is the brake: any extension beyond these three files would need a direct, proportional connection to this specific defect, which none exists for. | Technical | High | Open |
| C-002 | No sibling-fallback to the old location | The fix does not retain `<org_root>/<mission_type>/` (the pre-fix path) as a fallback after the fix. Every sibling org-tier resolver checks exactly one location; the old location has zero possible existing consumers (unreachable since the feature shipped per #3516). Operator-decided (see Clarifications). | Technical | High | Open |
| C-003 | Validator gate is out of scope | Adding an authoring-time `pack_validator` reachability gate for org-pack `expected-artifacts.yaml` (the issue's "Suggested shape" item 1) is explicitly out of scope for this mission — operator decision, see Clarifications. Ledger SK-75's broader tier-anchor-resolution ask (a different resolver family) is likewise deferred, not part of this mission. | Technical | High | Open |
| C-004 | Terminology canon | No new user-facing surface introduced by this fix may use `feature*` naming; "Mission" is canonical. This mission touches only internal resolver/docstring/test code with no new user-facing surface, so this constraint has no practical effect on the diff, but is recorded per charter requirement. The pre-existing internal Python parameter name `mission_type`/`mission` used throughout the touched files is already canon-compliant; any other pre-existing internal naming outside the touched file set (e.g. any lingering `feature`-named internal parameter elsewhere in the codebase) is explicitly not touched by, and not renamed by, this mission. | Technical | Medium | Open |
| C-005 | Canonical-source verification | Every file path cited in this spec was verified to exist on this checkout (HEAD `3442ca1af` at spec-authoring time) before being named. | Technical | High | Open |
| C-006 | Pre-existing failure baseline | `main` carries ~23 known-red tests and 2 errors, already tracked as issue [#3284](https://github.com/Priivacy-ai/spec-kitty/issues/3284). This mission's test runs must not be read against a fully-green baseline; no pre-existing failure from that baseline is attributable to this mission, and no duplicate issue is to be opened for them. | Technical | Medium | Open |

### Key Entities

- **`resolve_org_expected_artifacts` (`src/charter/org_expected_artifacts.py`)**: the free-function org-tier resolver for `expected-artifacts.yaml` overrides. Takes a list of existence-filtered org roots and a mission type; returns the parsed manifest of the last root with a matching, parseable file, or `None`.
- **Org-tier `expected-artifacts.yaml`**: an org pack's whole-file replacement of a mission type's expected-artifact manifest (contract C-4: whole-file replacement, never field-merged with the built-in manifest).
- **`ManifestRegistry.load_manifest` (`src/specify_cli/dossier/manifest.py`)** and **`_resolve_expected_artifacts_slot` (`src/charter/mission_type_profiles.py`)**: the two callers of `resolve_org_expected_artifacts`; both currently fall through to the built-in manifest (or `None`) with no warning when the org override is unreachable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A pack laid out at `<org_root>/missions/<mission_type>/expected-artifacts.yaml` is found by `resolve_org_expected_artifacts(org_roots, mission_type)` — it returns the parsed manifest, not `None`.
- **SC-002**: The same pack's override is found by `ManifestRegistry.load_manifest(mission_type, repo_root=...)`, reached via `_resolve_expected_artifacts_slot` / `resolve_mission_type_context` — it returns the org override, not the built-in manifest and not `None` for a custom type with no built-in baseline.
- **SC-003**: `pytest tests/charter/test_org_expected_artifacts.py tests/charter/test_mission_type_profiles.py` passes with the existing coverage matrix intact (no test deleted, weakened, or skipped to make this pass) against the corrected fixture location, modulo the pre-existing #3284 baseline (C-006).
- **SC-004**: A pack with `expected-artifacts.yaml` ONLY at the old, wrong location (`<org_root>/<mission_type>/expected-artifacts.yaml`, no `missions/` segment) resolves to `None` post-fix — confirmed as intended behavior per the no-sibling-fallback decision, not flagged as a regression.
- **SC-005**: A malformed (unparseable, or non-mapping) `expected-artifacts.yaml` at the corrected location still produces exactly one `logging.warning` naming the offending path, matching pre-fix malformed-file handling.
