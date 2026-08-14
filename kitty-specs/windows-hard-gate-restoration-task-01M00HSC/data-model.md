# Модель результата hard-gates

**Дата**: 2026-08-14
**Тип**: Reference

Mission не добавляет product storage. Для handoff используется концептуальная модель доказательств.

## GateResult

| Поле | Значение |
|------|----------|
| `gate` | `contract`, `architectural`, `collection`, `e2e_access`, `e2e_tests` |
| `state` | `pass`, `fail`, `blocked`, `not_run` |
| `command` | Точная воспроизводимая команда без секретов |
| `commit` | Проверенный Git SHA |
| `passed` / `failed` / `errors` / `skipped` / `xfailed` | Числовые counts, если применимо |
| `primary_cause` | Первая подтверждённая причина failure/blocker |
| `evidence` | Пути к test/report artifacts без credentials |

## ReadinessResult

| Поле | Условие `true` |
|------|----------------|
| `implementation_complete` | Оба implementation package приняты, task-owned tree clean |
| `local_ready` | Contract, architecture, collection и code map gates зелёные на одном финальном SHA |
| `e2e_ready` | Canonical E2E repo доступен и его tests зелёные для того же CLI SHA |
| `release_ready` | `implementation_complete && local_ready && e2e_ready` |

## Инварианты

- `state=pass` требует `failed=0` и `errors=0`.
- `e2e_tests=pass` невозможен, если `e2e_access != pass`.
- `implementation_complete=true` не означает `release_ready=true`.
- `blocked` не преобразуется в `pass` и не смешивается с product failure.
- Каждый inventory/allowlist delta ссылается на конкретный call-site и negative/mutation evidence.
- Handoff относится к одному exact commit и чистому task-owned worktree.
