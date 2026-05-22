# Tasks — Launch Auth, Sync, and Upgrade Readiness Docs

## Work package decomposition

Three small WPs, sequenced.

| WP | Title | Owned files | Depends on |
|---|---|---|---|
| WP01 | Author internal / pre-launch hosted-readiness how-to | `docs/how-to/internal-hosted-readiness.md` | — |
| WP02 | Author launch-readiness-future explanation doc | `docs/explanation/launch-readiness-future.md` | WP01 |
| WP03 | Cross-links + README gating note + env-var cross-links + CHANGELOG | `README.md`, `docs/how-to/toc.yml`, `docs/explanation/toc.yml`, `docs/recovery/logged-out-teamspace.md`, `docs/reference/environment-variables.md`, `CHANGELOG.md` | WP01, WP02 |

All WPs land in a single execution lane.

## WP01 — Internal / pre-launch hosted-readiness how-to

**Goal:** ship `docs/how-to/internal-hosted-readiness.md` per the
content outline in `plan.md`.

**Acceptance:**

- Frontmatter declares `type: how-to`, `audience: internal /
  pre-launch operators`.
- Opens with an explicit "Audience: internal contributors and dev
  operators" blockquote.
- Contains exactly these copy-pasteable code blocks (verbatim):
  - `export SPEC_KITTY_ENABLE_SAAS_SYNC=1` followed by
    `spec-kitty auth login`.
  - `export SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev`
    framed explicitly as a dev / staging override.
  - `spec-kitty sync doctor` as the diagnostic recipe.
- Includes a readiness-state table summarizing the coordinator's
  output buckets (disabled, enabled / authenticated, enabled /
  logged-out-on-connected-teamspace, …).
- Points at `src/specify_cli/saas/rollout.py` and
  `docs/recovery/logged-out-teamspace.md` as authoritative for byte-
  stable wording.
- Closing "Not for end users — see [launch-readiness-future]"
  cross-link is present (target file will exist after WP02).

**Non-goals:** no enum value restatement; no CLI behavior changes; no
new env vars.

## WP02 — Launch-readiness future explanation doc

**Goal:** ship `docs/explanation/launch-readiness-future.md` per the
content outline in `plan.md`.

**Acceptance:**

- Frontmatter declares `type: explanation`, `audience: launch
  coordinators`.
- First non-frontmatter line is a blockquote banner:
  `> **Status: pre-launch.** This page describes behavior that ships
  at the public Teamspace launch milestone. **None of this is in
  effect today.**`
- Contains a today-vs-at-launch table covering: default SaaS URL,
  sync default, meaning of `SPEC_KITTY_ENABLE_SAAS_SYNC`, default
  tracker, default `spec-kitty auth login` flow.
- Operator playbook section enumerates the launch-flip steps at a
  high level (release-cut order, what becomes user-facing, what
  stays internal). No exact dates or version numbers — those belong
  to a release-cut runbook, not this conceptual doc.
- Cross-links to `docs/how-to/internal-hosted-readiness.md` for the
  dev / staging override path.
- Closing "Out of scope" section lists what this doc deliberately
  does not specify.

## WP03 — Cross-links + README gating note + env-var cross-links + CHANGELOG

**Goal:** stitch the new docs into the rest of the site and ship the
CHANGELOG entry.

**Acceptance:**

1. `README.md`: the existing "Hosted Sync Workspaces" link entry under
   "Deeper topics" gains a one-line gating note (e.g.,
   `Internal / pre-launch operators dogfooding the hidden hosted
   mode: see Internal hosted-readiness mode (pre-launch).`) pointing
   at the new internal doc. No other README edits.
2. `docs/how-to/toc.yml`: a new entry
   `- name: Internal Hosted-Readiness (Pre-Launch)` /
   `href: internal-hosted-readiness.md` is added in an
   audience-appropriate spot (near the other operator / install
   entries; not at the very top of the user how-to list).
3. `docs/explanation/toc.yml`: a new entry
   `- name: Launch-Readiness Behavior (Coming Soon)` /
   `href: launch-readiness-future.md` is added.
4. `docs/recovery/logged-out-teamspace.md`: append one line to the
   "Related" list pointing to the internal doc.
5. `docs/reference/environment-variables.md`:
   - `SPEC_KITTY_ENABLE_SAAS_SYNC` section gets one closing line
     pointing to the internal doc and the launch-future doc.
   - `SPEC_KITTY_SAAS_URL` section gets one closing line pointing to
     the same two docs.
6. `CHANGELOG.md`: a single bullet under `[Unreleased]`:
   ```
   - Add pre-launch and launch-readiness operator docs for hosted SaaS
     sync (#1095). Public docs remain local-first; hosted readiness
     stays opt-in via SPEC_KITTY_ENABLE_SAAS_SYNC=1.
   ```

**Leakage gate (final WP03 check):**

```bash
grep -niE 'teamspace.*launch(ed)?|launched.*teamspace|now (generally|publicly) available' README.md docs/index.md
```

Must return zero matches before the WP closes.

## Sequencing

```
WP01 ─▶ WP02 ─▶ WP03
```

Single lane; each WP fully closes before the next opens to keep the
cross-links coherent.
