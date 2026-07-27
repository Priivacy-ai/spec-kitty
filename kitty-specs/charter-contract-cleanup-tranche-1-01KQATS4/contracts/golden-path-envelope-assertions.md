# Golden-Path E2E Envelope Assertion Contract

**Mission:** `charter-contract-cleanup-tranche-1-01KQATS4`
**Test surface:** `tests/e2e/test_charter_epic_golden_path.py`
**Authority:** spec.md FR-006, FR-007 + research.md R-005

This document is the assertion contract the Charter golden-path E2E enforces against runtime-emitted lifecycle envelopes. It binds the test, not the producer; the producer's wire format is the upstream truth, and this contract describes what the test inspects.

---

## Issued Action (kind=step)

**Discriminator:** envelope where the documented public discriminator is `"step"` (typically `kind == "step"`).

**Required of the test, per envelope:**

1. Read `prompt_file` (or the documented public equivalent the runtime guarantees).
2. Assert it is present (key exists), non-null, and non-empty (`!= ""`).
3. Resolve it to a path. Acceptable shapes:
   - Path relative to the E2E's test-project root — must `Path(test_project_root, prompt).is_file()` or equivalent.
   - Absolute path — must `Path(prompt).is_file()`.
   - Documented shipped-prompt-artifact path that the runtime guarantees exists in the installed package — must resolve via the same lookup the runtime would use.
4. If resolution fails, the test fails with a message that names the issued-action's identifier (envelope ID, step name, or whatever stable handle the envelope carries) and the unresolvable prompt value.

**Permitted multiplexing:** if the runtime emits more than one stable field that may carry a prompt path (e.g. `prompt_file` and a `prompt.path` sub-object), the assertion treats "at least one of them carries a resolvable prompt file" as success. The test must not hard-code internal field names beyond what the runtime publicly documents.

**Non-required:** the test does not assert prompt file *content*. Resolvability is the contract.

---

## Blocked Decision

**Discriminator:** envelope where the existing runtime indicator marks the decision as blocked (whatever flag/sub-object the runtime publicly defines for that state).

**Required of the test, per envelope:**

1. Read `reason`.
2. Assert it is present, non-null, and `reason.strip() != ""`.
3. Do NOT assert anything about `prompt_file`. Blocked decisions may carry one or none; either is acceptable.

**Failure mode:** a blocked decision with missing/null/whitespace-only `reason` causes the test to fail with a message naming the offending decision and (if available) which step it blocked.

---

## All Other Envelope Kinds

Existing assertions in `tests/e2e/test_charter_epic_golden_path.py` are unchanged. This contract adds the prompt-file/reason invariants without rewriting the rest of the test.

---

## Producer-side note (non-binding for this mission)

If the runtime ever changes the public discriminator or the prompt-path field, the test contract above is what governs the consumer. Producer-side changes that move the field name without a deprecation cycle would break this contract; this mission does not introduce any such producer-side change.
