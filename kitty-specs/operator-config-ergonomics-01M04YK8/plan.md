# Implementation Plan: Operator Config & Install Ergonomics

**Branch**: `fix/operator-config-ergonomics` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/operator-config-ergonomics-01M04YK8/spec.md` · Design record: [design-record.md](./design-record.md)

## Summary

Introduce one kernel `${VAR}` expansion seam and a two-tier `.kitty.env` operator config file (loaded by a pre-import shim), make committed charter/manifest provenance store portable `${SPEC_KITTY_PACKS_ROOT}/built-in/...` tokens (never absolute paths), add a default-off rc release channel, and document it all (ADRs + a new Team Kitty (SaaS) architecture section). Delivered as one mission with hard-sequenced tranches WP0 → (WP1 ∥ WP2) → WP3 → WP4. Approach is settled by a 6-agent design squad + a 3-lens post-spec squad; see design-record.md and research.md.

## Technical Context

**Language/Version**: Python 3.11+ (existing CLI baseline)
**Primary Dependencies**: NONE added. The `.kitty.env` parser is hand-rolled stdlib (`os`, `pathlib`) — `python-dotenv` is explicitly NOT introduced. Reuses `packaging.version` (already present) for pre-release comparison. (Supply-chain posture: no registry/lifecycle-script exposure — see research.md §Supply-Chain.)
**Storage**: Files only — `.kittify/config.yaml` (single `env_file` pointer), `${SPEC_KITTY_HOME}/.kitty.env` + `<repo>/.kittify/.kitty.env` (KEY=VALUE), `charter.yaml` / `agent_profiles_manifest.json` (provenance tokens), `~/.spec-kitty/config.toml` (existing; no new store).
**Testing**: pytest (unit + integration), parametrized POSIX/Windows path resolution; architectural tests (`tests/architectural/`) for layering + terminology + no-absolute-path regression; ATDD-first (red before green) per WP.
**Target Platform**: CLI on Linux/macOS/Windows.
**Project Type**: single (Python package `src/`).
**Performance Goals**: pre-import load overhead ≤ completion-benchmark noise floor; no regression to the TAB-completion benchmark.
**Constraints**: DR-1 (one env read per var at kernel floor); kernel gains no upward imports; 0 secret values printed; 0 absolute pack paths in committed artifacts; scaffold must not seed `SPEC_KITTY_PACKS_ROOT`; `SPEC_KITTY_` naming prefix.
**Scale/Scope**: CLI-wide (~88 `os.environ.get` reads benefit from early seeding without modification); 2 provenance carriers; 2 migrations; 5 tranches.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** — PASS: one kernel `expand_env_template`, one shared path→token normalizer, DR-1 single env read per var; the env-file seeds `os.environ` and adds no readers.
- **Architectural alignment** — PASS: extends existing seams (`RuntimeRoot`, `kernel.paths`, `core/env` grammar, the `org_pack_config` expander) — no god-object; layering `kernel ← doctrine ← charter ← specify_cli` preserved and arch-gated; `.kittify` vs `.spec-kitty` dual-root preserved.
- **DDD + tiered rigour** — PASS: core surfaces (kernel expander, provenance emit/heal, migrations, secret redaction) get high rigour + focused tests; glue (docs, skill prose) lighter. Complexity ceiling ≤15; helpers extracted with tests.
- **ATDD-first** — PASS: each FR maps to acceptance scenarios (spec US1–US5); WPs implement red-first through pre-existing entry points.
- **Terminology adherence** — PASS: `SPEC_KITTY_` prefix (no bare `KITTY_*`), no `feature*` aliases, Mission canon; `test_no_legacy_terminology.py` before pushing prose.

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/operator-config-ergonomics-01M04YK8/
├── plan.md              # This file
├── spec.md              # Committed spec
├── design-record.md     # Converged design (ADR seed)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (env-file, expander, provenance, redaction, migration, channel)
└── checklists/requirements.md
```

### Source Code (repository root)

```
src/kernel/
├── env_expand.py            # NEW — expand_env_template(inject_defaults), token detector, default-injection registry, UnresolvedEnvTokenError
└── paths.py                 # CHANGED — get_packs_root_default() = get_built_in_pack_root().parent

src/doctrine/drg/
└── org_pack_config.py       # CHANGED — _expand_path_template delegates to kernel (inject_defaults=False; fail-loud preserved)

src/charter/
├── compiler.py              # CHANGED — provenance emit routes through the shared path→token normalizer (retire src/doctrine marker trim)
└── (manifest emit) src/specify_cli/tool_surface/profiles/manifest.py, projection.py, _paths.py  # CHANGED — same normalizer

src/specify_cli/
├── bootstrap/env_file.py    # NEW — pre-import loader (two-tier merge → single setdefault), KEY=VALUE parser, config.yaml env_file pointer resolve
├── __init__.py              # CHANGED — invoke loader before the import-time reads
├── core/env.py              # CHANGED (optional) — typed accessors reused; is_truthy unchanged
├── upgrade/migrations/
│   ├── m_*_heal_provenance_paths.py     # NEW — WP1 heal migration (idempotent)
│   └── m_*_provision_kitty_env.py       # NEW — WP2 provision migration (idempotent; gitignore/claudeignore; never seeds PACKS_ROOT)
├── runtime/doctor.py + doctor subcommands  # CHANGED — provenance-leak check, env-file config-health facet, rc-channel line (isolated per-check; #1623 campsite)
├── distribution/simple_index.py, compat/provider.py, core/upgrade_probe.py, compat/planner.py, cli/commands/upgrade.py  # CHANGED — channel-aware latest + pinned rc install
└── (redaction) core/ secret allowlist  # NEW — printable-var allowlist consulted by doctor/status/logs

docs/adr/3.x/                # NEW — 2 ADRs (env-seam+provenance+layering; rc-channel)
docs/architecture/           # NEW — Team Kitty (SaaS) section + interaction diagrams
docs/api/, docs/guides/, src/doctrine/skills/spk-team-*  # CHANGED — consumption docs + SOURCE skills

tests/
├── kernel/, charter/, doctrine/, specify_cli/upgrade/migrations/, doctor/, distribution/  # unit
├── integration/            # loader ordering, sync-opt-in via .kitty.env, channel behavior
└── architectural/          # no-absolute-path, layering, terminology, TEMPLATE_ROOT-gate regressions
```

**Structure Decision**: Single Python package. New code lands at the correct layer — the pure expander + `.parent` accessor in `src/kernel/` (floor, consumable by charter); the `.kitty.env` file-convention + shim in `src/specify_cli/`; provenance emit in `src/charter/` + the profile-manifest surface; two migrations under `src/specify_cli/upgrade/migrations/`. Docs/ADRs under `docs/`.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Kernel env-expansion seam
- **Purpose**: One default-injecting `${VAR}` expander at the kernel floor so charter and the CLI share a single expansion authority; fix the `.parent` token-base arithmetic.
- **Relevant requirements**: FR-006; C-001, C-002.
- **Affected surfaces**: `src/kernel/env_expand.py` (new), `src/kernel/paths.py` (`get_packs_root_default`), `src/doctrine/drg/org_pack_config.py` (delegate).
- **Sequencing/depends-on**: none (foundation).
- **Risks**: preserve `org_pack_config` fail-loud contract; no kernel upward imports (arch-gated).

### IC-02 — Pre-import `.kitty.env` loader + config pointer
- **Purpose**: Two-tier `.kitty.env` seeded into `os.environ` before any spec-kitty import; the single `config.yaml` `env_file` pointer; fail policy.
- **Relevant requirements**: FR-004, FR-004a, FR-005; C-004, C-006.
- **Affected surfaces**: `src/specify_cli/bootstrap/env_file.py` (new), `src/specify_cli/__init__.py` (invoke before line 36), config.yaml key handling.
- **Sequencing/depends-on**: IC-01 (uses the expander for the pointer).
- **Risks**: merge-order (per-repo over home, then single `setdefault`); beat import-time reads; locator recursion; stdlib-only for TAB budget.

### IC-03 — Portable provenance emit + heal + leak-check
- **Purpose**: Emit `${SPEC_KITTY_PACKS_ROOT}/built-in/...` tokens through one shared normalizer for both carriers; heal existing absolute paths; doctor leak-check.
- **Relevant requirements**: FR-001, FR-002, FR-003; C-003, NFR-003.
- **Affected surfaces**: `src/charter/compiler.py`, profile-manifest surface (`manifest.py`/`projection.py`/`_paths.py`), a heal migration, `runtime/doctor.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: re-bake footgun (PACKS_ROOT=abs at emit) — regression-gated; two emit sites must share one normalizer.

### IC-04 — Env-file provisioning + secret redaction + config-health doctor
- **Purpose**: Provision migration (seed/register/ignore, never PACKS_ROOT), fail-closed printable-var allowlist, doctor env-file health facet.
- **Relevant requirements**: FR-007, FR-008, FR-010 (config-health); C-003a, NFR-002, NFR-004.
- **Affected surfaces**: `m_*_provision_kitty_env.py` (new), secret allowlist module, `.gitignore`/`.claudeignore`, `runtime/doctor.py` (isolated check).
- **Sequencing/depends-on**: IC-02.
- **Risks**: idempotency; coordinate migration ordering with #3381; never seed PACKS_ROOT (TEMPLATE_ROOT gate); never print secret values.

### IC-05 — rc release channel (consumer slice)
- **Purpose**: Default-off `SPEC_KITTY_PRERELEASE`; pre-release-aware "latest"; pinned rc install command; doctor channel line.
- **Relevant requirements**: FR-009, FR-010 (channel line); C-005.
- **Affected surfaces**: `distribution/simple_index.py`, `compat/provider.py`, `core/upgrade_probe.py`, `compat/planner.py` (cache key), `cli/commands/upgrade.py`, `runtime/doctor.py`.
- **Sequencing/depends-on**: IC-02 (reads `.kitty.env`).
- **Risks**: never nag stable users; #3047 discovery interface (index + PEP 440 pre-release pattern); no `--pre` transitive blast (pin exact rc).

### IC-06 — Docs, ADRs, Team Kitty (SaaS) architecture
- **Purpose**: Two ADRs; new Team Kitty (SaaS) architecture section + interaction diagrams; consumption docs + SOURCE `spk-team-*` skills.
- **Relevant requirements**: FR-011; C-007; SC-006.
- **Affected surfaces**: `docs/adr/3.x/`, `docs/architecture/`, `docs/api/`, `docs/guides/`, `src/doctrine/skills/spk-team-*`, `CHANGELOG.md` (docs-specific fragment only), `pyproject.toml` (WP0 owns the version bump — see corrections).
- **Sequencing/depends-on**: IC-01..IC-05 (documents the shipped behavior).
- **Risks**: edit SOURCE skills not `.claude/` copies; terminology guard; ADR count fixed at 2 (SC-006).

## Post-Plan Squad Corrections (BINDING — override the IC details above)

Three lenses (architect-alphonso code-state, paula-patterns brownfield, planner-priti tasks-readiness). Code-state verified: all named surfaces exist; layering legal (`test_layer_rules.py:75`); `.parent` arithmetic correct; defect empirically proven (committed `charter.yaml:124` = linux path, `agent_profiles_manifest.json` = mac wheel path).

### PPC-1 — Doctor checks target `cli/commands/doctor.py` siblings, NOT `runtime/doctor.py`
`runtime/doctor.py::run_global_checks` feeds `spec-kitty agent status`, not `spec-kitty doctor`. The `doctor` command (`cli/commands/doctor.py`) is an orchestration shim; canonical pattern (campsite **#2059**, not the closed #1623) is one `_*_doctor.py` sibling per facet. Each new check → its own sibling file: `_provenance_doctor.py` (WP03), `_env_file_doctor.py` (WP04), `_channel_doctor.py` (WP05).

**Post-tasks correction (CRITICAL — paula/renata C1):** `doctor.py` uses MANUAL sibling wiring (per-sibling `import` + `@app.command` shell), so three lanes editing it would collide. Fix: **WP03 adds an auto-discovery registration seam** to `doctor.py` (loop over `_*_doctor.py`, call each `register(app)` — mirror `upgrade/migrations/__init__.py:18`). Then WP04/WP05 drop *self-registering* siblings and touch `doctor.py` **zero times**. WP04 and WP05 therefore **depend on WP03** (seam must exist), keeping WP04∥WP05 parallel but after WP03. Update contracts C-PRV-5 / C-SEC-1 / C-CHN-3 accordingly.

### PPC-2 — The shared normalizer is a 3-class classifier; retirement is surgical
`FR-001`'s normalizer must classify: (a) built-in-pack path (under `get_built_in_pack_root()`) → `${SPEC_KITTY_PACKS_ROOT}/built-in/...` token; (b) in-tree project/org path → repo-relative (preserve today's behavior); (c) out-of-tree non-pack path → absolute (preserve). Replace ONLY: charter catalog source at `compiler.py:1424/1447` and manifest source at `projection.py:56`. EXCLUDE and leave byte-unchanged: mission-template callers `compiler.py:1482/1494`, local-support decl `compiler.py:1279`, and manifest `output_path` (`manifest.py:112`, must stay repo-relative). Regression test asserts the excluded callers are byte-identical + a 3-class matrix at both switched sites.

### PPC-3 — Env-file home-tier + the 4th-resolver hazard
Home-tier resolves to the **state root** (`get_runtime_root().base` → `.spec-kitty` POSIX / `%LOCALAPPDATA%\spec-kitty` Windows), i.e. secrets-are-state. Contract `C-LDR-7` corrected to `.spec-kitty` (not `.kittify`). The stdlib-only pre-import shim MUST NOT fork a 4th home resolver: WP0 exposes a stdlib-safe kernel-floor state-root primitive that the shim and `get_runtime_root` both consume (single authority). **Deferred (recorded):** consolidating the 3 existing duplicate `SPEC_KITTY_HOME` resolvers (`kernel/paths.py:76`, `runtime/home.py:39`, `windows_paths.py:79`) beyond what WP0 needs → tracking issue, not folded here (campsite noted, not silently assumed done).

### PPC-4 — FR-010 shared ownership; NFR IC coverage; WP3 parallelism
- **FR-010 stays a SINGLE spec row** (the requirement-mapping tooling normalizes letter-suffixed IDs like `FR-010a` back to `FR-010`, so a split breaks validation). It has **two owning WPs** — WP04 (env-file health `_env_file_doctor.py`) and WP05 (channel line `_channel_doctor.py`); a requirement may map to multiple WPs. The *facet isolation* is physical (separate sibling FILES via the PPC-1 auto-discovery seam), not a requirement-ID split.
- IC coverage: **NFR-001/NFR-005 → IC-02**; **NFR-002 → IC-03 and IC-04** (both migrations).
- With PPC-1 physically isolating `doctor.py`, **WP3 (IC-05) depends only on WP0 (IC-02 loader) and is parallel-eligible with WP1/WP2** — corrected from the earlier WP2→WP3 serialization (which only existed to paper over the doctor collision). Graph: `WP0 → (WP1 ∥ WP2 ∥ WP3) → WP4`.

### PPC-5 — Migration ordering + import-purity + pyproject ownership
- Migrations self-register (`@MigrationRegistry.register` + glob discovery) → genuinely independent files, no shared-list edit. **Pinned `target_version`s (post-tasks M1):** heal = `m_3_2_7_heal_provenance_paths.py` `"3.2.7"`; provision = `m_3_2_8_provision_kitty_env.py` `"3.2.8"` (sorts after heal). Provision is the one on the consent axis → its ordering vs #3381's consent migration must be confirmed at implement time (bump provision's version above #3381's if needed). A test asserts heal(3.2.7) < provision(3.2.8) and provision-vs-#3381 order. Filenames match their `target_version` per convention.
- **Loader import-purity:** add an architectural test that `specify_cli.bootstrap.env_file`'s transitive import set contains no module performing import-time `os.environ` reads (may import only stdlib + `core.env`, itself verified side-effect-free).
- **`__init__.py` change hygiene (C-007):** **WP0** owns the `pyproject.toml` version bump + its own `CHANGELOG.md` line; other WPs use per-WP changelog fragments (or rationale-backed leeway). `env_file` key must sit outside the `extra="forbid"` pydantic sections (`doctrine/org_charter.py:112/136`).

### PPC-6 — Explicit IC→WP table (for /tasks)

| WP | ICs | FRs | Depends on |
|----|-----|-----|------------|
| WP0 | IC-01 + IC-02 | FR-004/004a/005/006; NFR-001/005 | — |
| WP1 | IC-03 | FR-001/002/003; NFR-002/003; C-003 | WP0 |
| WP2 | IC-04 | FR-007/008/010a; NFR-002/004; C-003a | WP0 |
| WP3 | IC-05 | FR-009/010b; C-005 | WP0 |
| WP4 | IC-06 | FR-011; C-007; SC-006 | WP0–WP3 |

Contract-inventory note: 3 contract files (`env-expander.md`, `kitty-env-loader.md`, `provenance-and-channel.md`) cover all C-EXP/LDR/PRV/SEC/CHN/MIG guarantees; the earlier "6 contracts" phrasing in Project Structure is superseded by this list.
