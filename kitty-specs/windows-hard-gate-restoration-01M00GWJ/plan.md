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

### IC-01 — Windows portability тестовой обвязки

- **Цель**: убрать `/dev/null`, import-time `os.geteuid` и separator-sensitive comparisons без изменения смысла gates.
- **Требования**: FR-001, FR-002, FR-003, FR-006, FR-007.
- **Поверхности**: contract test, consent-health test и узкие shared/path gate helpers.
- **Зависимости**: нет.
- **Риски**: слишком широкий skip на Windows; нормализация уже после формирования baseline; потеря mutation sensitivity.

### IC-02 — Реальные architecture inventories и topology authority

- **Цель**: отделить stale inventory от production bypass и восстановить single canonical authority.
- **Требования**: FR-004, FR-005, FR-007, FR-008.
- **Поверхности**: `_read_path_resolver.py`, `mission_creation.py`, соответствующие inventory/audit files и code map.
- **Зависимости**: IC-01, чтобы диагностика не искажалась separator failures.
- **Риски**: self-validating inventory update; blanket allowlist; параллельный resolver; несогласованная JSON/HTML карта.

### IC-03 — Полнота collection и каскадные coverage gates

- **Цель**: собрать весь набор, используемый gate-coverage/shard/session-reaper, и устранить только первичные причины оставшихся ошибок.
- **Требования**: FR-006, FR-007.
- **Поверхности**: семь подтверждённых collection-sensitive test files, coverage aggregation и session reaper tests.
- **Зависимости**: IC-01, IC-02.
- **Риски**: чинить вторичные симптомы до collection root cause; запускать дорогой suite на каждом изменении.

### IC-04 — Финальный local packet и внешний E2E contract

- **Цель**: один раз доказать полный Windows result и отдельно проверить доступ/результат canonical cross-repo E2E.
- **Требования**: FR-009, FR-010; NFR-001–NFR-005.
- **Поверхности**: validation commands, handoff evidence, при наличии доступа — внешний E2E checkout без локальных подмен.
- **Зависимости**: IC-01–IC-03.
- **Риски**: объявить локальный green эквивалентом E2E; скрыть access blocker; потратить час на полный suite до targeted green.

## Последовательность реализации

1. Создать charter-required GitHub issue о pre-existing failures; приложить исходные команды и counts.
2. Зафиксировать RED для Windows portability и collection defects отдельным commit.
3. Реализовать минимальные platform-safe oracles; убить преднамеренные мутации и прогнать targeted packet.
4. Регенерировать code map, затем RED-first классифицировать inventory drift и raw topology predicate.
5. Исправить production boundary либо точечно синхронизировать inventory; доказать non-vacuity.
6. Собрать семь проблемных файлов и прогнать coverage/shard/session-reaper targeted packet.
7. Запустить полный contract suite и один полный architecture suite; повторять полный run только после конкретного исправления нового подтверждённого failure.
8. Проверить доступ к canonical E2E repo. При доступе выполнить его documented gate; без доступа вернуть explicit external blocker.
9. Синхронизировать фактический результат с mission, code map, issue и reproducible handoff.

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
| Разделить platform portability и real architecture drift | Они требуют разных oracles и разной ответственности | Массовая замена строк/allowlists могла бы скрыть настоящий resolver bypass |
| Отдельный финальный пакет для полного suite | Architecture run занимает около 55 минут | Запуск после каждого изменения не повышает доказательность и создаёт лишний runtime friction |
| E2E как отдельное fail-closed состояние | Доступ зависит от внешнего GitHub principal | Локальный pass не доказывает cross-repo compatibility |
