---
work_package_id: WP03
cycle: 1
verdict: REQUEST_CHANGES
---

# Цикл проверки WP03: полный architecture gate

## Проверенный SHA

- Worktree: `C:\spkhg\.worktrees\windows-hard-gate-restoration-task-01M00HSC-lane-a`
- Branch: `kitty/mission-windows-hard-gate-restoration-task-01M00HSC-lane-a`
- GREEN commit: `06026d6d0`
- WP03-локальные изменения не содержат новых dirty-файлов.

## Gates

- `tests/contract`: **305 passed, 3 skipped**.
- Targeted WP03 packet: **70 passed**; review signal smoke: **1 passed, 2 skipped**.
- Полный `tests/architectural`: **2107 passed, 5 skipped, 2 xfailed, 1 warning, 8 failed**.
- Поэтому `local_ready=false`; failure не относится к четырём исправленным WP03-классам.

## Классификация восьми residual-сигналов

1. `status_transition.py:784` делает `raw_feature_dir.parent.parent` и заново выводит mission anchor. Это реальный resolver-boundary bypass, а не Windows-форматирование; требуется отдельный production fix с resolver-first тестом.
2–3. `_checkout_grammar_offenders()` в `test_no_write_side_rederivation.py` формирует диагностический путь через `Path.relative_to()` без `.as_posix()`. Это cross-platform oracle defect; ожидается узкая нормализация сообщения без расширения allowlist.
4–7. Четыре проверки `test_resolution_authority_gates.py` видят stale token для `RealCoordCommitRouter.feature_write_dir`: allowlist ожидает `write_dir : Path = ...`, live source содержит `write_dir = ...`. Это stale fixture, но обновление допускается только после exact live-match и mutation/negative доказательства.
8. `test_topology_resolution_boundary.py` сравнивает lock с raw Windows bytes, а `docs/codemap/codemap.lock` хранит LF-нормализованные SHA. Требуется канонический cross-platform hash oracle и refresh lock, не изменение semantic code map без доказательства.

## Решение

WP03 не расширяется и не объявляется принятым на основании partial gate. Эти четыре класса вынесены в отдельные follow-up WP04–WP05; затем WP06 повторит полный gate и обновит acceptance/handoff. До этого `local_ready` остаётся `false`.
