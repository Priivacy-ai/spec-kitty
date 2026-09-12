---
work_package_id: WP04
title: Provision migration + secret redaction + config-health doctor
dependencies:
- WP02
- WP03
requirement_refs:
- FR-007
- FR-008
- FR-010
planning_base_branch: fix/operator-config-ergonomics
merge_target_branch: fix/operator-config-ergonomics
branch_strategy: Planning artifacts for this mission were generated on fix/operator-config-ergonomics. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/operator-config-ergonomics unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
history:
- '2026-08-16: authored by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent:
- src/specify_cli/core/secret_redaction.py
- src/specify_cli/upgrade/migrations/m_3_2_8_provision_kitty_env.py
- src/specify_cli/cli/commands/_env_file_doctor.py
- tests/specify_cli/core/test_secret_redaction.py
- tests/specify_cli/upgrade/migrations/test_provision_kitty_env.py
- tests/specify_cli/cli/commands/test_env_file_doctor.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/core/secret_redaction.py
- src/specify_cli/upgrade/migrations/m_3_2_8_provision_kitty_env.py
- src/specify_cli/cli/commands/_env_file_doctor.py
- tests/specify_cli/core/test_secret_redaction.py
- tests/specify_cli/upgrade/migrations/test_provision_kitty_env.py
- tests/specify_cli/cli/commands/test_env_file_doctor.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro` (implementer) via `/ad-hoc-profile-load`.

## Objective
Provision `.kitty.env` on upgrade (never leaking secrets or flipping the TEMPLATE_ROOT gate), add a fail-closed secret-redaction allowlist, and a `spec-kitty doctor` env-file health sibling. Contracts: [../contracts/provenance-and-channel.md](../contracts/provenance-and-channel.md) (C-MIG-1/2, C-SEC-1/2) + [../contracts/kitty-env-loader.md](../contracts/kitty-env-loader.md). Deps: **WP02** (loader/config). Coordinate migration ordering with **#3381**.

## Branch Strategy
Base + merge target: `fix/operator-config-ergonomics`. Lane worktree from `lanes.json`.

## Subtasks

### T017 — Provision migration (`m_3_2_8_provision_kitty_env.py`, `target_version="3.2.8"`)
- BaseMigration. `apply`: create `<repo>/.kittify/.kitty.env` if absent — seed ONLY already-set `SPEC_KITTY_*` operator vars from `os.environ`/legacy config; **NEVER write `SPEC_KITTY_PACKS_ROOT`** (C-003a — an always-set PACKS_ROOT flips the `kernel/paths.py:324` TEMPLATE_ROOT gate); never invent secret values (blank template lines otherwise). Register `env_file: ${SPEC_KITTY_HOME}/.kitty.env` in `config.yaml` (ruamel round-trip, outside `extra="forbid"`). Append `.kittify/.kitty.env` to `.gitignore` AND `.claudeignore` (idempotent line-presence). Idempotent overall (`detect` false once done). **Distinct `target_version`** with an explicit tiebreak vs #3381's consent migration; a test asserts relative order.

### T018 — Secret redaction (fail-closed allowlist)
- `core/secret_redaction.py`: a `_PRINTABLE_VARS` allowlist (names safe to render) + `redact(mapping)` that returns names+presence for everything else, never values. Integrate at the doctor env-file facet (T019) and any `sync status`/log surface that renders env. Fail-closed: a var not on the allowlist is redacted.

### T019 — `_env_file_doctor.py` sibling
- New `cli/commands/_env_file_doctor.py` exposing `register(app)` — **self-registers via WP03's doctor auto-discovery seam; touches `doctor.py` ZERO times** (that is why this WP now depends on WP03). Import shared collect/render infra from `_doctor_shared` (do not duplicate). Reports: resolved env-file path, exists?, gitignored?, `SPEC_KITTY_HOME` source, and which governed vars are set + from which tier — **names/presence only, via the T018 allowlist, never values.**

### T020 — Tests
- `test_provision_kitty_env.py`: C-MIG-1 (idempotent), C-MIG-2 (no `PACKS_ROOT` seed + a TEMPLATE_ROOT-still-governs regression when the scaffold is present), gitignore/claudeignore lines added, ordering-vs-#3381 assertion.
- `test_secret_redaction.py`: C-SEC-1 (a non-allowlisted token never renders by value).
- `test_env_file_doctor.py`: env-file health output + C-SEC-2 (`.kitty.env` matches an ignore rule in both files).

## Definition of Done
- **RED-first**: write the failing C-MIG-1/2 + C-SEC-1/2 + env-file-doctor tests before implementing.
- C-MIG-1/2, C-SEC-1/2 + env-file-doctor green; idempotent; no secret value ever printed.
- Migration `target_version="3.2.8"` (distinct from WP03 heal `3.2.7`); the ordering test asserts heal(3.2.7) < provision(3.2.8) and provision sorts after #3381's consent migration (confirm #3381's version at implement time; bump if needed).
- `ruff`/`mypy` clean.

## Reviewer guidance
- Verify the migration NEVER seeds `SPEC_KITTY_PACKS_ROOT` and the TEMPLATE_ROOT-gate regression is present.
- Verify the allowlist is fail-CLOSED (new secret var → redacted by default).
- Verify `.kitty.env` lands in BOTH `.gitignore` and `.claudeignore`.
