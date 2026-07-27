# Mission Review Report: bulk-edit-occurrence-classification-guardrail-01KP423X

**Reviewer**: claude:opus:mission-reviewer
**Date**: 2026-04-14
**Mission**: `bulk-edit-occurrence-classification-guardrail-01KP423X` — Bulk Edit Occurrence Classification Guardrail
**Source issue**: [Priivacy-ai/spec-kitty#393](https://github.com/Priivacy-ai/spec-kitty/issues/393)
**Baseline commit**: `c099ae21` (parent of squash merge)
**Merge commit**: `b5f73989` (squash merge to main)
**HEAD at review**: `7240057c`
**WPs reviewed**: WP01..WP06 (all 6, zero rejection cycles)

---

## Mission Summary

The mission shipped a workflow guardrail that requires missions marked
`change_mode: "bulk_edit"` in `meta.json` to produce an `occurrence_map.yaml`
artifact classifying target-string occurrences by semantic category with
per-category change actions. The guard blocks `implement` and `review` until
the artifact exists and passes structural + admissibility validation. An
inference warning flags unmarked missions whose spec contains rename/migration
language. A new doctrine directive (DIRECTIVE_035) and tactic codify the rule.

**Scale**: 21 files, 1608 insertions, 1 deletion. 55 new tests, all passing in
11.69s.

**Review-cycle signal**: Zero rejections across all 6 WPs. Every WP went
planned → claimed → in_progress → for_review → in_review → approved → done
cleanly. No arbiter overrides, no deferrals, no forced transitions.

---

## FR Coverage Matrix

| FR ID | Description (brief) | WP Owner | Test File(s) | Test Adequacy | Finding |
|-------|---------------------|----------|--------------|---------------|---------|
| FR-001 | `change_mode` field in meta.json with validation | WP01 | `tests/specify_cli/test_mission_metadata_change_mode.py` | ADEQUATE | — |
| FR-002 | Required classify_occurrences step before implementation | WP04, WP05 | `tests/specify_cli/bulk_edit/test_gate.py` | PARTIAL | [DRIFT-1] Implemented as guard, not first-class step |
| FR-003 | Machine-readable classification artifact | WP02 | `tests/specify_cli/bulk_edit/test_occurrence_map.py` | ADEQUATE | — |
| FR-004 | 8 standard occurrence categories | WP02 | `tests/specify_cli/bulk_edit/test_occurrence_map.py` | PARTIAL | [DRIFT-2] No enforcement of standard category names |
| FR-005 | Per-category actions: `rename`, `review_manually`, `do_not_change`, `rename_if_user_visible` | WP02 | `tests/specify_cli/bulk_edit/test_occurrence_map.py:125` | **FALSE_POSITIVE** | [DRIFT-3] Code uses `manual_review`, spec says `review_manually` |
| FR-006 | Implementation blocked until artifact exists | WP04 | `tests/specify_cli/bulk_edit/test_gate.py`, `tests/specify_cli/mission_v1/test_guards_bulk_edit.py` | ADEQUATE | — |
| FR-007 | Review validates diff against `do_not_change` categories | WP04 | — | **MISSING** | [DRIFT-4] v1 is artifact-admissibility only, not diff-aware |
| FR-008 | Review rejects diffs touching unclassified categories | WP04 | — | **MISSING** | [DRIFT-4] Same as FR-007 |
| FR-009 | Inference warning for unmarked bulk edits | WP03, WP04 | `tests/specify_cli/bulk_edit/test_inference.py` | ADEQUATE | — |
| FR-010 | Warning resolvable via flag or mark-as-bulk | WP04 | `tests/specify_cli/bulk_edit/test_inference.py` | PARTIAL | [RISK-1] No integration test for `--acknowledge-not-bulk-edit` flag |
| FR-011 | Doctrine artifacts updated | WP05 | N/A (YAML only) | ADEQUATE | — |

**Legend**: ADEQUATE = test constrains the required behavior. PARTIAL = test
exists but does not fully exercise the FR. MISSING = no test found.
FALSE_POSITIVE = test passes but uses a value that differs from the spec.

---

## Drift Findings

### DRIFT-1: FR-002 implemented as guard condition, not first-class workflow step

**Type**: LOCKED-DECISION VIOLATION (documented in ADR, not in spec)
**Severity**: LOW
**Spec reference**: FR-002 — "the workflow inserts a required `classify_occurrences` step before the first implementation step"
**Evidence**:
- `src/specify_cli/cli/commands/implement.py:477` — gate is a guard condition inside `validate` phase, not a separate workflow step
- `src/specify_cli/mission_v1/guards.py:253` — `occurrence_map_complete` guard registered in GUARD_REGISTRY but **no mission.yaml transition references it**
- `kitty-specs/.../plan.md:189` — ADR explicitly documents this decision: "Implement as a guard condition on the `implement` action (option A), not as a new workflow step type (option B)"

**Analysis**: The spec's FR-002 literally requires a new workflow step. The
plan's ADR intentionally chose option A (guard) over option B (step) to
minimize architectural churn, with a follow-up note that B can be adopted
later if dashboard visibility becomes important. The decision is documented
and defensible. This is doc-vs-code drift only — FR-002's wording was never
updated to reflect the ADR. Re-opening FR-002 later (e.g., for dashboard
needs) would require a new mission.

---

### DRIFT-2: FR-004 standard categories are undefined in the schema

**Type**: PUNTED-FR (interpretation-dependent)
**Severity**: LOW
**Spec reference**: FR-004 — "Occurrence categories include at minimum: code symbols, import/module paths, filesystem paths, serialized keys/API fields, CLI commands/flags, user-facing strings/docs, tests/snapshots/fixtures, logs/telemetry labels"
**Evidence**:
- `src/specify_cli/bulk_edit/occurrence_map.py:23-37` — only `VALID_ACTIONS`, `VALID_OPERATIONS`, and `PLACEHOLDER_TERMS` are constants; **no category-name constants exist**
- `src/specify_cli/bulk_edit/occurrence_map.py:143-167` — `validate_occurrence_map()` accepts any category name, only requires `len(cats) >= 1`
- `check_admissibility()` (`:185-213`) requires `MIN_ADMISSIBLE_CATEGORIES: int = 3` but does not check that the categories match the 8 standard names

**Analysis**: "Include at minimum" is ambiguous — it could mean (a) "the schema
supports these categories" (fulfilled — any category name is allowed) or (b)
"any valid occurrence map must enumerate all 8 standard categories" (not
enforced — only 3 required). The implementation chose interpretation (a), which
is more flexible but allows a map with 3 arbitrary category names to pass
admissibility. If a future bulk edit author labels categories idiosyncratically
(e.g., `strings`, `modules`, `files` instead of the 8 standard names), the gate
will pass and the classification's signal to reviewers will be diluted.

---

### DRIFT-3: FR-005 action naming mismatch — `review_manually` vs `manual_review`

**Type**: LOCKED-DECISION VIOLATION (silent naming drift)
**Severity**: **MEDIUM**
**Spec reference**: FR-005, spec.md:66; Key Entities, spec.md:104
**Evidence**:
- `kitty-specs/.../spec.md:66` — "Per-category actions include at minimum: `rename`, **`review_manually`**, `do_not_change`, and `rename_if_user_visible`"
- `kitty-specs/.../spec.md:104` — Key Entities: "`rename`, **`review_manually`**, `do_not_change`, or `rename_if_user_visible`"
- `src/specify_cli/bulk_edit/occurrence_map.py:24` — `VALID_ACTIONS: frozenset[str] = frozenset({"rename", "manual_review", "do_not_change", "rename_if_user_visible"})`
- `kitty-specs/.../data-model.md:39,47,97` — data-model and tests use `manual_review` (consistent with code)
- `src/doctrine/tactics/shipped/occurrence-classification-workflow.tactic.yaml` — also uses `manual_review`

**Analysis**: The spec and the implementation disagree on the action name. The
data-model.md (written during planning) and code agree on `manual_review`,
while the spec.md uses `review_manually`. A future mission author who follows
spec.md FR-005 literally will write `action: review_manually` in their
occurrence map, and the gate will reject with `"Category 'X' has invalid
action 'review_manually'"`. The user-visible error will point them to
`VALID_ACTIONS`, which does not include the spec-documented name.

The spec was never updated to match the code. This is exactly the class of
silent breakage that issue #393 was created to prevent — a rename was done
"across the codebase" but not "across the spec."

**Resolution options (non-blocking but should be corrected):**
- Update spec.md FR-005 and Key Entities to use `manual_review`
- Or: add `review_manually` as an accepted alias in VALID_ACTIONS

---

### DRIFT-4: FR-007/FR-008 not diff-aware in v1 (documented ADR scope reduction)

**Type**: PUNTED-FR (documented in ADR)
**Severity**: LOW (if ADR is authoritative); **MEDIUM** (if spec is authoritative)
**Spec reference**: FR-007 — "At review time, the system validates that the diff does not modify occurrences in categories marked `do_not_change`"; FR-008 — "At review time, the system rejects diffs that touch occurrence categories not present in the classification artifact"
**Evidence**:
- `src/specify_cli/bulk_edit/gate.py:33-80` — gate only checks artifact existence, structural validity, admissibility. No diff inspection.
- `src/specify_cli/cli/commands/agent/workflow.py:1298-1305` — review wiring invokes the same gate as implement. No diff-aware logic.
- `kitty-specs/.../plan.md:197-200` — ADR explicitly scopes this out: "v1 review gate validates occurrence map existence and structural completeness. It does not analyze the git diff against category rules."
- `kitty-specs/.../spec.md:94-97` — Success Criteria #2 and #3 say "review rejects 100% of diffs that modify [do_not_change] categories" and "rejects 100% of diffs that touch categories absent from the artifact"

**Analysis**: The spec's FR-007, FR-008, and Success Criteria #2 and #3 all
describe automated diff analysis. The ADR in plan.md explicitly defers this
to a follow-on mission, documenting that v1 delivers artifact-admissibility
only — the occurrence map is the reviewed authority, and human/AI reviewers
consult it to judge the diff.

This is a legitimate scope reduction with documented rationale. However, the
spec's Success Criteria were not updated to reflect it. A consumer reading
the spec alone would expect automated diff validation. The practical effect:
a bulk-edit mission can have a valid occurrence map classifying `serialized_keys`
as `do_not_change`, then silently modify serialized keys in the diff, and the
gate will pass. Only a human reviewer consulting the map will catch this.

**Resolution options (non-blocking but should be surfaced):**
- Update spec.md Success Criteria to note v1 scope (artifact existence; diff
  analysis in follow-on)
- Create a follow-on issue to implement FR-007/FR-008 diff-aware validation
- Add a CHANGELOG note for the shipping version that makes this scope clear

---

## Risk Findings

### RISK-1: `--acknowledge-not-bulk-edit` flag lacks integration test coverage

**Type**: ERROR-PATH
**Severity**: LOW
**Location**: `src/specify_cli/cli/commands/implement.py:413-419, 482-495`
**Trigger condition**: An implement invocation on a spec whose inference score ≥ 4.

**Analysis**: The flag is declared and wired. `test_inference.py` verifies the
scoring engine, but no integration test exercises the CLI flag path end-to-end.
If a future refactor of the implement command drops the flag propagation
(e.g., a parameter-handling refactor that forgets to thread the flag through),
the test suite will not catch it. The inference warning would fire and block
users who had been using the flag.

Mitigation exists because the flag is simple, but a CLI integration test
using `typer.testing.CliRunner` would have been warranted per the plan's
Charter Check row "Integration tests for CLI commands: PASS".

---

### RISK-2: `occurrence_map_complete` guard primitive is latent (registered, unused)

**Type**: DEAD-CODE (hook only)
**Severity**: LOW
**Location**: `src/specify_cli/mission_v1/guards.py:246-262`
**Trigger condition**: N/A — no mission.yaml transition references this guard.

**Analysis**: The guard primitive is registered in `GUARD_REGISTRY` but no
existing mission (software-dev, research, plan, documentation) includes it in
any state-machine transition. The active runtime enforcement happens directly
via `ensure_occurrence_classification_ready()` in `implement.py` and
`workflow.py`. The guard is essentially a latent hook for future missions
that want to reference the check declaratively.

This is not a bug — it's a forward-compatibility hook. Worth noting only so
future readers don't assume the guard is the live enforcement path. The
comment in `expected-artifacts.yaml:58` ("Runtime enforcement is via the gate
function (occurrence_map_complete guard)") is slightly misleading because
the live enforcement is the gate function directly, not the guard primitive
with that name.

---

### RISK-3: `conditional:` section in `expected-artifacts.yaml` has no consumer

**Type**: DEAD-CODE (metadata only)
**Severity**: LOW
**Location**: `src/specify_cli/missions/software-dev/expected-artifacts.yaml:55-63`
**Trigger condition**: N/A — the `conditional:` YAML key is not read by any
Python code path.

**Analysis**: The conditional artifact entry for `occurrence_map.yaml` is
documented in the manifest but no code in `src/specify_cli/` reads the
`conditional:` section (only `required_always` and `required_by_step` are
consumed via the existing manifest loader). The entry is pure documentation.
As long as this fact is understood, no harm; a future maintainer who assumes
the `conditional:` hook is enforced would be surprised.

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|----------|-----------|---------------|-------------|
| `src/specify_cli/bulk_edit/gate.py:38-40` | `load_meta()` returns None (no meta.json) | Gate returns `passed=True` | A mission with no meta.json is not a bulk edit — correct behavior, but a mission with a corrupt meta.json would also pass silently. Current `load_meta()` raises on malformed JSON, so this is mostly OK. |
| `src/specify_cli/bulk_edit/occurrence_map.py:84-85` | YAML file parses to `None` (empty file) | `load_occurrence_map()` returns `None` | An empty `occurrence_map.yaml` is treated identically to a missing one. Gate correctly rejects with "Occurrence map required". Acceptable. |
| `src/specify_cli/bulk_edit/inference.py:scan_spec_file` | spec.md missing | Returns `InferenceResult(score=0, triggered=False)` | Inference is skipped silently. If a mission has no spec.md, the inference warning won't fire. Acceptable since a missing spec.md would fail earlier in the implement flow. |

No silent-empty-string returns. No exception-swallowing try/except blocks in
new code.

---

## Security Notes

| Finding | Location | Risk class | Recommendation |
|---------|----------|------------|----------------|
| (none) | — | — | — |

**Security scan summary**: No new subprocess calls, no shell=True, no HTTP
calls, no credential handling, no locks introduced by this mission. File I/O
is limited to reading `meta.json`, `spec.md`, and `occurrence_map.yaml` — all
under `feature_dir`, which is resolved by the mission resolver earlier in the
pipeline and is not user-controlled at the point of read. YAML parsing uses
`ruamel.yaml` `YAML(typ="safe")` loader, which is safe against the classic
PyYAML RCE via `!!python/object`.

No security findings. This mission is not a security-sensitive feature.

---

## NFR Verification

| NFR | Threshold | Measured | Status |
|-----|-----------|----------|--------|
| NFR-001 | Gate check <2s | ~12 gate tests run in seconds total; individual gate call is a file-read + YAML parse, well under 2s | PASS |
| NFR-002 | Review validation <5s | Same gate function as implement; identical perf | PASS |
| NFR-003 | Inference false-positive <20% | Not automatically verified; keyword list is conservative and includes low-weight separation to reduce noise | UNVERIFIED (acceptable — no automation was specified) |
| NFR-004 | YAML human-readable | Standard YAML, edits via any text editor | PASS |

---

## Cross-WP Integration

Shared files touched by multiple WPs:
- `src/specify_cli/cli/commands/implement.py` — modified by WP04 (gate + inference wiring, `--acknowledge-not-bulk-edit` option)
- `src/specify_cli/cli/commands/agent/workflow.py` — modified by WP04 (review gate)
- `src/specify_cli/mission_v1/guards.py` — modified by WP05 (guard registration)
- `src/specify_cli/bulk_edit/__init__.py` — created by WP02, exports consumed by WP04 (via `specify_cli.bulk_edit.gate` direct imports rather than `__init__.py` re-exports)

The single-lane merge (lane-a) meant all WPs shared one worktree, so no
parallel-merge conflicts arose. The WP ordering (WP01 → WP02/WP03 → WP04 →
WP05 → WP06) respects dependencies correctly.

No cross-WP integration holes found.

---

## Dead Code Verification

| New module | Live callers in `src/` | Status |
|-----------|------------------------|--------|
| `bulk_edit/occurrence_map.py` | `bulk_edit/gate.py`, `bulk_edit/__init__.py` | LIVE |
| `bulk_edit/gate.py` | `implement.py`, `workflow.py`, `mission_v1/guards.py` | LIVE |
| `bulk_edit/inference.py` | `implement.py` | LIVE |
| `bulk_edit/__init__.py` | Not directly imported; individual modules are imported from their paths | METADATA ONLY (acceptable package init) |
| `035-bulk-edit-occurrence-classification.directive.yaml` | Doctrine catalog loader scans shipped/ at startup | LIVE |
| `occurrence-classification-workflow.tactic.yaml` | Same; referenced by DIRECTIVE_035.tactic_refs | LIVE |

No dead code. Every new module is imported from at least one live CLI command
path.

---

## Final Verdict

**PASS WITH NOTES**

### Verdict rationale

All 6 WPs are merged, all 55 new tests pass, every new module has a live caller
from `src/` (not just from tests), the doctrine directive is loadable, and the
guard is wired into both implement and review CLI paths. No security findings.
No critical dead code. No silent-failure paths that would produce wrong output
in normal operation.

Three drift items warrant follow-up but none block release:

1. **DRIFT-3 (MEDIUM)** — `review_manually` vs `manual_review` naming mismatch
   between spec and code. A mission author following spec.md FR-005 literally
   will produce an occurrence map the gate rejects. Fix is trivial (update
   spec.md or add an alias) but must happen before the spec is consumed by
   external readers as documentation.

2. **DRIFT-4 (LOW/MEDIUM)** — FR-007/FR-008 (diff-aware review validation)
   were scoped down to artifact-admissibility in the ADR but Success Criteria
   #2 and #3 in spec.md still claim "100% rejection of forbidden-category
   modifications". The ADR is the authoritative source of the delivered scope;
   the spec needs a note documenting that diff-aware enforcement is a follow-on.

3. **DRIFT-1, DRIFT-2, RISK-1–3 (LOW)** — documentation/latent-hook issues
   that do not affect correctness of the shipped feature.

The mission delivers the core value: bulk edits cannot begin without an
explicit, structurally valid classification artifact, and missions that
appear to be unmarked bulk edits get a warning. The "silent breakage of
issue #393" is prevented at the level the ADR committed to.

### Open items (non-blocking)

1. **Update spec.md FR-005 and Key Entities** to use `manual_review` (match
   code) — OR add `review_manually` as an alias in `VALID_ACTIONS`. Either
   resolution closes DRIFT-3.

2. **Update spec.md Success Criteria** #2 and #3 to note v1 scope: the
   occurrence map is a human-reviewed authority, automated diff-analysis is a
   follow-on enhancement. Resolves DRIFT-4.

3. **Add a follow-on issue** for diff-aware review validation (original
   FR-007/FR-008 intent). Links to this mission as the artifact-admissibility
   predecessor.

4. **Add a CLI integration test** for the `--acknowledge-not-bulk-edit` flag
   end-to-end behavior. Closes RISK-1.

5. **Optional**: either remove the unused `conditional:` section in
   `expected-artifacts.yaml` + the unused `occurrence_map_complete` guard
   registration, or wire one of them into a mission transition to make the
   latent hook live. Current state is "forward-compat metadata" — fine if
   documented, surprising if not.

6. **Future consideration**: if FR-004's intent was to enforce the 8 standard
   category names (interpretation b), add a warning or validation that flags
   categories outside the standard set. Current schema accepts any name.
