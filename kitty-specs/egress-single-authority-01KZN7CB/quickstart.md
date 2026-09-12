# Quickstart: Verifying Single-Authority Tracker-Egress Verdict

How to confirm the mission's success criteria. All checks are local (`pytest` / `ruff` / `mypy`); no SaaS.

## SC-001 — Enforcement unchanged (full matrix, incl. permit)

Run the enforcement-equivalence matrix over **`granted` + each precedence level (project-local / machine-index / env) + the three refusal states** × the Channel-2 value set × `LOCAL_SUBPROCESS`/`HOSTED_SERVICE`. Assert `refused` and `refusing_channels` are identical to the pre-change output for every cell, and that no previously-refused cell now permits.

```bash
PWHEADLESS=1 uv run pytest tests/sync/tracker/test_tracker_egress_verdict_3108.py -q
```

## SC-002 — Hosted byte-identity

Assert the `HOSTED_SERVICE` Channel-1 refusal message is byte-identical across `NO_RECORD` / `RECORDED_REFUSAL` / `NOT_CONSENTABLE` and to the shipped string (0-byte diff).

## SC-003 — One resolution each

With `resolve_checkout_sync_routing_readonly` and `resolve_project_consent` counted (spy/patch), assert exactly **one** call to each per gated verdict (down from two). This is also the rebuilt form of the old `TestReportingSplitNeverFlipsEnforcement` guarantee.

## SC-004 — Deletion + guards

```bash
# _classify_channel1 and its two non-authoritativeness pins are gone:
grep -rn "_classify_channel1" src/ tests/    # expect: no matches in src/
PWHEADLESS=1 uv run pytest tests/architectural/test_egress_consent_boundary.py tests/invocation/test_adapters.py -q
```

The iterate-all-members `permits_egress` guard (`test_adapters.py`) must stay green — only `GRANTED` permits.

## SC-005 — `sync doctor` parity

Assert `spec-kitty sync doctor` renders the same per-destination Channel-1 state and remedy for `granted` and the three refusal states. The **degraded** states are an intended improvement — import-failure no longer masquerades as `no_record` — so pin the pre-change degraded reported-state as the golden reference and assert the new behaviour against it explicitly (not under "unchanged").

## NFR-003 — Never raises / fail-closed (post-plan M2)

Enumerate each degraded resolver return — a bare `bool`, `None`, an unrecognized value, and a resolver-import-failure — and, for each, drive a verdict through the `OUTCOME_DEFER` branch: assert it **refuses**, renders **generic** wording (the `generic = True` path), and raises **nothing** at any `permits_egress` sink (including `propagator.py`). Red-first: this must fail against a build where a degraded `channel1_state` reaches the state-keyed description/remedy dicts.

## FR-004 — Widen-transport refusal string unchanged (post-plan MINOR-2)

Assert `saas_client/client.py`'s `SaasConsentError(project_egress_refusal(...))` refusal string is byte-identical before and after — it is **not** covered by SC-002's `HOSTED_SERVICE` pin.

## C-003/C-005 — `egress.py` holds no local derivation (post-plan M1)

```bash
# egress.py must not import sync.consent / sync.routing (the single derivation stays in the resolver):
grep -nE "import (specify_cli\.)?sync\.(consent|routing)|from (specify_cli\.)?sync\.(consent|routing)" src/specify_cli/egress.py   # expect: no matches
```

Also assert `undetermined` is still produced for `root is None` after `_classify_channel1` is deleted (post-plan NOTE-2).

## Whole-seam gates before hand-off

```bash
uv run ruff check src/specify_cli/{invocation/adapters,egress,tracker/egress_verdict}.py src/specify_cli/sync/__init__.py
uv run mypy --strict <changed src files>
PWHEADLESS=1 uv run pytest tests/sync/tracker/ tests/invocation/ tests/architectural/test_egress_consent_boundary.py -q
```
