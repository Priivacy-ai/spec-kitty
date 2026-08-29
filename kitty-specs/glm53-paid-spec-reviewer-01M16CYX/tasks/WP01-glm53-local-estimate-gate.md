---
work_package_id: WP01
title: Локальный порог advertised-оценки для GLM 5.3
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
tracker_refs:
- tmgsp-eup
planning_base_branch: codex/glm53-paid-spec-reviewer
merge_target_branch: codex/glm53-paid-spec-reviewer
branch_strategy: Все изменения выполняются последовательно в task-owned ветке codex/glm53-paid-spec-reviewer и остаются в ней до отдельного PR lifecycle.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Реализация и проверка
assignee: ''
agent: ''
shell_pid: ''
history:
- at: '2026-08-29T09:33:00Z'
  actor: codex
  action: Пакет сформирован после согласования исправленного денежного контракта
agent_profile: python-pedro
authoritative_surface: src/specify_cli/spec_review/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/spec_review.py
- src/specify_cli/spec_review/models.py
- src/specify_cli/spec_review/preflight.py
- src/specify_cli/spec_review/runner.py
- src/specify_cli/spec_review/service.py
- src/specify_cli/spec_review/storage.py
- src/specify_cli/spec_review/contracts/spec-review-run-v1.schema.yaml
- tests/specify_cli/spec_review/
- tests/integration/test_spec_review_integration.py
- docs/guides/spec-review.md
role: implementer
tags:
- glm53
- cost-control
- compatibility
task_type: implement
---

# Work Package Prompt: WP01 – Локальный порог advertised-оценки для GLM 5.3

## Цель

Добавить ровно один платный opt-in маршрут `openrouter/z-ai/glm-5.3`. Разрешение строится по metadata-only котировке и локальному порогу `--max-estimated-cost-usd`; оно не называется hard cap фактического счёта. Бесплатный маршрут сохраняет прежние digest, YAML и отсутствие pricing probe в preview.

## Ограничения

- Не выполнять model call, платный smoke, account mutation, fallback или retry.
- Не читать credentials и не передавать spec во внешнюю систему в тестах.
- Разрешать paid mode только для exact route `openrouter/z-ai/glm-5.3`.
- При неизвестной цене, лимите, duplicate route или metadata drift делать отказ до prompt, server spawn и `create_session`.
- Сохранить прежнюю бесплатную canonical form: paid-поля не сериализуются как `null`.

## Подзадачи

### T001 — Отдельный failing acceptance-коммит

Добавить offline-тесты, которые сначала падают на текущей реализации:

- CLI требует `--max-estimated-cost-usd` для paid route и отклоняет `NaN`, infinity, `<= 0` и `> 5` с exit code 2 до mission resolution.
- Paid preview включает threshold, canonical quote, оба лимита, advertised estimate и metadata fingerprint в digest, но не строит prompt/session.
- Execution повторно получает quote и при любом drift делает ноль server/session/model calls.
- Неполная/неизвестная/отрицательная price-map, duplicate route, отсутствующий `limit.context` или `limit.output` fail-closed.
- Golden assertions закрепляют прежние free manifest digest и YAML без новых полей.

Зафиксировать failing tests отдельным commit до production-кода и записать ожидаемые причины падений.

### T002 — Каноническая котировка и consent

- Ввести immutable paid quote/provenance с Decimal-валидацией, каноническим JSON и SHA-256.
- Все известные input/cache price leaves применить к полному `limit.context`; output price — к полному `limit.output`; округлить вверх до `0.000001 USD`.
- Paid manifest должен включать threshold, нормализованную quote, limits, estimate и fingerprint.
- Free manifest должен использовать ровно прежний документ для digest.
- Byte-bound оставить только integrity guard, не использовать как billable-token estimate.

### T003 — Fail-closed runner и orchestration

- Расширить pricing probe metadata-only методом получения exact quote; сохранить прежний `require_free`.
- Paid preview делает probe без OpenCode server/session; execution re-probe требует точного совпадения с consent.
- Permit связывает issuer, exact route, quote fingerprint, threshold, estimate и byte-bound.
- Любой отказ завершается до prompt construction и server/session creation.

### T004 — CLI, persistence и документация

- Добавить `--max-estimated-cost-usd` без дефолта для paid route и честное предупреждение о фактическом billing.
- Paid artifact сохраняет threshold/quote/limits/fingerprint/estimate в optional секции; free artifact остаётся прежним.
- Обновить schema и операторский guide, не обещая provider-side cap.

### T005 — Green и независимая проверка

Выполнить focused pytest, integration/placement tests, `ruff`, `mypy --strict`, codemap verification и `git diff --check`. Проверить ноль внешних model calls. После зелёного результата провести независимое review до accept/PR.

## Команды проверки

```text
pytest tests/specify_cli/spec_review tests/integration/test_spec_review_integration.py tests/mission_runtime/test_spec_review_artifact_placement.py -q
ruff check src/specify_cli/spec_review src/specify_cli/cli/commands/spec_review.py tests/specify_cli/spec_review tests/integration/test_spec_review_integration.py
mypy --strict src/specify_cli/spec_review src/specify_cli/cli/commands/spec_review.py
python docs/codemap/codemap.lock
git diff --check
```

## Критерии review

- Есть отдельный commit с ожидаемо красными acceptance-тестами до production-кода.
- Paid quote полностью consent-bound и re-probed; drift нельзя обойти старым digest.
- Free canonical digest/YAML закреплены golden-тестами и не изменились.
- Ни одна формулировка не обещает ограничение фактического счёта.
- В реализации и тестах не было реального paid/model call.
