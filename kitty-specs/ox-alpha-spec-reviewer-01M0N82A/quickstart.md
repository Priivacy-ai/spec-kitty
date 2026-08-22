# Quickstart: ручное ревью синтетической спецификации

## Предусловия

1. OpenCode CLI установлен и авторизован самим пользователем.
2. Выбрана mission с обезличенным `spec.md` размером не более 256 KiB.
3. Requested model route показан в disclosure manifest; Spec Kitty не подтверждает его availability, provider ownership, price или retention.

## Preview без отправки

```powershell
spec-kitty spec-review --mission <mission> --model opencode/x-preview-f-free --preview
```

Команда должна показать `transport=OpenCode CLI`, requested model route, canonical path, sizes и SHA-256 `spec.md`, рубрики и response schema, общий payload size и manifest digest. Availability, provider ownership, price и retention помечаются как непроверенные. Preview возвращает exit code 0 и не запускает внешний процесс.

## Явный non-interactive запуск

```powershell
spec-kitty spec-review --mission <mission> --model opencode/x-preview-f-free --confirm-external
```

Флаг подтверждает только неизменившийся digest текущего disclosure manifest. Его нельзя сохранять в config как постоянное consent; drift любого manifest field требует нового подтверждения.

## Проверка результата

- Убедиться, что создан новый файл `kitty-specs/<mission>/reviews/spec-review-<run-id>.yaml`.
- Проверить `schema=spec-review-run/v1`, `spec_sha256`, `requested_model_route`, `status` и host-computed summary counts.
- Замечания рассматривать вручную; `spec.md` не должен измениться.

## Сбой допустим

`timeout`, отсутствие auth, недоступная модель и invalid output не блокируют mission, но прямой CLI-вызов возвращает ненулевой exit code 4–7 согласно спецификации. Исправление выполняется вручную, после чего запускается новый независимый review; старый артефакт не перезаписывается.
