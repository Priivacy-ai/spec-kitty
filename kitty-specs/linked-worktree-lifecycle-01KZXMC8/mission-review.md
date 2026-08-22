# Mission Review Report: linked-worktree-lifecycle-01KZXMC8

**Рецензент**: Codex, post-merge mission reviewer  
**Дата**: 2026-08-14  
**Mission**: `linked-worktree-lifecycle-01KZXMC8` — Полный lifecycle Mission в пользовательском worktree  
**Baseline commit**: `6f139676978706458628000e69ea7621f1a68c25`  
**HEAD при review**: `89477955d4103b67fa441f38a474c67f6cf3d08d`  
**Проверенные пакеты**: WP01, WP02, WP03

---

## Gate Results

### Gate 1 — Contract tests

- Команда: `uv run --offline --with pytest --with pytest-timeout python -m pytest tests/contract -v -p no:cacheprovider --timeout=180`
- Exit code: `1`
- Результат: **FAIL**
- Доказательство: `292 passed, 3 skipped, 1 failed, 1 error`. `test_verify_enhanced_feature_detection_emits_canonical_mission_fields` использует отсутствующий на Windows `/dev/null`; `test_wheel_does_not_contain_vendored_spec_kitty_events` не собрал wheel, потому что build isolation не смог получить `hatchling` в offline-окружении. Contract gate не имеет exception path, поэтому ненулевой результат блокирует PASS независимо от вероятной платформенной/окруженческой природы этих двух сбоев.

### Gate 2 — Architectural tests

- Команда: `uv run --offline --with pytest --with pytest-timeout --with pytestarch python -m pytest tests/architectural -v -p no:cacheprovider --timeout=180`
- Exit code: `1`
- Результат: **FAIL**
- Доказательство: собрано `2105` тестов; полный sweep прерван timeout в fixture `tests/architectural/test_arch_shard_marker_completeness.py:169`, внутри `_gate_coverage.collect_universe()` при ожидании subprocess. Узкие архитектурные проверки, относящиеся к Mission, независимо прошли (`28/28`), но это не заменяет обязательный полный gate.

### Gate 3 — Cross-Repo E2E

- Команда: не запущена: checkout `spec-kitty-end-to-end-testing` и четыре обязательных сценария отсутствуют на машине.
- Exit code: не получен.
- Результат: **FAIL**
- Доказательство: поиск `dependent_wp_planning_lane.py`, `uninitialized_repo_fail_loud.py`, `saas_sync_enabled.py`, `contract_drift_caught.py` в доступных workspace не дал результатов. `mission-exception.md` отсутствует, поэтому окруженческий exception не оформлен.

### Gate 4 — Issue Matrix

- Файл: `kitty-specs/linked-worktree-lifecycle-01KZXMC8/issue-matrix.json`
- Строк: `1`
- Нетерминальных verdict: `1`
- Результат: **FAIL**
- Доказательство: строка `#3332` после перехода всех WP в `done` всё ещё содержит `"verdict": "in-mission"` (`issue-matrix.json:12`). Для завершённой Mission допустим только терминальный verdict.

---

## FR Coverage Matrix

| FR | Краткое обещание | Владелец | Production-path evidence | Адекватность | Вывод |
|---|---|---|---|---|---|
| FR-001 | Caller-owned checkout является Mission anchor | WP01, WP03 | `test_operation_context.py`; `test_caller_owned_worktree_lifecycle.py` | ADEQUATE | Основной путь доказан |
| FR-002 | Единое разрешение для полного lifecycle | WP03 | Сквозной production CLI lifecycle, `14/14` | ADEQUATE, но есть регрессия error precedence | RISK-1 |
| FR-003 | Repository root checkout не меняется | WP03 | Снимки branch/HEAD/tracked status в integration-тестах | ADEQUATE | Нарушений не найдено |
| FR-004 | Managed topology сохраняется | WP02, WP03 | Dual-root runtime и compatibility slice `62/62` | ADEQUATE | Нарушений не найдено |
| FR-005 | Split-brain завершается fail-closed | WP01, WP03 | Conflict matrix и typed resolver tests | ADEQUATE | Нарушений не найдено |
| FR-006 | Explicit root остаётся авторитетным | WP01 | Explicit-root и foreign-common-dir tests | ADEQUATE | Нарушений не найдено |
| FR-007 | Mission identity едина во всех командах | WP01–WP03 | Context/status/tasks/lifecycle production tests | ADEQUATE | Нарушений не найдено |
| FR-008 | Параллельные caller worktree изолированы | WP01, WP03 | Two-worktree и 100-call deterministic tests | ADEQUATE | Нарушений не найдено |

Целевые доказательства после последнего исправления: reviewer slice `62/62`, архитектурная пара `28/28`, production caller-owned lifecycle `14/14`, Ruff, strict mypy для `tasks_shared.py`, `py_compile`, codemap parity/hash и `git diff --check` — PASS.

## Drift Findings

### DRIFT-1 — Нетерминальный issue verdict после merge

**Тип**: LOCKED-DECISION VIOLATION  
**Severity**: HIGH  
**Ссылка на контракт**: post-merge Gate 4 / issue-matrix terminality  
**Evidence**: `kitty-specs/linked-worktree-lifecycle-01KZXMC8/issue-matrix.json:3-12`.

Mission завершила три WP и записала `done`, но PR #3332 остался `in-mission`. Это противоречит завершённому lifecycle и делает tracker evidence недостоверным.

### DRIFT-2 — Присвоенный номер Mission не отражён в canonical metadata

**Тип**: NFR-MISS  
**Severity**: LOW  
**Evidence**: merge сообщил номер `194`, однако `meta.json:21` содержит `null`, `acceptance-matrix.json:3` — пустую строку, а `retrospective.yaml:4` — пустое значение.

Это не ломает caller-owned routing, но оставляет три post-merge артефакта несогласованными.

## Risk Findings

### RISK-1 — `setup-plan` маскирует Git preflight ошибкой разрешения Mission

**Тип**: ERROR-PATH  
**Severity**: HIGH  
**Location**: `src/specify_cli/cli/commands/agent/mission_setup_plan.py:1038-1052`  
**Trigger**: `setup-plan --json` в checkout, где Git preflight должен вернуть remediation, но Mission ещё не разрешается.

После Mission-изменения `_resolve_setup_plan_operation()` вызывается раньше `_enforce_git_preflight()`. Поэтому существующий production test ожидает `GIT_PREFLIGHT_FAILED`, но получает `PLAN_CONTEXT_UNRESOLVED`. Изолированный прогон на HEAD стабильно падает; тот же тест на `origin/codex/spec-kitty-worktree-mission-create` проходит. Два соседних Windows create-Mission сбоя воспроизводятся и на baseline и к этой регрессии не относятся.

Пользовательский эффект: команда скрывает точную Git remediation за нерелевантной ошибкой Mission context. Исправление должно восстановить preflight precedence, не отменяя caller-owned operation context.

## Silent Failure Candidates

Новых подтверждённых silent-success путей в Mission diff не найдено. Legacy fallback в `tasks_shared.py` перехватывает только canonical `MissionNotFoundError`; конфликт, неоднозначность и остальные ошибки остаются fail-loud, что подтверждено cycle-5 review.

## Security Notes

| Finding | Location | Risk class | Recommendation |
|---|---|---|---|
| Git trust/preflight remediation маскируется более ранним Mission resolution | `mission_setup_plan.py:1038-1052` | ERROR-PATH / TRUST-DIAGNOSTIC | Восстановить проверенный порядок preflight и добавить regression test для caller-owned и repository-root checkout |

Новых `shell=True`, сетевых вызовов или credential-handling путей в целевом resolver/wiring не подтверждено. Path boundary защищена same-Git-common-directory, explicit-root и split-brain tests.

## Final Verdict

**FAIL**

### Verdict rationale

Функциональное ядро Mission реализовано и узкие production-path проверки подтверждают FR-001–FR-008. Однако релизный verdict обязан быть FAIL: Gate 1, Gate 2, Gate 3 и Gate 4 не прошли, а новый порядок `setup-plan` создаёт воспроизводимую регрессию на текущей ветке. До публикации обновления PR необходимо как минимум исправить RISK-1, перевести строку #3332 в терминальный verdict и повторить hard gates в подходящем окружении либо оформить допустимый exception только для Gate 3.

### Open items (non-blocking после закрытия blockers)

- Синхронизировать номер Mission `194` в `meta.json`, acceptance matrix и retrospective.
- Отдельно зарегистрировать два старых Windows create-Mission сбоя и платформенную проблему `/dev/null`, не смешивая их с регрессией этой Mission.

## Retrospective Reminder

`kitty-specs/linked-worktree-lifecycle-01KZXMC8/retrospective.yaml` существует и прочитан. После закрытия блокеров повторить mission review, затем выполнить `spec-kitty retrospect summary` и `spec-kitty agent retrospect synthesize --mission linked-worktree-lifecycle-01KZXMC8` (dry-run по умолчанию), чтобы проверить и агрегировать уже созданную ретроспективу.
