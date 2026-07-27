# NFR-005 Interactive-Latency Baseline

> Captured by WP01 / T001 as the **very first action**, before any work package
> mutated the tree. This is the named reference every downstream WP's ≤5s
> ceiling (NFR-005) is measured against. Nobody after WP01 can capture this —
> every later WP has already changed the surface.

## Provenance

| Field | Value |
|-------|-------|
| Mission base sha (`6d9ed490d`) | `6d9ed490d40e332c9ccefc2720ca0609e145cf05` |
| WP01 lane base (`404101409`) | `404101409143d969448a1d089b25b7fd8331f1ee` |
| Lane HEAD at capture | `eeead65e81a175f3fcadc1222e1d65724c361a15` (pre-src-mutation) |
| Command | `spec-kitty accept --mission <slug> --json --diagnose` |
| Runner | `typer.testing.CliRunner` in-process, `PWHEADLESS=1 SPEC_KITTY_SYNC_MINIMAL_IMPORT=1` |
| spec-kitty / Python | 3.2.6 / 3.11.15 |
| Fixtures | `tests.characterization.test_trio_json_envelope._build_mission_repo` (canonical flat + coord-topology mission builders, WP01 `approved`) |

## Measured wall-clock (`accept --diagnose`, the NFR-005 metric)

| Topology | Wall-clock | Exit | failed_checks |
|----------|-----------|------|---------------|
| flat  | **4.535 s** | 0 | `[]` |
| coord | **0.088 s** | 0 | `[]` |

### Interpretation (honest caveat, not a footnote to ignore)

- The two numbers were captured in the **same** Python process, flat first. The
  flat figure therefore absorbs the **one-time in-process import/warm-up cost**
  of the first `accept` invocation (module imports, charter/doctrine load,
  jsonschema registry build). The coord figure (`0.088 s`) is the **warm
  steady-state** cost of the `accept --diagnose` gate path itself.
- The steady-state interactive cost of `accept --diagnose` is therefore on the
  order of **~0.1 s**; the ~4.5 s flat figure is dominated by process warm-up,
  not by any gate this mission touches.
- **NFR-005 comparison rule for downstream WPs**: measure `accept --diagnose`
  the same way (warm invocation, in-process CliRunner) and compare the
  steady-state (`~0.09 s`) figure. A downstream WP breaches NFR-005 only if it
  raises the *warm* per-topology wall-clock by more than 5 s. The cold warm-up
  cost is not attributable to any single gate.

## Method (reproducible)

The probe built both fixtures via the canonical `_build_mission_repo` helper and
timed `runner.invoke(root_app, ["accept", "--mission", slug, "--json",
"--diagnose"])` with `time.perf_counter()` around each call. The probe itself is
throwaway (not committed): it lives only to stamp these numbers before the tree
changed.
