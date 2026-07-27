---
work_package_id: WP02
title: Record the resolution in the ADR and stability contract
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: feat/relocate-saas-sync-flag-to-core
merge_target_branch: feat/relocate-saas-sync-flag-to-core
branch_strategy: Planning artifacts for this mission were generated on feat/relocate-saas-sync-flag-to-core. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/relocate-saas-sync-flag-to-core unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
phase: Phase 2 - Record resolution
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1350138"
history:
- at: '2026-07-04T18:15:54Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: docs/adr/3.x/2026-06-26-1-core-integration-boundary.md
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/adr/3.x/2026-06-26-1-core-integration-boundary.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Record the resolution (ADR + stability contract)

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Objective

Now that WP01 has closed the CORE↛INTEGRATION exemption and relocated the flag
reader, update the two documentation surfaces so they no longer describe a live
exemption or the old module location: the ADR and the stability contract. Sweep
**every** stale "single/one exemption" and `len(ALLOWLIST) <= 1` reference (the
post-plan gate found more than the obvious ones).

## Charter notes
- **Doctrine/prose edits** → run the terminology guard (`test_no_legacy_terminology`) before done (per CLAUDE.md pre-push rule).
- **Scoped testing**: only the two bounding tests below.

## Subtasks

### T008 — Update the ADR (FR-005)
`docs/adr/3.x/2026-06-26-1-core-integration-boundary.md` — sweep ALL now-stale references (verified locations, re-confirm live):
- **~:150-151** point 7 "Pins `len(ALLOWLIST) <= 1` … shrink (when issue #2252 lands)" → `== 0`; note #2252 has landed.
- **~:179** "Exactly **one** exemption existed at the time this mission merged." → reword to past-tense-accurate ("… existed when #2172 merged; resolved by #2252") or strike; do NOT leave a bare "Exactly one exemption" reading as current state.
- **~:181-183** Allowlist Exemptions table → mark the `readiness/coordinator.py` → `specify_cli.saas.rollout` row RESOLVED / remove it (the table is now empty); the row's inline `<= 1` goes with it.
- **~:238-240** the negative bullet "The single remaining allowlist entry (`readiness/coordinator.py` → `specify_cli.saas.rollout`) leaves one structural coupling in CORE…" → move to the resolved/positive section or strike it (ZERO entries now; sweep the "one structural coupling" tail too).
- **~:252-253** Confirmation item 2 "passes with exactly one allowlist entry" (wraps across the two lines) → "zero".
- **~:254-255** Confirmation item 3 → checked/done, referencing #2252 and the new home `core/saas_sync_config.py`.
- Add a one-line note acknowledging the intentional **shim-depth trade-off**: `tracker`/`sync` `feature_flags` → `saas/rollout.py` (retained shim) → `core/saas_sync_config.py`, kept to avoid churning the NFR-001 identity tests.

### T009 — Update the stability contract (FR-006) `[P]`
`kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/saas_rollout.md` (this is a small, justified **out-of-map edit** — the finalizer forbids `kitty-specs/` paths in `owned_files`; record the one-line rationale in the commit: "FR-006 contract update; kitty-specs path can't be an owned_file"):
- **~:3** `**Module**: \`src/specify_cli/saas/rollout.py\`` → `\`src/specify_cli/core/saas_sync_config.py\`` (canonical home), noting `saas/rollout.py` is now a re-export shim.
- **~:49** "made once in `saas/rollout.py`" → "made once in `core/saas_sync_config.py`, re-exported by `saas/rollout.py`".
- The Backwards-Compatibility-Shims section → add `saas/rollout.py` as a shim over the core home (alongside the `sync`/`tracker` feature_flags entries).
- Bump the contract version + add a "relocated by #2252" line.
- **Do NOT add a `yaml`/` ``` ` codeblock** — the file is intentionally prose-only and legacy-allowlisted; the round-trip test skips content validation for it, and adding a codeblock would opt it into validation. Keep it prose.

### T010 — Validate (scoped, leak-proof gate)
```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/contract/test_example_round_trip.py -p no:cacheprovider -q
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -p no:cacheprovider -q
# CROSS-LINE (-z) + broad pattern — the plain line-based grep MISSES "exactly one\nallowlist entry" (:252-253):
grep -nzoE "<= *1|single remaining|exactly one|at most one|one structural coupling" docs/adr/3.x/2026-06-26-1-core-integration-boundary.md \
  && echo "FAIL: stale exemption prose remains" || echo "ADR swept clean"
# structural assertions: the Allowlist-Exemptions table has no data rows, and confirmation items 2/3 read resolved.
```
Both tests green; the `-z` sweep returns nothing (no stale `<= 1`/"single remaining"/"exactly one"/"at most one"/"one structural coupling" survives, cross-line included); the exemptions table is empty and confirmation items 2/3 are marked resolved. Commit as `docs(WP02): record CORE-INTEGRATION exemption resolved (ADR + saas_rollout contract)`.

## Definition of Done
- ADR: every stale `<= 1`/"single/exactly one" reference swept; the exemption recorded resolved; the shim-depth note added; #2252 referenced.
- Contract: module location + semantics + shims updated; version bumped; still prose-only (no codeblock).
- `test_example_round_trip` + `test_no_legacy_terminology` green.

## Risks
- **Adding a codeblock to the contract** would opt it into round-trip validation → possible red. Mitigation: keep it prose (T009 note).
- **A missed stale ADR ref** leaves the ADR self-contradictory. Mitigation: the T010 grep gate.

## Reviewer guidance
Verify: no stale `<= 1`/"single remaining"/"exactly one" survives in the ADR; the contract names the new canonical home + the retained shim + a bumped version and stays prose-only; both scoped tests green; terminology guard passes (no forbidden terms introduced). This is a docs-only WP — confirm no code files were touched.

## Activity Log

- 2026-07-04T18:49:26Z – claude:opus:implementer-ivan:implementer – shell_pid=1331379 – Assigned agent via action command
- 2026-07-04T18:54:51Z – claude:opus:implementer-ivan:implementer – shell_pid=1331379 – Ready for review: ADR + saas_rollout contract record CORE-INTEGRATION exemption RESOLVED by #2252. --force used because T009 is the prompt-authorized FR-006 out-of-map edit to kitty-specs/082.../contracts/saas_rollout.md (finalizer forbids kitty-specs paths in owned_files; rationale in commit 0a11b96). Gates: test_example_round_trip 24 passed/3 skipped; test_no_legacy_terminology 3 passed; ADR -z cross-line sweep => 'ADR swept clean'; exemptions table empty; confirmation items 2/3 resolved; shim-depth note added; contract prose-only (0 fenced codeblocks); frozen disabled-message untouched.
- 2026-07-04T18:55:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=1350138 – Started review via action command
