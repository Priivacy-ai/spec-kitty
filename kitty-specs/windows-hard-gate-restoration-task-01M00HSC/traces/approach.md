# Подход

## 2026-08-14 — planning

- Воспроизведены platform, inventory и collection классы отдельно.
- Выбран порядок: portability → real architecture classification → collection completeness → full gates → external E2E.
- Дорогой architecture suite ограничен финальной проверкой после targeted green.

## 2026-08-14 — post-plan audit

- Декомпозиция сокращена до двух последовательных implementation packages.
- На каждом окончательном SHA требуется полный local gate; внешний E2E остаётся отдельным release blocker.

## 2026-08-16 — финальная приёмка

- Полный gate повторён после approved WP07 на immutable SHA
  `bcc33914d45319aacbed6e049bf8cada500b091b`, а не на промежуточной ветке.
- Contract завершился как `305 passed, 3 skipped`; architecture — как
  `2120 passed, 5 skipped, 2 xfailed`, без failures/errors и collection errors.
- Единственный residual предыдущего полного run был вынесен в WP07: marker на
  легитимной cardinality assertion оставил frozen ceiling неизменным и прошёл
  mutation-проверку.
- Внешний E2E не подменялся локальным smoke: `e2e_access=blocked`, поэтому
  `e2e_ready=false` и `release_ready=false` сохранены.
