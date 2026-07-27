# Mission Specification — ToolSurfaceContract Residual Closeout

**Mission type:** software-dev · **Branch (planning = merge target):** `feat/tool-surface-contract-residuals` (PR-bound; lands on `main`).

## Intent

Epic **#1945** (Define and enforce `ToolSurfaceContract`) was closed COMPLETED when PR **#1948** merged, but a post-merge verification panel found that #1948's blanket "Closes #1936…#1943" **over-reported four children**: their acceptance criteria are not met by the shipped code. The epic was reopened. This mission finishes those four residuals so the children close on substance and the operator can close #1945 honestly.

The four verified gaps (against merged code on `main`):

- **#1940 — native agent-profile projection.** Four mandated finding codes specified in the mission's `data-model.md` never landed in code (no emit path), and the projection manifest carries 6 of the 8 mandated fields.
- **#1941 — legacy `agent config` routing.** `SKILL_ONLY_AGENTS` and `VALID_AGENTS` remain hardcoded literals that recompute the tool universe independently of the registry, contrary to the issue's acceptance criterion; a required test scenario is absent.
- **#1942 — docs-contract lint.** The linter is correct but its test is `unit`-marked and **no CI shard collects it**, so the issue's own "CI-collected fail-on-drift" criterion is unenforced.
- **#1944 / #1965 — migration/compat residual.** The required user-facing Tool-vs-Agent upgrade guide was never shipped (only a CHANGELOG entry + an internal contract doc), and `test_doctor_skills_json_error_schema_stable` is environment-leaky.

Success is defined as **#1940, #1941, #1942, #1944, and #1965 reaching honest closure.** Closing epic #1945 itself is out of scope (operator-owned).

## User Scenarios & Testing

- **Profile-projection diagnostics (#1940):** A maintainer runs `spec-kitty doctor tool-surfaces --kind agent-profile --json` against a project whose org/project overlay has a malformed profile, a name-colliding profile, an overlay conflict, and a sentinel profile. Success: each condition surfaces its specific stable finding code (`profile-source-invalid`, `profile-name-invalid`, `profile-overlay-conflict`, `profile-sentinel-skipped`) rather than being silently ignored or collapsed into a generic missing/drift code; the projection manifest records full provenance (`source_path`, `source_hash`, `projection_version`) so a projected native file can be traced back to its canonical YAML.
- **Registry-backed agent config (#1941):** A maintainer adds/removes tools via `spec-kitty agent config`. Success: the set of valid/skill-only tools is derived from the canonical registry (one source of truth), not from a literal hardcoded in `config.py`; `list`/`status`/`sync` behave identically to before (frozen text interface), and a "configured Claude with session presence" scenario is covered by a test.
- **Enforced docs-lint (#1942):** A contributor edits docs to mention a `.agents/skills/spec-kitty.*` path that no registry surface backs. Success: a CI job actually collects and runs the docs-contract lint and **fails the build**; the gate is no longer invisible to the marker/path filters.
- **Migration guide + deterministic test (#1944/#1965):** A user upgrading an existing project, or cloning fresh, finds a user-facing guide under `docs/` explaining the Tool-vs-Agent terminology and the `doctor tool-surfaces --fix` repair path. Success: the guide exists and is discoverable (TOC/inventory); and `test_doctor_skills_json_error_schema_stable` passes deterministically regardless of ambient `~/.claude` state or invocation cwd.

### Edge cases

- A profile that triggers two conditions at once (e.g. invalid name *and* sentinel) must emit the most-specific applicable code(s) deterministically, never a silent pass.
- Registry-backing `VALID_AGENTS`/`SKILL_ONLY_AGENTS` must not change which tools are accepted/rejected today (no behavioral drift in `agent config` accept/reject).
- The docs-lint CI gate must fail on injected drift **and** pass on a clean tree (no false positives that block unrelated PRs).
- The doctor-skills test fix must not weaken what the test asserts (the frozen error-envelope schema), only remove the environment leakage.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | **#1940 finding codes:** implement and emit the four mandated agent-profile-projection finding codes — `profile-source-invalid`, `profile-name-invalid`, `profile-overlay-conflict`, `profile-sentinel-skipped` — each from its triggering condition in the `tool_surface` agent-profile provider/projection path, with stable kebab-case values consistent with the existing 7-code vocabulary and schema-conformant `--json` output. | draft |
| FR-002 | **#1940 manifest provenance:** extend the agent-profile projection manifest entries to carry all eight mandated fields, adding the missing `source_path`, `source_hash`, and `projection_version`, so every projected native profile is traceable to its canonical source YAML. | draft |
| FR-003 | **#1941 registry-backed sets:** derive `SKILL_ONLY_AGENTS` and `VALID_AGENTS` (in `src/specify_cli/cli/commands/agent/config.py`) from the canonical registry / `command_installer` surface rather than standalone hardcoded literals, so the tool universe is not recomputed independently. The externally-visible `agent config` text interface stays byte-identical. | draft |
| FR-004 | **#1941 test scenario:** add the missing "configured Claude with session presence" test scenario asserting correct presence resolution through the registry path. | draft |
| FR-005 | **#1942 CI enforcement:** make the docs-contract lint a CI-collected fail-on-drift gate — the test that runs `tool_surface/docs.py` must be collected by an actual CI shard (via marker change and/or a CI path filter `src/specify_cli/tool_surface/ → tests/specify_cli/tool_surface/`) and must fail the build when docs reference an unregistered surface path. | draft |
| FR-006 | **#1944 upgrade guide:** ship a user-facing guide under `docs/` covering the Tool-vs-Agent (vs Tool Surface) terminology and the fresh-clone / existing-project repair path (`spec-kitty doctor tool-surfaces --fix`), discoverable via the docs TOC/inventory and passing the docs-contract lint. | draft |
| FR-007 | **#1965 deterministic test:** fix `test_doctor_skills_json_error_schema_stable` so it is deterministic regardless of ambient `~/.claude` or cwd — make the `SPECIFY_REPO_ROOT` override authoritative in `locate_project_root()` when the target lacks `.kittify/`, or isolate the test — without weakening the frozen error-envelope schema assertion. | draft |
| FR-008 | **Honest closure:** verify each addressed issue against its delivered behavior and resolve #1940/#1941/#1942/#1944/#1965 to terminal issue-matrix verdicts; record the per-issue evidence. Epic #1945 closure is explicitly out of scope (operator-owned). | draft |

## Non-Functional Requirements

- **NFR-001 — backward compatibility:** the frozen `doctor skills --json` schema and the `agent config list/status/sync` text interface remain byte/contract-identical before vs after (pinned by the existing `test_doctor_skills_*` baseline and `test_agent_config_compat.py`). No regression to command-skill safety invariants.
- **NFR-002 — quality gates:** new/touched code passes `ruff` and `mypy --strict` with zero new issues and zero suppressions; complexity stays ≤15.
- **NFR-003 — terminology canon:** Tool / Agent / Tool Surface kept distinct; `ToolSurfaceContract` naming; zero `feature*` aliases (enforced by `tests/architectural/test_no_legacy_terminology.py`).
- **NFR-004 — gate provability:** the #1942 docs-lint gate is demonstrated by a negative test (injected drift → CI failure) AND a positive case (clean tree → pass); the gate runs in a shard that actually collects it (no silent skip).
- **NFR-005 — determinism:** the #1965 test fix removes environment leakage such that the test passes with an ambient `~/.claude` present and from any cwd; no other test's isolation is weakened by the `locate_project_root()` change.

## Constraints

- **C-001:** runs on `feat/tool-surface-contract-residuals` (off `main`); PR-bound to `main`.
- **C-002:** honor #1948's boundary (C-001 there) — no new logic in `core.config`/`agent.config` beyond registry wiring; `doctor.py` stays a thin delegating subcommand; profile finding codes live in the `tool_surface` bounded context.
- **C-003:** do not weaken existing command-skill safety invariants or the frozen `doctor skills` / `agent config` baselines; the `locate_project_root()` change (FR-007) must be scoped so it does not alter project-root resolution for real `.kittify/` projects.
- **C-004:** finding-code values and manifest field names must match the canonical vocabulary already specified in the #1948 mission's `data-model.md` (no new invented names).
- **C-005 (ticket hygiene):** at accept, the issue-matrix maps #1940/#1941/#1942/#1944/#1965 to terminal verdicts; each gets a tracker comment naming this mission. Epic #1945 is referenced (parent) but its closure is NOT a mission deliverable.
- **C-006:** not a bulk-edit mission (no single string renamed across many files); no `occurrence_map.yaml`.

## Success Criteria

- **SC-1:** **#1940 closed** — the four finding codes emit under their conditions (proven by focused tests) and manifest entries carry all 8 fields incl. `source_path`/`source_hash`/`projection_version`.
- **SC-2:** **#1941 closed** — `SKILL_ONLY_AGENTS`/`VALID_AGENTS` are registry-derived (no standalone tool-universe literal), `agent config` interface frozen-test green, and the "configured Claude with session presence" test present + passing.
- **SC-3:** **#1942 closed** — a CI shard collects and runs the docs-contract lint and fails on injected drift; the `unit`-marker invisibility is eliminated.
- **SC-4:** **#1944 + #1965 closed** — the user-facing upgrade guide exists under `docs/`, is TOC/inventory-discoverable and lint-clean; `test_doctor_skills_json_error_schema_stable` is deterministic.
- **SC-5:** full architectural + affected suites green; terminology guard green; no backward-compat or command-skill-safety regression.
- **SC-6:** every addressed issue resolved to a terminal issue-matrix verdict at accept; epic #1945 closure handed to the operator with a readiness note.

## Governing Doctrine (explicit call-outs)

Beyond the standard charter directives, these approaches/tactics warrant conscious application by implementers and reviewers, mapped to the work they govern:

- **Cross-cutting — DIRECTIVE_010 Specification Fidelity:** this mission *exists* because implemented behavior drifted from approved specs (the `data-model.md` finding-code vocabulary and 8-field manifest schema were specified but never landed). Every FR here is a fidelity repair; deviations from the canonical `data-model.md` names must be explicitly justified, not silently re-invented (reinforces C-004). Pair with **DIRECTIVE_032 Conceptual Alignment** for the Tool / Agent / Tool Surface distinction.
- **#1940 (FR-001/FR-002) — `generated-code-stewardship`:** the agent-profile projection manifest and the native profile files are *generated* artifacts. The new finding codes and `source_path`/`source_hash`/`projection_version` fields must be typed, explained, and reviewable — not bloated, untyped generated output. Fidelity to the canonical vocabulary is DIRECTIVE_010.
- **#1941 (FR-003) — `connascence-analysis` + DIRECTIVE_001/DIRECTIVE_024:** `SKILL_ONLY_AGENTS`/`VALID_AGENTS` are connascence-of-value/meaning that duplicate the registry's tool universe in a second location. The fix is a targeted connascence reduction to a single registry-backed source (locality of change), without altering accept/reject behavior.
- **#1942 (FR-005) — `quality-gate-verification` + `atdd-adversarial-acceptance` (DIRECTIVE_030):** a gate that no CI shard collects is not a gate. Prove it adversarially — an injected-drift negative test that *fails CI* — and distinguish introduced from pre-existing failures (NFR-004).
- **#1944/#1965 (FR-006/FR-007) — DIRECTIVE_037 Living Documentation Sync, `formalized-constraint-testing`, DIRECTIVE_034 Test-First:** the upgrade guide must evolve with the shipped behavior it documents; the `test_doctor_skills_json_error_schema_stable` fix must preserve (not weaken) the frozen error-envelope contract (round-trip/structural invariant), and the determinism fix is authored test-first.
- **All work-streams — DIRECTIVE_025 Boy Scout Rule (leave the campground cleaner):** the *functional* focus stays on the four residuals, but cleanup in adjacent areas the work touches is expected and welcome — the aim is a stable, coherent delivery, not a minimal-diff exercise in blame-shifting. When a touched area surfaces a failing test or a lint/type issue, fixing it outright is usually cheaper than forensically establishing whether our change caused it or it was already broken; default to just fixing it. Reserve the introduced-vs-pre-existing distinction for where it is cheap and materially required (e.g. the #1942 gate must report *introduced* drift), not as a reason to leave adjacent breakage in place.

## Domain Language

- **Tool** — a concrete execution product/runtime (Claude Code, Codex, Cursor, …).
- **Agent** — a logical collaborator identity/role (Architect Alphonso, …); legacy `agents.available` / `agent config` are compatibility aliases, not license to call install/config concepts "agent".
- **Tool Surface** — an installable/verifiable/packageable artifact or config entry exposed to a concrete Tool.
- **Finding code** — a stable kebab-case diagnostic identifier emitted by a `tool_surface` provider and surfaced by `doctor tool-surfaces --json`.
- **Manifest provenance** — the `source_path` / `source_hash` / `projection_version` fields that trace a projected native profile back to its canonical source YAML.

## Assumptions

- The finding-code names (FR-001) and the 8-field manifest schema (FR-002) are already specified canonically in the #1948 mission's `data-model.md`; this mission implements them, it does not redesign them.
- The exact #1942 CI-wiring mechanism (re-mark the test `fast`/`integration` vs add a dedicated CI path filter) is a plan-phase decision; either satisfies FR-005 so long as the gate is actually collected and fails on drift.
- External dependencies (`spec-kitty-events`, `spec-kitty-tracker`) are unchanged.
- The verification-panel findings recorded on #1940/#1941/#1942/#1944 (and the #1965 ticket body) are the authoritative gap list.
