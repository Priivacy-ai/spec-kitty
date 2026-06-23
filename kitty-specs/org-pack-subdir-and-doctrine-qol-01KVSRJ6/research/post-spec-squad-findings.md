# Post-Spec Adversarial Squad — Convergent Findings

**Mission**: org-pack-subdir-and-doctrine-qol-01KVSRJ6
**Date**: 2026-06-23
**Point-cut**: after `/spec-kitty.specify`, before `/spec-kitty.plan`
**Profiles (loaded)**: architect-alphonso (seams), debugger-debbie (live-evidence/security), reviewer-renata (anti-laziness), planner-priti (scope/sizing). Read-only.

The value is **convergent** evidence — findings ≥2 independent profiles reached. The spec was revised to incorporate all CONFIRMED items.

## CONFIRMED — BLOCKER: "single resolution seam" claim was FALSE

Found independently by **alphonso, debbie, and priti**.

`resolve_org_roots` (`src/doctrine/drg/org_pack_config.py:170-173`) is a thin `[pack.local_path for …]` map — NOT the resolution seam. The registry fans out to ≥6 direct `pack.local_path` readers that bypass it:

| Site | Role | Severity |
|------|------|----------|
| `src/charter/drg.py:137` | `load_org_pack(.../drg/fragment.yaml)` — the path `doctor doctrine` health flows through (`doctor.py:2628`→`load_org_drg`→`_collect_org_layer_data`) | BLOCKER |
| `src/charter/pack_context.py:344` | modern `PackContext.from_config` path | BLOCKER/HIGH |
| `src/specify_cli/doctrine/org_charter.py:570` | org-charter policy load | HIGH |
| `src/specify_cli/cli/commands/doctor.py:2608` | pack-health renderer (`_build_pack_entries`) | HIGH |
| `src/charter/context.py:746` | direct `org-charter.yaml` read | MEDIUM |
| `src/specify_cli/charter_runtime/lint/checks/org_layer.py:236` | org-layer lint `DoctrineService(org_roots=...)` | MEDIUM |

**Debbie's repro trace**: fix `resolve_org_roots` alone → #2083 repro stays RED, because health is decided by `load_org_drg`→`load_org_pack(<pack.local_path>/drg/fragment.yaml)`, never touching `resolve_org_roots`.

**Pre-existing inconsistency (alphonso LOW / C-007)**: `resolve_org_roots` returns RAW `local_path`; `charter/drg.py` + `pack_context.py` resolve relative-to-repo_root. The effective-root seam must normalize ONCE and retire this split.

→ **Spec fix**: FR-001 moves the seam to `OrgPackConfig`/registry level (`effective_root(repo_root)`); FR-004 enumerates the consumer sites; C-007 mandates single normalization.

**CONFIRMED-CLEAN**: `doctrine fetch` correctly clones to `pack.local_path` (`snapshot.py:285`, `doctrine.py:135-139`) — `subdir` must NOT touch the clone target (C-003 honored).

## CONFIRMED — Security (FR-003/NFR-002): mechanism exists, timing matters

debbie + renata.

- Helper `ensure_within_directory(path, root)` (`src/specify_cli/core/utils.py:30`) uses strict `.resolve()` → symlink-safe; defeats absolute/`..`/symlink. NFR-002's 100% is achievable. **Name it** in FR-003.
- **Timing split**: `OrgPackConfig` is validated at config-load, before the clone exists. String escapes (absolute/`..`) → model-validation. Symlink-escape → resolution time (clone content can plant the symlink). NFR-002 split accordingly.
- **Structured error, not swallowed**: `load_pack_registry` swallows `ValidationError` into a warning and degrades to "no org packs" (`org_pack_config.py:128-139`) — contradicts Scenario A1's "structured, actionable error". FR-003 now requires operator-visible error.
- Rejected set must name absolute (POSIX/Windows/UNC), `..`, `.`/empty→absent.

## CONFIRMED — Thread C (#1843) fakeable as doctrine theater

renata + priti.

- Orphan `*.styleguide.yaml` auto-registers as a bare DRG node with NO required edges (`graph.yaml:274-296`); freshness test checks regeneration, not connectedness. So FR-009-original "discoverable and resolvable" passed on an inert stub. → **FR-011**: require ≥1 inbound DRG edge (doctrine-only) + non-orphan test.
- Pin kind = `styleguide` (generator only auto-discovers styleguides + directives; `extractor.py:580-582`, `:320`). Regen entry: `spec-kitty doctrine regenerate-graph [--check]`; smoke test `tests/doctrine/drg/test_shipped_graph_valid.py`. → C-004 accurate.
- Tier table must map to named existing `src/` areas (FR-010), not abstract labels.

## CONFIRMED — Thread B (#707) documents a rule that doesn't cleanly exist

renata (priti concurred usage is a real split).

- Same `config.yaml` is ruamel-round-tripped (`org_pack_config.py:151,167`) AND `safe_load`-ed (`org_pack_loader.py:38`). 3 dual-use modules (`pack_assembler.py`, `charter/pack_manager.py`, `dashboard/handlers/glossary.py`). → **FR-009**: declare current-vs-aspirational, verify against ≥3 named sites, name the contradiction sites.

## CONFIRMED — Scope additions

priti.

- **config-schema contract stale** (`…/layered-doctrine-org-layer-01KRNPEE/contracts/config-schema.yaml`, `additionalProperties:false`, no `subdir`) → **FR-008**.
- **`doctrine fetch` UX**: wrong `subdir` → fetch succeeds reporting clone-root artifacts; only `doctor` fails. Operator chose to add **FR-007** (report effective root).
- Each SC needs a named evidence artifact → SC-001 binds to an end-to-end `doctor doctrine` integration test.
- WP shape: WP01=A (code), WP02=B (docs, parallel), WP03=C (after A for graph stability), +WP04=D (#2092, parallel-capable).

## Disposition of newly-pulled issues

- **#2092** (P1) — FOLDED as Thread D. Bounded; de-risks Thread C (the new styleguide would itself be dropped if scoped `[any]`). Anchors: `scoping.py:~24` `applies_to_languages_match`, `service.py:75-83`, `charter/context.py:~1851`.
- **#2080** (P2 epic) — NOT folded. Daphne-led audit; deliverable is a remediation plan. Separate curator mission. The Thread-C orphan finding + alphonso's asymmetric-node-walking note are inputs to it.

## CONCESSIONS (where lenses did not apply)

- Thread A core mechanics (FR-002 backward-compat, the join) are genuinely testable/non-fakeable (renata).
- C-005 (`extra="forbid"`) and C-004 (generator registration) confirmed accurate and load-bearing.
- Threads B/C content quality outside alphonso's & debbie's structural/live lenses.
