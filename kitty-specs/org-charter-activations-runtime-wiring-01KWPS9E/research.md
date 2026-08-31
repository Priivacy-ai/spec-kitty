# Research & Brownfield Checks — Org-Charter Activations Runtime Wiring

Consolidates pre-spec grounding (2 sonnet agents) + post-spec squad (alphonso + paula, opus) + post-planning brownfield checks. HEAD: `upstream/main` `71b2787e8`.

## 1. Code-state verification (bug confirmed on HEAD)

The gap the issue reports against installed 3.2.4 **still lives on HEAD**. `OrgCharterPolicy.activations` (`org_charter.py:159`) is folded by `_fold_policies` (`org_charter.py:449-466`) and read by **nothing** downstream — `apply_org_charter_pre_fill`/`apply_org_charter_to_interview`/`org_charter_to_json_block` all ignore `merged_policy.activations`. The two activation sources never join:

```
org-charter.yaml → OrgCharterPolicy.activations → _fold_policies → merged.activations   [DEAD END]
project charter.md → Extractor._collect_activations_from_section → GovernanceConfig.activations
   → _load_governance_activations (context.py:2641) → render_activation_stanza → resolve_for_context
```

**Precedent to mirror**: `_read_org_required_selections` (context.py:732-765) + `_load_doctrine_selection` (context.py:768-813) — resolve-time org∪project union for `required_<kind>`, kept resolve-time by the layer boundary.

## 2. Surface correction (post-spec squad, both lenses)

Activations render **only** in the **text** bootstrap stanza (`"Selected activations:"`), not the `--json` `directives`/`tactics` arrays (those are DRG-bundle-fed via `build_charter_context_json`). Activations reach `--json` only through the spliced `context.text` field. Project activations behave identically. → Scope fenced to text-stanza parity (C-004); JSON-structured surfacing deferred.

`_render_activation_block` is **bootstrap-only** (`first_load`, depth ≥ 2); compact mode renders no activations for either source. → regression test must force bootstrap mode; compact-mode wiring out of scope.

## 3. Related-issues verdict (no duplicate, no blocker)

- **PRIMARY**: #2365. **PARENT**: #1799 (OPEN, 3.2.x) — confirmed correct home; #2196 (closed) and #2216 (override-tier scope) correctly ruled out.
- **Precedent (cited, not folded)**: #1465 (`required_<kind>` render-drop), #1242 (org charter not surfaced) — same class, both fixed. Third recurrence → FR-005 invariant.
- **Awareness**: #1894 refactored `_fold_policies` (current shape `_fold_policies(policies, *, strict_schema_version=False)`).
- **Origin**: `charter-mediated-doctrine-selection-01KRTZCA` — FR-008 required org→consumer propagation; dropped as a cross-WP seam (WP02 wired project path, WP06 wired org fold, nobody wired fold→consumption). No reopen.

## 4. Brownfield: split-brain / duplication scan

**Finding (split-brain / logical duplication)**: org-charter.yaml is read by THREE paths — the pydantic `OrgCharterPolicy` load (`org_charter.py`), the raw `_read_org_required_selections` rescan (`context.py`), and (as-proposed) a new activations rescan. This accreting duplication is the *same class* that caused #2365. → **Folded**: FR-006 extracts a shared `_iter_org_charter_docs(repo_root)` consumed by both charter-layer rescans; FR-003 unifies the dedup identity key into `charter.activations`. Consolidate-to-one-seam per [[brownfield-logical-duplication-consolidation]].

## 5. Brownfield: deprecation & LOC

- **Deprecation check**: no deprecated surfaces touched. `_render_activation_block`, `_load_governance_activations`, `render_activation_stanza`, `resolve_for_context` are current. No `specify_cli.next`/legacy-shim involvement.
- **LOC/blast radius**: small — 2 production files edited + 1 re-import line; the `_read_org_required_selections` refactor is behavior-preserving (existing tests guard it). No god-module interaction.

## 6. Campsite (#1931)

No domain-matched hygiene items; touched files carry zero live TODO/FIXME/skip/xfail markers. FR-006 is the only in-domain debt fold (duplication, not test hygiene).

## 7. Open design decisions — all resolved in spec rev 2

| Decision | Resolution |
|---|---|
| Generate-time fold vs resolve-time union | Resolve-time union (precedent + no shadow path) |
| Shared identity key home | `charter.activations` (down-layer, legal) |
| Validation vs silent-drop | Validate + raise, pre-`except` placement (FR-004) |
| Text stanza vs JSON arrays | Text stanza only (parity); JSON deferred (C-004) |
| Third rescan copy | Consolidate via shared reader (FR-006) |
