---
work_package_id: WP02
title: Architecture classification, topology remediation и acceptance
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-005
- FR-007
- FR-008
- FR-009
- FR-010
planning_base_branch: codex/setup-plan-hard-gates
merge_target_branch: codex/setup-plan-hard-gates
branch_strategy: Пакет начинается только от approved WP01, исполняется в отдельной lane и после review возвращается в codex/setup-plan-hard-gates.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
phase: Фаза 2 — architecture remediation и acceptance
history:
- at: '2026-08-14T16:36:00Z'
  actor: codex
  action: Prompt подготовлен после post-plan Sol-аудита
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/mission_creation.py
- src/specify_cli/missions/_read_path_resolver.py
- tests/architectural/test_surface_resolution_audit.py
- tests/architectural/test_topology_resolution_boundary.py
- tests/architectural/test_untrusted_path_containment.py
- tests/architectural/surface_resolution_audit/inventory.md
- tests/architectural/untrusted_path_audit/inventory.md
- docs/codemap/codemap.json
- docs/codemap/codemap.html
- docs/codemap/codemap.lock
role: implementer
tags:
- architecture
- topology
- codemap
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 — Architecture classification, topology remediation и acceptance

## Сначала загрузить профиль

Используй `/ad-hoc-profile-load` для `python-pedro`, затем полностью прочитай этот prompt, mission spec/plan/research/contract/quickstart, charter и approved WP01 handoff. Работай только в lane worktree, возвращённом runtime.

## Цель и критерии успеха

На уже исправленном Windows oracle:

- независимо воспроизвести missing inventory для `_compose_mission_anchor_feature_dir`;
- независимо воспроизвести raw coord-topology predicate в `mission_creation.py`;
- определить для каждого сигнала: stale inventory либо real boundary bypass;
- real bypass исправить через canonical topology/resolution authority до inventory sync;
- если predicate является необходимым create-time invariant, оформить минимальное точечное исключение с отдельным negative oracle и rationale;
- обновить оба inventories только по фактическому финальному code shape;
- обновить JSON/HTML/lock code map в том же commit, что production boundary;
- доказать callers/impact/tests независимым oracle, не только parity/hash;
- на одном окончательном SHA выполнить local acceptance;
- внешний E2E access/result отразить без green-wash.

## Обязательные источники и code map gate

Прочитай:

- `kitty-specs/windows-hard-gate-restoration-task-01M00HSC/spec.md`;
- `plan.md`, `research.md`, `data-model.md`, `quickstart.md`;
- `contracts/hard-gate-result.md`;
- approved WP01 prompt/handoff/review artifact;
- `.kittify/charter/charter.md`;
- `docs/codemap/codemap.json` и `.lock` до первой production write.

До изменения production-кода письменно ответь:

1. Кто вызывает `_compose_mission_anchor_feature_dir` и create-time topology corroboration?
2. Какие read/write/placement boundaries затрагивает каждый вариант исправления?
3. Какие существующие tests/audits покрывают эти flows?

Текущая карта не отвечает на всё это. Сначала зафиксируй read-only baseline; в production commit добавь необходимые nodes/edges/tests и синхронный HTML/lock.

## Ограничения

- Не изменять WP01-owned files.
- Не добавлять второй Mission resolver, raw Mission path join или parallel topology authority.
- Не расширять allowlist до всей `mission_creation.py` или каталога.
- Inventory update не может быть единственным исправлением real bypass.
- JSON/HTML parity и lock hash не заменяют callers/impact/tests coverage oracle.
- Full local tests являются acceptance gate: их failures возвращаются в owning task, а не становятся новым unplanned WP.
- External E2E repository не изменяется; credentials не читаются и не печатаются; access blocker не превращается в pass.
- Любой дополнительный production или inventory file требует material replan.

## T007 — RED-first architecture contract

Отдельный test-only RED commit обязан закрепить:

1. `surface_resolution_audit` обнаруживает `_compose_mission_anchor_feature_dir` как missing inventory row.
2. `untrusted_path_audit` обнаруживает тот же sink независимо от первого audit.
3. Topology boundary test обнаруживает raw coord-path predicate в `mission_creation.py`.
4. Synthetic rogue call-site в временной копии/fixture заставляет audit падать, даже если текущий inventory синхронизирован.
5. Исключение для create-time invariant, если оно потребуется, не разрешает соседний raw predicate с другой семантикой.

RED commit не содержит production, inventory или code map changes. Зафиксируй exact failures на approved WP01 base.

## T008 — Tidy-first и read-only codemap baseline

До functional commit:

- осмотри две production functions на локальное дублирование authority, сложность и stale comments;
- проверь Ruff/mypy diagnostics только owning production files;
- из текущего codemap извлеки callers/impact/tests; явно запиши отсутствующие связи;
- если cleanup нужен, отдельный behavior-preserving commit внутри owned files; иначе `none found` evidence без пустого commit.

Не обновляй code map до выбора production shape.

## T009 — Классификация и исправление boundary

Для каждого текущего сигнала сформируй таблицу:

| Signal | Current call-site | Canonical authority | Verdict | Fix |
|--------|-------------------|---------------------|---------|-----|
| Missing `_compose_mission_anchor_feature_dir` row | `_read_path_resolver.py` | read/placement seam | stale inventory или bypass | точное действие |
| Raw coord predicate | `mission_creation.py` | topology classifier/registered worktree authority | bypass или необходимый invariant | точное действие |

Правила:

- если canonical function уже владеет решением — production caller делегирует ей;
- если helper только композирует путь после уже resolved anchor, inventory может классифицировать его как санкционированный leaf, но negative oracle обязан ловить untrusted pre-resolution join;
- если create-time topology нельзя воспроизвести runtime classifier до `lanes.json`, исключение должно быть на конкретный AST pattern/qualname с rationale; соседний raw decision остаётся запрещён;
- не менять публичный error contract без material replan.

## T010 — Inventories и code map в том же commit

После production shape:

- обновить `surface_resolution_audit/inventory.md` и `untrusted_path_audit/inventory.md` точными composite keys/dispositions;
- обновить `docs/codemap/codemap.json`, `.html`, `.lock` в том же commit, что production boundary;
- JSON и HTML должны иметь exact node/edge/reference parity;
- lock hashes считаются canonical project algorithm;
- независимый test/assertion проверяет, что карта содержит callers, impact и tests для обеих boundaries;
- line-only churn без semantic delta не добавлять.

## T011 — Negative/mutation sensitivity

Обязательные мутации:

1. Добавить новый untrusted anchor join вне inventory — оба relevant audits либо owning audit падает ожидаемо.
2. Удалить canonical topology delegation/вернуть raw predicate — topology gate падает.
3. Расширить узкое исключение до всего файла — соседний rogue predicate проходит production scanner, но dedicated negative test обязан упасть.
4. Удалить одну callers/impact/tests edge из codemap JSON — independent coverage oracle падает, даже если JSON/HTML parity искусственно сохранена.
5. Оставить stale inventory row после удаления call-site — overcount/shrink-only gate падает.

Временно применять мутации точечным patch, фиксировать убивший test, восстанавливать точечным patch и повторять GREEN. Reset/checkout запрещены.

Targeted GREEN:

- три owning architecture test files;
- оба audit modules через их public entry points;
- related canonical resolver/topology tests;
- approved WP01 portability/collection sentinel tests;
- Ruff и strict mypy для двух production files;
- py_compile, cumulative diff-check;
- codemap parity/hash/coverage;
- exact owned diff.

## T012 — Local acceptance и external E2E gate

После targeted GREEN создать окончательный candidate SHA и не менять файлы во время проверки.

Local commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\contract -q
.\.venv\Scripts\python.exe -m pytest tests\architectural -q
```

Требуется `0 failed`, `0 errors`. Existing documented skip/xfail перечислить отдельно. Если full run обнаружил defect:

1. классифицировать ownership WP01/WP02;
2. вернуть соответствующий package/task в работу;
3. исправить через RED/GREEN;
4. создать новый candidate SHA;
5. повторить full gate на новом SHA.

External gate:

- read-only проверить доступ текущего GitHub principal к `Priivacy-ai/spec-kitty-end-to-end-testing`;
- при доступе прочитать canonical instructions и запустить documented compatible packet против exact CLI SHA;
- при отсутствии доступа записать `e2e_access=blocked`, `e2e_ready=false`, `release_ready=false`;
- локальная реализация при этом может иметь `implementation_complete=true` и `local_ready=true`;
- не создавать локальный clone substitute, exception или секретный auth workaround.

## T013 — SHA-bound handoff

Итоговый handoff содержит:

- worktree, branch, implementation/review commits;
- exact final SHA, после которого файлы не менялись;
- RED/GREEN и mutation evidence по FR-004/005/007/008;
- contract/architecture counts, skip/xfail;
- codemap parity, hashes и callers/impact/tests evidence;
- `implementation_complete`, `local_ready`, `e2e_access`, `e2e_ready`, `release_ready`;
- ссылку/комментарий в pre-existing failure issue;
- оценку трёх tracer files;
- clean lane status.

## Definition of Done

- [ ] T007–T013 done через runtime.
- [ ] Отдельный RED commit предшествует production/inventory changes.
- [ ] Каждый signal имеет независимую классификацию и rationale.
- [ ] Real bypass исправлен через canonical authority; узкое исключение, если есть, имеет dedicated negative test.
- [ ] Inventories синхронизированы без wildcard/blanket growth.
- [ ] Code map обновлена в production commit и проходит parity/hash/coverage.
- [ ] Пять mutations убиты.
- [ ] Contract и architecture full suites имеют `0 failed`, `0 errors` на финальном SHA.
- [ ] External E2E state не green-wash'ится.
- [ ] Ruff, strict mypy, py_compile, diff-check и exact scope зелёные.
- [ ] Handoff SHA-bound, lane clean, issue/tracers обновлены.

## Review guidance

Reviewer обязан независимо проверить:

1. RED commit реально красный на approved WP01 base.
2. Missing sink не закрыт одной строкой inventory без disposition oracle.
3. Raw predicate не спрятан broad allowlist.
4. Нет второй topology/path authority.
5. Negative tests невакуумны и ловят rogue call-site.
6. Code map coverage независим от parity/hash.
7. Full local suites выполнены на exact финальном SHA.
8. `implementation_complete` не подменяет `release_ready`.
9. WP01-owned files не изменены.
10. External access проверен read-only без credentials.

Review blocker, если full suite выполнен до последнего code change, если expected inventory сам нормализуется implementation helper, если E2E blocker скрыт или если mutation evidence synthetic/helper-only.

## Activity Log

- 2026-08-14T16:36:00Z — codex — Prompt подготовлен; реализация не начата.
