---
work_package_id: WP04
title: Безопасный OpenCode transport
dependencies:
- WP01
- WP02
requirement_refs:
- C-001
- C-003
- FR-005
- FR-006
- FR-010
- FR-013
- NFR-001
- NFR-003
- NFR-004
- NFR-005
- NFR-006
planning_base_branch: codex/ox-alpha-spec-reviewer
merge_target_branch: codex/ox-alpha-spec-reviewer
branch_strategy: Planning artifacts for this mission were generated on codex/ox-alpha-spec-reviewer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/ox-alpha-spec-reviewer unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
- T021
phase: Phase 2 - External transport
history:
- at: '2026-08-22T17:51:11Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
agent: codex
authoritative_surface: src/specify_cli/spec_review/runner.py
create_intent:
- src/specify_cli/spec_review/runner.py
- tests/specify_cli/spec_review/test_runner.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/spec_review/runner.py
- tests/specify_cli/spec_review/test_runner.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Безопасный OpenCode transport

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `codex`

---

## ⚠️ IMPORTANT: Review Feedback

Прочитай `review_ref`. Любое раскрытие raw stdout/stderr — blocker severity 5.

## Review Feedback

Уже учтено: bounded private streams, no raw exception text, process-tree cleanup, exact argv verification и no credential ownership.

## Objectives & Success Criteria

- Typed runner protocol не зависит от CLI/service/storage.
- OpenCode headless server запускается argv-list с `shell=False`, а prompt передаётся только в body loopback HTTP API.
- Default requested route configurable, без hidden fallback.
- Перед внешним запуском runner предоставляет typed pricing snapshot только для exact requested route; ненулевая, отсутствующая или устаревшая нулевая цена не даёт запускать модель.
- Raw stdout/stderr никогда не выводятся, не логируются и не входят в exceptions/results.
- Stream size ограничен; framing/parse handoff не раскрывает диагностический шум.
- Timeout завершает всё process tree за 5 секунд на supported OS.
- Tests используют fake executables/processes и 0 network calls.

## Context & Constraints

Прочитай:

- `spec.md`: FR-005/006/010, NFR-001/003/004/005/006.
- `plan.md` IC-03.
- `data-model.md` diagnostics/exit mapping.
- WP02 models/prompt contract после dependency completion.

Не читать OpenCode auth storage, env token values или credentials. Разрешён `opencode run --help` как read-only local capability check, но запрещён model call без отдельного gate.

## Branch Strategy

- **Planning base**: `codex/ox-alpha-spec-reviewer`
- **Merge target**: `codex/ox-alpha-spec-reviewer`
- WP04 может идти параллельно WP03 после WP02.

## Subtasks & Detailed Guidance

### T016 — Проверить локальный CLI contract

- Выполни только `opencode --version` и `opencode run --help` или эквивалентные no-network commands.
- Зафиксируй supported flags для pure/sessionless run, model route, input/output framing и cwd behavior.
- Не предполагай `--pure` или output flag, если help их не подтверждает.
- Если required headless/server/session HTTP surface отсутствует, остановись с material replan; не парси interactive UI.
- Не печатай config/auth paths.

### T017 — Red runner contract tests

- Spy/fake server/client фиксирует argv, HTTP body и environment names без secret values.
- Assert `shell=False`, server bind только на `127.0.0.1`, no prompt in argv и обязательное удаление созданной session.
- Outcomes: executable missing, auth marker, provider nonzero, 429/rate limit, timeout, invalid JSON/framing, oversized streams.
- Каждый вызов runner запускает внешний процесс не более одного раза; автоматические retry запрещены.
- Result type содержит только bounded metadata: diagnostic enum, exit code, byte counts, optional validated payload buffer.
- Exception messages не содержат child output.

### T018 — Runner protocol и adapter

- Определи protocol/interface для injectable runner.
- Input: immutable prompt bytes/string, requested route, timeout.
- Output: typed local result; host timestamps monotonic/UTC where needed.
- Build argv для headless server из verified T016 contract и platform-resolved executable; loopback HTTP client принимает prompt только как request body.
- Не устанавливай OpenCode и не управляй login.
- Default route находится в caller/config constant, не является provider guarantee.

### T019 — Private bounded streams и framing

- Захватывай server stdout/stderr и HTTP response body в bounded in-memory sinks; не используй unbounded `communicate()` или неограниченное чтение HTTP-тела.
- При превышении 2 MiB заверши process tree и верни `invalid_output` metadata-only.
- Raw server stderr никогда не передаётся parser; parser получает только единственный `text` part из документированного HTTP message-envelope, который обязан содержать один JSON-документ `review-response/v1` без префикса, суффикса или дополнительных событий.
- Иной envelope, несколько text parts либо дополнительные байты в извлечённом text part классифицируются как `invalid_output`; delimiter-based extraction и выбор «последнего JSON» запрещены.
- Invalid UTF-8 обрабатывается без включения raw bytes в error.

### T020 — Cross-platform process-tree cleanup

- POSIX: новая process session/group и group termination escalation.
- Windows: process group/job-object либо доказанный эквивалент, который завершает descendants.
- Graceful → forced escalation bounded 5 seconds.
- Закрывай HTTP/pipe handles, чтобы descendants не удерживали процесс; созданная server session удаляется в `finally`, а непроверенная очистка даёт локальный отказ без fallback.
- Fake helper порождает grandchild; test подтверждает отсутствие обоих после timeout.
- Cleanup errors сворачиваются в local diagnostic без command/output dump.

### T021 — Adversarial diagnostics tests

- Fake server echo полного prompt в HTTP-теле и stdout/stderr.
- Fragmented sentinel across chunks/encoding boundaries.
- Invalid UTF-8 and very large output.
- Auth/provider strings mixed with echoed prompt.
- 429/rate-limit response подтверждает один process invocation и `provider_error` без retry.
- Timeout during partial output, exception before spawn, exception during read, failed tree cleanup.
- Во всех paths captured user-visible/loggable result не содержит sentinel, argv prompt или raw stream.
- Separate diagnostic codes сохраняют FR-010 taxonomy.

## Test Strategy

- Target: `pytest tests/specify_cli/spec_review/test_runner.py`.
- Fake executable/helper создаётся в pytest temp dir; no real OpenCode in automated tests.
- Platform-specific tests skip только по реальной OS capability с объяснением.
- Ruff/mypy strict.
- Reversion test удаляет no-raw-stream boundary и обязан падать.

## Risks & Mitigations

- **Help contract drift** → T016 и thin adapter constant.
- **Prompt leak через child** → no raw propagation by construction.
- **Deadlock/large output** → streaming limits and concurrent drains.
- **Orphan descendants** → process group/job tests.
- **Hidden provider fallback** → exact route argv assertion.
- **Повторная передача** → process-spawn count равен единице для provider/429/network failures.

## Review Guidance

Reviewer проверяет:

- никаких secret/config reads;
- prompt только в loopback HTTP body;
- raw streams отсутствуют во всех result/exception/log paths;
- timeout действительно убивает grandchild;
- no real network/model call в tests;
- unsupported CLI contract приводит к blocker, не brittle parser.

## Definition of Done

- [ ] T016 help evidence зафиксировано без model call.
- [ ] Exact argv покрыт тестом и не содержит prompt.
- [ ] `shell=False` доказан spy/fake.
- [ ] Runner protocol injectable и typed.
- [ ] Raw stdout/stderr отсутствуют в result/exception/loggable fields.
- [ ] Both streams bounded и drained без deadlock.
- [ ] Oversize завершает process tree.
- [ ] Invalid UTF-8 не раскрывает bytes.
- [ ] Full/fragmented sentinel tests зелёные.
- [ ] Auth/provider diagnostics различимы без raw text.
- [ ] Timeout kills child + grandchild ≤5 seconds.
- [ ] Windows and POSIX branches имеют tests или explicit platform evidence.
- [ ] No fallback model exists.
- [ ] No network in automated tests.
- [ ] Ruff/mypy/pytest зелёные.

## Forbidden Changes

- Не читать OpenCode auth/config contents.
- Не передавать prompt в argv/env/temp file.
- Не логировать command with secret-bearing environment.
- Не возвращать child stderr как remediation.
- Не использовать unbounded buffer.
- Не запускать real model в WP implementation.
- Не fallback-ить на другой route/provider.
- Не выводить из суффикса route (включая `-free`) факт бесплатности; отсутствие проверяемого snapshot — отказ до создания prompt и HTTP-передачи.

## Verification Evidence

Handoff включает verified help flags, sanitized argv shape, stream-limit values, process-tree test duration, diagnostics matrix и sentinel non-leak assertion counts. Raw streams не прикладывать.

## Rejection Conditions

Reviewer отклоняет WP, если prompt попадает в argv/env/temp file, raw child output достижим через result/exception/logging, buffer не ограничен, timeout оставляет descendant, automated test вызывает network или unsupported OpenCode output парсится эвристически без framed contract.

Leakage finding имеет максимальный приоритет над green functional tests.

## Activity Log

- 2026-08-22T17:51:11Z – system – Prompt created.

### Updating Status

`spec-kitty agent tasks move-task WP04 --to <status>`.
