# Tooling friction

## 2026-08-14 — planning

- `bd 1.1.2` дважды выбрал `C:\Users\Ruslan\.beads` и проигнорировал task-local `BEADS_DIR`; записи остановлены.
- Долгий pytest session потерялся при compaction; репрезентативный bounded subset был повторён и дал 7/7 ожидаемых failures.
- Полный architecture suite занимает около 55 минут, поэтому план использует targeted-first порядок.
- `spec-kitty agent mission setup-plan` признал план substantive, но `safe_commit` потребовал checkout целевой integration-ветки внутри task-owned worktree; planning artifacts коммитятся на текущую task-ветку, чтобы не нарушать Git isolation.
