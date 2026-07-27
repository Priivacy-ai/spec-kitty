---
affected_files: []
cycle_number: 2
mission_slug: tool-surface-contract-residuals-01KV4S5B
reproduction_command:
reviewed_at: '2026-06-15T06:27:22Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
---

# WP02 Review Feedback — Cycle 1

**Reviewer**: reviewer-renata  
**Date**: 2026-06-15  
**Status**: Changes requested

---

## Summary

The squad-hardened DoD items (per-code emit tests, manifest round-trip, legacy-read, two-hash distinction, model.py out-of-map edit, ruff/mypy, pre-existing failure) **all pass**. The implementation is correct and well-tested at the unit level.

However, **one blocking issue** prevents approval: `ProfileProjector.diagnose()` is a new public method with **zero production callers**, making it dead code in the production execution path. The WP02 Definition of Done requires `doctor tool-surfaces --kind agent-profile --json` to surface the new codes. That is impossible without wiring `diagnose()` into `AgentProfilesProvider`.

---

## Issue 1 — BLOCKING: `ProfileProjector.diagnose()` has no production callers (anti-pattern checklist item 1)

**What**: `ProfileProjector.diagnose(tool_key, project_root)` is declared public and exported in `profiles/__init__.py.__all__`, but no production code calls it. The `AgentProfilesProvider` (the only code that uses `ProfileProjector` in production) calls only `projector.project()` and `projector.render()` — never `diagnose()`.

**Evidence**: 
```
grep -rn "\.diagnose(" src/ --include="*.py" | grep -v test_
# → 0 results in production code
```

**Impact**: The four new finding codes (`profile-source-invalid`, `profile-name-invalid`, `profile-overlay-conflict`, `profile-sentinel-skipped`) exist and are correctly emitted by `diagnose()`, but they can never reach the `doctor tool-surfaces --kind agent-profile --json` output because the provider never calls `diagnose()`. This violates:

1. **Anti-pattern checklist item 1**: "every new public function has at least one live caller from production code — zero production hits means dead code."
2. **WP02 Definition of Done**: "`doctor tool-surfaces --kind agent-profile --json` surfaces the new codes."
3. **FR-001**: "emit the four mandated finding codes ... in the tool_surface agent-profile provider/projection path."

**How to fix**: Wire `projector.diagnose()` into `AgentProfilesProvider` so the new findings reach the doctor output. Two options — choose whichever fits the provider's architecture best:

**Option A — expand() collects diagnose() findings as synthetic sentinel instances**:
In `AgentProfilesProvider.expand()`, after building the normal projected instances, call `projector.diagnose(tool_key, project_root)` and attach findings to the provider output. This may require adding a diagnostic-instance type or augmenting `SurfaceStatus` to carry non-instance findings.

**Option B — add a `pre_scan()` / `diagnose()` hook to the provider protocol**:
If the provider protocol supports a scan-level hook separate from per-instance probe, implement it in `AgentProfilesProvider` by delegating to `projector.diagnose()`. This is the cleaner architectural seam if `doctor` can call it.

The simplest acceptable fix that satisfies both the anti-pattern checklist and the DoD is to have `AgentProfilesProvider.expand()` (or a new `diagnose()` method on the provider) call `projector.diagnose()` and return the findings in a discoverable way. The exact mechanism is implementation latitude — what matters is that `doctor tool-surfaces --kind agent-profile --json` can surface at least one of the new codes given a project with a triggering condition.

**Note**: `providers/agent_profiles.py` is not in WP02's current `owned_files`. Since this is a required fix to satisfy WP02's own DoD, an out-of-owned-files edit to `providers/agent_profiles.py` is justified (same rationale as the model.py edit — the provider is the caller WP02's new API requires). Document the rationale in the commit message.

---

## Passing Items (for the record)

All squad-hardened DoD checks passed:

- **Per-code emit tests drive real conditions**: each of the 4 tests constructs a real triggering input (invalid YAML, actual overlay conflict via built-in + invalid project override of `architect-alphonso`, sentinel in the built-in repo, illegal-id profile injected via test seam) and asserts the code is in the emitted `SurfaceFinding` list. None is a dead-constant assertion. PASS.
- **profile-sentinel-skipped recorded as info**: `test_diagnose_emits_profile_sentinel_skipped` asserts `f.severity == SEVERITY_INFO` for all sentinel findings. PASS.
- **Names verbatim**: `PROFILE_SOURCE_INVALID = "profile-source-invalid"` etc. match `contracts/profile-findings-and-manifest.md` exactly. PASS.
- **Existing 3 codes unchanged**: `NATIVE_AGENT_PROFILE_MISSING`, `NATIVE_AGENT_PROFILE_DRIFT`, `PROFILE_PROJECTION_UNSUPPORTED` are untouched. PASS.
- **Manifest 8 fields, raw.get defaults, no except-swallowing**: `_opt_str`/`_opt_int` use `raw.get(key)` with explicit `None` defaults. No `except` blocks. PASS.
- **Named legacy 6-field fixture**: `test_load_legacy_six_field_entry_populates_with_none_provenance` writes a real JSON file and asserts the loaded entry is populated (not dropped) with `source_path/source_hash/projection_version = None`. PASS.
- **Two-hash distinction both directions**: `test_source_hash_change_is_independent_of_file_hash` and `test_file_hash_change_is_independent_of_source_hash` exercise both drift signals independently. PASS.
- **model.py out-of-map edit**: WP02's commit adds exactly 3 optional fields with `None` defaults to `NativeAgentProfile`. It does not revert WP01's `SurfaceFinding` deletion (WP01's deletion commit `9cdf624df` is already on lane-b). The edit is purely additive, conflict-free, and justified (the `NativeAgentProfile` dataclass is the manifest entry type that WP02's manifest provenance fields live in). PASS.
- **ruff clean**: `ruff check src/specify_cli/tool_surface/ tests/specify_cli/tool_surface/` → 0 issues. PASS.
- **mypy --strict clean on owned files**: `mypy --strict src/specify_cli/tool_surface/findings.py model.py profiles/ tests/specify_cli/tool_surface/profiles/` → 0 issues. The 7 mypy errors in `test_enums.py`, `test_plugin_bundle.py`, `test_managed_skills.py` are pre-existing on the mission base branch. PASS.
- **47/47 profiles tests green**. PASS.
- **test_doctor_skills_json_error_schema_stable failure pre-existing**: confirmed absent from WP02's commit history; predates the mission base branch (introduced in commit `3aaf618fd`). PASS.
- **SLF001 noqa in test_projection.py**: two narrowly-scoped `# noqa: SLF001 - test seam` annotations for `repo._profiles` and `repo._provenance` access in the name-invalid test. These are justified (private-attribute test seam access with inline rationale). PASS.

---

## Required Action

Wire `ProfileProjector.diagnose()` into `AgentProfilesProvider` so the four new finding codes are reachable via `doctor tool-surfaces --kind agent-profile --json`. Add at least one integration-level test that verifies a code (e.g. `profile-sentinel-skipped`) appears in doctor output for a project with a triggering condition. Re-submit for review-cycle-2.
