# Tooling friction

## 2026-08-14 — planning

- `bd 1.1.2` дважды выбрал `C:\Users\Ruslan\.beads` и проигнорировал task-local `BEADS_DIR`; записи остановлены.
- Долгий pytest session потерялся при compaction; репрезентативный bounded subset был повторён и дал 7/7 ожидаемых failures.
- Полный architecture suite занимает около 55 минут, поэтому план использует targeted-first порядок.
- `spec-kitty agent mission setup-plan` признал план substantive, но `safe_commit` потребовал checkout целевой integration-ветки внутри task-owned worktree; planning artifacts коммитятся на текущую task-ветку, чтобы не нарушать Git isolation.

## 2026-08-16 — финальная проверка

- Полный architecture run занял около 69 минут; bounded/targeted проверки не
  смешивались с финальным результатом.
- Запуск из неправильного cwd давал project-root false-red. Повтор из
  `windows-hard-gate-restoration-task-01M00HSC-integration` устранил эту
  ошибку разрешения и является единственным authoritative evidence.
- Глобальный pre-review coverage hook не импортировал pytest в одном runtime
  (`no_coverage`), но он не блокировал переходы; независимые task-venv gates,
  полная collection и review evidence прошли. Это предупреждение оркестрации,
  а не product failure.
- `bd` по-прежнему не используется: resolver выбирает чужую глобальную DB,
  поэтому Beads не менялся и не включён в доказательства продукта.
