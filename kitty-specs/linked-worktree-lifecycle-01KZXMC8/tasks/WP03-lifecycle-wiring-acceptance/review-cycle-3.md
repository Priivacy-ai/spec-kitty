# WP03 review cycle 3 — REQUEST_CHANGES

## Blocker 1 — tasks lifecycle всё ещё обходит общий Mission resolver

Сквозной тест `test_complete_caller_owned_cli_lifecycle_keeps_primary_unchanged`
теперь действительно создаёт Mission и вызывает production CLI для context/status,
setup-plan, tasks status/finalize, action implement/review, next и accept. Однако
обязательные переходы `in_progress -> for_review` и `in_review -> done` он выполняет
напрямую через `append_event(..., force=True)`, а не через production tasks CLI.

Это скрывает незакрытые mission-scoped consumers: `tasks.py`,
`tasks_move_task.py` и `tasks_mark_status.py` по-прежнему вызывают raw
`locate_project_root` / `_find_mission_slug` и не получают
`MissionOperationContext`. Поэтому FR-002/T013 для tasks surface не доказаны,
а полный lifecycle может снова выбрать primary checkout на реальном
`move-task`/`mark-status` шаге.

Минимальное исправление: провести уже разрешённый operation context через
`move-task` и `mark-status` (без нового root authority) и заменить прямые
`append_event` в acceptance-сценарии хотя бы одним реальным production CLI
переходом до review и одним после review. Оставить снимок branch/HEAD/tracked
status primary до и после.

## Blocker 2 — architectural guard остаётся ручным списком, а не repo-wide census

`test_mission_operation_root_boundary.py` сканирует только фиксированный tuple
из 15 файлов. Новый или уже существующий mission-scoped consumer вне tuple не
попадает в gate. Это уже наблюдается на перечисленных выше tasks-модулях и на
`mission_branch_context.py`, где raw root lookup существует, но тест остаётся
зелёным. Mutation test добавляет второй lookup лишь в одном уже включённом
файле и не доказывает обнаружение обхода за пределами tuple.

Минимальное исправление: строить census динамически по production `src/**` для
call sites общего operation resolver и всех mission-scoped lifecycle entrypoints
либо добавить отдельный проверяемый inventory, чья полнота выводится из реальных
CLI registrations/call sites. Зафиксировать shrink-only allowlist только
foundation-callers и mutation, добавляющую raw lookup в ранее не перечисленный
lifecycle consumer; gate должен стать красным.

## Проверки review

- `195 passed` — scoped caller-owned/status/transaction regressions.
- `4 passed` — full-lifecycle + architectural tests отдельно.
- Ruff по изменённым Python-файлам: PASS.
- Codemap: 7/7 nodes, 11/11 edges, оба SHA-256 совпадают с lock.
- Broad `mypy --strict` по 10 затронутым production-модулям: 13 ошибок на
  строках, которые `git blame` относит к старым коммитам; это не новая
  регрессия WP03, но текущий gate целиком зелёным не является.

## Anti-pattern checklist

1. Dead code — PASS: новый `mission_anchor_root` имеет production callers.
2. Synthetic-fixture test — FAIL: два lifecycle-перехода заменены прямой
   записью event fixture и не проверяют production tasks CLI.
3. Silent empty return — PASS: новых недокументированных silent-empty ветвей не найдено.
4. FR coverage — FAIL: FR-002/T013 не покрывают `move-task`/`mark-status` в caller-owned worktree.
5. Frozen surface — N/A: frozen/untouchable файлы не заданы.
6. Locked decision — FAIL: C-002 нарушается raw root/selector lookup в tasks consumers вне общего context.
7. Shared-file ownership — PASS: WP03 основан на утверждённом WP02 и изменения входят в owned files.
8. Production fragility — PASS: новых недокументированных fail-loud `raise` не обнаружено.
