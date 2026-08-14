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
