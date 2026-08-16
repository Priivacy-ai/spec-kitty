# Решения

## 2026-08-14 — planning

- Canonical internal path representation для gate keys — repo-relative POSIX.
- Inventory не расширяется до независимой классификации call-site.
- E2E access и E2E result хранятся как разные fail-closed состояния.
- Beads lifecycle временно не используется, чтобы не писать в чужую глобальную DB.

## 2026-08-14 — post-plan audit

- Portability и collection closure объединены в один package с единым ownership.
- Full local suite и external E2E оформлены как acceptance/release gates, а не implementation packages.
- Static expected inventory не нормализуется той же функцией, что actual census.

## 2026-08-16 — финальная приёмка

- `local_ready` выставляется по одному проверенному integration SHA только при
  нуле failures/errors в обоих полных наборах; targeted и `--confcutdir`
  результаты не используются как замена.
- `overall_verdict` остаётся `blocked`, когда блокирован внешний E2E, даже если
  `implementation_complete=true` и `local_ready=true`. Это сохраняет fail-closed
  границу между локальным качеством и публикацией.
- WP07 разрешён как последовательный marker-only follow-up после WP04/WP05;
  frozen count floor не повышается и не превращается в wildcard allowlist.
- Запуск из корня integration worktree является частью handoff: cwd влияет на
  разрешение project root, поэтому ложные результаты из несвязанного cwd явно
  отделены от authoritative gates.
