# План реализации: полный lifecycle Mission в пользовательском worktree

**Ветка**: `codex/spec-kitty-worktree-mission-create`  
**Дата**: 2026-08-13  
**Спецификация**: [spec.md](spec.md)

## Summary

Добавить единый mission-scoped resolver с двумя независимыми корнями. `repository_root` остаётся общим Git/topology anchor, а `mission_anchor_root` указывает checkout, где лежат PRIMARY-метаданные и планирующие артефакты выбранной Mission. Resolver формирует ограниченный набор кандидатов — явно заданный root, managed coordination/lane, текущий caller-owned checkout и repository-root checkout — проверяет общую Git-identity и Mission identity, после чего возвращает один `MissionOperationContext`. Существующий placement seam получает оба корня и по-прежнему единолично выбирает фактические PRIMARY/STATUS surfaces; глобальные `locate_project_root()` и `get_main_repo_root()` сохраняют прежнюю семантику.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Typer, Rich, Git CLI, существующие `mission_runtime` и `specify_cli` resolver/placement API  
**Storage**: `kitty-specs/<mission>/`, `meta.json`, status/event JSONL и Git refs/worktrees  
**Testing**: pytest, `CliRunner`, реальные временные Git worktree; отдельный RED commit до production-кода  
**Target Platform**: Windows, Linux, macOS  
**Project Type**: Python CLI  
**Performance Goals**: не более одного дополнительного индексирования Mission-кандидатов; p95 overhead не более 50 мс при 100 Mission  
**Constraints**: без миграции, без изменения primary checkout, без дублирования topology/placement логики  
**Scale/Scope**: status, context, planning, tasks, implement/review, next и accept

## Charter Check

- Единственный владелец решения: новый mission-scoped resolver выбирает checkout, существующий placement seam выбирает artifact surface.
- ATDD-first: acceptance-тест, воспроизводящий полный caller-owned lifecycle, коммитится падающим до production-правки.
- Fail-closed: конфликт идентичности и чужой Git common directory дают типизированную ошибку без записи.
- Минимальный diff: не менять глобальные root helpers и не создавать альтернативную topology-модель.
- Совместимость: managed coordination/lane и явно заданный root сохраняют приоритет.
- Quality gates: targeted pytest, regressions resolver/placement/managed worktrees, Ruff, mypy strict для изменённых production-модулей, `git diff --check`.

Повторная проверка после проектирования: нарушений устава нет; исключения не требуются.

## Project Structure

```text
src/specify_cli/
├── core/paths.py                         # классификация ближайшего checkout и Git identity
├── context/mission_resolver.py           # существующая Mission identity
├── missions/
│   ├── operation_context.py              # новый единый mission-scoped dual-root resolver
│   └── _read_path_resolver.py            # PRIMARY от anchor, STATUS по topology
└── cli/
    ├── selector_resolution.py            # единая CLI-точка разрешения
    └── commands/...                       # только прямые обходы общей boundary

tests/
├── integration/                          # полный lifecycle в caller-owned worktree
└── specify_cli/                           # конфликт, explicit root, managed topology, selector forms
```

**Решение по структуре**: новый resolver размещается рядом с Mission read boundary, а не в Git-root helper. Команды получают готовый operation context и не принимают собственных решений по `cwd`. `feature_dir` не хранится как единый универсальный путь: конкретный artifact dir возвращает существующий kind-aware placement seam.

## Модель разрешения

1. Явно переданный root авторитетен и не подменяется `cwd`.
2. Managed coordination/lane определяется существующей topology и сохраняет текущий placement.
3. Caller-owned worktree допустим только если:
   - это ближайший linked checkout;
   - он относится к тому же Git common directory;
   - содержит `.kittify` и выбранную Mission;
   - не классифицирован как Spec Kitty managed surface.
4. Repository-root checkout остаётся fallback для существующих сценариев.
5. Если один selector или совпадающий slug соответствует несовместимым `mission_id`, resolver возвращает стабильную структурированную ошибку с безопасными путями кандидатов и ничего не пишет. Проверка выполняется и для full `mission_id`, чтобы конфликтующая slug-копия не осталась невидимой.
6. Совпадающая Mission identity на нескольких допустимых поверхностях не считается конфликтом; порядок выбора остаётся детерминированным согласно пунктам 1–4.

## Implementation Concern Map

### IC-01 — Классификация checkout и кандидатов

- **Назначение**: отличить explicit, caller-owned, managed и repository-root поверхности без изменения глобального root lookup.
- **Требования**: FR-001, FR-004, FR-006, FR-008; NFR-001, NFR-003; C-001.
- **Поверхности**: `core/paths.py`, новый `missions/operation_context.py`.
- **Зависимости**: нет.
- **Риски**: Windows path casing, symlink resolution, linked worktree другого Git common directory.

### IC-02 — Mission identity и fail-closed выбор

- **Назначение**: разрешать все формы selector через существующий Mission resolver и обнаруживать split-brain.
- **Требования**: FR-005, FR-007; NFR-003; C-002.
- **Поверхности**: `context/mission_resolver.py`, `missions/operation_context.py`, типизированные CLI diagnostics.
- **Зависимости**: IC-01.
- **Риски**: не превратить одинаковую identity в ложный конфликт; не раскрывать лишние данные в ошибке.

### IC-03 — Подключение полного lifecycle

- **Назначение**: провести `repository_root` и `mission_anchor_root` через status, context, planning, tasks, action, next и accept, не меняя artifact partition/topology.
- **Требования**: FR-002, FR-003, FR-004, FR-007; C-002, C-004.
- **Поверхности**: `cli/selector_resolution.py`, `missions/_read_path_resolver.py`, прямые вызовы `locate_project_root()` в lifecycle-командах.
- **Зависимости**: IC-01, IC-02.
- **Риски**: скрытые обходы общего resolver; расхождение read root и commit target.

### IC-04 — Acceptance и регрессионные доказательства

- **Назначение**: доказать полный caller-owned lifecycle, неизменность primary, managed topology и производительность.
- **Требования**: все FR; NFR-001–NFR-004.
- **Поверхности**: integration/unit/architectural tests.
- **Зависимости**: IC-01–IC-03.
- **Риски**: тестировать production CLI, а не только новый helper; исключить платформенно-зависимые предположения о путях.

## Порядок реализации

1. Зафиксировать отдельным коммитом падающий production-CLI тест текущего дефекта и снимки неизменности primary checkout.
2. Реализовать `MissionOperationContext`, Git/managed-классификацию, selector + slug conflict matrix.
3. Провести dual-root contract через placement/read/action runtime: topology от `repository_root`, PRIMARY от `mission_anchor_root`.
4. Подключить status/context/setup-plan/tasks/action/next/accept и branch/commit paths; добавить architectural guard против повторного root lookup после context.
5. Прогнать полный lifecycle, explicit root, managed regressions, два caller worktree и benchmark на 100 Mission; обновить changelog/внутреннюю документацию при необходимости.

## Критерии завершения

- Один Mission selector даёт одинаковые `mission_id`, slug и operation root на всех lifecycle-командах.
- Primary checkout сохраняет branch, HEAD и нулевой tracked diff.
- Managed lane/coord regressions без изменений.
- Split-brain завершается стабильным error code до любой записи.
- Targeted и relevant regression suites, Ruff, mypy strict и diff-check проходят.

## Complexity Tracking

Нарушений устава и дополнительных архитектурных слоёв сверх одного resolver-контекста нет.
