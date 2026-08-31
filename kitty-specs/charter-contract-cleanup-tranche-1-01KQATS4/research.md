# Phase 0 Research — Charter Contract Cleanup Tranche 1

**Mission:** `charter-contract-cleanup-tranche-1-01KQATS4`
**Spec:** [spec.md](./spec.md)

This document records the resolved technical decisions that drive the design artifacts in Phase 1. Each entry follows: **Decision → Rationale → Alternatives considered**.

---

## R-001 — JSON envelope strictness placement (FR-001)

**Decision:** When `--json` is set, `charter synthesize` emits exactly one JSON document to stdout. Evidence warnings live in the JSON envelope's `warnings` array. Human-readable progress remains permitted on stderr.

**Rationale:**

- A strict-stdout contract means callers can pipe `... --json` straight into `json.loads(...)` without preprocessing. This is the contract the test gate (NFR-001 → `tests/integration/test_json_envelope_strict.py`) is designed to assert.
- Putting warnings inside the envelope (rather than stderr) keeps a single source of truth for callers that already inspect the JSON. Stderr-only warnings would force every consumer to wire up two streams.
- Avoids the bug that triggered FR-001: warnings printed via `console.print` (or `print`) before the JSON branch broke `json.loads(stdout)`.

**Alternatives considered:**

- **Stderr-only warnings.** Cleaner separation, but loses warnings for any caller that captures only stdout (which is the majority of programmatic callers). Rejected.
- **Sentinel-prefixed lines on stdout.** Would require every consumer to filter; defeats the "strict JSON" contract. Rejected.
- **Multiple JSON documents (NDJSON-style).** Breaks `json.loads` for the success case and complicates the envelope contract. Rejected.

**Implementation cue (informational only):** The `json_output` branch in `src/specify_cli/cli/commands/charter.py` currently calls `console.print` for `evidence_result.warnings` before reaching the JSON branch. The fix is to gather warnings into a list and pass them into the envelope builder. Anything left going to stdout outside the JSON document is a contract violation.

---

## R-002 — Synthesis envelope contract (FR-002, FR-003)

**Decision:** The success envelope produced by `charter synthesize --adapter fixture --json` (and by every other `--json` success path) carries the following stable fields:

| Field | Required | Description |
|---|---|---|
| `result` | yes | Stable string (`"success"`, `"failure"`, `"dry_run"` for dry-run) |
| `adapter` | yes | Object with `id` (string) and `version` (string) |
| `written_artifacts` | yes | Array of objects (see R-003) describing each artifact actually staged or promoted; may be `[]` |
| `warnings` | yes | Array of strings; may be `[]` |
| Legacy compatibility fields | optional | Existing `target_kind`, `target_slug`, `inputs_hash`, `adapter_id`, `adapter_version` may remain alongside the contracted set |

The four contracted fields are emitted unconditionally; tests assert their presence and shape, not just `result == "success"`.

**Rationale:**

- The four-field shape is the contract the brief and downstream test fixtures already expect; adding it stops every consumer from having to introspect adapter-specific keys.
- Permitting legacy fields keeps backward compatibility with any caller currently reading them (low blast radius).
- An empty list for `written_artifacts` and `warnings` is meaningfully different from a missing field; preserving the field always lets callers branch on length without optional-key handling.

**Alternatives considered:**

- **Strip legacy fields immediately.** Cleaner schema but introduces a consumer-visible breaking change for fields like `inputs_hash` that may be referenced externally. Rejected for this tranche; revisit when contract is fully cut over.
- **`written_artifacts` as `list[str]` of paths only.** Loses the kind/slug/artifact_id provenance that callers (and the dry-run/parity check, FR-004) depend on. Rejected. See R-003.

---

## R-003 — `written_artifacts` element shape and sourcing

**Decision:** Each entry in `written_artifacts` is an object. Required keys per element:

| Key | Type | Description |
|---|---|---|
| `path` | string | Repo-relative path of the staged-or-promoted artifact (the path the non-dry-run actually writes / wrote) |
| `kind` | string | Doctrine kind (`directive`, `tactic`, `styleguide`, etc.) |
| `slug` | string | Slug component used in the filename |
| `artifact_id` | string \| null | Concrete artifact identifier (e.g. `PROJECT_001`, `DIRECTIVE_NEW_EXAMPLE`) when one exists; `null` for kinds that do not carry an ID |

Sourcing rule: every element is derived from a typed staged-artifact entry returned by the synthesizer's write pipeline (`src/charter/synthesizer/write_pipeline.py`) — never reconstructed from `kind:slug` selectors or any other lossy projection.

**Rationale:**

- The non-dry-run already routes every write through `PathGuard` and the staged-and-promoted manifest (per the existing KD-2 atomicity model documented in `write_pipeline.py`). Returning a typed list of those entries to the CLI lets us populate `written_artifacts` from the same source of truth.
- Including `path`, `kind`, `slug`, and `artifact_id` together is what enables the dry-run/non-dry-run path-parity check (FR-004) without a second lookup.
- Avoids the subtle bug class where `--json` reports "directive PROJECT_005" but the live tree wrote a different filename because the path reconstruction used a different rule.

**Implementation cue (informational only):** If `promote(...)` and the staging pipeline already return the manifest entries with content hashes and target paths, exposing them upward to the CLI may be a one-call addition. If they don't, FR-003 explicitly authorises extending the staged-artifact return shape in `write_pipeline.py`.

---

## R-004 — Dry-run / non-dry-run path parity (FR-004, FR-005)

**Decision:** The `--dry-run --json` envelope reports `written_artifacts` whose `path` and `artifact_id` are byte-equal to what a subsequent non-dry-run with the same `SynthesisRequest` would write. Both code paths derive the list from the same staged-artifact entries; no reconstruction step is allowed in the dry-run branch. The placeholder string `PROJECT_000` is internal-only — it never appears in any user-visible CLI output, JSON value, log message, or error message.

**Rationale:**

- This is the only shape that makes a dry-run useful as a preview. If the dry-run shows `PROJECT_000/foo.directive.yaml` but the real run writes `PROJECT_005/foo.directive.yaml`, the dry-run is actively misleading and the bug is invisible until production.
- A single derivation function (one source of truth for both branches) is cheaper than two parallel implementations and removes the drift class entirely.

**Alternatives considered:**

- **Display `PROJECT_000` with a note.** Users still have to mentally translate; dry-run loses its purpose. Rejected.
- **Emit a sentinel field for "preview vs real".** Adds surface area without solving the parity problem. Rejected.

**Test cue:** A new test fixture must construct a `SynthesisRequest` whose provenance yields a non-placeholder ID (e.g. `PROJECT_001`). Two assertions:
1. The dry-run envelope reports the expected target path.
2. A real run emits a `written_artifacts[*].path` byte-equal to that same path.

---

## R-005 — Golden-path E2E prompt-file assertion (FR-006, FR-007)

**Decision:** In `tests/e2e/test_charter_epic_golden_path.py`, the per-envelope assertion logic becomes:

```
for envelope in lifecycle_envelopes:
    if envelope.kind == "step":
        prompt = envelope.prompt_file_or_documented_equivalent()
        assert prompt is not None and prompt != ""
        assert resolves_to_existing_file(prompt, test_project_root)
    elif envelope.is_blocked_decision():
        reason = envelope.reason
        assert reason is not None and reason.strip() != ""
    else:
        # other envelope kinds keep their existing assertions
```

The "documented public equivalent" is the field the runtime currently emits; the test reads whatever stable name the runtime contract guarantees rather than guessing at internal structure. If the runtime emits more than one stable field, the assertion is "at least one of them carries a resolvable prompt file."

**Rationale:**

- FR-006 and FR-007 are the issue the user opened in `#844`. Asserting *presence* of `prompt_file` was the partial fix; *resolvability* is the load-bearing assertion that catches the regression class where a prompt path is computed but the file doesn't exist on disk.
- Allowing blocked decisions to substitute a `reason` mirrors the runtime contract: a blocked decision intentionally has no prompt, so failing it for missing prompt would be wrong.

**Alternatives considered:**

- **Snapshot-test the entire envelope.** Brittle; every legitimate runtime change cracks the test. Rejected.
- **Assert prompt path is absolute.** Too restrictive; relative paths under the test project are normal. Replaced with "resolves to an existing file."

---

## R-006 — `mypy` availability in `e2e-cross-cutting` (FR-008, decision_id `01KQAVR8S1299R9N67BTFAD67Q`)

**Decision (resolved):** Install the `lint` extra in the `e2e-cross-cutting` job so `python -m mypy` is on PATH. Concretely, replace `pip install -e .[test]` with `pip install -e .[test,lint]` in `.github/workflows/ci-quality.yml`. The test (`tests/cross_cutting/test_mypy_strict_mission_step_contracts.py`) is then exercising the strict-typing contract it was designed to enforce, in CI, on every push.

**Rationale:**

- The charter explicitly lists `mypy --strict` as a required policy and `mypy>=1.10.0` already lives in the `lint` extra.
- The test docstring already names the requirement: *"this test invokes mypy via sys.executable -m mypy, which requires the lint extra to be installed."* The job environment, not the test, is the broken party.
- Skipping silently weakens coverage; failing actionably just relocates the failure without buying coverage.

**Alternatives considered (per the decision options):**

- **`skip_with_clear_message`.** Cheaper CI minutes but leaves a hole in the strict-typing signal. Rejected.
- **`fail_with_actionable_error`.** Shifts the failure mode without buying coverage. Rejected.

**Implementation cue (informational only):** The change is a single line in the install step of the `e2e-cross-cutting` job. Side-effects are minimal: `bandit`, `pip-audit`, and `cyclonedx-bom` come along but are dormant unless invoked.

---

## R-007 — Regression-guard verification approach (FR-009, FR-010, C-003)

**Decision:** Verify-only via the existing test suites. The agent runs the listed test files at branch-cut and again before PR open; if every assertion passes on the feature branch, no production-code change is made. If any test fails, the failure is treated as an in-scope regression and a fix is added to this mission. No edits to `runtime_bridge.py`, `retrospective/schema.py`, or the verified golden-path helpers (`_parse_first_json_object`, `_run_next_and_assert_lifecycle`) are made on speculation.

**Rationale:**

- C-003 and the brief are explicit: *"verify, do not re-implement unless regression is observed."*
- Touching production code that is currently green creates regression risk for zero benefit and a noisier diff that obscures the actual contract fixes.
- The verification is itself the gate signal for those FRs; if the gate is green, the FR is satisfied by definition.

**Alternatives considered:**

- **Add new explicit-assertion tests on top.** Considered; rejected as scope creep — the existing tests already encode the invariants the brief calls out.

**Verification command set:**

```bash
uv run pytest \
  tests/next/test_retrospective_terminus_wiring.py \
  tests/retrospective/test_gate_decision.py \
  tests/doctrine_synthesizer/test_path_traversal_rejection.py -q
```

Plus a code-level sanity grep for the string anchors named in the brief (`PROJECT_000` user-visibility, lifecycle-trail hard-fail, real-synthesizer call) is performed during the contract-cleanup work itself, before the PR is opened.

---

## R-008 — `Protect Main Branch` failure handling (FR-013)

**Decision:** Diagnose first. Classification choice tree:

1. If the failure is reproducible from product code in `src/`, fix it in this PR.
2. If the failure is the release-merge workflow's compliance check (i.e. a release PR being a direct merge into `main` without going through the lane pipeline) and is not produced by `src/` code, file or update a GitHub issue describing the situation and link it from the PR description.

This mission does not silently ignore the failure either way.

**Rationale:**

- The brief lists this failure but explicitly leaves the disposition to the agent. A diagnose-then-classify rule keeps the disposition honest and creates a paper trail for whichever branch we take.
- Filing an issue is cheap and the right move when a CI failure is a release-process artifact rather than a code regression.

**Alternatives considered:**

- **Always fix in this PR.** Couples release-process hygiene to a contract-cleanup tranche, expanding scope unpredictably. Rejected.
- **Always defer to a follow-up.** Risks ignoring a real product-code regression that happens to be expressed as a Protect-Main failure. Rejected.

---

## R-009 — Hosted-surface command rule operationalisation (NFR-005, C-005)

**Decision:** Every command path (in tests, fixtures, examples, CI workflows added or modified by this mission, and PR-description reproduction commands) that touches hosted auth, tracker, SaaS sync, or sync behaviour is invoked with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. Tests that do not touch these surfaces are not modified. New tests added by this mission are explicitly classified up-front: hosted vs. local.

**Rationale:**

- Machine rule from the brief; carrying it into tests and PR docs makes the rule visible to reviewers and to future agents, not just the author.

**Alternatives considered:**

- **Apply globally to every test invocation.** Hides which commands are actually hosted-surface-aware; makes the policy meaningless in practice. Rejected.

---

## R-010 — Issue hygiene cadence (FR-011, FR-013, C-006)

**Decision:** GH issue updates land *after* the PR is merged, in a single batched comment per issue. Pre-merge, the PR description names which issues will be closed/commented and what evidence will be cited. Issue closure/comment commands run with `unset GITHUB_TOKEN` if the keyring scope path is needed (per CLAUDE.md guidance for organisation repos).

**Rationale:**

- Pre-merge issue updates can be premature if the PR is rejected; post-merge updates carry definitive evidence.
- Naming the planned updates in the PR description gives reviewers and stakeholders advance visibility without commitment.

**Alternatives considered:**

- **Update issues incrementally during review.** Risk of stale comments if the PR pivots. Rejected.

---

## Open Items

None. All `[NEEDS CLARIFICATION]` markers are resolved.
