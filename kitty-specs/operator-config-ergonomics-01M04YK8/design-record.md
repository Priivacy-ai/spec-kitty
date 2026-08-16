---
title: 'Operator configuration resolves through one kernel env-expansion seam; committed provenance stores tokens'
description: 'ADR: a single kernel ${VAR} expander plus a two-tier .kitty.env seed the process env; committed charter/manifest provenance stores SPEC_KITTY_* tokens, never resolved machine paths.'
doc_status: active
updated: '2026-08-16'
---
# Operator configuration resolves through one kernel env-expansion seam; committed provenance stores tokens

**Filename:** `2026-08-16-1-operator-config-env-expansion-seam.md` (draft — formalize in `docs/adr/3.x/` during WP4)

**Status:** Proposed

**Date:** 2026-08-16

**Deciders:** Stijn Dejongh (operator); design squad (architect-alphonso design + paula-patterns adversarial review)

**Technical Story:** Epic #3493 (children #3494 portable provenance, #3495 `.kitty.env`); related #3047, #3381, #2519, #3251, #3022

---

## Context and Problem Statement

Three operator-facing config frictions share one root: the CLI resolves environment and
directory state through ~88 scattered `os.environ.get` reads with no single authority, and it
commits machine-specific absolute paths into governance files.

1. Charter/doctrine catalog `source_path` is emitted as an absolute machine path (the
   `_trim_source_path` normalizer keys on the dead `src/doctrine/` marker after built-in doctrine
   moved to `packs/built-in/`). Repo-relative is *already* not install-mode invariant — an
   installed wheel emits `site-packages/...`.
2. Opting into hosted SaaS sync requires hand-exporting `SPEC_KITTY_ENABLE_SAAS_SYNC`,
   `SPEC_KITTY_SAAS_URL` and tokens on every shell — there is no config-file home.
3. There is no smooth way to consume rc/internal builds.

We need one coherent resolution seam that makes committed provenance portable across all install
modes, gives operators a single file for their knobs, and does so without violating the kernel's
layering floor or the DR-1 single-read invariant.

## Decision Drivers

* Committed governance files must be byte-identical across editable checkout, installed wheel,
  and future externally-extracted packs (#3022).
* Operators must configure path/sync/beta knobs once, not per shell.
* DR-1: exactly one env read per var at the kernel floor; no second resolver.
* Layering: kernel ← doctrine ← charter ← specify_cli; kernel may gain no upward imports.
* Preserve the deliberate dual-root split `.kittify` (assets) vs `.spec-kitty` (state).
* Secrets must never be committed, slurped into agent context, or printed.

## Considered Options

* **A.** Repo-relative provenance only; no env-file (narrow bug fix).
* **B.** Env-templated provenance (`${SPEC_KITTY_PACKS_ROOT}/...`) with NO central expander.
* **C. (chosen)** One kernel `${VAR}` expander + token provenance + a two-tier `.kitty.env`
  (located via the existing `SPEC_KITTY_HOME`) seeded into `os.environ` by a pre-import shim.
* **D.** Introduce a new `SPEC_KITTY_CONFIG_HOME` locator var for the env-file.

## Decision Outcome

**Chosen option: "C"**, because it is the only option that makes committed provenance invariant
across all install modes while retiring the scattered-read problem behind one authority, and it
reuses the token-preservation pattern the codebase already proved for org-pack `local_path`.

Concretely:
- **Committed provenance stores the token** `${SPEC_KITTY_PACKS_ROOT}/built-in/...`, never a
  resolved path. `.kitty.env` may set `SPEC_KITTY_PACKS_ROOT` as a per-machine *resolution*
  override; because provenance stores the symbol, the machine path is never baked in.
- **One expander at the kernel floor** (`kernel/env_expand.py`): `expand_env_template(raw, *,
  inject_defaults)` — fail-loud for resolution fields, default-inject for provenance/config
  fields. `get_packs_root_default()` = `get_built_in_pack_root().parent` (the token names the
  parent; the resolver returns the `built-in` child). `org_pack_config` delegates, keeping its
  fail-loud contract.
- **`.kitty.env` is the one home** for path (excl. `SPEC_KITTY_HOME`) / sync / beta knobs.
  Two tiers: user-global `${SPEC_KITTY_HOME}/.kitty.env` overridden by
  `<repo>/.kittify/.kitty.env`. `config.yaml` carries one expansion `env_file:
  ${SPEC_KITTY_HOME}/.kitty.env`, resolved once at bootstrap. **Reusing `SPEC_KITTY_HOME` as the
  locator** (option D rejected) avoids an invented var and any bootstrap circularity, since the
  env file never *sets* HOME.
- **Loaded by a pre-import shim** (not `main()`), `os.environ.setdefault` so real env always
  wins — because `SPEC_KITTY_TEST_MODE`/`SPEC_KITTY_SYNC_MINIMAL_IMPORT` are read at import time.

### Consequences

#### Positive
* Committed charter/manifest provenance is identical across editable/wheel/extracted layouts;
  a regression test forbids any absolute pack path in committed artifacts.
* Operators configure once; the ~88 downstream reads work unchanged against the seeded env.
* One expansion authority; kernel keeps DR-1 and gains no upward imports.

#### Negative
* Provenance tokens are less human-legible in committed YAML than a literal path (accepted:
  provenance is metadata; matches the existing org-pack convention).
* An always-set `SPEC_KITTY_PACKS_ROOT` flips the `kernel/paths.py` TEMPLATE_ROOT presence gate —
  must be documented and tested.
* Mixing secrets and portable knobs in one file forces the whole file to be treated as secret
  (mitigated: fully gitignored + `.claudeignore`d + a redaction allowlist).

#### Neutral
* A pre-import shim is a new, tiny startup surface; must stay stdlib-only for the TAB budget.

### Confirmation
Success signals: (1) a portable-provenance regression test stays green across editable + wheel
installs; (2) `spec-kitty sync opt-in` works after a single `.kitty.env` edit with no shell
exports; (3) `doctor` reports env-file health and never prints token values; (4) architectural
tests confirm kernel has no upward import and the home-owner pins are undisturbed.

## Pros and Cons of the Options

### A. Repo-relative provenance, no env-file
**Pros:** smallest change. **Cons:** not install-mode invariant (wheel → site-packages absolute);
breaks under #3022; does nothing for SaaS opt-in ergonomics.

### B. Env-templated provenance, no expander
**Pros:** portable string. **Cons:** nothing expands these fields today — the token renders
literally and is unresolvable; strictly worse than a concrete path absent the expander.

### C. Kernel expander + token provenance + two-tier `.kitty.env` (chosen)
**Pros:** install-mode invariant; one authority; reuses a proven pattern; solves all three
frictions coherently. **Cons:** more moving parts (expander, shim, migration); token legibility.

### D. New `SPEC_KITTY_CONFIG_HOME` locator var
**Pros:** explicit config-home. **Cons:** invents a var that collides conceptually with
`SPEC_KITTY_HOME`; adds a bootstrap circularity surface. Rejected in favour of reusing HOME.

## More Information
- Design source: this record + the mission `spec.md`/`plan.md`/`research.md` (the transient `.kittify/mission-brief.md` intake was retired post-spec).
- A companion ADR will record the default-off rc release-channel decision (T3 / #3496), scoped
  against the rc-cadence producer half in #3047.
- Cross-refs: #3251 (PACKS_ROOT fail-closed), #3381 (auto-run migration lesson), #2519.
