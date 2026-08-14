---
work_package_id: WP01
title: Восстановить приоритет Git preflight в setup-plan
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
planning_base_branch: codex/setup-plan-preflight-closeout
merge_target_branch: codex/setup-plan-preflight-closeout
branch_strategy: Planning artifacts for this mission were generated on codex/setup-plan-preflight-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/setup-plan-preflight-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Фаза 1 — regression fix
history:
- at: '2026-08-14T10:21:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- src/specify_cli/cli/selector_resolution.py
- tests/agent/test_agent_feature.py
- tests/integration/test_caller_owned_worktree_lifecycle.py
- tests/specify_cli/cli/commands/test_selector_resolution.py
- docs/codemap/codemap.json
- docs/codemap/codemap.html
- docs/codemap/codemap.lock
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Восстановить приоритет Git preflight в setup-plan

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Перед реализацией проверь `review_ref` в event log и Activity Log. Если пакет возвращён с review, каждый пункт feedback становится обязательным TODO; не расширяй scope сверх него без material replan.

---

## Review Feedback

На момент генерации feedback отсутствует. При повторном цикле используй canonical review artifact, указанный runtime, и не исправляй исторические замечания, уже закрытые более поздним verdict.

---

## Markdown Formatting

HTML/XML-теги заключай в backticks. Для code blocks указывай язык. Человекочитаемые activity notes пиши по-русски; команды, пути и идентификаторы оставляй без перевода.

---

## Objectives & Success Criteria

Цель — восстановить наблюдаемый контракт `setup-plan`, не отменяя caller-owned linked-worktree routing:

- после сохранённых hosted-auth и SaaS boundary gates Git preflight выполняется до Mission resolution;
- failed preflight возвращает `GIT_PREFLIGHT_FAILED` и существующую remediation в JSON и human режимах;
- на failed path Mission resolver и planning writes не вызываются;
- один вызов команды выполняет preflight ровно один раз;
- caller-owned linked worktree проверяется как активный checkout, а не как primary repository root;
- после успешного preflight Mission identity и anchor по-прежнему определяет только `MissionOperationContext`;
- обычный checkout сохраняет действующий feature-dir resolver;
- tests чувствительны к перестановке порядка, удалению early exit, второму вызову и неверному checkout root.

## Context & Constraints

Обязательные источники:

- `kitty-specs/setup-plan-preflight-closeout-01KZZT3V/spec.md`;
- `kitty-specs/setup-plan-preflight-closeout-01KZZT3V/plan.md`;
- `kitty-specs/setup-plan-preflight-closeout-01KZZT3V/research.md`;
- `kitty-specs/setup-plan-preflight-closeout-01KZZT3V/contracts/setup-plan-preflight.md`;
- `kitty-specs/setup-plan-preflight-closeout-01KZZT3V/quickstart.md`;
- `.kittify/charter/charter.md`;
- `docs/codemap/codemap.json` и `docs/codemap/codemap.lock` до первой code write.

До изменения production-кода ответь по карте кода:

1. Что вызывает `mission_setup_plan` и selector logic?
2. Какие lifecycle/placement поверхности затронет изменение?
3. Какие существующие тесты покрывают этот flow?

Архитектурные ограничения:

- `MissionOperationContext` остаётся единственной authority для Mission identity и `mission_anchor_root`.
- Checkout helper отвечает только за выбор Git checkout для policy preflight.
- Нельзя добавлять raw path-join для Mission artifacts или новый Mission resolver.
- Hosted-auth и SaaS boundary сохраняют текущий приоритет относительно Git ошибки.
- Helper выбора checkout не запускает Git subprocess; он переиспользует существующую common-dir abstraction.
- Production diff ограничен двумя заявленными модулями.
- Release, deploy, SaaS, user config и публикация в `main` вне scope.

Работай только в lane worktree, который вернёт runtime. Planning checkout не является местом для product writes.

## Branch Strategy

- **Planning base branch**: `codex/setup-plan-preflight-closeout`
- **Mission merge target**: `codex/setup-plan-preflight-closeout`
- **Delivery PR target**: `codex/spec-kitty-worktree-mission-create`
- **Execution**: `finalize-tasks` вычисляет lane в `lanes.json`; команда `spec-kitty agent action implement WP01 --agent codex --mission setup-plan-preflight-closeout-01KZZT3V` обязана вернуть точные worktree и branch.

Не создавай lane вручную, не переключай planning checkout и не коммить product code в planning branch. После implementation/review Mission merge идёт во внутренний merge target; отдельный проверенный task-owned PR публикует итог в delivery target.

## Subtasks & Detailed Guidance

### T001 — Зафиксировать RED для приоритета Git preflight и error contract

**Защищаемая поломка**: failed Git preflight сейчас маскируется более поздней ошибкой `PLAN_CONTEXT_UNRESOLVED`, потому что Mission resolution выполняется раньше.

Шаги:

1. Запусти существующий regression `test_setup_plan_exits_on_preflight_failure_json` на исходном HEAD и сохрани точную причину RED.
2. Расширь тесты так, чтобы независимые литеральные assertions проверяли:
   - error code `GIT_PREFLIGHT_FAILED`;
   - существующую remediation в JSON и human mode;
   - отсутствие `PLAN_CONTEXT_UNRESOLVED` на failed-preflight path;
   - ноль вызовов Mission resolver;
   - ноль planning writes/изменений артефактов.
3. Проверяй наблюдаемый CLI payload/exit behavior, а не порядок строк в production source.
4. Mock размещай только на внешних границах Git preflight и Mission resolution; сам command flow должен оставаться production.
5. Убедись, что RED вызван нужным порядком gate, а не ошибкой fixture/import/setup.

Файлы:

- `tests/agent/test_agent_feature.py`;
- при необходимости минимальный reusable fixture в том же owned test file.

Validation:

- исходный HEAD падает ожидаемо на error-contract assertion;
- тест стал бы зелёным только при раннем failed-preflight exit;
- human remediation проверяется отдельно от JSON payload.

Не вноси production fix до фиксации RED evidence в Activity Log/commit rationale.

### T002 — Добавить canonical helper выбора caller-owned linked checkout

**Защищаемая поломка**: простое использование `locate_project_root()` направит Git preflight в primary/repository checkout и пропустит состояние caller-owned linked worktree.

Рекомендуемый узкий API рядом с `is_same_repository_worktree_context`:

```python
def resolve_same_repository_worktree_root(
    project_root: Path,
    *,
    cwd: Path | None = None,
) -> Path | None:
    ...
```

Допустимо уточнить имя в рамках существующих naming conventions, но не менять семантику.

Шаги:

1. Переиспользуй `_nearest_checkout_root`, common-dir identity helper и `normcase`.
2. Возвращай caller checkout только когда:
   - `cwd` находится внутри Git checkout;
   - checkout является linked worktree;
   - его Git common dir совпадает с `project_root` repository identity.
3. Для unrelated checkout, ordinary primary checkout или неразрешимого пути возвращай `None`; caller выполняет fallback на `located_root`.
4. Не запускай `git`, `subprocess` или filesystem writes внутри helper.
5. Не читай Mission metadata и не возвращай `mission_anchor_root`.
6. Если существующий bool helper дублирует traversal, безопасно делегируй его новому primitive; не ломай публичный bool contract.

Фокусные helper tests:

- same-repository linked worktree возвращает exact caller checkout;
- ordinary checkout не выдаётся за linked checkout;
- unrelated linked checkout возвращает `None`;
- nested cwd нормализуется к checkout root;
- Windows case normalization не требует platform branch в production;
- no-subprocess oracle подтверждает отсутствие Git process calls.

Файлы:

- `src/specify_cli/cli/selector_resolution.py`;
- `tests/specify_cli/cli/commands/test_selector_resolution.py`.

Mutation check: helper, который без common-dir проверки возвращает любой nearest checkout, обязан быть убит unrelated-checkout тестом.

### T003 — Перестроить setup-plan на один ранний Git preflight

**Защищаемая поломка**: Mission resolver вызывается до Git policy, а наивный перенос может изменить auth/SaaS precedence или удвоить preflight.

Целевой порядок:

1. существующий hosted-auth gate;
2. существующий SaaS boundary gate;
3. выбор `active_git_checkout_root` через helper с fallback на `located_root`;
4. единственный вызов существующего Git preflight;
5. немедленный возврат существующего `GIT_PREFLIGHT_FAILED` при отказе;
6. caller-owned Mission resolution через `MissionOperationContext` либо существующий ordinary feature-dir resolver;
7. дальнейшая planning логика без изменения контракта.

Шаги:

1. Вычисли checkout root один раз и передай его в существующий preflight.
2. Не копируй formatter/remediation: используй текущую fail-path ветвь, чтобы JSON/human contract не разошёлся.
3. Удали/перемести прежний поздний preflight вместо добавления второго.
4. Не передавай active checkout root как Mission anchor и не материализуй Mission paths вручную.
5. Ordinary checkout должен продолжить `_resolve_setup_plan_feature_dir` или эквивалентную существующую ветвь.
6. Caller-owned branch после successful preflight должен вызвать `_resolve_setup_plan_operation` и получить canonical `MissionOperationContext`.

Файлы:

- `src/specify_cli/cli/commands/agent/mission_setup_plan.py`;
- возможно import нового helper из `selector_resolution.py`.

Validation:

- failed path: preflight call count `1`, Mission resolver `0`;
- successful ordinary path: preflight `1`, действующий feature-dir resolver;
- successful caller-owned path: preflight `1`, Mission resolver `1`;
- auth/SaaS failures сохраняют прежний приоритет и не требуют новых Git calls.

### T004 — Доказать caller-owned lifecycle и неизменность primary

**Защищаемая поломка**: mock-only command test может подтвердить payload, но не обнаружить preflight по primary root или запись Mission artifacts не в тот checkout.

Шаги:

1. Расширь реальный caller-owned linked-worktree integration scenario.
2. До вызова зафиксируй независимый snapshot защищённой primary surface:
   - список tracked/mission files, которые могут измениться;
   - содержимое или hashes релевантных файлов;
   - working-tree status, если это надёжно в существующем harness.
3. Запусти production `setup-plan` из nested cwd caller-owned worktree.
4. Spy/recording boundary должен показать, что preflight получил exact linked checkout root, а не primary repository root.
5. После успеха проверь корректные planning paths из canonical Mission context.
6. Сравни primary snapshot до/после и докажи отсутствие изменений.
7. Не подменяй Mission resolver synthetic result, если integration harness способен создать реальную Mission surface.

Файл:

- `tests/integration/test_caller_owned_worktree_lifecycle.py`.

Acceptance oracle:

- `repository_root`, active checkout и `mission_anchor_root` могут быть разными;
- Git preflight получает active checkout;
- topology/coordination сохраняют repository root;
- Mission artifacts используют anchor surface;
- primary snapshot идентичен.

Тест должен быть кроссплатформенным: используй `Path`, существующие Git test helpers и semantic comparisons, не литеральные slash-separated Windows пути.

### T005 — Добавить mutation/deletion sensitivity

Тесты считаются достаточными только если ловят реалистичные production regressions. Выполни узкие локальные mutations или эквивалентный deletion oracle для четырёх случаев:

1. Mission resolver снова вызывается до Git preflight.
2. Failed-preflight early return удалён и flow продолжается.
3. Добавлен второй вызов Git preflight.
4. В caller-owned scenario preflight получает `located_root`/primary вместо active linked checkout.

Для каждой мутации:

- назови наблюдаемую поломку;
- зафиксируй хотя бы один конкретный падающий test;
- восстанови production source без reset/checkout чужих изменений;
- повторно запусти узкий GREEN;
- не принимай grep-only проверку как единственное evidence.

Дополнительная helper mutation:

- удаление same-repository common-dir проверки должно падать на unrelated-checkout oracle;
- добавление subprocess в helper должно падать на no-subprocess guard либо быть явно обнаружено статическим тестом.

Результат запиши в Activity Log или commit rationale кратко: mutation → test that killed it.

### T006 — Выполнить gates, differential и codemap assessment

Минимальный verification packet:

1. Фокусные pytest:
   - preflight/error-contract tests;
   - selector helper tests;
   - caller-owned linked-worktree integration test.
2. `ruff check` для изменённых Python-файлов.
3. `mypy --strict` для изменённых production-файлов.
4. `python -m py_compile` для изменённых production-файлов.
5. `git diff --check` по cumulative Mission diff.
6. Exact owned-files diff и чистый lane status после commit.

Если широкий или соседний набор даёт красный результат:

- воспроизведи его на branch/base без product diff;
- классифицируй как regression или baseline;
- для baseline укажи существующий GitHub issue либо создай отдельный issue по charter;
- не маскируй новый failure ссылкой на общий технический долг.

Codemap gate:

- до правки зафиксирована текущая caller/impact/test цепочка;
- если module boundaries/edges не меняются, оставь codemap без косметического churn и запиши rationale;
- если helper создаёт новую значимую dependency/flow, синхронно обнови `docs/codemap/codemap.json`, `.html` и `.lock`, затем проверь parity и fingerprints.

Финальный evidence должен содержать RED/GREEN, mutation kills, exact tests, static gates, codemap decision, worktree/branch/commit и отсутствие deploy/release.

## Test Strategy

Применяй ATDD/TDD:

- сначала наблюдаемый RED текущей regression;
- expected получать литерально из публичного error contract и независимых filesystem snapshots;
- mocks держать на минимальной внешней границе;
- реальный linked-worktree integration обязателен для checkout/root semantics;
- каждый critical assertion должен защищать конкретную production-поломку;
- после GREEN выполнить узкие mutations и вернуть source в проверенное состояние.

Не ограничивайся общим `pytest passed`: в handoff перечисли, какой тест доказывает каждый FR.

## Risks & Mitigations

| Риск | Мера |
|---|---|
| Preflight проверяет primary вместо caller checkout | Exact argument oracle и реальный linked-worktree test |
| Появляется вторая Mission authority | Helper не читает Mission metadata; Mission context остаётся единственным anchor resolver |
| Меняется auth/SaaS error precedence | Фокусные regression tests существующих ранних gates |
| Выполняются два preflight | Call-count assertion и mutation с дублированием |
| Failed path успевает записать artifacts | Resolver/write spies и before/after snapshot |
| Cross-platform path mismatch | `Path`, common-dir identity и semantic comparisons |
| Baseline Windows failures смешиваются с diff | Branch/base differential и issue attribution |
| Codemap churn не соответствует границе | Обновлять три файла только при реальном boundary delta |

## Definition of Done

- [ ] T001–T006 отмечены `done` через штатный lifecycle.
- [ ] FR-001–FR-005 имеют test/output evidence.
- [ ] Failed JSON и human paths возвращают `GIT_PREFLIGHT_FAILED` с действующей remediation.
- [ ] Failed path не вызывает Mission resolver и не меняет planning artifacts.
- [ ] Один command invocation выполняет ровно один preflight.
- [ ] Caller-owned preflight получает exact active linked checkout root.
- [ ] Successful caller-owned flow использует canonical `MissionOperationContext`.
- [ ] Ordinary checkout сохраняет действующий feature-dir behavior.
- [ ] Primary snapshot не меняется.
- [ ] Четыре обязательные mutations убиты тестами.
- [ ] Ruff, strict mypy, py_compile и diff-check зелёные.
- [ ] Codemap parity/fingerprint подтверждены либо документировано, почему обновление не требуется.
- [ ] Lane содержит только owned/обоснованные out-of-map файлы и чист после commit.
- [ ] Release/deploy/main publication не выполнялись.

## Review Guidance

Reviewer обязан независимо проверить:

1. Точный порядок hosted-auth → SaaS boundary → Git preflight → Mission resolution.
2. Один вызов preflight во всех релевантных путях.
3. Exact checkout argument в caller-owned path.
4. Ноль Mission resolution/write на failed path.
5. Отсутствие новой Mission-root authority или raw Mission path-join.
6. Реальную чувствительность committed tests, а не только synthetic fixtures.
7. Mutation evidence по четырём обязательным дефектам.
8. Cross-platform semantics и отсутствие новых subprocess в checkout helper.
9. Exact owned diff, codemap decision и static gates.

Review blocker, если тесты не отличают primary root от active linked checkout, если failure contract проверяется только mock payload, если helper принимает unrelated checkout или если preflight вызывается до SaaS boundary/после Mission resolver.

## Activity Log

- 2026-08-14T10:21:17Z — system — Prompt generated via `/spec-kitty.tasks`; реализация не начата.

После каждого implementation/review cycle добавляй краткую запись: commit, RED/GREEN, mutation evidence, gates, blockers и lifecycle result. Не вставляй длинные логи или внутренние секреты.
