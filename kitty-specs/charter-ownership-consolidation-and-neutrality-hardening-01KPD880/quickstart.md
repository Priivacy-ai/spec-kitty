# Quickstart — Charter Ownership Consolidation and Neutrality Hardening

**Audience**: spec-kitty contributors writing or reviewing work packages for this mission, and contributors adding new doctrine content after the mission lands.

This quickstart shows the three most common workflows the mission creates or changes:

1. Adding a new banned term to the neutrality lint.
2. Registering a Python-scoped doctrine file in the allowlist.
3. Running the mission's new test gates locally.

---

## 1. Adding a banned term

If you observe (or want to prevent) a specific language/tool-specific string from reappearing in generic shipped doctrine, extend `src/charter/neutrality/banned_terms.yaml`.

```yaml
# src/charter/neutrality/banned_terms.yaml
schema_version: "1"
terms:
  # ... existing terms ...
  - id: RUBY-001
    kind: literal
    pattern: "bundle install"
    rationale: "Ruby-specific install command; bias class analogous to 'pip install'."
    added_in: "3.4.0"
```

- `id` must match the pattern `[A-Z]{2,4}-\d{3}` and be unique.
- `kind`: `literal` or `regex`.
- `pattern`: the term or regex source.
- `rationale`: an eight-character-minimum justification.

Run `pytest tests/charter/test_neutrality_lint.py` locally to confirm the updated lint passes (or correctly catches the cases you want it to catch).

---

## 2. Registering a Python-scoped doctrine file

If you're adding a new shipped file that **intentionally** contains language-specific guidance — e.g., a Python profile README — register its path in `src/charter/neutrality/language_scoped_allowlist.yaml`.

```yaml
# src/charter/neutrality/language_scoped_allowlist.yaml
schema_version: "1"
paths:
  - path: "src/charter/profiles/python/README.md"
    scope: python
    owner: "charter team"
    reason: "Canonical Python profile guidance; pytest appears intentionally."
    added_in: "3.3.0"
```

Rules:

- `path` is repo-relative with forward slashes. Globs like `src/charter/profiles/python/**/*.md` are supported.
- `scope` is a lowercase language family identifier.
- `owner` and `reason` are required (≥ 2 / ≥ 8 chars).
- The path (or glob) MUST resolve to at least one file at lint time — stale entries fail the lint.

---

## 3. Running the mission's test gates locally

Three new pytest files enforce the mission's invariants. From repo root:

```bash
# All three, fast (< 10 seconds combined):
pytest tests/charter/test_charter_ownership_invariant.py \
       tests/charter/test_neutrality_lint.py \
       tests/specify_cli/charter/test_shim_deprecation.py -q

# Or as part of the full suite (they are collected by default):
pytest tests/
```

What each one enforces:

| File | Enforces | Typical failure signal |
|---|---|---|
| `test_charter_ownership_invariant.py` | `build_charter_context` and `ensure_charter_bundle_fresh` each have exactly one definition, at the canonical file | A duplicate definition anywhere under `src/` (regressed ownership). |
| `test_neutrality_lint.py` | Generic-scoped doctrine artifacts contain zero banned-term hits | A new artifact added or edited with Python-specific vocabulary not covered by the allowlist. |
| `test_shim_deprecation.py` | Importing any legacy `specify_cli.charter.*` path triggers the package `__init__.py`'s single `DeprecationWarning` (submodule shims stay silent) with canonical-path + removal-release in the message | The package lost its warning call, a submodule shim reintroduced a duplicate warning, or `__removal_release__` drifted from the CHANGELOG entry. |

---

## Migration: I was importing from `specify_cli.charter`

If your Python code uses `from specify_cli.charter import X`, update to `from charter import X`. The legacy import still works but emits a `DeprecationWarning`; it is scheduled for removal in the next minor after the landing release (see `CHANGELOG.md` and `docs/migration/charter-ownership-consolidation.md` for the concrete target release).

```diff
-from specify_cli.charter import build_charter_context
+from charter import build_charter_context

-from specify_cli.charter.compiler import compile_charter
+from charter.compiler import compile_charter
```

Symbol names do not change; only the owning package path changes.

---

## Developer checklist before pushing a PR that touches charter code

- [ ] `pytest tests/charter/ tests/specify_cli/charter/` passes locally.
- [ ] `mypy --strict` passes on any new/edited modules.
- [ ] If you added a banned term or allowlist entry, the rationale/reason is ≥ 8 characters.
- [ ] If you touched shim modules, `__canonical_import__` and `__removal_release__` are still accurate.
- [ ] If you renamed a charter-owning function, update `CANONICAL_OWNERS` in `test_charter_ownership_invariant.py` and the canonical path reference.

---

## References

- Spec: [spec.md](./spec.md)
- Plan: [plan.md](./plan.md)
- Research: [research.md](./research.md)
- Data model: [data-model.md](./data-model.md)
- Contracts: [contracts/](./contracts/)
- Occurrence map (DIRECTIVE_035): [occurrence_map.yaml](./occurrence_map.yaml)
- Migration guide (produced by the mission): `docs/migration/charter-ownership-consolidation.md`
