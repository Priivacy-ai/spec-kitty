# Tasks: Operator Config & Install Ergonomics

**Mission**: operator-config-ergonomics-01M04YK8 · **Branch**: `fix/operator-config-ergonomics`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) (IC→WP table = PPC-6) · **Design**: [design-record.md](./design-record.md)

Dependency graph: `WP01 → {WP02, WP03}`, `{WP02, WP03} → {WP04, WP05}`, `{WP01..WP05} → WP06`.
Parallelism: WP02 ∥ WP03 (after WP01); WP04 ∥ WP05 (after WP02 AND WP03 — WP04/WP05 depend on WP03 for the doctor auto-discovery seam so their `_*_doctor.py` siblings self-register without editing `doctor.py`; post-tasks squad fix).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | `get_packs_root_default()` = `get_built_in_pack_root().parent` + kernel state-root primitive | WP01 | |
| T002 | `kernel/env_expand.py`: `expand_env_template(inject_defaults)`, token detector, `UnresolvedEnvTokenError` | WP01 | |
| T003 | Default-injection registry: `${SPEC_KITTY_PACKS_ROOT}` → `get_packs_root_default()` | WP01 | |
| T004 | `org_pack_config._expand_path_template` delegates (`inject_defaults=False`); fail-loud preserved | WP01 | |
| T005 | Tests C-EXP-1..5 (+ kernel-no-upward-import arch test) | WP01 | |
| T006 | `bootstrap/env_file.py`: KEY=VALUE parser, two-tier discovery, `{**home,**repo}` + one `setdefault` | WP02 | |
| T007 | `config.yaml` `env_file` pointer read + single expansion (outside `extra="forbid"`) | WP02 | |
| T008 | Fail policy: absent→warn, unreadable→loud, malformed→skip, locator-recursion→ignore | WP02 | |
| T009 | Wire loader as first statements of `specify_cli/__init__.py` (before line 36) | WP02 | |
| T010 | Tests C-LDR-1..7 + import-purity arch test | WP02 | |
| T011 | `doctrine/provenance.py`: 3-class path→token normalizer | WP03 | [P] |
| T012 | Route charter catalog source (`compiler.py:1424/1447`) through normalizer; retire marker-trim for catalog only | WP03 | [P] |
| T013 | Route manifest source (`projection.py:56`) through normalizer; leave `output_path` repo-relative | WP03 | [P] |
| T014 | Heal migration (both carriers; idempotent) | WP03 | [P] |
| T015 | `_provenance_doctor.py` sibling — leak-check | WP03 | [P] |
| T016 | Tests C-PRV-1..6 (re-bake gate, invariance, heal idempotent, 3-class matrix, excluded-callers byte-unchanged) | WP03 | [P] |
| T017 | Provision migration: seed (never PACKS_ROOT), register pointer, gitignore+claudeignore; distinct `target_version` vs #3381 | WP04 | [P] |
| T018 | Secret redaction fail-closed allowlist + integration into doctor/status/logs | WP04 | [P] |
| T019 | `_env_file_doctor.py` sibling — env-file health (names only) | WP04 | [P] |
| T020 | Tests C-MIG-1/2 (idempotent, no-PACKS_ROOT-seed + TEMPLATE_ROOT gate), C-SEC-1/2 | WP04 | [P] |
| T021 | Channel preference accessor (`SPEC_KITTY_PRERELEASE`, default off, single-read) | WP05 | [P] |
| T022 | Channel-aware "latest" (provider/simple_index/upgrade_probe) — stable-only default | WP05 | [P] |
| T023 | Pinned rc install command (`==<rc>`) + planner cache-key includes channel | WP05 | [P] |
| T024 | `_channel_doctor.py` sibling — channel line | WP05 | [P] |
| T025 | Tests C-CHN-1..3 | WP05 | [P] |
| T026 | ADR: env-resolution seam + provenance form + layering | WP06 | |
| T027 | ADR: default-off rc channel | WP06 | |
| T028 | Team Kitty (SaaS) architecture section + interaction diagram | WP06 | |
| T029 | Consumption docs (env-vars, configuration, install/upgrade, sync-drain/consent/readiness) + SOURCE `spk-team-*` skills | WP06 | |
| T030 | `CHANGELOG.md` entry | WP06 | |

## Work Packages

### WP01 — Kernel env-expansion seam (IC-01) · prompt: [tasks/WP01-kernel-env-expansion-seam.md](./tasks/WP01-kernel-env-expansion-seam.md)
Goal: one kernel `${VAR}` expander (two policies) + `get_packs_root_default` + state-root primitive; `org_pack_config` delegates. **Priority: P1 (foundation).** Independent test: C-EXP-1..5. Deps: none. Subtasks T001–T005 (~5). ~260 lines.

### WP02 — Pre-import `.kitty.env` loader + config pointer (IC-02) · prompt: [tasks/WP02-kitty-env-loader.md](./tasks/WP02-kitty-env-loader.md)
Goal: two-tier `.kitty.env` seeded pre-import (merge→setdefault); single `config.yaml` pointer; fail policy. **Priority: P1.** Independent test: C-LDR-1..7. Deps: WP01. Subtasks T006–T010 (~5). ~300 lines.

### WP03 — Portable provenance emit + heal + leak-check (IC-03) · prompt: [tasks/WP03-portable-provenance.md](./tasks/WP03-portable-provenance.md)
Goal: 3-class shared normalizer; token emit for both carriers; heal migration; provenance doctor. **Priority: P1 (US1).** Independent test: C-PRV-1..6. Deps: WP01. Subtasks T011–T016 (~6). ~320 lines.

### WP04 — Provision migration + secret redaction + config-health doctor (IC-04) · prompt: [tasks/WP04-provision-and-secrets.md](./tasks/WP04-provision-and-secrets.md)
Goal: provision migration (never seeds PACKS_ROOT), fail-closed secret allowlist, env-file health doctor. **Priority: P1 (US2/US4).** Independent test: C-MIG/C-SEC. Deps: WP02. Subtasks T017–T020 (~4). ~250 lines.

### WP05 — rc release channel consumer slice (IC-05) · prompt: [tasks/WP05-rc-channel.md](./tasks/WP05-rc-channel.md)
Goal: default-off channel; pre-release-aware latest; pinned rc install; channel doctor. **Priority: P2 (US3).** Independent test: C-CHN-1..3. Deps: WP02. Subtasks T021–T025 (~5). ~270 lines.

### WP06 — Docs, ADRs, Team Kitty (SaaS) architecture (IC-06) · prompt: [tasks/WP06-docs-adr-saas.md](./tasks/WP06-docs-adr-saas.md)
Goal: 2 ADRs; Team Kitty (SaaS) section + interaction diagram; consumption docs + SOURCE skills; CHANGELOG. **Priority: P3 (US5).** Independent test: SC-006. Deps: WP01–WP05. Subtasks T026–T030 (~5). ~240 lines.

## MVP

WP01 + WP02 + WP03 = the portable-provenance + config-seam core (US1 ships; US2 opt-in enabled). WP04/WP05/WP06 complete the operator experience.
