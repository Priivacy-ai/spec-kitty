# WP02 — независимое ревью, цикл 1

## Вердикт: REQUEST_CHANGES

1. Новый `mypy --strict` blocker: anchor-ветвь flat STATUS в
   `_resolve_status_surface_dir` возвращает `Any` вместо объявленного `Path`.
2. `resolve_placement_only` и `resolve_artifact_surface` вычисляют lifecycle
   phase только от repository root. Caller-owned Mission с
   `baseline_merge_commit` в anchor поэтому ошибочно выглядит как
   `PRE_CONSOLIDATION`.

Требуется сузить тип результата anchor-ветви и передать anchor PRIMARY
metadata в единственный lifecycle-phase authority, сохранив Git probes на
`repository_root`. Добавить production-path regression для anchor с
`baseline_merge_commit`.

Остальные проверки прошли: четыре dual-root runtime сценария, точная raw-join
санкция и mutation sensitivity, Ruff, `py_compile`, `git diff --check`.
