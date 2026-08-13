# WP03 review cycle 1 — REQUEST_CHANGES

## Blocker 1 — обязательный full-lifecycle RED отсутствует

Коммит `f6368b27e` добавляет только два RED-теста: разрешение `context` и изоляцию двух caller-owned worktree. Независимый запуск этого snapshot дал `2 failed`, но в нём нет требуемого T011 production-CLI сценария `create -> status/context -> setup-plan/tasks -> implement/review -> next -> accept`. Остальные lifecycle-тесты появились уже в GREEN-коммите `512b3df33`, а существующий итоговый файл разбивает команды по независимым fixtures и не выполняет один сквозной lifecycle от создания Mission до accept.

Минимальное исправление: добавить один production-CLI acceptance test на реальном linked worktree, который последовательно выполняет полный T011 lifecycle, снимает branch/HEAD/tracked status repository-root checkout до и после и доказывает RED до соответствующей production-правки, затем GREEN. Не заменять этот oracle набором раздельных helper/fixture тестов.

## Blocker 2 — architectural guard не является repo-wide и допускает обход boundary

`tests/architectural/test_mission_operation_root_boundary.py` проверяет только пять вручную перечисленных функций (`setup-plan`, `implement`, `review`, `next`, `accept`). Он не охватывает обязательные `context`, `status`, tasks entrypoints/consumers и не фиксирует разрешённый набор foundation-callers. Проверка ограничена телом одной функции после строки resolver-call и не видит повторный lookup в вызываемых helpers. Поэтому удаление wiring в неперечисленном lifecycle consumer или добавление второго root authority там не делает gate красным, вопреки T014.

Минимальное исправление: сделать guard repo-wide census для mission-scoped lifecycle consumers с явным shrink-only/fixed allowlist только foundation-callers; включить context/status/planning/tasks/action/next/accept и доказать deletion/mutation sensitivity тестом, который падает при добавлении второго `locate_project_root`/`get_main_repo_root`/selector lookup после получения `MissionOperationContext`.
