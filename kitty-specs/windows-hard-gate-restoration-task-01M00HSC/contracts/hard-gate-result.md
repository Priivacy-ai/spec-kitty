# Контракт публикационного hard-gate результата

**Дата финальной проверки**: 2026-08-16
**Финальный product SHA**: `bcc33914d45319aacbed6e049bf8cada500b091b`
**Исходный approved SHA**: `6cc416c427edaa40c13fdf8a341e446be91bb3a5`
**Follow-up SHA**: `eae4dc006129f81bd0b0934d019a40d7d9dca42a`
**Integration worktree**: `C:\spkhg\.worktrees\windows-hard-gate-restoration-task-01M00HSC-integration`
**Integration branch**: detached HEAD, собран из lane-b и approved WP07

## Статусы

| Поле | Значение | Основание |
|---|---|---|
| `implementation_complete` | `true` | WP01–WP07 approved, task-owned product lanes clean |
| `local_ready` | `true` | Полные contract/architecture suites на одном immutable SHA: 0 failures, 0 errors |
| `e2e_access` | `blocked` | Нет доступа к canonical `Priivacy-ai/spec-kitty-end-to-end-testing` |
| `e2e_ready` | `false` | Внешний набор не запускался без доступа |
| `release_ready` | `false` | Требует `e2e_ready=true`; локальный pass его не заменяет |

`overall_verdict=pass` в acceptance matrix означает принятие локальной
mission readiness. Это не превращает внешний gate в pass: `e2e_access` остаётся
`blocked`, а `e2e_ready` и `release_ready` — `false`. Поэтому публикационная
готовность всё ещё заблокирована, хотя локальный hard-gate результат принят.

## Полные воспроизводимые gates

Команды запускались из корня integration worktree с task Python:

```powershell
$py = 'C:\codex-scratch\spklw-planning\.venv\Scripts\python.exe'
$env:PYTHONPATH = 'C:\spkhg\.worktrees\windows-hard-gate-restoration-task-01M00HSC-integration\src'
& $py -m pytest tests/contract -q --junitxml=C:\Users\Ruslan\AppData\Local\Temp\windows-hard-gate-contract-bcc33914d-cwd.xml
& $py -m pytest tests/architectural -q --junitxml=C:\Users\Ruslan\AppData\Local\Temp\windows-hard-gate-architecture-bcc33914d-cwd.xml
```

Результаты:

- contract: `305 passed, 3 skipped, 0 failed, 0 errors` за `179.41s`;
- architecture: `2120 passed, 5 skipped, 2 xfailed, 0 failed, 0 errors,
  14 warnings` за `4140.66s`;
- collection architecture завершена без ошибок;
- codemap JSON↔HTML parity и lock SHA-256 совпадают;
- task-owned integration tree clean на указанном SHA.

Предупреждения не скрыты: один диагностический `UserWarning` width guard и
13 `PytestWarning` о `record_property` с `xunit2`. Они не являются failures или
errors и не меняют readiness.

## Residual и follow-up

Предыдущий полный run на `6cc416c42` дал единственный новый residual: 25
неэкранированных `convert`-sites при frozen ceiling 24. WP07 добавил только
маркер `golden-count: cardinality-is-contract` на легитимную assertion
уникальности authority-записи. Ceiling не повышался. Снятие маркера снова
делает recurrence guard красным; после восстановления marker полный финальный
architecture gate зелёный.

## False-red и границы доказательств

Некоторые диагностические запуски из `C:\Users\Ruslan` или временного
worktree искали `kitty-specs` под текущим cwd и давали ложные project-root
ошибки. В acceptance учитывается только запуск из корня integration worktree,
где project root и mission metadata разрешились корректно.

Внешний E2E намеренно не подменён локальным smoke, зеркалом или operator
exception. До получения canonical доступа публикационная готовность остаётся
`false`.

## Privacy

В отчёте присутствуют только команды, пути workspace, публичные
идентификаторы, SHA и test counts. Токены, cookies, auth headers и credential
files не читались и не выводились.
