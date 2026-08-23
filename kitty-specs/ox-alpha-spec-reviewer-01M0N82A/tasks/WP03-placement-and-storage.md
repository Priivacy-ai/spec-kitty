---
work_package_id: WP03
title: Canonical PRIMARY placement и atomic storage
dependencies:
- WP01
- WP02
requirement_refs:
- C-004
- FR-008
- FR-009
- FR-012
- NFR-001
- NFR-005
- NFR-008
planning_base_branch: codex/ox-alpha-spec-reviewer
merge_target_branch: codex/ox-alpha-spec-reviewer
branch_strategy: Planning artifacts for this mission were generated on codex/ox-alpha-spec-reviewer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/ox-alpha-spec-reviewer unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 2 - Artifact authority
history:
- at: '2026-08-22T17:51:11Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
agent: codex
authoritative_surface: src/mission_runtime/
create_intent:
- src/specify_cli/spec_review/storage.py
- tests/mission_runtime/test_spec_review_artifact_placement.py
- tests/specify_cli/spec_review/test_storage.py
- docs/adr/3.x/2026-08-22-spec-review-is-primary-planning-evidence.md
execution_mode: code_change
model: ''
owned_files:
- src/mission_runtime/artifacts.py
- src/mission_runtime/resolution.py
- src/specify_cli/spec_review/storage.py
- tests/mission_runtime/test_spec_review_artifact_placement.py
- tests/specify_cli/spec_review/test_storage.py
- docs/adr/3.x/2026-08-22-spec-review-is-primary-planning-evidence.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Canonical PRIMARY placement и atomic storage

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `architect-alphonso`
- **Role**: `implementer`
- **Agent/tool**: `codex`

---

## ⚠️ IMPORTANT: Review Feedback

Проверь `review_ref`. Load-bearing findings по placement нельзя откладывать в другой WP.

## Review Feedback

Уже учтено: filename-only classifier, canonical resolver, topology matrix, atomic exclusive create и legacy compatibility.

## Objectives & Success Criteria

- Ввести `MissionArtifactKind.SPEC_REVIEW` как PRIMARY planning evidence.
- Классифицировать только `reviews/spec-review-*.yaml`; historical `*.findings.yaml` и unrelated files остаются прежними.
- Storage получает path/target исключительно через canonical runtime seams.
- Ни cwd, ни raw `feature_dir/reviews` не определяют место записи.
- Concurrent calls не перезаписывают файлы и не выходят из mission surface.
- ADR объясняет ownership до/после consolidation и stale-copy semantics.

## Context & Constraints

Обязательные источники:

- `plan.md` IC-04 и test strategy.
- `data-model.md` lifecycle/persistence.
- `src/mission_runtime/artifacts.py`: enum, partitions, classifier.
- `src/mission_runtime/resolution.py`: `PlacementSeam`, `resolve_artifact_surface`, topology/E2 rules.
- ADR о review-cycle artifacts для противопоставления per-WP bookkeeping.

Не использовать directory-level `_COORD_RESIDUE_DIRS["reviews"]`. Не мигрировать existing files. Изменение artifact kind и writer обязаны land в одном WP.

## Branch Strategy

- **Planning base**: `codex/ox-alpha-spec-reviewer`
- **Merge target**: `codex/ox-alpha-spec-reviewer`
- WP может выполняться параллельно WP04 после WP02; files не пересекаются.

## Subtasks & Detailed Guidance

### T011 — ADR о placement ownership

- Зафиксируй, почему advisory spec review — стабильное planning evidence, а не `ISSUE_MATRIX` или `REVIEW_CYCLE` bookkeeping.
- Определи read/write surface до и после planning, execution, consolidation, publication.
- Определи stale primary copy как реальный owned artifact, не coord residue.
- Объясни filename pattern и отказ от legacy migration.
- Определи append-only/atomicity и failure semantics.
- Перечисли альтернативы и почему rejected.

### T012 — Artifact kind и classifier

- Добавь enum member и PRIMARY partition membership.
- Добавь filename glob `spec-review-*.yaml` с проверкой первого segment `reviews`.
- Выполни classifier leg до directory fallback по образцу `review-cycle-*.md`, но не копируй его partition rationale.
- Не классифицируй `reviews/foo/spec-review-x.yaml`, malformed extensions, bare directory, `.findings.yaml` и unrelated `.yaml`.
- Проверь POSIX/Windows separators и explicit mission slug mismatch.

### T013 — Canonical storage routing

- `storage.py` принимает repo/mission context и host-built `SpecReviewRun`.
- Получает base path через `resolve_artifact_surface(..., SPEC_REVIEW)`.
- Получает write/commit target через canonical placement seam, не re-derives topology.
- Не создаёт путь из cwd или user string.
- Проверяет resolved parent, mission containment и `reviews` component непосредственно перед open.
- Возвращает metadata path/run ID, не file content.

### T014 — Atomic exclusive writer

- Run ID ASCII-only, deterministic timestamp portion + collision-resistant suffix.
- Создавай temp/exclusive file в resolved destination и публикуй без overwrite.
- На collision генерируй новый ID bounded number of retries.
- Cleanup удаляет только собственный temp path после exact ownership check.
- Fsync/replace policy документируется по supported OS; no partial final file after simulated crash.
- `write_failed` наружу только code/target metadata, без serialized payload.
- При `write_failed` final artifact отсутствует, полученные findings не персистятся, а внешний вызов storage не повторяет.
- Bounded collision retry относится только к локальному выбору свободного run ID и не повторяет внешний model call.

### T015 — Topology и attack tests

- Matrix: single branch, coord, lanes, lanes-with-coord, backfilled mission, deleted coord branch, post-consolidation.
- Для каждой cell проверяй actual filesystem path и commit target, не только set membership.
- CWD-invariance: запуск из root/lane/other dir даёт один canonical result.
- Legacy classifier regression: sample `spec-arch.findings.yaml` остаётся unclassified.
- Concurrency barrier: многие processes/threads не перезаписывают.
- Occupied run ID, symlink directory, Windows reparse surrogate и path separator tests.

## Test Strategy

- Targeted pytest для двух owned test files.
- Existing mission_runtime artifact/resolution suite должна пройти полностью.
- Reversion test: direct `feature_dir / "reviews"` implementation должна быть поймана architecture/CWD test.
- JSON/YAML serialization content проверяется через WP02 model, не raw dict.
- `git diff --check`, Ruff, mypy.

## Risks & Mitigations

- **Legacy reclassification** → filename-anchored tests.
- **Topology bypass** → resolver-only writer API and CWD tests.
- **Race/overwrite** → exclusive create + barrier tests.
- **Symlink escape** → check at open boundary, not only preflight.
- **Half boundary** → artifact kind + storage owned together.

## Review Guidance

Reviewer проверяет:

- ADR и code agree on PRIMARY semantics;
- no call site branches on topology itself;
- no directory-level reviews mapping;
- storage never uses raw feature dir as authority;
- all matrix cells assert path and target;
- no partial/temp residue on tested failures.

## Definition of Done

- [ ] ADR принят как единственная rationale authority.
- [ ] `SPEC_REVIEW` находится только в PRIMARY partition.
- [ ] Classifier требует directory `reviews` и filename `spec-review-*.yaml`.
- [ ] Legacy samples сохраняют прежний classification result.
- [ ] Resolver выдаёт PRIMARY path во всех topology cells.
- [ ] Commit target совпадает с primary target branch semantics.
- [ ] Storage не принимает raw destination path.
- [ ] Parent containment проверяется непосредственно перед exclusive open.
- [ ] Run IDs ASCII-only.
- [ ] Collision retry bounded и протестирован.
- [ ] Concurrent writers создают различимые final files.
- [ ] Symlink/reparse escape отказан.
- [ ] Crash/write failure не оставляет partial final artifact.
- [ ] `write_failed` не создаёт final artifact и не инициирует повторный внешний вызов.
- [ ] Existing mission_runtime tests зелёные.
- [ ] Ruff/mypy/targeted pytest зелёные.

## Forbidden Changes

- Не добавлять `reviews` в directory fallback.
- Не мигрировать или редактировать historical review files.
- Не вычислять topology в storage call site.
- Не использовать current working directory как authority.
- Не использовать overwrite/replace существующего final artifact.
- Не удалять чужие temp/final files при cleanup.
- Не разносить kind и writer по разным commits без working boundary.

## Verification Evidence

Предоставь topology matrix с expected/actual path и target, classifier table для positive/negative names, concurrency count, reparse/symlink outcomes и подтверждение clean temp residue.

## Rejection Conditions

Reviewer отклоняет WP при directory-level classifier, direct `feature_dir/reviews` authority, отсутствии legacy regression, проверке только enum membership вместо реального path/target, overwrite-capable writer, unbounded collision retry или cleanup чужих files.

Любой topology gap считается load-bearing blocker.

## Activity Log

- 2026-08-22T17:51:11Z – system – Prompt created.

### Updating Status

`spec-kitty agent tasks move-task WP03 --to <status>`.
