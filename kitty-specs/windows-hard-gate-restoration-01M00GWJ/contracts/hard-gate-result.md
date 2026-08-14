# Контракт публикационного hard-gate результата

**Дата**: 2026-08-14
**Тип**: Reference

## Локальная готовность

`local_ready=true` допустим только при одновременном выполнении:

- contract: `0 failed`, `0 errors`;
- architecture: `0 failed`, `0 errors`;
- collection: `0 errors`;
- code map parity и hashes совпадают;
- task-owned worktree clean на указанном commit.

## Cross-repo готовность

| Access | Tests | Результат |
|--------|-------|-----------|
| pass | pass | `e2e_ready=true` |
| pass | fail | `e2e_ready=false`, product/test failure |
| blocked | not_run | `e2e_ready=false`, external blocker |
| not_run | not_run | `e2e_ready=false`, incomplete evidence |

Никакое локальное состояние не заменяет `e2e_ready=true`.

## Privacy

В отчёте разрешены команды, публичные repo identifiers, commit SHA и test counts. Запрещены токены, auth headers, cookies и содержимое credential files.
