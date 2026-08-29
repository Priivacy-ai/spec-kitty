# Исследование: enforceable cost cap поверх OpenCode

**Дата**: 2026-08-29  
**Целевая аудитория**: разработчик transport/cost gate

## Проверенные факты

- OpenRouter публикует полный GLM 5.3 как платную text-only модель с always-on reasoning и отдельными input/output тарифами: <https://openrouter.ai/z-ai/glm-5.3>.
- Официальный OpenCode server contract для `POST /session/:id/message` принимает model, agent, system, tools и parts, но не объявляет `maxTokens`: <https://opencode.ai/docs/server/>.
- Сгенерированный официальный SDK тип `SessionPromptData` также не содержит `maxTokens`: <https://github.com/anomalyco/opencode/blob/dev/packages/sdk/js/src/gen/types.gen.ts>.

## Решение

Provider-side output reservation через текущий OpenCode loopback доказать нельзя. Поэтому Mission не обещает фактический billing lock. Она вводит локальный fail-closed advertised upper bound: exact metadata должна содержать полную цену и положительный максимальный output; консервативная оценка обязана быть не выше подтверждённого cap. Любая неопределённость означает ноль session calls.

## Отвергнутые варианты

- **Только сравнить цену за миллион токенов** — не ограничивает стоимость конкретного запуска.
- **Передать неописанный `maxTokens` в body** — контракт OpenCode этого не гарантирует.
- **Разрешить все платные модели с одним cap** — расширяет scope и риск без запроса пользователя.
- **Считать фактическую стоимость после ответа** — слишком поздно для prevent-before-spend gate.
