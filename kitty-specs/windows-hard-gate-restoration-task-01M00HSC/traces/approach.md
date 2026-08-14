# Подход

## 2026-08-14 — planning

- Воспроизведены platform, inventory и collection классы отдельно.
- Выбран порядок: portability → real architecture classification → collection completeness → full gates → external E2E.
- Дорогой architecture suite ограничен финальной проверкой после targeted green.

## 2026-08-14 — post-plan audit

- Декомпозиция сокращена до двух последовательных implementation packages.
- На каждом окончательном SHA требуется полный local gate; внешний E2E остаётся отдельным release blocker.
