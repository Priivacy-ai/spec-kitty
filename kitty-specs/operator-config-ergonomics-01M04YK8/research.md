# Research: Operator Config & Install Ergonomics

Phase 0 consolidation. Full evidence lives in [design-record.md](./design-record.md); this records the load-bearing decisions, their rationale, alternatives, and the adversarial-evidence dispositions.

## Decisions

### D1 — Provenance stores a token, not a resolved path
- **Decision**: `charter.yaml` and `agent_profiles_manifest.json` `source_path` emit `${SPEC_KITTY_PACKS_ROOT}/built-in/...` tokens.
- **Rationale**: repo-relative is already NOT install-mode invariant (installed wheels emit `site-packages/...`); the token is byte-identical across editable/wheel/extracted layouts and matches the established `org_pack_config.local_path` token-preservation pattern.
- **Alternatives**: repo-relative (rejected — not invariant, breaks under #3022); resolved-absolute (rejected — non-portable); env-templated *without* an expander (rejected — renders literally).

### D2 — One kernel expander with two policies
- **Decision**: `kernel/env_expand.py::expand_env_template(raw, *, inject_defaults)` — fail-loud (resolution fields) vs default-inject (provenance/config); `get_packs_root_default() = get_built_in_pack_root().parent`; `org_pack_config` delegates.
- **Rationale**: single expansion authority; `.parent` is required because the token names `…/packs` while the resolver returns `…/packs/built-in`.
- **Alternatives**: two expanders (rejected — drift); reuse `os.path.expandvars` alone (rejected — cannot default-inject).

### D3 — `.kitty.env` located via `SPEC_KITTY_HOME`, HOME excluded, two-tier
- **Decision**: `env_file: ${SPEC_KITTY_HOME}/.kitty.env` (home tier) overridden by `<repo>/.kittify/.kitty.env`; `.kitty.env` never sets `SPEC_KITTY_HOME`; no new `CONFIG_HOME` var.
- **Rationale (operator decisions)**: reusing HOME kills the invented-var + bootstrap-circularity risk; excluding HOME preserves the deliberate `.kittify`/`.spec-kitty` dual-root and avoids the `test_home_owner_never_wins` collision.
- **Alternatives**: `SPEC_KITTY_CONFIG_HOME` (rejected); single-tier (rejected — secrets re-entered per repo).

### D4 — Pre-import shim, merge-then-setdefault precedence
- **Decision**: load `.kitty.env` before any spec-kitty import (stdlib-only); merge tiers `{**home, **repo}` then a single `os.environ.setdefault` so precedence is real-env > per-repo > home.
- **Rationale**: `SPEC_KITTY_TEST_MODE`/`SPEC_KITTY_SYNC_MINIMAL_IMPORT` are read at import time — a `main()` load is too late. Naive per-tier `setdefault` inverts repo-vs-home; merge-first fixes it.
- **Alternatives**: `main()` load (rejected — import-time reads); overwrite semantics (rejected — CI can't override).

### D5 — Secret redaction is a fail-closed allowlist
- **Decision**: an allowlist of printable var *names*; anything not listed is never printed by value.
- **Rationale**: a denylist fails open on newly-added secrets; the allowlist fails closed, satisfying "0 secret values printed."
- **Alternatives**: denylist (rejected — fails open).

### D6 — rc channel default-off, pinned install, consumer-only
- **Decision**: `SPEC_KITTY_PRERELEASE` default off; when on, "latest" includes PEP 440 pre-releases from the same index; upgrade command pins `spec-kitty-cli==<rc>`.
- **Rationale**: stable users never nagged onto rc; pinning avoids `--pre` transitive blast. CI rc-cadence/publication stays in #3047.
- **Alternatives**: `pip install --pre` (rejected — transitive prereleases); always-on (rejected).

### D7 — Two independent migrations; per-check doctor isolation
- **Decision**: heal (WP1) and provision (WP2) are separate idempotent migrations; `doctor.py` checks are isolated per-check (#1623 campsite).
- **Rationale**: keeps WP1∥WP2 collision-free; provisions coordinate ordering with #3381.

## Supply-Chain Security (plan gate)

**No dependency is added, upgraded, or removed.** The `.kitty.env` parser is hand-rolled stdlib (deliberately avoiding `python-dotenv`); pre-release comparison reuses the already-present `packaging`. Therefore: no new registry authenticity, package-freshness, or lifecycle-script (`preinstall`/`postinstall`) exposure; no Node LTS surface. The `051-supply-chain-install-safety` directive is satisfied by the null-change: the one relevant risk — a default that silently pulls prerelease *transitive* deps — is explicitly closed by D6 (pin exact rc, never `--pre`).

## Adversarial Evidence (post-spec squad dispositions)

Per `contracts/adversarial-evidence-contract.md`, every contested finding's disposition (accepted / changed / deferred_with_rationale):

| Finding (lens) | Disposition |
|---|---|
| FR-008 allowlist vs denylist contradiction (renata H1 / architect M3) | **changed** — pinned fail-closed allowlist (FR-008, NFR-004, Key Entities). |
| Present-but-unreadable env_file fail-loud unpinned (renata H2) | **changed** — FR-004a + US2.5. |
| Doctor env-file/channel health no FR (renata H3 / planner M2) | **changed** — FR-010 + US4.4/US3.4. |
| Pre-import ordering untested (renata H5 / architect H1) | **changed** — FR-004 + US2.4. |
| Two-tier setdefault merge inverts repo/home (architect H2) | **changed** — FR-004 merge-then-setdefault + US2.3. |
| Single shared path→token normalizer (architect H4) | **changed** — FR-001. |
| `get_packs_root_default()` = `.parent` (architect M1) | **changed** — FR-006. |
| Scaffold must not seed PACKS_ROOT / TEMPLATE_ROOT gate (renata M4 / planner M6 / architect H3) | **changed** — C-003a + US4.2. |
| Re-bake footgun (PACKS_ROOT=abs) (architect M2) | **changed** — C-003 + US1.4 + SC-001. |
| org_pack fail-loud acceptance (renata M1 / architect M4) | **changed** — covered by FR-006 + a contract test (see contracts/). |
| Cross-mission deps only in checklist (planner H3) | **changed** — Dependencies & Assumptions section. |
| #3047 discovery interface undefined (planner M1) | **changed** — Dependencies & Assumptions (index + PEP 440 pre-release pattern). |
| No-CONFIG_HOME-var not a constraint (planner M4) | **changed** — C-004. |
| Two-migrations + doctor.py ownership (planner H1/H2) | **changed** — Dependencies & Assumptions + IC map. |
| Dangling `.kittify/mission-brief.md` reference (planner M5) | **changed** — replaced by committed design-record.md. |
| NFR-001 absolute-ms unmeasurable (renata M2) | **changed** — delta-vs-baseline against the completion benchmark. |
| SC-002 "sync now succeed" non-deterministic (renata M6) | **changed** — reaches drain/delivery stage without config error. |
| NFR-003 "(forward) extracted-pack" untestable now (renata L2) | **deferred_with_rationale** — scoped to editable+wheel; extracted-pack noted non-blocking (blocked on #3022). |
| Windows CI reachability (renata M5) | **deferred_with_rationale** — scoped to parametrized path-resolution unit tests (NFR-005); full Windows-CI matrix out of mission scope. |

No contested finding was silently dropped.

## Adversarial Evidence (post-PLAN squad dispositions)

| Finding (lens) | Disposition |
|---|---|
| Doctor checks target `runtime/doctor.py` (agent-status), not `spec-kitty doctor`; collision across WP1/WP2/WP3 (paula H1, planner H1, architect M2) | **changed** — PPC-1: per-facet `_*_doctor.py` siblings under `cli/commands/doctor.py`; physically isolated; campsite #2059. |
| Blanket normalizer would mis-token mission-path/`output_path` callers (paula H2, architect H1) | **changed** — PPC-2 / C-PRV-6: surgical 3-class normalizer, exact sites + byte-unchanged regression. |
| Shim forks a 4th home resolver; `.spec-kitty` vs `.kittify` mismatch (paula M1) | **changed** — PPC-3: state-root home via one kernel primitive; C-LDR-7 fixed. Duplicate-resolver consolidation **deferred_with_rationale** (tracking issue). |
| WP3 dependency mislabeled; over-serialized (planner H2, architect L1) | **changed** — PPC-4: WP3 depends on WP0, parallel with WP1/WP2 once doctor is split. |
| FR-010 straddles two WPs (planner M2, architect M2) | **changed** — PPC-4: split FR-010a/FR-010b. |
| NFR-001/005/002 absent from IC map (planner M1) | **changed** — PPC-4: assigned. |
| Migration ordering vs #3381 no mechanism (paula M2, planner M4) | **changed** — PPC-5: distinct `target_version` + ordering test. |
| Loader import-purity not gated (architect M3) | **changed** — PPC-5: arch test on transitive import set. |
| pyproject/CHANGELOG cross-WP ownership (planner M3) | **changed** — PPC-5: WP0 owns bump; per-WP fragments. |
| IC→WP mapping implicit (architect M1, planner) | **changed** — PPC-6: explicit table. |
| Dangling design-record brief line (paula L1) | **changed** — design-record.md corrected. |
| Contract inventory "6 vs 3" (planner L2, architect L2) | **changed** — PPC-6 note. |

All post-plan HIGH/MEDIUM findings folded; one `deferred_with_rationale` (duplicate home-resolver consolidation). No contested finding silently dropped.
