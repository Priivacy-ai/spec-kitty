# Phase 1 Data Model — Charter Contract Cleanup Tranche 1

**Mission:** `charter-contract-cleanup-tranche-1-01KQATS4`
**Spec:** [spec.md](./spec.md)
**Research:** [research.md](./research.md)

This document captures the user-visible data shapes the mission introduces or hardens. It is contract-level, not implementation-level: field names are the wire/CLI contract, types and invariants are normative.

---

## Entity 1 — `SynthesisEnvelope`

**Surface:** stdout of `spec-kitty charter synthesize ... --json` (and any other `--json`-bearing charter synthesize invocation).

**Authoring location:** `src/specify_cli/cli/commands/charter.py`.

**Required fields**

| Field | Type | Description | Invariants |
|---|---|---|---|
| `result` | string | Outcome label | One of `"success"`, `"failure"`, `"dry_run"`. `"dry_run"` is used only when the run was invoked with `--dry-run` |
| `adapter` | object → see `AdapterRef` | Adapter metadata | Always present; `id` is non-empty |
| `written_artifacts` | array → see `WrittenArtifact` | Artifacts staged or promoted by this run | May be empty. For `result == "dry_run"`, this lists what *would* be written and must match what a real run would produce. Never derived from lossy `kind:slug` reconstruction |
| `warnings` | array of string | Non-fatal warnings from evidence gathering and adjacent stages | May be empty. Strictly a `list[str]` (no nested objects) |

**Permitted legacy fields (optional, present when not removed)**

| Field | Type | Notes |
|---|---|---|
| `target_kind` | string | Compatibility |
| `target_slug` | string | Compatibility |
| `inputs_hash` | string | Compatibility |
| `adapter_id` | string | Compatibility — duplicates `adapter.id` |
| `adapter_version` | string | Compatibility — duplicates `adapter.version` |

**Invariants (envelope-level)**

- `INV-E-1` — When `--json` is set, stdout contains exactly one JSON document and nothing else (no warnings, no progress, no Rich console output). `json.loads(stdout)` over the full stdout succeeds.
- `INV-E-2` — `result`, `adapter`, `written_artifacts`, and `warnings` are present unconditionally, including when their natural value is empty (`[]`).
- `INV-E-3` — No envelope value (string, key, or substring) contains the placeholder `PROJECT_000`.

---

## Entity 2 — `AdapterRef`

**Surface:** sub-object inside `SynthesisEnvelope.adapter`.

| Field | Type | Description | Invariants |
|---|---|---|---|
| `id` | string | Stable identifier of the synthesis adapter (e.g. `"fixture"`, `"openai-claude-3-5-sonnet"`) | Non-empty |
| `version` | string | Adapter version string | Non-empty; format adapter-specific (semver, model name, snapshot) |

---

## Entity 3 — `WrittenArtifact`

**Surface:** element of `SynthesisEnvelope.written_artifacts`.

| Field | Type | Description | Invariants |
|---|---|---|---|
| `path` | string | Repo-relative path (POSIX-style) of the staged-or-promoted artifact | Non-empty. For `result == "dry_run"`, byte-equal to the path a real run with the same inputs would write |
| `kind` | string | Doctrine kind | One of `"directive"`, `"tactic"`, `"styleguide"`, … (existing doctrine kinds) |
| `slug` | string | Slug component used in the artifact filename | Non-empty |
| `artifact_id` | string \| null | Concrete artifact identifier | Non-null when the kind carries an ID (e.g. directives → `PROJECT_001`, `DIRECTIVE_NEW_EXAMPLE`); never the placeholder `PROJECT_000` |

**Invariants (entry-level)**

- `INV-W-1` — `path` is sourced from typed staged-artifact entries returned by the synthesizer's write pipeline (`src/charter/synthesizer/write_pipeline.py`), not from `kind`/`slug`-based path reconstruction.
- `INV-W-2` — When `artifact_id` is non-null, the `<NNN>` segment of `path` (where present) is derived from that `artifact_id` (e.g. `PROJECT_001` → `001`).
- `INV-W-3` — Dry-run and non-dry-run runs produce equal entries, member-for-member, when given the same `SynthesisRequest`.

---

## Entity 4 — `IssuedActionEnvelope`

**Surface:** lifecycle envelope emitted by the runtime during the Charter golden-path E2E. Identified by `kind == "step"` (the documented public discriminator).

**Authoring location:** runtime emitter; consumed by `tests/e2e/test_charter_epic_golden_path.py`.

| Field | Type | Description | Invariants |
|---|---|---|---|
| `kind` | string | Envelope discriminator | `"step"` |
| `prompt_file` (or documented public equivalent) | string | Path to the prompt artifact this issued action points to | Present, non-null, non-empty. Resolves to an existing file on disk: either a path under the test project, an absolute path that exists, or a documented shipped prompt artifact path |
| (other existing envelope fields) | — | — | Unchanged |

**Invariants (E2E-level)**

- `INV-I-1` — For every envelope with `kind == "step"`, the resolved prompt-file path exists on disk at the moment the assertion runs.
- `INV-I-2` — A missing/null/empty/unresolvable prompt path causes the test to fail with a message naming the offending action.

---

## Entity 5 — `BlockedDecisionEnvelope`

**Surface:** lifecycle envelope emitted by the runtime when a step is intentionally halted.

| Field | Type | Description | Invariants |
|---|---|---|---|
| `is_blocked_decision` indicator | bool/discriminator | The runtime's existing flag/shape that identifies a blocked decision | Truthy for blocked decisions |
| `reason` | string | Human-readable reason the decision blocked | Present, non-null, non-empty (`reason.strip() != ""`) |
| `prompt_file` | string \| null | Optional; permitted to be absent | If present, MAY be empty/unresolvable — the assertion does not require resolvability for blocked decisions |

**Invariants (E2E-level)**

- `INV-B-1` — A blocked decision without a non-empty `reason` causes the test to fail.
- `INV-B-2` — A blocked decision is exempt from the prompt-file resolvability requirement (`INV-I-1` does not apply).

---

## Entity 6 — `MissionStepContractsExecutorTypingClaim`

**Surface:** invariant asserted by `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py`. Not a wire entity; a test-time claim about the strict-typing posture of `src/specify_cli/mission_step_contracts/executor.py`.

| Aspect | Value | Invariant |
|---|---|---|
| Tool | `mypy --strict` | Must be available on `sys.executable -m mypy` in the test environment |
| Target | `src/specify_cli/mission_step_contracts/executor.py` | Returns exit 0 |
| CI environment that exercises this claim | `e2e-cross-cutting` job in `.github/workflows/ci-quality.yml` | Installs `pip install -e .[test,lint]` so `mypy` is on PATH |

---

## State Transitions

This mission does not introduce new state machines. The relevant existing transitions it touches are:

- **`SynthesisRequest → SynthesisManifest → SynthesisEnvelope`** (synthesizer pipeline). The mission hardens the projection from manifest to envelope, not the manifest itself.
- **runtime → lifecycle envelope sequence** (next/runtime). The mission tightens the test-side assertion shape, not the producer.

---

## Validation Rules (cross-cutting)

| ID | Rule | Where enforced |
|---|---|---|
| V-001 | `json.loads(charter_synthesize_stdout)` succeeds when `--json` is set, even with warnings | `tests/integration/test_json_envelope_strict.py`; `tests/agent/cli/commands/test_charter_synthesize_cli.py` |
| V-002 | Envelope contains all of `{result, adapter, written_artifacts, warnings}` | Same as V-001 |
| V-003 | `written_artifacts` entries have `{path, kind, slug, artifact_id}` and `path` is sourced from staged-artifact entries | New test under `tests/charter/synthesizer/` and/or `tests/agent/cli/commands/` |
| V-004 | Dry-run/non-dry-run path parity for non-`PROJECT_000` provenance | New test under `tests/charter/synthesizer/` |
| V-005 | No user-visible string contains `PROJECT_000` | grep-style regression check + V-003/V-004 |
| V-006 | Issued action carries resolvable prompt file; blocked decision carries non-empty `reason` | `tests/e2e/test_charter_epic_golden_path.py` |
| V-007 | `mypy --strict` runs and passes on the executor under `e2e-cross-cutting` | `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` + workflow change |
| V-008 | Regression guards still pass | `tests/next/test_retrospective_terminus_wiring.py`, `tests/retrospective/test_gate_decision.py`, `tests/doctrine_synthesizer/test_path_traversal_rejection.py` |
