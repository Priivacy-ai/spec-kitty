# Mission Research — Scope-Increase & Surface Survey

**Mission:** `org-doctrine-profile-integrity-closeout-01KT3G68` (close-out, on `mission/org-doctrine-profile-integrity-activation-closure`, rebased onto upstream `9ea764050`)
**Date:** 2026-06-02
**Method:** 4 read-only profile-driven surveyors (reviewer-renata = pre-existing-issue triage; python-pedro = code debt/refactors; debugger-debbie = latent defects/error-handling; architect-alphonso = architectural needle-movement vs #1111/#1599/#1040/#645). All claims proven by execution/grep/file:line; **no code changed**.
**Discipline:** small scope increase only — DIRECTIVE_025 Boy-Scout (touched-files), DIRECTIVE_024 locality, NFR-002 (no new debt). Each candidate is ABSORB (in-surface, low-risk) or TRACKER.

---

## Headline findings (must act on)

### H1 — WP04 / FR-009 is under-scoped (renata, load-bearing)
`test_no_dead_symbols` has **~23 failing entries**, not the 2 `events.py` re-exports WP04 currently targets:
- **~13 mission-authored** charter/doctrine `__all__` exports unimported on this branch (`charter.{activation_engine::ActivationPlan, cascade::DeactivationPlan/REFERENCE_RELATIONS/ReferencedArtifact/SharedSkip, drg::UnknownRelationError, kind_vocabulary::CHARTER_KIND_TOKENS/MISSION_TYPE_TOKEN}`, `doctrine.drg.org_pack_loader::{AUGMENTATION_RELATIONS,TOPOLOGY_KINDS,merge_topology_artifact}`, `doctrine.template_catalog::{template_id_for,template_node,template_nodes,template_urn}`, `specify_cli.cli.commands._doctrine_health::PackHealth`). These were allowlisted by the parent's WP15, which was **dropped during the rebase** (it conflicted with upstream's `specify_cli.next`→`runtime.next` namespace migration). They are mission scope, not new — **NFR-002/SC-009 are unsatisfiable until WP04 handles the full set**.
- **5 stale entries to REMOVE** (now wired by the parent's WPs): `charter.invocation_context::{OperationalContext,build_operational_context}` (WP14), `charter.pack_context::CharterPackConfigError` (WP12), `specify_cli.status.lifecycle_events::{mission_event_log_path,read_lifecycle_events}`.
- **5 upstream pre-existing** (`specify_cli.coordination.status_service::{EventLogWriteTarget,StatusContractError,StatusReadSource,append_event_log_batch,read_wp_lane_actor}`) — RED on clean `upstream/main` too (from merged #1614; **no tracker exists**). → allowlist-with-ticket + DIRECTIVE_013 tracker; do NOT fix upstream coordination code here.

### H2 — I-1 is one mask of a structural fail-to-green class (debbie, proven)
`DoctrineHealthReport.healthy` = `all(pack.healthy for packs)` → **vacuously `True` on empty**, and it **ignores `org_drg["errors"]`**. Three masks, all in WP01's surface, same class, cheap:
1. profile-load crash → empty report → green (the I-1 target).
2. `org_drg["errors"]` populated (`doctor.py:2351/2354`) but never read by `healthy` → org-DRG load failure reports green (proven).
3. human renderer defaults present-but-unknown packs to green (`doctor.py:1892-1894`, `.get("healthy", True)`).
**Structural fix:** `DoctrineHealthReport.healthy` → `bool(self.packs) and all(...) and not self.org_drg.get("errors")`; `_collect_profile_health` records its crash instead of emptying silently; renderer default → `False`. Add a DIRECTIVE_030 producer-conformance regression test. This closes I-1 + masks #2/#3 in one structural change rather than a point-patch — and composes with the RC=1 directive (honest `healthy=false` → `Exit(1)`).

### H3 — Path correction (pedro): `events.py` is `src/runtime/next/_internal_runtime/events.py` (not `specify_cli.next`); allowlist keys are `runtime.next.*`. WP04 `owned_files` must be corrected.

---

## Recommended scope increase — ABSORB subset (small, in-surface, boyscout)

| # | Item | WP | Effort | North-star / rationale |
|---|------|----|--------|------------------------|
| A1 | **Structural `healthy`-honesty fix** (debbie H2): `DoctrineHealthReport.healthy` honors `bool(packs)` + `org_drg.errors`; `_collect_profile_health` records its crash; renderer default→False; + DIR-030 regression test | **WP01** | small | Closes I-1 + 2 sibling masks; #1584 objective; operator loud-over-hidden |
| A2 | **WP04 re-scope to the full dead-symbol set** (renata H1): re-add the ~13 mission charter/doctrine symbols to the allowlist (restore WP15 intent in `runtime.*` namespace), remove the 5 now-wired stale entries, allowlist-with-ticket the 5 upstream `status_service` + handle the lifecycle stale | **WP04** | small-med | NFR-002/SC-009 satisfiability; #1111 gate cleanliness |
| A3 | **Pin the `doctor doctrine` CLI contract** in the FR-002 test: assert `--json` health keys + RC mapping (0 healthy / 1 unhealthy/degraded) | **WP01/FR-002** | XS | #645 stable API surface; #1599 gate |
| A4 | **Annotate the 2 intentional lazy doctrine imports** (`activate.py:117`, `list_cmd.py:85`) as deliberately-not-facaded (`# boundary: lazy import intentionally not facaded`) | **WP03** | XS | Protects the #1111 allowlist 2→0 win from a future "cleanup" |
| A5 | **Cross-link ADR `architecture/3.x/adr/2026-05-16-1`** from the FR-011 CLAUDE.md section | **WP06** | XS | #1040 ADR↔subsystem linkage; DIRECTIVE_003 |
| A6 | **Land the FR-014 tracker reference inside `_baselines.yaml`** (next to the entries it governs), per the file's own `# justification:`+tracker policy | **WP06** | XS | #1599 release-gate audit trail lives where the ratchet reads it |
| A7 | **`ceremony` → "status commit"** (`guidelines.md:26`) — 1 word, glossary-canonical, flips `test_no_legacy_terminology[ceremony]` GREEN, closes #1563 | **WP06** (or WP02) | XS | ⚠ template-surface + currently FR-014-tracker → **HiC decision** (cost to track > cost to fix) |
| A8 | *(optional)* narrow `_build_pack_entries(registry: object)` to drop `# type: ignore[attr-defined]` (`doctor.py:2093`) | WP01 | XS | same-file boyscout |

## TRACKERS — explicitly OUT (scope discipline; DIRECTIVE_013 / design-needed)
- **4 × `git_repo` marker gaps** (renata corrected the count **2→4**: `test_no_legacy_terminology.py`, `tests/specify_cli/sync/test_local_commit_wiring.py`, `tests/specify_cli/test_sync_state_gitignore_migration.py`, `tests/status/test_bootstrap.py`) — out-of-surface, 4 subsystems → DIRECTIVE_024 violation to absorb. FR-014 tracker, **corrected count**.
- **Upstream `status_service` + lifecycle dead-symbol RED** — new DIRECTIVE_013 tracker (no issue exists; #1614 merged); allowlist-with-ticket only.
- **`doctor.py` god-module split** (FR-012/I-10) — LARGE; defer (renderers already extracted; only the module-wide split remains).
- **`provenance` typed wrapper** (FR-013/I-11) — defer unless trivial in `merge.py`.
- **Silent empty-lineage** (`repository.py:286-295`, debbie) — shipped-DRG load failure produces 0 nodes silently; needs a surface (design).
- **Cascade partial-failure RC=0** (`activate.py:171-178` + deactivate twin, debbie) — a failed cascade target is a warning + `continue`, command exits 0; UX/contract decision.
- **`pack_validator` empty-builtin-set** (`pack_validator.py:477-481`) + **`_load_default_pack` malformed asset** (`pack_manager.py:316-317`) — fail-soft on packaged invariants; low likelihood.
- **Epics:** #1040 `spec-kitty adr` primitive, #645 service-layer/HATEOAS, #1111 Slice F DRG/workflow — epic-sized, do NOT pull in. #1584 closes when parent+close-out merge.

## Anti-findings (verified clean — no action)
`activate_cmd`/`deactivate_cmd` top-level paths fail-closed (`Exit(1)`); `list_cmd.py`/`drg/merge.py` have no broad excepts; the WP05 per-file profile skip records every `SkippedProfile`; `diagnostics.py` is a pure dataclass; `ruff` clean on all touched src files; the boundary-ratchet + marker REDs are the **parent's own** RED→GREEN targets (WP03/WP02), not pre-existing-on-main (pedro).
