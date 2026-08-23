# Quickstart: ручное ревью синтетической спецификации

## Предусловия

1. OpenCode CLI установлен и авторизован самим пользователем.
2. Выбрана mission с `spec.md` размером не более 256 KiB; heuristic scanner не гарантирует обезличивание.
3. Requested model route показан в disclosure manifest; Spec Kitty не подтверждает его availability, provider ownership, price, retention или anonymization.

## Preview без отправки

```powershell
spec-kitty spec-review --mission <mission> --model opencode/x-preview-f-free --preview
```

Команда должна показать `transport=OpenCode CLI`, requested model route, canonical path, sizes и SHA-256 `spec.md`, рубрики, response schema и prompt template, общий payload size и manifest digest. Availability, provider ownership, price, retention и anonymization помечаются как непроверенные. Preview возвращает exit code 0 и не запускает внешний процесс.

## Явный non-interactive запуск

```powershell
spec-kitty spec-review --mission <mission> --model opencode/x-preview-f-free --confirm-digest <sha256-из-preview>
```

Значение флага обязано точно совпасть с пересчитанным digest текущего disclosure manifest. Его нельзя сохранять в config как постоянное consent; drift любого manifest field требует нового подтверждения.

## Проверка результата

- Убедиться, что создан новый файл `kitty-specs/<mission>/reviews/spec-review-<run-id>.yaml`.
- Проверить `schema=spec-review-run/v1`, `spec_sha256`, `transport`, `requested_model_route`, `actual_model`, `status` и host-computed summary counts.
- Замечания рассматривать вручную; `spec.md` не должен измениться.

## Сбой допустим

`timeout`, отсутствие auth, недоступная модель, 429 и invalid output не блокируют mission, но прямой CLI-вызов возвращает ненулевой exit code 4–7 согласно спецификации. Автоматические retry запрещены: исправление выполняется вручную, после чего с новым consent запускается новый независимый review; старый артефакт не перезаписывается.
