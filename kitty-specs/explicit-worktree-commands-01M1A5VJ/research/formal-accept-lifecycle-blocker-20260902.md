# Блокер формальной приёмки после bootstrap

## Выполнено

- `finalize-tasks --owned-checkout` создал канонические `lanes.json`,
  `status.json`, acceptance matrix и WP01.
- `planning_commit_sha` исправлен на `9ad0dee2c84e5ca60300fe8cbaaa7f39223ba836`:
  это проверенный planning-коммит перед первым implementation-коммитом
  `603e7b250`.
- WP01 штатно переведён `planned -> in_progress` в выбранной рабочей копии.
- Primary checkout остался чистым на
  `7b6c9f4fadf3f551e578f2c7176b8f134b38daaa`.

## Воспроизводимый блокер

Команда перехода WP01 в `for_review` остановилась, потому что канонические
состояния T001-T013 остаются `pending`. Отметки `[x]` в `tasks.md` являются
справочным текстом и не заменяют события `InnerStateChanged`.

Штатная команда для записи этих событий, `agent tasks mark-status`, не имеет
`--owned-checkout`. Её текущий write path в
`tasks_shared._ensure_target_branch_checked_out` явно вызывает
`get_main_repo_root(repo_root)` и закрепляет сериализацию за primary checkout.
`tasks_mark_status._ms_resolve_read_dir` затем строит `MissionHandle` и status
surface от этого main root. Поэтому даже `SPECIFY_REPO_ROOT`, указывающий на
выбранный worktree, перед записью снова канонизируется в primary.

Запуск `mark-status` не выполнялся: он не может безопасно записать lifecycle
этой локальной mission в выбранную копию. `--force` также не применялся.

Повторный read-only запуск `accept --diagnose --lenient --owned-checkout`
выбрал task-ветку и вернул `ok=false` без dirty-файлов. Он подтвердил WP01 в
`in_progress` и два последовательных gate: сначала довести WP01 до
`approved`/`done`, затем подтвердить пока ещё `pending` acceptance matrix.
`--lenient` превратил отсутствие `contracts/` только в предупреждение и не
обошёл ни lifecycle, ни acceptance matrix.

## Решение

Формальная приёмка остаётся `partial`. Следующая реализация требует отдельного
согласованного изменения: добавить `--owned-checkout` в `mark-status` с теми же
проверками владения и изоляции, что уже действуют для `move-task`. До этого
нельзя честно провести WP01 через `for_review -> in_review -> approved` и
запустить финальную локальную приёмку.

Никаких push, PR, merge, install или publication не выполнялось.
