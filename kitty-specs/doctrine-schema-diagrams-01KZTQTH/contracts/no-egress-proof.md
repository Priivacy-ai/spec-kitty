# Contract: No-egress proof (NFR-002, C-001) — hardened per post-plan squad

## Execution locus (architecture HIGH)
- Python orchestration (fence recovery, `html.unescape`, SVG injection) runs **host-native**, **stdlib-only** (docs-pages.yml has no setup-python / no pip install — no third-party imports).
- Only the untrusted `java -jar plantuml.jar` invocation is wrapped: `docker run --network=none -v <tmp>:<tmp> <digest-pinned-JRE-image> java -jar plantuml.jar …`. The JRE image is **prefetched before** the isolated run. Drop host `setup-java` (redundant).

## Proof (both required, BLOCKING CI gates)
- (a) **Behavioral SANDBOX** (reviewer MEDIUM): a diagram with `!includeurl` pointed at a **local listener** renders under SANDBOX and the listener sees **zero inbound connection** (or the SANDBOX-specific refusal signal). NOT the weak "build fails" disjunct.
- (b) **Network isolation** (reviewer HIGH): the isolation test renders the **actual authored schema-diagram corpus** (not a sample) under `docker run --network=none`, and passes. This IS the hard gate (not the ≤60s budget).

## Spike (blocking WP01 — planner/architecture HIGH)
Runnability is currently **UNPROVEN**. WP01 renders a **real** `@startyaml` diagram under `--network=none` on **both** `ubuntu-latest` and `blacksmith-4vcpu-ubuntu-2404`, confirming no font/DNS-driven failure. Its green exit-criterion gates every render/diagram WP. URL-grep is a secondary lint.
