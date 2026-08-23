---
work_package_id: WP05
title: Advisory service и CLI integration
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- C-002
- C-004
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- NFR-001
- NFR-007
planning_base_branch: codex/ox-alpha-spec-reviewer
merge_target_branch: codex/ox-alpha-spec-reviewer
branch_strategy: Planning artifacts for this mission were generated on codex/ox-alpha-spec-reviewer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/ox-alpha-spec-reviewer unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
- T027
phase: Phase 3 - User workflow
history:
- at: '2026-08-22T17:51:11Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
agent: codex
authoritative_surface: src/specify_cli/spec_review/
create_intent:
- src/specify_cli/spec_review/__init__.py
- src/specify_cli/spec_review/service.py
- src/specify_cli/cli/commands/spec_review.py
- tests/specify_cli/spec_review/test_service.py
- tests/specify_cli/cli/test_spec_review_command.py
- tests/specify_cli/cli/test_review_command_compatibility.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/spec_review/__init__.py
- src/specify_cli/spec_review/service.py
- src/specify_cli/cli/commands/spec_review.py
- src/specify_cli/cli/commands/__init__.py
- tests/specify_cli/spec_review/test_service.py
- tests/specify_cli/cli/test_spec_review_command.py
- tests/specify_cli/cli/test_review_command_compatibility.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – Advisory service и CLI integration

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `codex`

---

## ⚠️ IMPORTANT: Review Feedback

Проверь `review_ref`. Existing `spec-kitty review` compatibility и exit semantics являются обязательными acceptance gates.

## Review Feedback

План включает audit findings: отдельная top-level command, manifest-wide consent, advisory lifecycle ≠ exit 0, no eager import.

## Objectives & Success Criteria

- Собрать existing typed components в один use case без дублирования validation/placement/process logic.
- Добавить `spec-kitty spec-review` как отдельную leaf command.
- Сохранить `spec-kitty review` help/options/behavior.
- Реализовать явный `--preview` и одноразовый `--confirm-digest <sha256>`.
- Показать disclosure manifest до интерактивного prompt.
- Возвращать stable exit codes 0/2–7 по spec.
- Не менять `spec.md`, meta lifecycle, status events или WP state.

## Context & Constraints

Прочитай:

- весь `spec.md`, особенно exit-code table.
- `plan.md` IC-05 и compatibility strategy.
- `quickstart.md` operator UX.
- WP02 models/preflight, WP03 storage, WP04 runner APIs.
- existing `commands/review/__init__.py` and root registration.

Не использовать `ProfileInvocationExecutor` как LLM transport. Если нужен governance record, он может фиксировать только metadata intent/result и не содержать prompt/spec/raw streams.

## Branch Strategy

- **Planning base**: `codex/ox-alpha-spec-reviewer`
- **Merge target**: `codex/ox-alpha-spec-reviewer`
- Начинай только после merge WP02–WP04 в execution base.

## Subtasks & Detailed Guidance

### T022 — Red service/CLI acceptance tests

- Root help содержит `review` и `spec-review`.
- `--preview`: manifest printed, runner/storage 0 calls, exit 0.
- Interactive decline: runner/storage 0 calls, exit 0, explicit cancelled outcome.
- Noninteractive missing confirm: exit 2.
- Noninteractive mismatched `--confirm-digest`: exit 2, runner/storage 0 calls.
- Input refusal: exit 3.
- CLI/auth/provider: exit 4; timeout 5; invalid output 6; write failure 7.
- Complete: exit 0, one artifact, counts/path summary, original spec/meta/status unchanged.

### T023 — Advisory orchestration service

- Resolve mission through canonical selector, never manual path parsing.
- Build preflight + disclosure manifest, render safe metadata-only view.
- Preview short-circuits before consent/runner.
- Interactive consent binds exact manifest digest; `--confirm-digest <sha256>` authorizes only current invocation и только при точном совпадении с пересчитанным manifest digest.
- After consent, request immutable buffer from preflight and invoke injected runner.
- Map runner → parser → host run → storage; no raw output enters service result.
- Persist `completed`, `provider_error`, `timeout` и `invalid_output`; при `write_failed` вернуть exit 7 без артефакта, findings persistence или повторного model call.
- Return typed outcome carrying safe diagnostic, exit code, artifact path and counts.

### T024 — Thin CLI adapter

- Options: required `--mission`, optional `--model`, `--timeout`, `--preview`, `--confirm-digest <sha256>`.
- Validate timeout 10–600 as usage error without process call.
- Detect interactive terminal only for prompt; CI/noninteractive never prompts.
- Render `transport=OpenCode CLI`, `requested model route=...`, digests всех четырёх payload parts и explicit unverified availability/ownership/price/retention/anonymization warning.
- Never print input content, child output or exception repr.
- Exit with exact spec table.

### T025 — Safe registration and imports

- Register new command without converting existing `review` to group.
- Preserve command sorting and short-help conventions.
- Fast path/doctor registration must not import runner/OpenCode integration eagerly.
- Package `spec_review.__init__` exports minimal public types, without side effects.
- No optional dependency import at module import time.

### T026 — Existing review compatibility tests

- Snapshot/semantic tests for `review --help` flags: mission, mode, check-residual.
- Existing direct invocation continues to call `review_mission` leaf.
- Exit behavior for missing mission/env skew remains unchanged.
- Root help order may include new command but old command text stays stable.
- Doctor/next/test fast paths do not instantiate service/runner.

### T027 — Non-mutation and summary tests

- Hash `spec.md`, meta.json and status events before/after every outcome.
- Complete path writes only canonical review artifact through storage.
- Failure after process start may write metadata-only failure artifact; prompt/sentinel absent.
- Write failure leaves no partial/temp file.
- Human summary shows status, counts and path only.
- Repeated run creates new file and preserves old artifact.

## Test Strategy

- Target service and CLI test files with Typer runner/fakes.
- No subprocess/network: inject WP04 fake runner.
- Capture stdout/stderr and assert absence of unique sentinel across all outcomes.
- Reversion tests for `review` leaf compatibility and lifecycle non-mutation.
- Ruff/mypy strict.

## Risks & Mitigations

- **Advisory ambiguity** → stable exit table.
- **Implicit consent** → explicit preview vs confirm surfaces.
- **Existing command breakage** → dedicated compatibility test file.
- **Eager external stack import** → fast-path tests.
- **Business logic in CLI** → thin adapter, service owns use case.

## Review Guidance

Reviewer проверяет:

- preview/decline/missing-confirm behavior различаются;
- exact manifest displayed without content;
- every failure maps to documented exit;
- mission lifecycle never changes;
- existing `review` remains leaf and flags unchanged;
- no raw child/result data reaches Rich/Typer errors.

## Definition of Done

- [ ] `spec-review` виден в root help как отдельная leaf command.
- [ ] Existing `review` flags/help/behavior сохранены.
- [ ] Preview всегда 0 calls runner/storage.
- [ ] Interactive decline и noninteractive missing consent различаются.
- [ ] Disclosure показывает весь manifest и warning.
- [ ] Consent связан с exact digest.
- [ ] Несовпадающий `--confirm-digest` даёт exit 2 и 0 calls runner/storage.
- [ ] 429/provider failure не вызывает автоматический retry.
- [ ] Service orchestration не дублирует parser/storage/runner logic.
- [ ] Exit mapping 0/2–7 покрыт table-driven tests.
- [ ] Mission/spec/meta/status неизменны во всех outcomes.
- [ ] Success summary содержит только safe metadata.
- [ ] Failure output не содержит raw streams/prompt.
- [ ] Repeated run сохраняет старый artifact.
- [ ] Каждый подтверждённый запуск вызывает runner не более одного раза; повторный запуск требует нового consent.
- [ ] Fast paths не import external stack eagerly.
- [ ] Ruff/mypy/pytest зелёные.

## Forbidden Changes

- Не превращать `review` в Typer group.
- Не включать auto-run в specify/plan/tasks/accept/merge.
- Не сохранять global consent.
- Не ловить broad exception с `str(exc)` в user output.
- Не менять mission lifecycle/status events.
- Не добавлять arbitrary file input.
- Не заявлять requested route как фактического provider.

## Verification Evidence

Handoff содержит root/review/spec-review help checks, exit-code matrix, runner/storage spy counts, before/after hashes mission artifacts и sentinel absence assertions.

## Activity Log

- 2026-08-22T17:51:11Z – system – Prompt created.

### Updating Status

`spec-kitty agent tasks move-task WP05 --to <status>`.
