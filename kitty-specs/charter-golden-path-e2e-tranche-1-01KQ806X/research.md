# Research — Charter Golden-Path E2E (Tranche 1)

This document consolidates Phase 0 research findings used to lock the design before Phase 1.

## R-001 — Composed mission choice (resolves FR-005)

**Decision.** Pin the test to `software-dev`.

**Rationale.** Per DM-01KQ80QCTTFP9KJZTFTQY363QJ, planning research commits to one mission rather than implementing a runtime fallback chain. `software-dev` is the spec's first preference (FR-005), is the default `mission_type` for `spec-kitty agent mission create`, and is the same mission type the existing `tests/e2e/test_cli_smoke.py` smoke walk exercises (via `implement`/`move-task` rather than `next`, but the artifact recipe is known and minimal). It is also the mission the live `spec-kitty charter interview` command treats as the default (`--mission-type` defaults to `software-dev`).

**Alternatives considered.**
- `documentation` — viable per FR-005 fallback, but adds a research scaffolding burden (Divio types, generators, audit) we don't need to prove the operator-path spine.
- Minimal custom mission — last-resort per FR-005; adding a custom mission definition would expand the deliverable beyond a single test file plus a fresh-project fixture.

**Verification owed at implementation time.** The implementer SHALL run `spec-kitty next --agent test-agent --mission <slug> --json` against the freshly created minimal `software-dev` mission and confirm the engine returns a `step` decision (not a `blocked` decision that requires unscaffolded artifacts beyond what the test seeds). If `software-dev` fails to advance, that is a product finding (per spec Escalation Rules) and is reported, not papered over.

## R-002 — `charter synthesize` adapter (deviation from `start-here.md`)

**Decision.** The test MUST run `spec-kitty charter synthesize --adapter fixture --dry-run --json` and `spec-kitty charter synthesize --adapter fixture --json`, **not** the bare `--json` form recommended in `start-here.md`.

**Rationale.** Live `--help` output shows `synthesize --adapter` defaults to `generated`, which "validates agent-authored YAML under `.kittify/charter/generated/`". The `generated` adapter assumes an LLM harness has already written project-local doctrine YAML — there is no LLM in an automated CI test, so synthesize would fail. The `fixture` adapter is documented as "offline/testing only" and is precisely what the operator-path proof needs: a deterministic, hermetic synthesis path that exercises validate + promote without requiring an LLM.

**Spec / brief alignment.** This is a documented deviation from `start-here.md`'s recommended flow, accepted under spec FR-021 ("If the public CLI surface differs from the recommended flow … the deviation SHALL be recorded in the PR description as a finding"). The PR will state explicitly: "synthesize uses `--adapter fixture` because the default `generated` adapter is not suitable for an automated test without an LLM harness."

**Alternatives considered.**
- Default `generated` adapter — rejected, fails without LLM-authored doctrine.
- Pre-write a minimal fake `.kittify/charter/generated/` YAML inside the test to satisfy `generated` — rejected, would re-create the "fixture-copy" anti-pattern the tranche is trying to escape and would couple the test to private adapter contracts.

## R-003 — Mission scaffolding via public CLI (resolves FR-005, FR-006)

**Decision.** Scaffold the mission in the temp project using public commands in this order:

1. `spec-kitty agent mission create "<slug>" --mission-type software-dev --friendly-name "<title>" --purpose-tldr "<…>" --purpose-context "<…>" --json`
2. `spec-kitty agent mission setup-plan --mission <slug> --json`
3. Write seed `spec.md` (FR/NFR/C tables), `tasks.md`, `tasks/WP01-*.md`, and a meta.json patch — mirroring the proven recipe in `tests/e2e/test_cli_smoke.py::test_full_workflow_sequence`.
4. `git add . && git commit` (clean working tree before finalize).
5. `spec-kitty agent mission finalize-tasks --mission <slug> --json` — finalizes WP frontmatter and commits.

**Rationale.** Both `agent mission create` and `agent mission setup-plan` are part of the public `agent mission` group ("Mission lifecycle commands for AI agents") — this is the same surface `/spec-kitty.specify` and `/spec-kitty.plan` slash commands use. The smoke test already proves this scaffolding pattern works for a `software-dev` mission with one WP, including under `git init` + commit.

The seed `spec.md` / `tasks.md` content can be borrowed from `test_cli_smoke.py:132-194` (one FR-001, one NFR-001, one C-001, one WP01 with one subtask).

**Verification owed at implementation time.** Confirm that, after `finalize-tasks`, calling `spec-kitty next --agent test-agent --mission <slug> --json` (query mode) returns a structured decision pointing at the first composed action. If `next` returns `blocked` for missing artifacts beyond what the seed provides, document the additional artifact in the test (or surface it as a product finding if the requirement is undocumented).

## R-004 — `next` issue + advance shape (resolves FR-006, FR-014, FR-015, FR-016)

**Decision.** The test issues exactly one composed action via:

```
spec-kitty next --agent test-agent --mission <slug> --json
```

(query mode; `--result` omitted) and advances it via:

```
spec-kitty next --agent test-agent --mission <slug> --result success --json
```

**Rationale.** Live `--help` output documents:
- `--result` omitted ⇒ "returns current state without advancing (query mode)"
- `--result success|failed|blocked` ⇒ advancing mode

The composition dispatch path that `next` triggers writes paired pre/post lifecycle records to `.kittify/events/profile-invocations/<invocation_id>.jsonl`, observable from the filesystem without calling private helpers (confirmed by `tests/integration/test_documentation_runtime_walk.py` which reads the same path; we read it the same way but never call `decide_next_via_runtime`).

**Verification owed at implementation time.**
- Confirm the public JSON envelope from `next --json` includes a prompt-file field for the issued step (FR-014). The agent is expected to read that prompt; if the field is absent or null on a real composed step, that's a product finding.
- Confirm that `next --result success` produces a paired pre/post lifecycle record under `.kittify/events/profile-invocations/`. The recorded `action` field MUST equal the actual mission step (e.g. `specify`, `plan`, `tasks`), not a role-default verb (FR-016).
- Confirm that `next --result success` either advances exactly one composed action OR returns a documented structured "blocked / missing guard artifact" envelope (FR-015). Either is acceptable; silent no-ops are not.

## R-005 — Source-checkout pollution guard (resolves FR-017, FR-018)

**Decision.** The test SHALL implement a two-layer guard:

- **Layer 1 (FR-017):** capture `git status --short` in `REPO_ROOT` before any temp-project work; assert post-test value matches byte-for-byte.
- **Layer 2 (FR-018):** independently of git, walk `REPO_ROOT/{kitty-specs,.kittify,.worktrees,docs}` and recursively search for any path matching `profile-invocations`; record before/after file lists and assert no additions or modifications.

**Rationale.** `git status --short` alone is insufficient because `.gitignore` masks newly-created paths under ignored prefixes (e.g. a stray `.kittify/events/profile-invocations/` write into the source checkout would be invisible to `git status` if the path is ignored). The second layer catches that class of pollution. Past findings cited in `start-here.md` were exactly this kind: smoke tests creating `kitty-specs/*` in the product checkout.

**Implementation hint.** `REPO_ROOT = Path(__file__).resolve().parents[2]` (matches the convention in `tests/e2e/conftest.py:21`).

## R-006 — Subprocess isolation helper (resolves FR-002)

**Decision.** Use the `run_cli` fixture (`tests/conftest.py:344`) for individual CLI invocations. Each step is well under its 60-second per-call timeout. For the few invocations that need the lower-level helper (e.g. raw git commands), use `subprocess.run` directly.

**Rationale.** `run_cli` builds an isolated environment (PYTHONPATH → source `src/`, `SPEC_KITTY_TEMPLATE_ROOT` → REPO_ROOT, `SPEC_KITTY_TEST_MODE=1`) and invokes the CLI as `python -m specify_cli.__init__ <args>` from the venv interpreter. This guarantees we test source code, not an installed wheel. The 60-second per-call timeout is fine for individual subprocess steps; total test budget is bounded by NFR-001 at 180 seconds.

**Alternative considered.** `run_cli_subprocess` from `tests/test_isolation_helpers.py:93` — same isolation environment but with no built-in timeout. We don't need that flexibility for any single step in this flow.

## R-007 — Fresh-project fixture shape (resolves FR-003, FR-020)

**Decision.** Add a new fixture `fresh_e2e_project(tmp_path)` to `tests/e2e/conftest.py`. Behaviour:

1. Create `tmp_path / "fresh-e2e-project"`.
2. `git init -b main` in that directory.
3. `git config user.email e2e@example.com` and `git config user.name "E2E Test"`.
4. Run `spec-kitty init . --ai codex --non-interactive` via `run_cli_subprocess` (or the `run_cli` fixture if the test imports it explicitly).
5. `git add . && git commit -m "Initial spec-kitty init"`.
6. Yield the project path.
7. On teardown, `tmp_path` cleanup is automatic (pytest standard); no manual cleanup required.

**What the fixture does NOT do.**
- Does NOT copy `.kittify` from `REPO_ROOT` (deliberate contrast with existing `e2e_project` fixture at `tests/e2e/conftest.py:24-120`).
- Does NOT pre-write missions, charter artifacts, metadata, or any other state — the test drives those via public CLI.
- Does NOT run charter interview, generate, or any other charter command — those are the test's responsibility, not the fixture's, because they are part of the operator path under proof.

**Rationale.** The point of the tranche is operator-path proof from a clean project; any fixture-side scaffolding beyond `init` would weaken the test in exactly the ways flagged by `start-here.md`.

## R-008 — `retrospect summary` shape (resolves FR-007)

**Decision.** Run `spec-kitty retrospect summary --project <temp-project> --json` and assert the output is a parseable JSON object.

**Rationale.** `summary` reads `.kittify/missions/*/retrospective.yaml` and `kitty-specs/*/status.events.jsonl` and emits a non-mutating cross-mission view. The `--project` flag explicitly scopes the read to the temp project root, which guarantees the assertion is about the temp project's state and not the source checkout (defence in depth alongside R-005).

**Verification owed at implementation time.** Confirm the JSON envelope shape. Minimum assertion: top-level is a `dict` and parses without error. Stronger assertions (specific field names) can be added once the live shape is observed.

## R-009 — Premortem (sabotage attempts that the design must withstand)

Per the `premortem-risk-identification` tactic, here are the most plausible failure modes and how the design defends against each:

| Sabotage attempt | Where it shows up | Defence |
|---|---|---|
| Future change to `spec-kitty init` adds an interactive prompt that bypasses `--non-interactive` | Test hangs on init | NFR-001 (180 s budget) + `run_cli` 60 s per-call timeout fail loudly with stdout/stderr in the assertion message (NFR-004). |
| Future change to `synthesize --adapter fixture` removes the offline path | Test fails at synthesize step | R-002 deviation note in PR; surface as product finding per FR-021. |
| `next` quietly returns `blocked` without an `action` field on a fresh `software-dev` mission | Test passes but doesn't actually advance | FR-015 splits acceptable outcomes into "advances exactly one action" vs. "returns documented structured block" — any other shape (silent no-op, missing fields) fails FR-008. |
| A future commit writes profile-invocations under the source checkout because of a misconfigured event sink | Source checkout pollution | R-005 layer 2 catches it even when `.gitignore` masks the write. |
| Test author accidentally imports a forbidden private helper for "convenience" | C-001/C-002 violation | Add an architectural-style assertion: scan the test file's imports at test setup time and fail if any forbidden symbol is present. (Optional polish; not required by spec but aligns with the spirit of C-001/C-002.) |
| Composed action name in lifecycle record is `analyze` instead of `specify`/`plan` | Role-default-verb leak (the exact regression class start-here.md flags) | FR-016 explicit assertion comparing recorded action to the issued step ID returned by the prior `next --json` call. |

## R-010 — Out of Phase 0 scope

The following are explicitly NOT researched in Phase 0 and are deferred to follow-up tranches per spec Out of Scope:

- External canary integration (`spec-kitty-end-to-end-testing`).
- Plain-English scenarios.
- Multi-mission walks.
- Browser / dashboard surfaces.
- Retrospective synthesize via `agent retrospect synthesize` (separate command, not in the recommended flow; the test only calls `retrospect summary`).

---

**Phase 0 verdict:** all NEEDS CLARIFICATION items resolved. Ready for Phase 1 (data-model, contracts, quickstart).
