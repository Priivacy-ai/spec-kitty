# Contract: The Three Rulers — Blocking Interfaces (FR-011)

Mission A shipped the three structural rulers **report-only**. Mission B flips them to **blocking**.
The flip is **non-uniform**: two are a `--strict` CLI toggle; the third is a **code change**. This
contract pins the exact pre-state (verified live on this branch) and the required post-state.

---

## R1 — Anti-sprawl ratchet (`scripts/docs/anti_sprawl_ratchet.py`)

**Pre-state (verified):** `--strict` is **wired but off** by default; report-only. The blocking branch
already exists:

```python
# anti_sprawl_ratchet.py
ADR_FRONTMATTER_REQUIRED_KEYS: Final[tuple[str, ...]] = ("title", "status", "date")
...
if args.strict and report["baseline_count"] > 0:
    return 1
return 0  # report-only (C-002): the default ruler never blocks.
```

**Contract (post-flip):**
- **Interface unchanged** — flip is achieved by **invoking with `--strict`** in CI.
- **Input:** the cleaned `docs/` tree. **Output:** exit **non-zero** when a sprawl regression is
  present (second doc root, missing section `index.md`, un-frontmattered ADR, shadow tree); exit
  **0** on a clean tree.
- **ADR-frontmatter rule:** an ADR is valid iff its frontmatter contains **all** of
  `("title", "status", "date")` (bare `status`, MADR vocabulary).

---

## R2 — `related:` validator (`scripts/docs/related_validator.py`)

**Pre-state (verified):** report-only; `--strict` **wired but off**:

```python
# related_validator.py
if args.strict and report.dangling_edges:
    ...  # non-zero
```

**Contract (post-flip):**
- **Interface unchanged** — flip via **`--strict`** in CI.
- **Input:** all `related:` frontmatter edges across `docs/`. **Output:** exit **non-zero** on any
  **dangling `related:` edge** (a `related:` path that does not resolve to a real `.md`); exit **0**
  when every edge resolves (NFR-004 = 0 dangling edges).

---

## R3 — Lockfile drift gate (`scripts/docs/check_docs_freshness.py`) — **CODE CHANGE**

**Pre-state (verified):** the gate has **NO flag**. `_check_inventory_lockfile_drift` hardcodes
`strict=False`, and `_lockfile_finding` hardcodes `severity="warning"`, so the finding can never raise
the aggregate exit (which keys off `any(f.severity == "error")`):

```python
# check_docs_freshness.py — PRE
def _check_inventory_lockfile_drift(inventory: Path, docs_root: Path) -> list[FreshnessFinding]:
    ...
    report = run_generate_and_compare(docs_root=docs_root, inventory=inventory,
                                       repo_root=None, strict=False)   # ← hardcoded False
    ...

def _lockfile_finding(location: str, message: str) -> FreshnessFinding:
    return FreshnessFinding(rule_id="INVENTORY-LOCKFILE-DRIFT",
                            severity="warning",   # ← hardcoded warning
                            ...)
```

**Contract (post-flip — THREE code changes, not two):**
1. Thread **`strict=True`** through `_check_inventory_lockfile_drift` (so
   `run_generate_and_compare(..., strict=True)`).
   **Annotation:** in *this* codepath `strict=True` is a **harmless no-op** — `run_generate_and_compare`
   returns the same drift report regardless; the value that actually flips the gate is change (2), the
   severity escalation. Thread it for intent/consistency, but the implementer should not expect (1)
   alone to change CI behavior.
2. **Escalate `INVENTORY-LOCKFILE-DRIFT` from `severity="warning"` to `severity="error"`** in
   `_lockfile_finding` — **this is the real gate change** (the aggregate exit keys off
   `any(f.severity == "error")`).
3. **Remove the `if inventory_lockfile_check:` opt-in guard** in
   `check_docs_freshness.run_orchestrator` (~line 433) — make the lockfile check **default-on**.
   **Without (3) the escalation is DEAD CODE in CI**: `.github/workflows/docs-freshness.yml:24` invokes
   `check_docs_freshness.py --ci --report freshness.json --link-check none` **with no
   `--inventory-lockfile`**, so the guarded block never runs. (Equivalent alternative: add
   `--inventory-lockfile` to the CI invocation — but default-on is the robust choice.)
- **Result:** any lockfile drift (added/removed/changed) makes `check_docs_freshness.py` exit
  **non-zero** (the aggregate already raises on an `error` finding). Exit **0** only when drift = 0.
- **Ordering precondition:** the gate is flipped **after** the move (IC-03) + backfill (IC-05) close
  the live drift (252 removed / 296 changed) to **0** — else the flip red-fails the mission's own
  merge.

---

## CI wiring (FR-011) — NO CI job invokes the rulers today

**Verified:** only `.github/workflows/docs-freshness.yml` runs any of the three scripts, and it runs
**only** `check_docs_freshness.py` (without `--inventory-lockfile`). **Neither `anti_sprawl_ratchet.py`
nor `related_validator.py` is invoked by any CI job.** So flipping `--strict` (R1/R2) is inert until
they are **wired into CI**.

**Contract (IC-06 CI wiring):** add to **`.github/workflows/docs-freshness.yml`** a step (or steps)
invoking:
- `uv run python scripts/docs/anti_sprawl_ratchet.py --strict`
- `uv run python scripts/docs/related_validator.py --strict`
- `check_docs_freshness.py` with the lockfile check **default-on** (change (3) above) or
  `--inventory-lockfile` passed.

`/tasks` names the exact step. All three are paired with the C-005 whole-tree dry-run below.

---

## Cross-cutting: gate-unmask discipline (C-005)

All three flips are paired with a **full-gate dry-run over the whole tree before merge**, not scoped
to the mission diff. A ruler that only bites on the mission diff is invisible until post-merge
("gate-unmask cannot self-validate"). The dry-run is quickstart **S3** run against the entire tree.

**LEAK coupling (FR-014):** `version_leakage_check.py`'s `LEAK-FRONTMATTER-MISMATCH` is retired
**only after** R3 is proven red-live + blocking — the lockfile drift gate subsumes it.
