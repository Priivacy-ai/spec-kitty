# Research — Deliver Loaded Doctrine to the Agent (M4)

Phase 0 consolidation. All four open operator decisions were resolved with the operator at discovery (before spec authoring); this file records each decision, its rationale, and the alternatives rejected, plus the code-grounded findings that shape the design. No `[NEEDS CLARIFICATION]` markers remain.

## D-001 — Glossary delivery: real slot + term-name surface list + fetch pointer

- **Decision**: Give `NodeKind.GLOSSARY_PACK` a real action-bundle delivery slot (`"glossary_packs"`, gate `ACTIVATED`) and a dedicated render row that emits each term's `surface` (name) as a comma/line surface list plus a `--include glossary-pack:<id>` fetch pointer for full definitions. **No profile-channel glossary renderer** (C-007).
- **Rationale**: Glossary is activation-scoped org/project doctrine, not profile-attested — the action-doctrine bundle is its natural home, consistent with the `ACTIVATED` gate the table already assigned it. Names-only keeps the payload budget-safe (NFR-001); a pack can carry many terms and full definitions would blow the bundle. The profile schema does not attest glossary, so inventing a profile-channel renderer would be a doctrine decision the schema does not answer (same reason asset/anti-pattern/paradigm are C-007 deferrals in the profile channel).
- **Alternatives rejected**:
  - *Full inline term definitions* — blows NFR-001 on large packs; the per-entry cap would silently truncate to a pointer anyway, so the extra code buys nothing.
  - *Document-only exclusion (keep slot=None + stated reason)* — leaves an entire authored kind structurally unreachable in the bundle; the operator explicitly chose delivery over ratified exclusion for glossary.
  - *Profile-channel glossary renderer* — unattested by the profile schema (C-007); out of scope.
- **Code grounding**: `GlossaryPack(id, provenance, terms: list[GlossaryTerm], description)`, `GlossaryTerm.surface`/`.definition`. `service.glossary_packs` repo already exists. The generic `_extend_named_artifact_lines` (title_attr/summary_attr) cannot express a term-list, so WP-A adds a dedicated glossary render path (a `_format_inline_glossary_body`-style helper emitting `Terms: <surface>, …` + fetch stanza), not a generic `_ActionRenderRow`.

## D-002 — Styleguide/toolguide: ratify pointer-only, document it

- **Decision**: Keep the styleguide/toolguide profile-channel references pointer-only (`body_fn=None` → fetch stanza) and make that a **documented, intentional** choice in schema/docs — not an unlabeled silent no-op.
- **Rationale**: Pointer-only was a deliberate NFR-001 budget decision; the operator chose to preserve it. The defect that #3488 names is that the choice reads as an accidental no-op; the remedy is discoverability (a stated reason on the renderer + a schema/doc note), not a behavior change.
- **Alternatives rejected**:
  - *Grant a budgeted inline body* — the per-entry cap (`_PROFILE_INLINE_BODY_LIMIT_CHARS`) would bound it, but the operator preferred to keep the smaller, predictable pointer-only surface rather than reverse a deliberate design.
- **Code grounding**: `render_profile_styleguides` / `render_profile_toolguides` pass `body_fn=None`; `render_profile_selector_refs` already documents "`body_fn=None` always emits the fetch stanza". WP-A tightens that into an explicit stated reason (constant/docstring) and a schema/doc note; no runtime change.

## D-003 — Asset asymmetry: reference-only, stated in contract

- **Decision**: Promote `procedure` to the fifth typed array in `context --json`; keep `asset` reference-only (folded into `references[]`, no typed array) and state that asymmetry deliberately in the versioned contract. One schema-version bump.
- **Rationale**: Asset has no resolution/install path (deferred behind #3037) and no repository on the bootstrap render lane, so a typed `assets[]` would ship bare ids implying a path that does not exist. Procedure is fully resolvable and already delivered in the text render, so its JSON array closes a real render-parity gap.
- **Alternatives rejected**:
  - *Also promote asset to a sixth typed array* — implies an install/resolution contract that #3037 has not built; would ship bare ids.
- **Code grounding**: `context.py` builds `repos_by_kind` for directive/tactic/styleguide/toolguide and passes procedure+asset via `extra_delivered`. WP-C moves only `procedure` into `repos_by_kind` (with `_ARRAY_BY_KIND["procedure"]="procedures"`); asset stays in `extra_delivered`.

## D-004 — Org acceptance: full org reach (M2 landed)

- **Decision**: M4 covers org-authored glossary/procedure reach, not just built-in/project.
- **Rationale**: M2 (DRG read-path bridge, #3572/#3573) landed on `main`, so org `drg/fragment.yaml` edges bridge into cascade; org-authored artifacts can reach the delivery paths. Acceptance includes an org-authored glossary pack reaching the agent.
- **Alternatives rejected**:
  - *Scope to built-in/project with an org follow-up* — unnecessary now that M2 is in; would leave the org tier second-class for another cycle.

## D-005 — Builder overlay seam shape (#3176)

- **Decision**: Thread an optional `agent_profile_overlay_dir: Path | None = None` through `build_activation_aware_doctrine_service` → `_build_activation_aware_doctrine_service` → `_build_doctrine_service` → `doctrine.service.DoctrineService`, defaulting to `None` (no override → byte-identical). `DoctrineService.agent_profiles` uses the override when set, else the existing `self._project_dir("agent_profiles")`. Then migrate `default_profile_repository` to build via the factory with the overlay pointed at `.kittify/agent_profiles`, deleting the carve-out.
- **Rationale**: The projection module's own docstring names exactly this as the correct fix ("a builder-level change letting a caller override the project-overlay directory"). Threading one optional param preserves the single-wrapper-body invariant (C-006): only `_build_activation_aware_doctrine_service` constructs the wrapper; the public builder stays a thin delegate. Default `None` keeps every existing caller byte-identical (NFR-002).
- **Alternatives rejected**:
  - *Reasoned exclusion of the site from FR-001* — the operator chose the builder-level fix (option (a) in the docstring) over option (b) exclusion.
  - *Point `resolve_project_root` at `.kittify/agent_profiles`* — wrong seam: that candidate list is the doctrine project root for all kinds, not the agent-profile overlay; changing it would mislocate every other repository.
- **Constraint check**: `charter` must not import `specify_cli` (C-001) — satisfied: the param lives in `charter.doctrine_service_builder` + `doctrine.service`; `specify_cli.tool_surface.profiles.projection` consumes it (correct direction). C-008 preserved: `default_profile_repository` still merges org profiles via `resolve_activated_org_profiles` (the activation gate), not a raw `org_dirs` splice.

## Supply-chain / adversarial posture

- **No dependency changes.** This mission adds/upgrades/removes no packages in any ecosystem, so the supply-chain install-safety directive (051) does not engage — recorded here explicitly (silence is not compliance).
- **Adversarial evidence**: a consolidation review squad (correctness / scope / test-quality lenses, per the M1 precedent) runs on the combined diff before the PR to `main`; contested findings will be recorded `accepted` / `changed` / `deferred_with_rationale`. No security-impacting dependency decision exists to challenge at plan time.
