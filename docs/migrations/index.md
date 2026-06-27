---
title: Migrations
description: 'Migrations landing page: the unified home for the migration/shim ruleset and the back-compat shim registry relocated from architecture/2.x, plus their runtime readers.'
doc_status: active
updated: '2026-06-27'
---
# Migrations

Migration and shim rules for Spec Kitty cutovers.

This section is the unified home (Mission B, FR-001) for:

- **`06_migration_and_shim_rules.md`** — the migration/shim ruleset,
  relocated from `architecture/2.x/`.
- **`shim-registry.yaml`** — the back-compat shim registry. This is a
  runtime-read target (`compat/doctor.py`, `compat/registry.py`, the
  `doctor` remediation string); those readers were re-pointed here in WP01
  with a dual-read so old and new paths both resolve until the WP08 sweep.
