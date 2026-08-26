---
title: 'ADR: результаты ревью спецификации — PRIMARY planning evidence'
description: 'Закрепляет результаты внешнего ревью спецификации как PRIMARY planning evidence, не относя их к lifecycle work package и сохраняя canonical placement.'
status: Accepted
date: '2026-08-22'
---

# ADR: результаты ревью спецификации — PRIMARY planning evidence

**Статус:** принято для миссии `ox-alpha-spec-reviewer-01M0N82A`  
**Дата:** 2026-08-22

## Контекст

Ручной внешний ревьюер создаёт host-owned результат только после явного
согласия автора и валидации ответа. Этот результат нужен автору миссии как
долговечное доказательство advisory-ревью; он не является записью жизненного
цикла work package и не управляет состоянием миссии.

В topology с coordination branch нельзя классифицировать такие результаты по
каталогу `reviews/`: directory-level правило захватит historical и чужие файлы.
Нужна единая placement-seam, которая одинаково определяет read path, write path
и commit target для всех topology.

## Решение

1. Вводится `MissionArtifactKind.SPEC_REVIEW`. Он входит только в PRIMARY
   partition и разрешается через `resolve_artifact_surface`; writer не выводит
   путь из cwd, raw `feature_dir` или topology-ветвлений.
2. Classifier распознаёт только файл, у которого первый segment — `reviews`, а
   имя соответствует `spec-review-*.yaml`. Вложенный `reviews/foo/...`, bare
   directory, другие расширения и historical `*.findings.yaml` не получают этот
   kind.
3. Новые результаты живут на canonical PRIMARY surface во время planning,
   execution и consolidation. После publication они остаются owned evidence на
   consolidated PRIMARY target; отсутствие coordination branch не меняет их
   authority.
4. Existing review files не мигрируются и не переклассифицируются. Stale copy
   на PRIMARY — реальный owned artifact, а не coordination residue.
5. Writer принимает только host-built `SpecReviewRun` и context миссии. Run ID
   ASCII-only; destination проверяется на containment и точный компонент
   `reviews` непосредственно перед открытием.
6. Каждый write использует exclusive create в resolved destination. Коллизия
   порождает новый collision-resistant suffix в ограниченном числе локальных
   попыток; это не повтор внешнего model call. Temp cleanup допускается только
   для доказанно собственного пути. При `write_failed` final artifact не
   остаётся, findings не персистятся, а наружу выходят лишь код и metadata
   target.

## Lifecycle и ownership

| Фаза | Read/write surface | Commit target | Семантика |
|------|--------------------|---------------|-----------|
| Planning | PRIMARY | primary target | Результат ещё не создаётся; контракт определяет home. |
| Execution | PRIMARY | primary target | Новый review artifact создаётся только после external start. |
| Consolidation | PRIMARY | primary target | Артефакт остаётся стабильным evidence, не переносится в coord. |
| Publication | consolidated PRIMARY | published primary target | Сохранённый результат остаётся читаемым без coordination branch. |

## Альтернативы

- **REVIEW_CYCLE**: отклонено. Это повторяемое per-WP lifecycle bookkeeping, а
  не evidence пользовательского advisory-ревью.
- **ISSUE_MATRIX**: отклонено. Matrix хранит вердикты по tracker/issue, не
  validated model result и не подходит для append-only run history.
- **Directory fallback для `reviews/`**: отклонено. Оно меняет семантику
  historical и unrelated файлов.
- **Прямой `feature_dir / "reviews"`**: отклонено. Обходит canonical resolver,
  topology matrix и commit target.

## Последствия

Classifier, partition membership и writer поставляются как одна working
boundary. Тесты обязаны проверять реальные path и commit target для single,
coord, lanes, lanes-with-coord, backfilled, deleted-coord и post-consolidation
topology; также обязательны collision, concurrency, symlink/reparse и
legacy-negative случаи.
