---
work_package_id: WP05
title: Consent index and resolution rule
dependencies:
- WP04
requirement_refs:
- FR-002
- FR-013
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_commit: 1dc38ea23ee04dbcabd5a56bb19e141163bbb497
created_at: '2026-07-28T13:54:16.365774+00:00'
subtasks:
- T014
- T015
- T016
history: []
execution_mode: code_change
tags: []
tracker_refs: []
authoritative_surface: src/specify_cli/sync/
create_intent:
- src/specify_cli/sync/consent.py
owned_files:
- src/specify_cli/sync/consent.py
- src/specify_cli/sync/config.py
---

# WP05 — Consent index and resolution rule

Supplies the join the predicate needs: consent is keyed by **resolved absolute path**
(`sync/config.py:216,233`) while events carry `project_uuid`. `project_uuid` appears nowhere in
`sync/config.py`, and identity lives only inside each checkout (`routing.py:64`).
`sync/project_identity.py` holds no mapping today.

## Decisions already made — do not re-litigate

- **Conflict rule**: two checkouts can share a `project_uuid` via a committed `.kittify/config.yaml`
  and hold opposite overrides. Rule is **deny if any checkout of the project is opted out**, encoded
  once, not re-derived per call site.
- **Absence denies** (FR-002), overriding the default-allow fall-through at `routing.py:87`. This is the
  inversion that actually closes the incident: the five leaked projects had *no* record.
- **Storage**: keep YAML, but backfill as a **single batched write**. `SyncConfig` setters are unlocked
  whole-file read-modify-writes (`config.py:198-234`) and the daemon writes the same file as an
  interactive `sync enable` — a lost record is now a silent delivery denial, not a cosmetic loss.
- **Unresolvable paths**: retain the path-keyed entry with an `unresolved` marker that WP07 renders and
  the predicate ignores, so reported state and enforced state agree (US2 scenario 3).
- **`enable_checkout_sync` fails loudly** when no uuid resolves (`routing.py:91` yields `None`), rather
  than writing a path-only record that silently never delivers.

## Definition of done

- Consent is grantable/revocable by slug or uuid **without standing in the checkout**.
- Tests assert on the resolver's public seam.
