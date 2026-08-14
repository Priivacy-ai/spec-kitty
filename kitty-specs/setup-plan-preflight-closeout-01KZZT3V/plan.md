# План реализации: восстановить Git preflight в setup-plan

**Ветка**: `codex/setup-plan-preflight-closeout` | **Дата**: 2026-08-14 | **Спецификация**: [spec.md](spec.md)  
**Доставка**: внутренний Mission merge остаётся в `codex/setup-plan-preflight-closeout`; проверенный task-owned PR направляется в `codex/spec-kitty-worktree-mission-create`.

## Краткое решение

После существующих hosted-auth и SaaS boundary gates определить активный Git checkout через единственный canonical checkout helper, выполнить существующий Git preflight ровно один раз и только после его успеха разрешать caller-owned Mission path. Для обычного checkout helper возвращает repository root и сохраняется действующий feature-dir resolver; для caller-owned linked worktree выбирается текущий checkout той же Git identity. Mission identity и `mission_anchor_root` по-прежнему определяет только `MissionOperationContext`.

## Инженерное согласование

- **Инвариант отказа**: failed Git preflight завершает команду до Mission resolution и до любых planning-записей.
- **Инвариант authority**: checkout selection для Git-политики не становится Mission-root authority; Mission identity/anchor остаются за `MissionOperationContext`.
- **Инвариант количества**: один вызов `setup-plan` выполняет Git preflight ровно один раз.
- **Порядок gate**: hosted-auth отказ и SaaS boundary сохраняют существующий приоритет; затем выполняется Git preflight, и только после него — Mission resolution.
- **Delivery**: исправляется regression PR #3332 без release, deploy, SaaS или изменения пользовательской конфигурации.

## Technical Context

*Технический контекст реализации.*

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Typer CLI, `pathlib`, существующие `core.paths`, `selector_resolution`, `MissionOperationContext`, `git_preflight`  
**Storage**: локальные Git checkout и Markdown/JSONL Mission-артефакты; новая схема хранения отсутствует  
**Testing**: pytest unit + caller-owned linked-worktree integration, независимые spy/mutation-oracles, Ruff, mypy strict, py_compile  
**Target Platform**: Windows 10+, Linux, macOS  
**Project Type**: Python CLI  
**Performance Goals**: один Git preflight и ноль дополнительных Git subprocess-вызовов на один `setup-plan`  
**Constraints**: ATDD-first; fail-closed; без второй Mission-root authority; без записи до failed preflight  
**Scale/Scope**: один CLI flow, не более двух production-модулей и фокусные тесты

## Charter Check — проверка charter

*GATE до Phase 0 и повторно после Phase 1: PASS.*

- **Canonical authority**: caller-owned путь использует существующий Mission resolver; обычный checkout сохраняет действующий feature-dir resolver; checkout helper отвечает только за Git checkout до Mission selection.
- **ATDD-first**: сначала воспроизводится RED `PLAN_CONTEXT_UNRESOLVED` вместо `GIT_PREFLIGHT_FAILED`, затем production fix.
- **Cross-platform**: решение основано на `Path` и существующей Git identity abstraction, без Windows-only ветвей.
- **Static quality**: изменённые Python-файлы проходят Ruff, strict mypy и py_compile без suppressions.
- **Regression vigilance**: targeted branch/base differential обязателен; обнаруженные pre-existing failures до принятия baseline сверяются с GitHub issues или оформляются отдельным issue.
- **Git workflow**: code пишется только после task finalization в отдельном lane worktree; итог публикуется task-owned PR.

## Структура проекта

### Документация Mission

```text
kitty-specs/setup-plan-preflight-closeout-01KZZT3V/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── setup-plan-preflight.md
└── checklists/
    └── requirements.md
```

### Production и тесты

```text
src/specify_cli/
├── cli/commands/agent/mission_setup_plan.py
└── cli/selector_resolution.py            # только если нужен canonical checkout helper

tests/
├── agent/test_agent_feature.py
├── integration/test_caller_owned_worktree_lifecycle.py
└── cli/                                  # фокусный helper-test, если helper вынесен сюда
```

**Решение по структуре**: сохранить orchestration в `mission_setup_plan.py`; общий pre-Mission checkout primitive размещать рядом с существующим same-repository selector logic, а не в новом модуле.

## Фаза 0 — исследование решения

Результаты зафиксированы в [research.md](research.md). Выбран вариант с canonical pre-Mission checkout helper. Простое перемещение preflight на `located_root` отклонено: `locate_project_root()` намеренно возвращает repository-root checkout и тем самым перестал бы проверять caller-owned checkout.

## Фаза 1 — design и contracts

- [data-model.md](data-model.md) фиксирует ephemeral roots и порядок переходов без новой persisted-сущности.
- [contracts/setup-plan-preflight.md](contracts/setup-plan-preflight.md) фиксирует observable JSON/human error contract и успешный caller-owned path.
- [quickstart.md](quickstart.md) содержит RED/GREEN и финальные verification-команды.

Повторная Charter Check: **PASS** — дизайн не добавляет authority, storage, network или platform-specific path.

## Implementation Concern Map — карта аспектов реализации

### IC-01 — выбор Git checkout до Mission selection

- **Назначение**: после hosted-auth/SaaS boundary выбрать checkout для Git preflight до Mission resolution и не спутать его с Mission anchor.
- **Требования**: FR-001, FR-003, FR-004, FR-005; NFR-001, NFR-004; C-001, C-002.
- **Поверхности**: `mission_setup_plan.py`, при необходимости `selector_resolution.py`.
- **Зависимости**: отсутствуют.
- **Риски**: preflight repository root вместо caller checkout; выбор unrelated CWD; дублирование root authority; случайное изменение SaaS-vs-Git error precedence.

### IC-02 — regression и mutation evidence

- **Назначение**: доказать precedence, один preflight, отсутствие writes и сохранение caller-owned success path.
- **Требования**: FR-001–FR-005; NFR-002, NFR-003; C-004.
- **Поверхности**: `test_agent_feature.py`, `test_caller_owned_worktree_lifecycle.py`, точечный helper-test при необходимости.
- **Зависимости**: IC-01 определяет observable contract, но RED фиксируется до production-изменения.
- **Риски**: mock-only тест не поймает реальный linked-worktree root; broad Windows suite содержит известные baseline reds. Оракул обязан проверить preflight argument, call count, отсутствие Mission resolver на failed path и неизменность primary snapshot.

### IC-03 — charter-compliant execution evidence

- **Назначение**: сохранить обязательный RED-first proof, выполнить узкий tidy-first осмотр выбранной поверхности и вести три Mission tracer через coordination-aware CLI.
- **Требования**: C-004 и binding charter ATDD/campsite/tracer rules.
- **Поверхности**: отдельный RED commit в lane; `spec-kitty agent tracer-append` для `approach`, `design-decisions`, `tooling-friction`; без прямой записи tracer из product worktree.
- **Зависимости**: RED фиксируется первым; campsite-clean выполняется после RED и до функционального production commit.
- **Риски**: test и implementation попадут в один commit; tidy-first разрастит file set; tracer будет записан в неверную partition. Защита: отдельный commit, текущий owned file set и только canonical tracer CLI.

## Gates перед реализацией и delivery

1. RED существующего preflight test и нового precedence/spies oracle на текущем HEAD; failing test закоммитить отдельным commit до implementation commits.
2. После RED выполнить отдельный behavior-preserving campsite-clean выбранных production/test surfaces; при отсутствии релевантного debt записать `none found`.
3. GREEN targeted unit + caller-owned integration.
4. Deletion/mutation: resolver-before-preflight, пропущенный early exit, второй preflight и repository-root checkout вместо caller checkout должны падать.
5. Ruff changed files, `mypy --strict` changed production, py_compile, `git diff --check`.
6. Targeted branch/base differential для любых посторонних красных тестов; pre-existing failures связать с существующим GitHub issue либо открыть отдельный issue.
7. Вести `approach`, `design-decisions` и `tooling-friction` только через `spec-kitty agent tracer-append`; оценить их при closeout.
8. Независимый review, Mission accept, push и PR в `codex/spec-kitty-worktree-mission-create`; release/deploy не выполнять.
