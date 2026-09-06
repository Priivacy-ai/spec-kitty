# Tasks: Post-Convergence Governance & Enforcement

**Mission**: `post-convergence-governance-01M1TMPH` | **Branch**: `tier3/governance-enforcement`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Three independent work packages (no inter-WP dependencies — each is a self-contained governance/gate
slice). Each WP is charter red-first: the enforcement change and its non-vacuity/proof-of-teeth test
land together.

| WP | Title | Concern | Requirements | Depends on |
|----|-------|---------|--------------|------------|
| WP01 | ADR hygiene + convergence-retirement ADR | IC-01 | FR-001, FR-002, FR-003 | — |
| WP02 | Modularity SSOT canonicalization + ownership-doc demotion (D7) | IC-02 | FR-004, FR-005, FR-006, FR-007 | — |
| WP03 | runtime→specify_cli boundary ledger + `_PRODUCTION_ROOTS` refresh | IC-03 | FR-008, FR-009 | — |

## WP01 — ADR hygiene + convergence-retirement ADR

- **T001** Read each of the four target ADRs' front-matter to learn the real `status` field shape.
- **T002** Mark the four ADRs `Superseded` with a one-line supersession note pointing at the new ADR.
- **T003** Author `docs/adr/3.x/2026-09-06-1-convergence-retirement-and-client-repo-inversion.md`
  (`Accepted`): records what was retired (sync transport/daemon, delivery/event-journal emit,
  `websockets`, `src/specify_cli/saas/`) and the client-repo inversion (core = client;
  `spec-kitty/zeitgeist` + `spec-kitty/saas` authoritative upstream; `zeitgeist_client`/`saas_client`
  are consumer code), superseding the four; explicitly leaves `2026-04-25-1` Accepted as the precedent.
- **T004** [red-first] Add `tests/architectural/test_adr_hygiene_convergence_retirement.py`: assert the
  four are `Superseded` + link the new ADR; the new ADR is `Accepted` + supersedes the four + names the
  inversion; `2026-04-25-1` is `Accepted`. Include a non-vacuity guard (the parser flags a synthetic
  still-`Accepted` retired ADR).
- **T005** Run the gate; confirm green.

## WP02 — Modularity SSOT canonicalization + ownership-doc demotion (D7)

- **T001** Delete `docs/architecture/05_ownership_manifest.yaml`.
- **T002** Delete `tests/architecture/test_ownership_manifest_schema.py` (it pins the stale 8 keys — D7)
  AND remove its entry from `pyproject.toml [tool.ruff.format].exclude` (else the ruff-format ratchet reds).
- **T003** Rewrite `docs/architecture/05_ownership_map.md` as narrative-only: state that the canonical
  modularity SSOT is the enforced pair (`pyproject [wheel].packages` + `conftest.landscape`/
  `test_layer_rules`); drop every deleted `src/specify_cli/sync/`, `saas/`, `src/doctrine/`,
  `src/lifecycle/`, `src/orchestrator/` path; keep only a short historical/extraction-roadmap note.
- **T004** Add an SSOT statement to `docs/architecture/00_landscape/README.md` and `CLAUDE.md`
  (→ AGENTS.md): name the enforced pair canonical; frame `zeitgeist_client`/`saas_client` as clients of
  the upstream authoritative repos `spec-kitty/zeitgeist` + `spec-kitty/saas`.
- **T005** Verify no gate references the deleted manifest/test (grep + run
  `test_ruff_format_exclude_ratchet`, `test_no_legacy_terminology`, `test_no_stale_charter_path_literals`).

## WP03 — runtime→specify_cli boundary ledger + `_PRODUCTION_ROOTS` refresh

- **T001** [red-first design] In `tests/architectural/test_layer_rules.py`, add `_RUNTIME_ROOT` and
  `_RUNTIME_ALLOWED_SPECIFY_CLI` (the 23 live first-level subpackages + a bare-`import specify_cli`
  sentinel), reusing the existing `_collect_specify_cli_imports` / `_out_of_ledger_specify_cli_imports`
  / `_specify_cli_subpackage` helpers.
- **T002** Add `TestRuntimeSpecifyCliLedger` with three tests mirroring `TestMissionRuntimeBoundary`:
  `test_runtime_specify_cli_imports_within_ledger`, `test_rule_rejects_out_of_ledger_import`
  (non-vacuity, synthetic `specify_cli.cli` edge), `test_ledger_has_no_stale_entries` (shrink-only).
- **T003** Refresh `_PRODUCTION_ROOTS` in `test_shared_package_boundary.py`: drop the retired `doctrine`
  shim; add `mission_runtime` + `glossary` (D6).
- **T004** Run `test_layer_rules.py` + `test_shared_package_boundary.py`; confirm green and ≤5 s.
