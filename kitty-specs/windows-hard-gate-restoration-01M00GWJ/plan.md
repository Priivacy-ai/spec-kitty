# План реализации: восстановить hard-gates Spec Kitty на Windows

**Ветка**: `codex/setup-plan-hard-gates` | **Дата**: 2026-08-14 | **Спецификация**: [spec.md](spec.md)

## Резюме

Восстановить обязательные contract и architecture gates на Windows без green-wash. Сначала устраняются платформенные дефекты тестовой обвязки (`/dev/null`, `os.geteuid`, `\` против `/`) через узкие RED-first oracles. Затем отдельно классифицируются реальные архитектурные сигналы: устаревшие inventories и raw coord-topology predicate. После зелёной targeted-проверки выполняется один полный Windows gate packet. Cross-repo E2E остаётся отдельным fail-closed состоянием и не считается пройденным без доступа к canonical репозиторию.

## Technical Context

_Технический контекст_

**Language/Version**: Python 3.11+; локально проверяется через task-owned `.venv`

**Primary Dependencies**: pytest, Typer, Rich, mypy, Ruff, Git

**Storage**: файловые inventories/allowlists, mission metadata, code map; БД продукта нет

**Testing**: ATDD/RED-first, targeted pytest, mutation/negative fixtures, финальные `tests/contract` и `tests/architectural`

**Target Platform**: Windows 10+ с сохранением Linux/macOS-семантики

**Project Type**: Python CLI, один репозиторий

**Performance Goals**: targeted-цикл до полного gate; полный architecture run запускается один раз после зелёного targeted packet

**Constraints**: без blanket skip/allowlist growth; без credentials; без записи в глобальную Beads DB; внешний E2E доступ не подменяется
**Scale/Scope**: один contract portability defect, минимум семь collection-sensitive файлов, семь репрезентативных architecture failures и полный итоговый architecture suite

## Проверка charter

- **ATDD-first**: каждый пакет начинается с отдельного RED commit через существующую точку запуска pytest; GREEN commit следует после него.
- **Pre-existing failures**: перед реализацией создаётся GitHub issue с командами, counts и доказательством, что failures существовали до task branch.
- **Non-vacuous gates**: path normalization и inventory updates получают mutation/negative oracle; count floors не уменьшаются.
- **Campsite cleaning**: только внутри минимального набора затрагиваемых файлов; отдельный tidy-first commit нужен лишь при подтверждённом локальном долге, мешающем исправлению.
- **Git discipline**: task-owned worktree и ветка уже созданы; интеграция только PR в `codex/setup-plan-preflight-closeout`.
- **Code map**: текущая карта не покрывает глобальные test-gate boundaries; JSON/HTML/lock синхронизируются до production boundary change и повторно в итоговом commit.
- **Full suite policy**: scoped tests на каждом пакете; полный architecture suite только в заключительном пакете, поскольку он дорогой и cross-cutting.
- **Tracer files**: `traces/approach.md`, `traces/design-decisions.md`, `traces/tooling-friction.md` создаются на planning phase и дополняются по ходу реализации.
- **Beads**: `bd 1.1.2` дважды выбрал чужую глобальную DB и проигнорировал task-local `BEADS_DIR`; это зафиксированный tooling blocker, запись туда запрещена.

Charter violations не планируются. Внешний E2E access и неисправный Beads resolver — явные blockers, а не исключения из quality policy.

## Структура проекта

### Документация mission

```text
kitty-specs/windows-hard-gate-restoration-01M00GWJ/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── hard-gate-result.md
├── traces/
│   ├── approach.md
│   ├── design-decisions.md
│   └── tooling-friction.md
└── tasks.md
```

### Затрагиваемые поверхности репозитория

```text
src/specify_cli/
├── core/mission_creation.py                 # возможный real topology bypass
└── missions/_read_path_resolver.py          # canonical resolver/inventory subject

tests/
├── contract/test_machine_facing_canonical_fields.py
├── cli/commands/test_sync_doctor_consent_health_3030.py
├── architectural/                           # path/census/inventory/coverage gates
└── ...                                      # только файлы, реально сорвавшие collection

docs/codemap/
├── codemap.json
├── codemap.html
└── codemap.lock
```

**Решение по структуре**: новые runtime-модули не создаются без необходимости. Платформенные fixes остаются рядом с owning tests/helpers. Production edit допускается только если независимый oracle подтверждает raw boundary bypass, а не устаревший inventory.

## Implementation Concern Map

_Карта implementation concerns_

### IC-01 — Windows portability и collection closure

- **Цель**: убрать `/dev/null`, import-time `os.geteuid` и separator-sensitive comparisons, затем доказать полную collection для семи известных файлов и зависимых coverage/shard/session-reaper gates.
- **Требования**: FR-001, FR-002, FR-003, FR-006, FR-007.
- **Поверхности**: `tests/contract/test_machine_facing_canonical_fields.py`; `tests/cli/commands/test_sync_doctor_consent_health_3030.py`; `tests/integration/test_intake_size_cap.py`; `tests/review/test_pre_review_gate_engine.py`; `tests/specify_cli/core/test_target_branch_primitive.py`; `tests/sync/test_consent_fault_vocabulary_3030.py`; `tests/sync/test_consent_write_refusal_3030.py`; `tests/sync/test_issue_598_hang_fixes.py`; только owning path/census gate tests, не production topology и не code map.
- **Зависимости**: нет.
- **Риски**: слишком широкий Windows skip; нормализация actual и expected одной функцией; лечение вторичных coverage errors до collection root cause.

### IC-02 — Architecture classification, topology remediation и code map

- **Цель**: отделить stale inventory от production bypass, восстановить single canonical authority и синхронизировать карту кода в том же commit, что production boundary.
- **Требования**: FR-004, FR-005, FR-007, FR-008.
- **Поверхности**: затронутые `tests/architectural` inventory/audit gates, `_read_path_resolver.py`, `mission_creation.py`, `docs/codemap/codemap.json`, `.html`, `.lock`.
- **Зависимости**: IC-01, чтобы диагностика не искажалась platform failures.
- **Риски**: self-validating inventory update; blanket allowlist; параллельный resolver; parity/hash без независимого callers/impact/tests oracle.

## Приёмочные gates, не implementation concerns

### Local acceptance

На окончательном неизменённом SHA выполняются полные contract/architecture suites, статические проверки, collection oracle, code map parity/hash/coverage и clean-tree check. Если обнаружен новый дефект, он возвращается в owning concern; после исправления новый финальный SHA проверяется повторно.

### External E2E release gate

Доступность canonical E2E repo и результат его tests проверяются после `implementation_complete`. Недоступность repo допускает принятие локальной реализации, но оставляет `e2e_ready=false` и `release_ready=false`; отдельный implementation package для внешней авторизации не создаётся.

## Последовательность реализации

1. Создать charter-required GitHub issue о pre-existing failures; приложить исходные команды и counts.
2. IC-01: отдельным RED commit зафиксировать null sink, EUID, separator и collect-only failures всех семи файлов.
3. IC-01: реализовать platform-safe actual-path boundary и узкий permission oracle; доказать static expected inventory и mutation sensitivity; закрыть targeted coverage/shard/session-reaper.
4. IC-02: на зелёной platform base зафиксировать RED для missing sink и raw topology predicate; read-only baseline code map предшествует production edit.
5. IC-02: исправить production boundary либо доказать узкое исключение; точечно синхронизировать inventory и code map в том же commit; проверить независимые callers/impact/tests.
6. Local acceptance: на окончательном SHA запустить полные contract и architecture suites, static gates и clean-tree check; найденные дефекты вернуть в owning concern.
7. External gate: проверить доступ к canonical E2E repo. При доступе выполнить documented gate; без доступа сохранить `implementation_complete=true`, но `e2e_ready=false` и `release_ready=false`.
8. Синхронизировать фактический результат с mission, issue и reproducible handoff, привязанным к неизменённому SHA.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m pytest tests\contract -q
.\.venv\Scripts\python.exe -m pytest tests\architectural -q
.\.venv\Scripts\python.exe -m ruff check <changed-python-files>
.\.venv\Scripts\python.exe -m mypy --strict <changed-production-files>
.\.venv\Scripts\python.exe -m py_compile <changed-python-files>
git diff --check
```

Дополнительно выполняются dedicated mutation/negative commands из work-package prompts и SHA/parity-проверка `docs/codemap`.

## Complexity tracking

| Решение | Почему нужно | Более простой вариант отклонён потому что |
|---------|--------------|-------------------------------------------|
| Разделить platform portability и real architecture drift | Они требуют разных oracles и непересекающегося ownership | Массовая замена строк/allowlists могла бы скрыть настоящий resolver bypass |
| Полный suite как acceptance gate, не WP | Architecture run занимает около 55 минут и не производит implementation artifact | Отдельный WP смешивал реализацию и проверку готовности |
| E2E как release gate, не WP | Доступ зависит от внешнего GitHub principal | Вечный локальный WP не способен исправить внешнюю авторизацию, а локальный pass не доказывает cross-repo compatibility |
