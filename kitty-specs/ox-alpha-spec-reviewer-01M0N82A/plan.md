# План реализации: ручной ревьюер спецификаций Ox Alpha

**Ветка**: `codex/ox-alpha-spec-reviewer` | **Дата**: 2026-08-22 | **Спецификация**: [spec.md](./spec.md)  
**Ввод**: подтверждённый ручной opt-in режим для выбранного обезличенного `spec.md`.

## Резюме

Добавить отдельную provider-neutral команду `spec-kitty spec-review`, которая разрешает канонический `spec.md`, выполняет локальный privacy-preflight, показывает disclosure summary, требует одноразовое подтверждение и только затем вызывает OpenCode через отдельный subprocess-runner. Ответ валидируется по `review-findings/v1` и сохраняется append-only артефактом на PRIMARY planning surface. Существующие `spec-kitty review` и `ProfileInvocationExecutor` не меняют семантику.

## Technical Context

Технический контекст реализации:

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Typer, Pydantic/dataclasses и PyYAML в рамках уже закреплённых зависимостей; внешний `opencode` CLI как опциональная runtime-зависимость  
**Storage / Хранение**: YAML-файлы `kitty-specs/<mission>/reviews/spec-review-<run-id>.yaml`; credentials не хранятся  
**Testing / Тестирование**: ATDD-first, unit и contract tests с fake runner; opt-in live smoke только на синтетическом `spec.md`  
**Target Platform / Платформы**: Windows 10+, Linux, macOS  
**Project Type / Тип проекта**: Python CLI  
**Performance Goals / Производительность**: локальный preflight до 2 секунд; timeout внешнего вызова 10–600 секунд, default 180  
**Constraints / Ограничения**: максимум 256 KiB входа, 2 MiB ответа, 100 findings; shell не используется; model ID configurable  
**Scale/Scope / Масштаб**: один выбранный `spec.md` и один внешний запуск на команду

## Инженерное выравнивание

### Существующие границы

- `src/specify_cli/cli/commands/review/` реализует post-merge mission review и остаётся без изменений интерфейса; превращать `review` в command group нельзя без compatibility break.
- `ProfileInvocationExecutor` прямо документирован как синхронная governance-seam, которая не вызывает LLM; внешний запуск в неё не добавляется.
- `mission_runtime.artifacts` — единственная authority для placement. Каталог `reviews/` сейчас не классифицирован, хотя исторически используется как review trail.
- `packs/built-in/agent_profiles/reviewer-renata.agent.yaml` задаёт reviewer role/rubric, но не является transport runner.

### Выбранные решения

1. Новый top-level интерфейс: `spec-kitty spec-review --mission <handle> [--model <id>] [--confirm-external]`.
2. CLI orchestration отделена от доменного пакета `specify_cli.spec_review`; subprocess скрыт за typed runner protocol.
3. Prompt передаётся только через stdin в `opencode run --pure --model <id>`; `shell=False`, argv строится списком.
4. Добавляется `MissionArtifactKind.SPEC_REVIEW` в PRIMARY partition и classifier entry для `reviews/`; выбор фиксируется ADR, потому что это стабильное planning evidence, а не per-WP coordination bookkeeping.
5. Успешные и неуспешные внешние запуски не меняют mission lifecycle. До consent и при preflight refusal файл не создаётся; после фактического внешнего старта сохраняется минимальный provenance/result artifact без prompt.
6. Auth полностью принадлежит OpenCode. Код не читает `auth.json`, env tokens или credential files и не логирует их пути.
7. Free/ZDR/ownership claims не входят в контракт. Default model — конфигурируемая текущая строка `opencode/x-preview-f-free`, которую provider может отклонить.

## Charter check

- **Единая authority**: placement идёт через новый `SPEC_REVIEW`, schema — через один parser/model, subprocess — через один runner.
- **Архитектурное соответствие**: существующие review/gate и invocation boundaries не смешиваются с внешним transport.
- **ATDD-first**: первый кодовый WP начинает с acceptance tests consent, scope и advisory failure.
- **Переносимость**: argv-list, stdin и fake runner исключают shell quoting.
- **Безопасность**: credential ownership, prompt redaction, size limits и sensitive-content refusal заданы до внешнего старта.
- **Качество**: Ruff, mypy, targeted tests и 90%+ coverage новых ветвей обязательны.
- **Git workflow**: работа остаётся на task-owned branch/worktrees; merge в upstream protected main выполняет оператор.
- **Code map gate**: `docs/codemap/` отсутствует; до первой product-code правки должны быть созданы и проверены `codemap.html`, `codemap.json`, `codemap.lock` с ответами «кто вызывает / что затрагивает / какие тесты покрывают».

Нарушений charter, требующих исключения, не выявлено.

## Поток выполнения

```mermaid
flowchart LR
    A[Автор выбирает mission] --> B[Разрешить канонический spec.md]
    B --> C[Privacy и size preflight]
    C -->|refuse| X[Локальная диагностика, 0 внешних вызовов]
    C --> D[Disclosure summary]
    D -->|нет consent| X
    D -->|явный consent| E[Governed rubric + spec через stdin]
    E --> F[OpenCode runner]
    F --> G[Schema и size validation]
    G --> H[Append-only review artifact]
    H --> I[Advisory summary, lifecycle без изменений]
```

## Структура проекта

### Артефакты миссии

```text
kitty-specs/ox-alpha-spec-reviewer-01M0N82A/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── review-findings-v1.schema.yaml
└── tasks.md
```

### Планируемые изменения исходного кода

```text
src/
├── mission_runtime/
│   └── artifacts.py                    # SPEC_REVIEW placement authority
└── specify_cli/
    ├── cli/commands/
    │   ├── __init__.py                 # регистрация spec-review
    │   └── spec_review.py              # тонкий Typer adapter
    └── spec_review/
        ├── __init__.py
        ├── models.py                   # request/result/finding/status
        ├── preflight.py                # canonical path, size, sensitive markers
        ├── prompt.py                   # bounded rubric + schema contract
        ├── runner.py                   # protocol + OpenCode subprocess adapter
        ├── parser.py                   # strict review-findings/v1 validation
        ├── service.py                  # use-case orchestration
        └── storage.py                  # collision-safe append-only writer

tests/
├── mission_runtime/
│   └── test_spec_review_artifact_placement.py
├── specify_cli/cli/
│   └── test_spec_review_command.py
└── specify_cli/spec_review/
    ├── test_preflight.py
    ├── test_prompt.py
    ├── test_runner.py
    ├── test_parser.py
    ├── test_service.py
    └── test_storage.py

docs/
├── adr/3.x/<date>-spec-review-is-primary-planning-evidence.md
├── codemap/codemap.html
├── codemap/codemap.json
└── codemap/codemap.lock
```

**Решение по структуре**: новый bounded context `spec_review` локализует external-review поведение. CLI остаётся тонким, а mission placement меняется только в canonical artifact seam.

## Карта implementation concerns

### IC-01 — Канонический вход и consent

- **Назначение**: не допустить неявную или чрезмерную внешнюю отправку.
- **Требования**: FR-001–FR-004, FR-011, NFR-001, NFR-002, NFR-007, C-005.
- **Поверхности**: `spec_review/preflight.py`, CLI adapter, tests.
- **Зависимости**: нет.
- **Риски**: TOCTOU между disclosure и запуском; spec необходимо перечитать и сверить SHA-256 после consent.

### IC-02 — Модель и schema contract

- **Назначение**: обеспечить детерминированный structured output и лимиты.
- **Требования**: FR-004, FR-007, NFR-004.
- **Поверхности**: `models.py`, `prompt.py`, `parser.py`, contract schema.
- **Зависимости**: IC-01 задаёт вход.
- **Риски**: OpenCode может смешать diagnostics и output; parser принимает только выделенный machine payload и fail-closed по формату.

### IC-03 — OpenCode transport

- **Назначение**: безопасно выполнить внешний процесс, не владея его credentials.
- **Требования**: FR-005, FR-006, FR-010, NFR-001, NFR-003, NFR-005, NFR-006, C-001–C-003.
- **Поверхности**: `runner.py`, runner tests.
- **Зависимости**: IC-02.
- **Риски**: timeout/child cleanup на Windows; stderr redaction; отсутствие live network в обычных tests.

### IC-04 — Review artifact authority

- **Назначение**: сохранить append-only provenance в правильной topology surface.
- **Требования**: FR-008, FR-009, FR-012, SC-003–SC-005.
- **Поверхности**: `mission_runtime/artifacts.py`, `storage.py`, ADR, placement tests.
- **Зависимости**: IC-02.
- **Риски**: неклассифицированный `reviews/` нарушит single authority; run ID должен быть ASCII и collision-safe.

### IC-05 — Оркестрация и operator UX

- **Назначение**: собрать preflight, consent, runner, parser и storage в advisory use case.
- **Требования**: FR-001–FR-012, SC-001–SC-006.
- **Поверхности**: `service.py`, `commands/spec_review.py`, command/service tests, quickstart.
- **Зависимости**: IC-01–IC-04.
- **Риски**: exit code не должен ошибочно блокировать основной workflow; при этом прямой пользовательский запуск обязан ясно сообщать собственный failed/partial status.

### IC-06 — Проверки и opt-in smoke

- **Назначение**: доказать privacy, portability и advisory semantics без зависимости CI от модели.
- **Требования**: все NFR и SC.
- **Поверхности**: tests, markers, documentation, codemap.
- **Зависимости**: IC-01–IC-05.
- **Риски**: green fake tests не подтверждают реальную модель; live smoke фиксируется отдельно и никогда не передаёт реальную project spec.

## Последовательность реализации

1. Сгенерировать code map и зафиксировать архитектурный baseline до product-code изменений.
2. Добавить red acceptance/contract tests для consent, input scope, failure taxonomy и non-mutation.
3. Ввести schema/domain models и parser с жёсткими лимитами.
4. Добавить preflight и TOCTOU hash recheck.
5. Добавить typed runner и исчерпывающие subprocess tests, включая Windows timeout cleanup.
6. Классифицировать `SPEC_REVIEW` как PRIMARY artifact, добавить ADR и topology tests.
7. Собрать service и CLI, сохранить append-only artifact, документировать operator UX.
8. Выполнить Ruff, mypy, targeted/full relevant tests и coverage gate.
9. Только после отдельного подтверждения внешней отправки выполнить live smoke на synthetic spec через Ox Alpha.

## Тестовая стратегия

- **Acceptance**: CLI без consent, CLI с fake success, provider timeout/error, invalid output, repeated/concurrent run.
- **Unit**: path containment, symlink escape, size boundaries, secret/PII marker detection, prompt composition, parser enums/limits, filename/run-id generation.
- **Contract**: точный argv OpenCode, stdin-only prompt, no shell, timeout cleanup, stable diagnostic codes, `review-findings/v1` round trip.
- **Architecture**: `ProfileInvocationExecutor` по-прежнему не импортирует/не вызывает runner; `reviews/` всегда разрешается как PRIMARY через mission runtime.
- **Privacy teeth tests**: уникальный sentinel из spec отсутствует во всех captured logs/errors/failure artifacts; каждый call-site, добавляющий логирование, имеет отдельную reversion-sensitive проверку.
- **Live smoke**: manual marker, synthetic input, explicit consent; ни один CI job не зависит от модели или бесплатного quota.

## Документация и совместимость

- Добавить краткую how-to секцию с prerequisites, disclosure example, запуском и чтением findings.
- Отметить OpenCode/Ox как optional integration; не рекламировать free/ZDR как контракт.
- `spec-kitty review` сохраняет текущую post-merge семантику; новая команда не меняет существующие flags и exit codes.
- Если появится публичный machine-readable CLI output, он получает отдельную versioned JSON schema; в v1 достаточно стабильного YAML artifact и human summary.

## Gates

- **До реализации**: baseline одобрен пользователем; Beads либо восстановлен project-local, либо blocker явно принят; code map создан.
- **До внешнего smoke**: отдельное подтверждение отправки synthetic spec; текущий model ID показан пользователю.
- **До PR**: Ruff, mypy, targeted tests, coverage новых ветвей ≥90%, full relevant suite, независимое review без unresolved severity 4–5.
- **До merge**: PR mergeable, CI green, diff соответствует миссии; merge выполняет уполномоченный оператор, deploy отсутствует.

## Complexity tracking

Исключения из charter не требуются. Новый artifact kind и ADR оправданы существующей single-authority placement архитектурой; запись напрямую в неклассифицированный `reviews/` была бы более рискованной и менее совместимой.
