# Отчёт post-merge review: setup-plan-preflight-closeout-01KZZT3V

**Ревьюер**: Codex  
**Дата**: 2026-08-14  
**Миссия**: `setup-plan-preflight-closeout-01KZZT3V` — восстановить Git preflight в `setup-plan`  
**Baseline commit**: `6732c8d1410428ce528e3047d8aac30228abec3e`  
**HEAD на момент review**: `2a1a4e407637dd74bd830ec94bb1b5c854838a39`  
**Проверенные WP**: WP01

## Результаты обязательных gates

### Gate 1 — Contract tests

- Команда: `.\.venv\Scripts\python.exe -m pytest tests\contract -q --tb=short --confcutdir=tests\contract -p no:cacheprovider`
- Результат: **FAIL**, exit code `1`.
- Итог: `293 passed, 3 skipped, 1 failed`.
- Единственный failure: `tests/contract/test_machine_facing_canonical_fields.py::test_verify_enhanced_feature_detection_emits_canonical_mission_fields` открывает `/dev/null` на Windows. Строка появилась в commit `c0ef5d284a` от 2026-04-08 и не относится к diff этой миссии. Политика hard-gate не допускает исключение даже для baseline-дефекта.

### Gate 2 — Architectural tests

- Команда: `.\.venv\Scripts\python.exe -m pytest tests\architectural -q --tb=short --confcutdir=tests\architectural -p no:cacheprovider`
- Результат: **FAIL**, exit code `1`.
- Итог: `2036 passed, 5 skipped, 2 xfailed, 28 failed, 34 errors` за `3343.05s`.
- Основные классы сбоев: Windows-разделители путей в frozen inventories, семь общих collection errors, устаревшие architecture allowlists/inventories и глобальные guards. Ни один выведенный failure не указывает на `mission_setup_plan.py` или `selector_resolution.py`, однако hard-gate остаётся красным.

### Gate 3 — Cross-repo E2E

- Проверка доступности: `gh repo view Priivacy-ai/spec-kitty-end-to-end-testing ...`.
- Результат: **FAIL / UNVERIFIED**, репозиторий отсутствует локально и недоступен текущему GitHub principal; `scenarios/` запустить невозможно.
- `mission-exception.md` отсутствует, поэтому policy не разрешает считать gate пройденным.

### Gate 4 — Issue matrix

- Файл: `kitty-specs/setup-plan-preflight-closeout-01KZZT3V/issue-matrix.json`.
- Строк: `1`; `#3332` имеет terminal verdict `fixed` и evidence на RED `00b7d7b21`, GREEN `2f2fbbbc0` и независимый review.
- Результат: **PASS**.
- На момент review поле `title` было шаблонным; последующий metadata-only commit заменил его актуальным заголовком PR #3332 — `Allow mission creation from caller-owned linked worktrees`.

## Целевой post-merge пакет

- `TestGitPreflightEnforcement`: `7 passed`.
- `test_selector_resolution.py`: `34 passed`.
- Реальный `test_setup_plan_scaffolds_in_caller_worktree_not_primary`: `1 passed`.
- Ruff для пяти изменённых Python-файлов: PASS.
- `mypy --strict` для двух production-файлов: PASS.
- `py_compile` и cumulative `git diff --check`: PASS.

## Покрытие требований

| FR | Реализация | Проверка | Достаточность |
|---|---|---|---|
| FR-001 | Git preflight перенесён перед Mission resolution | JSON failure и resolver-spy в `test_agent_feature.py` | ADEQUATE |
| FR-002 | Сохранены `GIT_PREFLIGHT_FAILED` и remediation | JSON и human failure tests | ADEQUATE |
| FR-003 | Активный same-repo checkout выбирается только для Git policy; Mission authority не меняется | Реальный linked-worktree integration и пять helper tests | ADEQUATE |
| FR-004 | `setup-plan` вызывает preflight один раз | Spy assertions и mutation с duplicate call | ADEQUATE |
| FR-005 | Failed preflight завершается без Mission resolution и записей | Resolver `assert_not_called`, snapshot before/after и отсутствие `feature_dir` | ADEQUATE |

## Drift findings

### DRIFT-1 — `codemap.lock` не соответствует артефактам

**Тип**: NFR-MISS  
**Severity**: HIGH  
**Требование**: NFR-003 / T007 delivery evidence

- В lock записано: JSON `b3a09600214fec21a70704f2679f060aa1f3316758595c525ce05669ca57d0c7`, HTML `4e9d8bd83c3bf301aa731adbf72fe45e7da668d8d3a6b266b19c65a696c95277`.
- Фактический SHA-256 Git blobs: JSON `1025abb398f1dd7c066ff0acb0c6484dc531e395b6366160177982c89d727d98`, HTML `fb1fb1c99b5441f36ca1ef7cd565bce595b696e73a39f66d746b499f12a84d12`.
- Baseline lock до миссии точно совпадал с baseline blobs, поэтому это регрессия текущей доставки, а не иной алгоритм проверки.
- **Remediation после review**: исправлено отдельным metadata-only commit; фактические SHA повторно проверены.

### DRIFT-2 — шаблонный заголовок issue matrix

**Тип**: документационный  
**Severity**: LOW

Terminal verdict и evidence корректны, но шаблонное поле ухудшает долговечность audit trail.

**Remediation после review**: заголовок заменён актуальным названием PR #3332.

## Риски

### RISK-1 — общие hard-gates не воспроизводятся зелёными на Windows

Целевая функция проверена, но репозиторий нельзя считать release-ready по действующей mission-review policy, пока contract и architecture gates имеют ненулевой exit code.

### RISK-2 — внешний E2E-контур недоступен

Нельзя подтвердить cross-repo сценарии без доступного `spec-kitty-end-to-end-testing` либо узкого operator-exception для конкретного сценария.

## Кандидаты на silent failure

В diff не найдено `except Exception` с возвратом пустого значения. Возврат `None` из `resolve_same_repository_worktree_root` — документированный отрицательный результат для ordinary/unrelated checkout, а не скрытая ошибка.

## Security notes

- Новый helper не запускает subprocess и сравнивает Git common-dir перед возвратом caller checkout.
- Пользовательский selector не используется для нового raw path-join.
- Auth/network/credential surfaces не изменялись.
- Новых security-блокеров в diff не найдено.

## Финальный verdict

**FAIL**

Предметная реализация FR-001–FR-005 корректна и независимо проверена; найденные metadata-дефекты `codemap.lock` и issue title уже устранены. Публикация всё ещё блокируется тремя hard-gates: необходимо восстановить зелёные contract/architecture gates либо получить допустимую policy-развязку, а также обеспечить доступ к cross-repo E2E или корректный operator-exception.

## Retrospective reminder

`kitty-specs/setup-plan-preflight-closeout-01KZZT3V/retrospective.yaml` создан автоматически при merge. Следующий штатный шаг: `spec-kitty retrospect summary` и dry-run `spec-kitty agent retrospect synthesize --mission setup-plan-preflight-closeout-01KZZT3V`; применять предложения без отдельной оценки не следует.
