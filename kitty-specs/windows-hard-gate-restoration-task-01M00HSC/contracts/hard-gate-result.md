# Контракт публикационного hard-gate результата

**Дата**: 2026-08-14
**Тип**: Reference

## Завершённость реализации и локальная готовность

`implementation_complete=true` означает, что оба implementation package приняты и task-owned tree clean. Это состояние не заменяет локальные или внешние gates.

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

`release_ready=true` требует одновременно `implementation_complete=true`, `local_ready=true` и `e2e_ready=true`. Никакое локальное состояние не заменяет `e2e_ready=true`.

## Privacy

В отчёте разрешены команды, публичные repo identifiers, commit SHA и test counts. Запрещены токены, auth headers, cookies и содержимое credential files.

## Текущий snapshot после полного gate WP03

На GREEN SHA WP03 `06026d6d0` состояние реализации `implementation_complete=true`,
но `local_ready=false`: полный contract gate подтверждён как `305 passed, 3 skipped`,
а полный architecture run дал `2107 passed, 5 skipped, 2 xfailed, 1 warning,
8 failed`.

WP03 закрыл четыре подтверждённых residual-класса:

- Windows-разделители в ключах doctrine/kernel census;
- CRLF checkout против LF-ориентира glossary seed без изменения самого seed;
- stale golden-count ceilings и один новый cardinality-only site;
- изменение parametrized node-id у capability fallback.

Полный gate выявил четыре новые группы, вынесенные в WP04–WP05:

- raw `parent.parent` mission-anchor derivation в `status_transition`;
- Windows-разделитель в checkout-grammar diagnostic path;
- stale exact token для `RealCoordCommitRouter.feature_write_dir`;
- CRLF-sensitive сравнение SHA-256 code-map lock.

CLI width guard проверен официальным запуском с корневым `tests/conftest.py` и дал
`3 passed, 1 warning`; его красный результат в диагностическом `--confcutdir`
режиме не считается локальным failure.

До завершения WP06 acceptance matrix должна оставаться `local_ready=false`.
`e2e_access=blocked`, `e2e_ready=false` и `release_ready=false` сохраняются
независимо от локального результата.
