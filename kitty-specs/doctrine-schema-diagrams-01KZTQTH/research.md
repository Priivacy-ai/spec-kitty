# Research: Doctrine Schema Diagrams and PlantUML Rendering (Scope B)

## D1 — PlantUML rendering approach (FR-001, NFR-002/003/004)
- **Decision**: local build-time `plantuml.jar` pre-render, a post-processor AFTER `glossary_linker` in BOTH docs workflows. Recover ` ```plantuml ` fences from `docs/_site` (`html.unescape` the payload; assert `language-plantuml` class), render under `-DPLANTUML_SECURITY_PROFILE=SANDBOX`, inject SVG + alt.
- **Egress isolation (post-spec squad BLOCKER)**: `unshare -rn` is NOT reliable on Ubuntu-24.04 runners (AppArmor `apparmor_restrict_unprivileged_userns=1`). **Portable default: `docker run --network=none`** (runners have Docker). A plan-time spike confirms on `blacksmith-4vcpu-ubuntu-2404` + `ubuntu-latest`. SANDBOX proven behaviorally (a `!includeurl` diagram fails-closed), not by flag presence.
- **Alternatives rejected**: client-side plantuml-server (egress), .NET DocFX plugin (effort).

## D2 — Drift guard (FR-004, NFR-001, C-003)
- **Decision**: explicit `file:class` binding table (1:N). Introspect: Pydantic `model_fields` with `FieldInfo.alias or name` + transitive nested recursion; frozen-dataclass `fields()`; StrEnum `list()`. Binding-completeness from `list(ArtifactKind)` + priority list. FAIL on mismatch or unregistered kind. ATDD red-first.
- **Model families (verified)**: Pydantic-with-aliases (`AgentProfileSchema` + nested), frozen dataclass (`ActionIndex`), StrEnum (`NodeKind`=16, `Relation`=15, `ArtifactKind`=12).

## D3 — Doctrine filing corrections (C-004, confirmed by doctrine lens)
- `NodeKind`=16 (live); `action-index` ∉ `ArtifactKind` (mission concept — diagram + prose in `mission-type-resolution.md`); `step-contract` already documented (augment-only); `template` audited, kept as a note; `styleguides.AntiPattern` ≠ DRG `anti_pattern` (NodeKind string, no class). Fill only `glossary-pack` + `anti-pattern`.

## D4 — ADR / R-04 reconciliation (FR-002, C-006)
- Cite the active `plantuml-diagramming` toolguide (charter-prose active); position schema diagrams as a NEW genre distinct from C4 zoom; record the accessibility "restate-facts-in-prose → discharged by doctrine-kinds prose" carve-out; state the new lane trades github.com-source rendering for generated fidelity (docsite-only).

## D5 — Module READMEs (FR-005, C-005)
- Pointer-only; explicit module→plan mapping + fallback; **precondition: Scope A merged to `main`**; a structural lint (length cap / forbid field-table markers) enforces no-duplication by machine.
