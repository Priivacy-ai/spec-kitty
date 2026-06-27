# Phase 0 Research — Doctrine Governance Fidelity

Source: pre-planning adversarial squad (planner-priti, architect-alphonso,
paula-patterns, debugger-debbie), profile-loaded, read-only against `upstream/main`
tip `aac0635b5`. All findings are convergent unless noted.

## Lane B (#2156 + #2166) — the org_dirs omission is a duplicated pattern, not one site

`AgentProfileRepository` accepts `built_in_dir` / `org_dirs` / `project_dir`
(`src/doctrine/agent_profiles/repository.py:222`). Only **one** construction site
passes `org_dirs`. Census (org-awareness):

| Site | Layer passed | org_dirs? | Disposition |
|------|--------------|-----------|-------------|
| `doctrine/service.py:141` (`DoctrineService.agent_profiles`) | `.kittify/doctrine/agent_profiles` | ✅ canonical | reference seam |
| `specify_cli/invocation/registry.py:24` (`ProfileRegistry`) | `.kittify/profiles` | ❌ | **FR-004 (IC-03)** |
| `specify_cli/tool_surface/profiles/projection.py:78` | `.kittify/agent_profiles` | ❌ | **#2166 / FR-006 (IC-04)** |
| `charter/context.py:1602` (`_DEFAULT_AGENT_PROFILE_REPO`) | built-in only (cache) | ❌ | **FR-005 (IC-03)** — governance-context leg |
| `runtime/next/runtime_bridge.py:2369` | `.kittify/doctrine` (wrong subdir) | ❌ | out of scope (note in friction trace) |
| `cli/commands/agent/tasks.py:281,3209` | built-in only | ❌ | intentional (language resolution) — exclude (C-003) |
| `cli/commands/profiles_cmd.py:85` | `.kittify/profiles` + hand-rolled org overlay | partial | duplication smell; collapse onto IC-02 if low-risk |

- **Canonical seam exists**: `resolve_org_roots(repo_root)` (`drg/org_pack_config.py:263`)
  → `<pack>/agent_profiles/`. IC-02 wraps it once; IC-03/IC-04 consume it.
- **Two distinct project layers** (`alphonso` + `paula`, binding): `.kittify/profiles`
  (invocation) vs `.kittify/doctrine/agent_profiles` (doctrine). **Add** `org_dirs`;
  do NOT reroute `ProfileRegistry` through `DoctrineService` (would change which
  project profiles dispatch sees). → C-002.
- **Live divergence (debbie, dynamic)**: with an explicitly **activated** net-new org
  profile, charter/specify catalog = 19, dispatch catalog = 18 → org profile
  unroutable. On-disk: `.kittify/config.yaml` `doctrine.org.packs[].local_path`,
  profiles at `<pack>/agent_profiles/*.agent.yaml`. → NFR-002 requires live proof.
- **#2166 confirmed** = the projection leg (`projection.py:78`), same root cause, P1.

## Lane A (#2153) — single read-but-dropped field, distinct from #1416

- `src/charter/compiler.py:937-939` interpolates `risk_boundaries`; `:942-944` reads
  `documentation_policy` (`if docs:`) but emits a **hardcoded** string — value dropped.
- **Field census (paula)**: 13 interview fields interpolate; `documentation_policy` is
  the **sole** read-but-dropped one → not a class; one-line fix. Resisted promoting to
  a "field-interpolation framework" (over-consolidation bias flagged + rejected).
- **Single sink**: directive output flows only to `charter.md` Project Directives — no
  `directives.yaml` emitted here; governance context reads doctrine, not compiled prose.
  `documentation_policy` is also rendered verbatim into `user-project-profile.md:799`
  (so not globally lost — only dropped in the directive).
- **Prior art #1416** (CLOSED, PR #1419): touched only `charter/synthesizer/*`
  (key-drift), **never** `compiler.py`. #2153 is distinct & unaddressed.
- **Live repro (debbie)**: sentinels → `SENTINEL_RISK` present, `SENTINEL_DOCS` absent.

## Lane C (#2082) — hidden depth: adjudicator is test-local, must be promoted

- `src/doctrine/drg/override_policy.py` `__all__` = `ReplaceableBuiltin`,
  `ReplaceableBuiltinsPolicy`, `POLICY_RELPATH`, `load_replaceable_builtins` (4 symbols).
- **Critical (alphonso + debbie + priti)**: `find_unsanctioned_overrides`,
  `find_overridden_builtin_urns`, `UnsanctionedOverride` **do not exist in production** —
  they live inside `tests/architectural/test_builtin_override_policy.py` (~line 79).
  → FR-009 (IC-06) must PROMOTE them before wiring.
- **Consumer seam already half-built**: `doctor doctrine` (`_doctrine_collect`) already
  loads the merged 3-layer DRG and `repo_root`; slot diagnostics into the
  org-packs-present branch after `_collect_doctrine_collisions`, guarded by the existing
  no-packs short-circuit → no new DRG plumbing (C-006).
- **Allowlists (debbie, exact)**: all 4 symbols in `_CATEGORY_C_BUILTIN_OVERRIDE_POLICY`
  (`test_no_dead_symbols.py:714-717`); module in `_CATEGORY_7_GRANDFATHERED_ORPHANS`
  (`test_no_dead_modules.py:369`); `_baselines.yaml:70` `category_7_grandfathered_orphans: 7`
  → 6 after wiring. No `src/` runtime caller today (grep clean; `merge.py` hits are
  doc-comments; `model_task_routing` `OverridePolicy` is unrelated).
- **Not dead code** — a dormant governance gate (test-consumed). Wire, never delete.
  Project-tier overrides stay ungoverned (trusted operator tier) → FR-012.

## Brownfield checks (post-planning)

- **Foldable issues**: #2166 folded (Lane B leg 3). #2049 (ratchet-allowlist shrink) &
  #2059 (`doctor.py` god-module) referenced-by-checklist only — FR-011 delivers one
  #2049 burn-down item; IC-07 prefers extraction over insertion (partial #2059 credit),
  no full de-godding. No other open issue is domain-matched.
- **Split-brain / dual-authority**: the org_dirs omission IS a split-brain (specify vs
  dispatch see different catalogs) — IC-02 consolidates to one resolver + FR-008 gate.
- **Deprecation check**: none of the touched surfaces are slated for removal; `charter/
  context.py` module cache + `agent/tasks.py` built-in-only sites are intentional.
- **Sizing**: undersized ~2–3× vs the naive "3 surgical fixes" framing → 8 ICs, 3 lanes.

## Architectural-alignment squad (charter-as-runtime-entry-point) — UNANIMOUS, live-proven

Lenses: architect-alphonso, doctrine-daphne, debugger-debbie (profile-loaded).
**Verdict: the original Lane B plan BYPASSED charter as the entry point → revised.**

- **The gate** lives in `charter/resolver.py:121-130` — `DoctrineService.agent_profiles`
  filters the merged set by `PackContext.activated_agent_profiles` (three-state:
  `None`→all / explicit set→only those / `frozenset()`→none). It sits **two layers
  above** `resolve_org_roots`. Canonical gated chain:
  `build_activation_aware_doctrine_service(repo_root)` (`doctrine_service_factory.py:38`)
  → inner `DoctrineService(org_roots=resolve_org_roots(...))` (`service.py:29`,
  activation-BLIND) → `charter.resolver.DoctrineService(inner, PackContext.from_config(repo_root))`
  → `.agent_profiles`.
- **Original IC-02 ("thin wrapper over `resolve_org_roots`") was below the gate** —
  would surface declared-but-de-activated org profiles to dispatch/projection.
- **debbie's live 4-surface × 4-state matrix** (org probe, 18-builtin universe):

  | Config state | activation-aware S1 | raw DoctrineService S2 | raw repo+org_dirs S3 | dispatch S4 |
  |---|---|---|---|---|
  | key absent (default) | 19 | 19 | 19 | 18 (broken) |
  | explicit list INCLUDES | 1 | 19 | 19 | 18 |
  | explicit list EXCLUDES | **hidden** | **19 ❌** | **19 ❌** | 18 |
  | CLI-activated | 17 | 19 | 19 | 18 |

  Row 3 = the bypass: raw paths show a profile the charter EXPLICITLY de-activated.
- **Gate is opt-in/off-by-default**: `None` (key absent) → all admitted (so #2156
  "install→visible" holds with no activation for the common case); first
  `charter activate` materialises a ~16-entry list, turning the gate on thereafter.
- **Planned NFR-002 proof was FAKEABLE** — activated-only assertion (rows 2/4) where
  raw==filtered passes a bypassing impl → added the negative regime (row 3).
- **Planned FR-008 gate was INVERTED** — "assert site passes `org_dirs`" certifies
  the bypass → revised to assert the activation-aware seam is used (C-008).
- **C-002 reconciliation**: C-002 governs the PROJECT overlay only; the ORG overlay's
  sole notion of "active" is charter activation. Correct design = keep each
  consumer's project repo, **merge** the org-provenance activated subset onto it
  (C-008). Precedent: `charter/context.py:1300-1333` already gates `charter context
  --include agent-profile:<id>` (FR-016/#1636) — Lane B raw would have created the
  opposite split-brain.
- **Layout split-brain (debbie finding 4 → folded as FR-013/IC-09)**: runtime reads
  `<pack>/agent_profiles/` (`resolve_org_roots`); the activation subsystem reads
  `<pack>/doctrine/<plural>/org/` (`_layer_roots.py:24-26` doctrine-dir gate +
  `pack_manager._scan_layer_dirs:566-567`). `charter activate agent-profile <id>`
  FAILS "Unknown agent-profile ID" against a runtime-flat pack. **Operator decision
  2026-06-27**: `<pack>/agent_profiles/` (flat) is canonical; fix the activation
  subsystem to match runtime. No existing tracker issue — to be filed under #1799.
- **Override-shadow (daphne, medium, OUT of Lane B)**: a raw org profile reusing a
  built-in id could shadow it at dispatch with no activation/sanction check; routing
  through the activation filter closes the activation half; override-sanction stays
  a `doctor doctrine` diagnostic (Lane C) — noted for a later mission.

## Post-tasks anti-laziness squad (reviewer-renata, debugger-debbie, python-pedro) — remediated

All cited file:line claims verified accurate (debbie — no substantive drift; WP01 RED proven live). Binding remediations folded into the WP prompts:
- **[HIGH, renata+pedro] WP02→WP04 contract gap**: `AgentProfile` carries no provenance; `source_layer`/`source_path` live on the repository. WP02 return contract changed to `list[ResolvedOrgProfile]` (provenance+source_path), recovered from the activation-aware inner repo — otherwise WP04's #2166 `source_layer="org"` is unsatisfiable (repo fallback → "builtin").
- **[HIGH, pedro] WP06 blast radius**: hard cutover to flat layout would RED the non-owned `tests/charter/test_pack_manager_catalog.py` (≥6 nested fixtures). Resolution: layout-tolerant resolver (flat preferred, nested fallback) as the DEFAULT.
- **[MED-HIGH, renata] WP03 fakeable context**: `assert context != ""` passes on a built-in fallback → assert an org-doctrine sentinel; drive the dispatch `--profile` path (`_default_agent_profile_repository` :1593), not the already-gated `charter context --include` (:363).
- **[MED, renata] WP05 gate teeth**: binding assertion = absence of raw `org_dirs`/`resolve_org_roots` at named surfaces; "references seam" is advisory; teeth fixture imports-seam-yet-bypasses.
- **[MED, renata] WP09 self-attestation**: T027 requires real CI `integration-tests-core-misc` evidence, not an Activity-Log note.
- **WP08 ownership false-alarm RESOLVED** (debbie+pedro): route findings through the existing `org_drg["errors"]` channel in owned `_doctrine_collect.py`; `healthy` already keys off it — no `_doctrine_health.py` edit. Added: extract `_adjudicate_org_overrides` helper (complexity ≤15) + isinstance narrowing.

## Open questions for `/spec-kitty.tasks`

1. Final module placement for the IC-02 `resolve_activated_org_profiles` resolver (avoid import cycle; reuse `build_activation_aware_doctrine_service`).
2. Whether to collapse the `profiles_cmd.py` hand-rolled org overlay onto IC-02 (low-risk?) or leave it.
3. Exact JSON schema key for `doctor doctrine` override findings (editorial — confirm with #2082 requester/daphne).
4. IC-09 layout fix: hard cutover to flat `<pack>/<plural>/` vs layout-tolerant resolver (accept both, prefer flat) for backward-compat across all org-pack kinds.
