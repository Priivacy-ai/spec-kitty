# Модель данных: external spec review

## DisclosureManifest

- `transport`: фиксированное значение `opencode-cli`.
- `requested_model_route`: model ID, показанный пользователю без обещания фактического provider.
- `spec_path`, `spec_size_bytes`, `spec_sha256`.
- `rubric_version`, `rubric_size_bytes`, `rubric_sha256`.
- `response_schema_version`, `response_schema_size_bytes`, `response_schema_sha256`.
- `prompt_template_version`, `prompt_template_size_bytes`, `prompt_template_sha256`.
- `total_payload_bytes`.
- `manifest_sha256`: digest канонического представления всех полей выше.

**Инварианты**: consent относится только к одному `manifest_sha256`. После consent каждый компонент повторно проверяется. `spec.md` читается один раз в immutable buffer после проверки пути и именно этот buffer передаётся runner.

## SpecReviewRequest

- `mission_id`: canonical ULID.
- `mission_slug`: resolved ASCII mission slug.
- `manifest`: подтверждённый `DisclosureManifest`.
- `timeout_seconds`: 10–600.
- `consent`: одноразовое подтверждение, которое не сериализуется в preferences.

## ReviewResponse

Недоверенный model payload по `review-response/v1`:

- `schema`: `review-response/v1`.
- `findings`: не более 100 элементов.

Модель не задаёт provenance, status, timestamps или summary.

## SpecReviewFinding

- `id`: ASCII identifier, уникальный в одном response.
- `lens`: bounded text.
- `severity`: integer 1–5.
- `title`: ограниченная строка.
- `evidence.line_start`, `evidence.line_end`: проверяемый диапазон строк `spec.md` с подтверждённым digest; цитаты не сохраняются.
- `claim`, `remediation`: bounded model-authored text; точные spans входа длиной от 32 символов запрещены.

## SpecReviewRun

Доверенный host-owned artifact по `spec-review-run/v1`:

- `run_id`: timestamp + random ASCII suffix.
- `mission`, `spec_sha256`, `transport`, `requested_model_route`, `actual_model`, `rubric_version`.
- `started_at`, `completed_at` в UTC.
- `status`: `completed | provider_error | timeout | invalid_output`.
- `diagnostic_code`: `null` только для `completed`, обязателен для failure status.
- `findings`: validated response findings для `completed` (включая валидный пустой массив), пустой массив для failure status.
- `summary`: host-computed `total` и counts для severity 1–5; сумма обязана равняться `findings.length`.

**Жизненный цикл**: после фактического external process start host создаёт один append-only artifact через PRIMARY resolver для `completed`, `provider_error`, `timeout` или `invalid_output`. Preflight refusal, missing/mismatched consent и missing executable не создают run. `refused` и `write_failed` являются неперсистируемыми invocation outcomes: при отказе storage существует только metadata-only CLI diagnostic, findings не сохраняются и partial/temp file не остаётся. Ни один исход не меняет mission lifecycle и не вызывает повторный внешний model call.

## Failure taxonomy и exit codes

| Код | Условие | Process start | Persisted artifact | Exit |
|-----|---------|---------------|--------------------|------|
| `SPEC_REVIEW_PREVIEW` | явный `--preview` | Нет | Нет | 0 |
| `SPEC_REVIEW_CANCELLED` | интерактивный отказ | Нет | Нет | 0 |
| `SPEC_REVIEW_CONSENT_REQUIRED` | non-interactive запуск без consent или с несовпадающим `--confirm-digest` | Нет | Нет | 2 |
| `SPEC_REVIEW_INPUT_REFUSED` | path/size/sensitive marker/manifest drift | Нет | Нет | 3 |
| `SPEC_REVIEW_CLI_MISSING` | executable не найден | Нет | Нет | 4 |
| `SPEC_REVIEW_AUTH_REQUIRED` | классифицированный auth failure → status `provider_error` | Да | Да | 4 |
| `SPEC_REVIEW_PROVIDER_ERROR` | ненулевой provider/429 result без retry | Да | Да | 4 |
| `SPEC_REVIEW_TIMEOUT` | превышен timeout | Да | Да | 5 |
| `SPEC_REVIEW_INVALID_OUTPUT` | framing/schema/size/privacy failure | Да | Да | 6 |
| `SPEC_REVIEW_WRITE_FAILED` | atomic storage отказал | Да | Нет | 7 |
