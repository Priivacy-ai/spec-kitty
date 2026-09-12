# Contract — guard-seam non-laundering invariant (FR-009 / FR-010)

The #3412 launder must be closed **by construction** at the composed-action guard.

## The seam

`src/runtime/next/runtime_bridge_composition.py` around lines 486–510:

```
name_set = gather_artifact_presence(...)        # :486  — OUTSIDE the try
try:
    guards = evaluate_guards_strict(...)         # :503  — inside the try
except UnregisteredMissionFamilyError:           # :504  — MUST stay this type ONLY
    return []                                    # tolerant green for truly-unregistered families
```

## Invariants

1. **Gather-time propagation.** A `MalformedManifestError` raised during
   `gather_artifact_presence` is raised at `:486`, OUTSIDE the try — so it
   propagates regardless of the `:504` handler. The custom-family launder path
   runs `_expected_artifacts_manifest_resolves → _resolve_org_manifest_mapping →
   resolve_org_expected_artifacts → _read_yaml_mapping` (feeds
   `blocking_artifact_names`); `_presence_filenames_for` is a **sibling** gather
   path (feeds the presence name-set). A malformed manifest can raise from either
   — both are called inside `gather_artifact_presence`, both outside the try.

   **Note:** `:504` is ALREADY `except _cores.UnregisteredMissionFamilyError` only
   and gather is ALREADY outside the try in the live code — so once
   `_read_yaml_mapping` raises (WP03), this seam is closed with no production
   `except`-change. WP04's deliverable is the integration regression + a
   durability test that LOCKS the pin, not a code edit to the handler.
2. **Handler type-pinning.** The `except` at `:504` catches
   `UnregisteredMissionFamilyError` and NOTHING that a malformed manifest raises.
   A broadened handler (`except (UnregisteredMissionFamilyError,
   MalformedManifestError)` or an added `except MalformedManifestError: return []`)
   is a regression.
3. **Distinct-from-unregistered.** A custom family with a *corrupt* manifest must
   surface `MalformedManifestError` — NOT `UnregisteredMissionFamilyError` — so the
   operator sees "your manifest is malformed", not "unknown family".

## Contract tests (RED on upstream/main before fix)

- `test_malformed_org_manifest_propagates_through_composed_guard` — a custom
  family + YAML-broken org manifest, driven through the real composed-action guard
  entry point (`_dispatch_via_composition`, `repo_root` threaded at `:637-638`);
  asserts `MalformedManifestError` is raised and the result is NEVER `[]`.
  `@pytest.mark.regression`.
- `test_504_handler_is_pinned_to_unregistered_only` — a structural/behavioral
  assertion that broadening the handler re-reddens the propagation test (the
  durability proof).
- `test_absent_manifest_still_tolerant_green` — custom family with NO manifest
  still returns `[]` via the unregistered path (characterization — absence
  unchanged).
