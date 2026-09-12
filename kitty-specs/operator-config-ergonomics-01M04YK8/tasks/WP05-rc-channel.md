---
work_package_id: WP05
title: rc release channel (consumer slice)
dependencies:
- WP02
- WP03
requirement_refs:
- FR-009
- FR-010
planning_base_branch: fix/operator-config-ergonomics
merge_target_branch: fix/operator-config-ergonomics
branch_strategy: Planning artifacts for this mission were generated on fix/operator-config-ergonomics. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/operator-config-ergonomics unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
history:
- '2026-08-16: authored by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/distribution/
create_intent:
- src/specify_cli/core/channel.py
- src/specify_cli/cli/commands/_channel_doctor.py
- tests/specify_cli/distribution/test_prerelease_channel.py
- tests/specify_cli/compat/test_channel_aware_latest.py
- tests/specify_cli/cli/commands/test_channel_doctor.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/core/channel.py
- src/specify_cli/distribution/simple_index.py
- src/specify_cli/compat/provider.py
- src/specify_cli/core/upgrade_probe.py
- src/specify_cli/compat/planner.py
- src/specify_cli/cli/commands/upgrade.py
- src/specify_cli/cli/commands/_channel_doctor.py
- tests/specify_cli/distribution/test_prerelease_channel.py
- tests/specify_cli/compat/test_channel_aware_latest.py
- tests/specify_cli/cli/commands/test_channel_doctor.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro` (implementer) via `/ad-hoc-profile-load`.

## Objective
Add a default-off unstable/rc channel: opted-in operators get pre-release-aware "latest" and a pinned rc install command; stable users are never nagged onto an rc. Contracts: [../contracts/provenance-and-channel.md](../contracts/provenance-and-channel.md) (C-CHN-1..3). Deps: **WP02** (reads `SPEC_KITTY_PRERELEASE` from `.kitty.env`). Scope boundary: CI rc-cadence + publication stay in **#3047**; this WP owns the consumer read only.

## Branch Strategy
Base + merge target: `fix/operator-config-ergonomics`. Lane worktree from `lanes.json`.

## Subtasks

### T021 — Channel preference accessor (`core/channel.py`)
- `prerelease_enabled() -> bool`: env `SPEC_KITTY_PRERELEASE` via `core/env.is_truthy` (default off). Single read, resolved once and threaded down (mirror the DR-1 style). Since the loader (WP02) seeds `.kitty.env` into `os.environ`, no file read here — just the env read.

### T022 — Channel-aware "latest" (stable-only default)
- `compat/provider.py::PyPIProvider.get_latest` (`:193`): when opted in, compute highest from `payload["releases"].keys()` (incl. PEP 440 pre-releases) instead of stable `info.version`.
- `distribution/simple_index.py::_highest_version` (`:296`): gate the `not is_prerelease` filter on the channel.
- `core/upgrade_probe.py` (`_classify`/`probe_pypi`): channel-aware "latest" so an rc build stops reading as `AHEAD_OF_PYPI` when opted in.
- Default (unset) path unchanged — stable `info.version`.

### T023 — Pinned rc install + cache key
- `cli/commands/upgrade.py::_agent_check_payload` (`:179`): pass the (possibly-rc) `latest_version` as `target_version` to `build_upgrade_hint` → pinned `spec-kitty-cli==<rc>` (no `--pre`, avoids transitive prerelease blast).
- `compat/planner.py::_resolve_latest_version` (`:833`): fold the channel into the nag-cache key so switching channels re-probes.

### T024 — `_channel_doctor.py` sibling
- New `cli/commands/_channel_doctor.py` exposing `register(app)` — **self-registers via WP03's doctor auto-discovery seam; touches `doctor.py` ZERO times** (hence the WP03 dependency). Import shared infra from `_doctor_shared`. Reports the active channel (stable / prerelease-opt-in).

### T025 — Tests (C-CHN-1..3)
- `test_prerelease_channel.py`: C-CHN-1 (default off + newer rc on index → latest is stable, no advisory).
- `test_channel_aware_latest.py`: C-CHN-2 (opted in → newest PEP 440 pre-release surfaced; `upgrade_command == spec-kitty-cli==<rc>`).
- `test_channel_doctor.py`: C-CHN-3 (doctor reports channel).

## Definition of Done
- **RED-first**: write the failing C-CHN-1..3 tests before implementing.
- C-CHN-1..3 green; stable-channel default behavior byte-unchanged; no `--pre` in the emitted command.
- `ruff`/`mypy` clean.

## Reviewer guidance
- Verify the default-off guarantee: with `SPEC_KITTY_PRERELEASE` unset, a newer rc on the index produces NO advisory (regression-critical for stable users).
- Verify the install command pins `==<rc>` (not `--pre`).
- Verify the channel is a single read threaded down, not re-read at each of the ~6 sites.
