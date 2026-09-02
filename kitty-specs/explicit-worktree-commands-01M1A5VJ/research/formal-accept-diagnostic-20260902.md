# Диагностика формальной приёмки

## Проверенная команда

Read-only диагностика выполнена project-local CLI с явной выбранной копией:

```text
uv run spec-kitty accept \
  --mission explicit-worktree-commands-01M1A5VJ \
  --mode local \
  --owned-checkout C:\Users\Ruslan\.codex-worktrees\spec-kitty-explicit-worktree-repair \
  --diagnose --json
```

Команда завершилась штатно и правильно выбрала task-ветку, owned worktree и
mission directory. Вызов без `--owned-checkout` дважды дал
`mission_not_found`, потому что обычный Git-root resolver канонизировал
worktree к primary, где локальная mission отсутствует.

## Результат

Acceptance вернула `ok=false` без изменений файлов. Блокеры:

- WP01 находится в canonical lane `planned`, а не `approved` или `done`;
- `lanes.json` отсутствует, WP не имеет canonical lane entry и runtime agent;
- `status.events.jsonl` содержит только `MissionCreated` и `SpecifyStarted`, но
  не lifecycle WP;
- строгая software-dev convention ожидает каталог `contracts/`.

`--lenient` может понизить только path-convention finding до warning и не
устраняет отсутствие canonical lifecycle. Поэтому штамповать acceptance или
создавать каталог только ради зелёного gate нельзя.

## Следующий gate

Следующий пакет должен сначала выполнить штатный `finalize-tasks` с тем же
`--owned-checkout`, а затем провести WP через реальный evidence-backed
lifecycle до независимого approval. Это изменит repository-owned audit trail и
должно выполняться как отдельный согласованный шаг; прежние отметки в
`tasks.md` не выдаются за canonical runtime history.

Push, PR, merge, установка и публикация не выполнялись.
