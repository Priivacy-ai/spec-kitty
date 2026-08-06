---
affected_files: []
cycle_number: 1
mission_slug: supply-chain-security-checks-layer-01KZBFBS
reproduction_command:
reviewed_at: '2026-08-06T20:46:56Z'
reviewer_agent: user
verdict: rejected
wp_id: WP03
---

**Issue 1 (blocking)**: Stale golden-count literal in `tests/doctrine/test_pack_relocation_preflight.py::test_baseline_smoke_counts`.

- This WP's changes correctly bumped the DRG's edge count from 900 to 916 (16 new `requires` edges from the 7 targeted profiles to `directive:DIRECTIVE_047` / `tactic:dependency-hygiene` / `tactic:supply-chain-install-safety`), and the fixture `tests/doctrine/fixtures/graph-identity.baseline.json` was correctly regenerated to reflect this.
- However, `tests/doctrine/test_pack_relocation_preflight.py` line 164 still asserts `assert len(baseline["edges"]) == 900`, reading the very same `graph-identity.baseline.json` fixture that this WP updated. This assertion was NOT updated (confirmed via `git diff <WP01-tip>..<WP03-tip> -- tests/doctrine/test_pack_relocation_preflight.py` — zero diff — while the fixture it reads changed under it).
- Verified failing on the current lane HEAD: `./.venv/bin/python -m pytest tests/doctrine -q` → `1 failed, 2571 passed, 8 skipped` with:
  ```
  FAILED tests/doctrine/test_pack_relocation_preflight.py::test_baseline_smoke_counts
  AssertionError: assert 916 == 900
  ```
  This is a real, WP03-attributable regression, not a pre-existing/environment issue (the implementer's own re-baselining sweep of `test_pack_relocation_doctor_gate.py` and `test_pack_relocation_identity.py` correctly bumped their 900→916 / 326-900→326-916 references — this sibling file in the same "pack relocation" family was simply missed).
- **Fix**: update line 164 to `assert len(baseline["edges"]) == 916  # golden-count: cardinality-is-contract`. The node-count line (326) is already correct and needs no change.

**Issue 2 (non-blocking, cleanup)**: `tests/doctrine/test_packaging_parity.py:157` has a comment `# full-graph (326/900) proof from a clean install lives in WP07. Here we assert` that is now stale (should read `326/916`) given the graph moved. It's a comment, not an assertion, so it does not fail CI, but please update it for consistency while you're re-baselining Issue 1's file, since both live in the same "pack relocation / packaging" test family this WP already touched other members of.

---

## Acceptance criteria checklist

1. No new persona/profile introduced (only the 7 targeted profiles enhanced) — **PASS**
2. `reviewer-renata.agent.yaml` (T009): directive `047` + tactic `supply-chain-install-safety` references present; adversarial-evidence disposition vocabulary (`accepted`/`changed`/`deferred_with_rationale`, each traceable to `evidence_location`) matches `adversarial-evidence-contract.md` verbatim, not a paraphrase — **PASS**
3. `implementer-ivan`/`node-norris`/`frontend-freddy` (T010): directive/tactic layer referenced; `node-norris`/`frontend-freddy` carry Node Active-LTS / npm registry-check posture (explicit `npm view ... && node --version` gate commands) — **PASS**
4. `python-pedro`/`java-jenny`/`architect-alphonso` (T011): each scoped to its own ecosystem (PyPI/pip-uv, Maven Central/Gradle, ADR-level architectural framing respectively) — not a copy-pasted generic block — **PASS**
5. `agent_profile.graph.yaml` (T012): all new edges use well-formed `<kind>:<id>` URNs (`agent_profile:X` → `directive:DIRECTIVE_047` / `tactic:dependency-hygiene` / `tactic:supply-chain-install-safety`), scoped only to the 7 targeted profiles, targets are pre-existing WP01 nodes (no orphans) — **PASS**
6. Each profile's primary role/persona unchanged — all diffs are pure additions (no deletions to `purpose`, `role`, etc.) — **PASS**
7. DRG/golden-count baseline files updated consistently and match the live shipped graph — **FAIL** (see Issue 1). The `graph-identity.baseline.json` fixture itself is correct and byte-identical to the regenerated live graph (`test_pack_relocation_identity.py`'s exact-projection-equality test passes), but a sibling smoke-check test pinning the same fixture's cardinality was left stale.
8. No changes outside WP03's owned scope — confirmed via `git show <WP03-commit> --stat`: only the 7 owned profile YAMLs + `agent_profile.graph.yaml` + expected shared re-baselining touches (`graph-identity.baseline.json`, golden-count test literals in `test_reachability.py`/`test_extractor_projection.py`/`test_unknown_kind_fails_loudly.py`/`test_no_authored_applies_edge.py`/`test_loader_fail_closed.py`/`test_pack_relocation_doctor_gate.py`/`test_pack_relocation_identity.py`/`test_shipped_profiles.py`, plus 1-line golden-count docstring syncs in `docs/architecture/doctrine-relationships.md` and `src/doctrine/drg/models.py`). No WP01/02/04/05-owned files (directive/tactic content, action indexes, step-contracts, `action.graph.yaml`, SOURCE mission-step prompts) touched — **PASS**
9. Terminology canon compliance — spot-checked all touched YAML/docs prose; the one "feature reviews" occurrence in `reviewer-renata.agent.yaml` is pre-existing unchanged context, not a new line — **PASS**

## Verification run

- `./.venv/bin/python -m pytest tests/doctrine -q` → **1 failed, 2571 passed, 8 skipped, 84 warnings** (exit code 0 reported by shell wrapper, but pytest reported 1 FAILED — see Issue 1). No `test_hatch_build.py` collection error was observed in this run (that CLI-gate artifact did not reproduce here).
- `./.venv/bin/python -m pytest tests/doctrine/drg/migration/test_extractor_projection.py tests/doctrine/drg/test_unknown_kind_fails_loudly.py tests/architectural/test_no_authored_applies_edge.py tests/doctrine/drg/test_reachability.py tests/doctrine/test_shipped_profiles.py -q` → **332 passed**, exit code 0.
- `./.venv/bin/python -m ruff check <9 changed .py files>` → **All checks passed**, exit code 0.
- `spec-kitty@head doctor doctrine --json` → `profile_health.healthy: true`, builtin pack `discovered_count: 18, valid_count: 18, invalid_profiles: []` — zero skipped/invalid profiles.
- `git diff <WP01-tip>..<WP03-tip> -- tests/doctrine/test_pack_relocation_preflight.py` → empty (confirms the stale-literal file was untouched by this WP despite the fixture it reads changing).
- `git status --short` in the lane worktree → clean.

## Please fix and resubmit

Update `tests/doctrine/test_pack_relocation_preflight.py:164` (900→916) and, ideally, the stale comment in `tests/doctrine/test_packaging_parity.py:157` (326/900→326/916), then re-run `./.venv/bin/python -m pytest tests/doctrine -q` to confirm a fully green suite before resubmitting for review. Everything else in this WP (profile content, graph edges, scope, terminology) is solid.
