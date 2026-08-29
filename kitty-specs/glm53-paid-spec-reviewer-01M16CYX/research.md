# Исследование: локальный cost-authorization gate поверх OpenCode

**Дата**: 2026-08-29  
**Целевая аудитория**: разработчик transport/cost gate

## Проверенные факты

- OpenRouter публикует полный GLM 5.3 как платную text-only модель с always-on reasoning и отдельными input/output тарифами: <https://openrouter.ai/z-ai/glm-5.3>.
- Официальный OpenCode server contract для `POST /session/:id/message` принимает model, agent, system, tools и parts, но не объявляет `maxTokens`: <https://opencode.ai/docs/server/>.
- Сгенерированный официальный SDK тип `SessionPromptData` также не содержит `maxTokens`: <https://github.com/anomalyco/opencode/blob/dev/packages/sdk/js/src/gen/types.gen.ts>.

## Решение

Provider-side output reservation через текущий OpenCode loopback доказать нельзя. Поэтому Mission не обещает фактический billing lock или hard cap. Она вводит локальный fail-closed authorization threshold для advertised-оценки: exact metadata должна содержать полную цену и положительные `limit.context`/`limit.output`; все входные/cache цены применяются к полному контекстному потолку, а output price — к полному выходному потолку. Это включает OpenCode system/agent framing без попытки заранее угадать его размер.

Paid preview получает metadata-only quote и связывает с consent exact route, threshold, нормализованную price-map, оба лимита, оценку и SHA-256 канонических метаданных. Перед session creation execution повторяет probe и требует точного совпадения. Любая неопределённость или drift означает ноль session calls и новый preview. Сам probe может обновлять/fetch-ить CLI metadata, поэтому документация не называет её кэшированной и не приравнивает к model call.

Байтовая граница пользовательского пакета остаётся полезной только как integrity guard для permit. Она не доказывает число billable input tokens, потому что OpenCode добавляет собственный framing.

## Отвергнутые варианты

- **Только сравнить цену за миллион токенов** — не ограничивает стоимость конкретного запуска.
- **Оценивать input по байтам пользовательского prompt** — не учитывает добавляемый OpenCode system/agent framing.
- **Передать неописанный `maxTokens` в body** — контракт OpenCode этого не гарантирует.
- **Разрешить все платные модели с одним cap** — расширяет scope и риск без запроса пользователя.
- **Считать фактическую стоимость после ответа** — слишком поздно для prevent-before-spend gate.
