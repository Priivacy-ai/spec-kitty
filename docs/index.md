---
title: Spec Kitty 3.2 Documentation
description: Current Spec Kitty 3.2 documentation for new adopters, upgrade operators, harness users, and CLI integrators.
doc_status: active
updated: '2026-06-03'
related:
- docs/migration/from-charter-2x.md
- docs/migration/index.md
- docs/migration/upgrade-to-0-12-0.md
---

<section class="sk-docs-hero" aria-labelledby="sk-docs-title">
  <p class="sk-eyebrow">Spec Kitty</p>
  <h1 id="sk-docs-title">Spec Kitty documentation</h1>
  <p class="sk-docs-lead">Install the CLI, run missions through your AI harness, and keep specs, plans, work packages, and review evidence aligned.</p>
  <nav class="sk-docs-actions" aria-label="Primary documentation paths">
    <a class="sk-btn sk-btn-primary" href="guides/index.md">Start from zero</a>
    <a class="sk-btn" href="migrations/index.md">Upgrade a project</a>
    <a class="sk-btn" href="api/index.md">Open the API reference</a>
  </nav>
</section>

Spec Kitty documentation is organized as a single 13-section Common Docs structure under this one entry point. Use it when you are installing Spec Kitty for the first time, upgrading an existing project, running missions through an AI harness, or checking exact CLI behavior.

## Answer summary

- Current runtime model: Charter-era missions with governed context injection.
- Current governance source: `.kittify/charter/charter.md`.
- Current mission loop: `spec-kitty next --agent <name> --mission <slug>`.
- Upgrade path: start at [Migrations](migrations/index.md), then follow the current guides.

## Sections

Every section has its own `index.md` landing page. This page is the single entry point (SC-001) that links each one.

<div class="sk-card-grid">
  <a class="sk-doc-card" href="context/index.md">
    <span class="sk-card-kicker">Context</span>
    <strong>Context</strong>
    <span>Glossary narrative, audiences, and the Charter-era governance model.</span>
  </a>
  <a class="sk-doc-card" href="architecture/index.md">
    <span class="sk-card-kicker">Architecture</span>
    <strong>Architecture</strong>
    <span>Unified, unversioned living design for the system.</span>
  </a>
  <a class="sk-doc-card" href="adr/index.md">
    <span class="sk-card-kicker">ADRs</span>
    <strong>Decision records</strong>
    <span>Architecture decision records by era (1.x, 2.x, 3.x).</span>
  </a>
  <a class="sk-doc-card" href="plans/index.md">
    <span class="sk-card-kicker">Plans</span>
    <strong>Plans</strong>
    <span>User journeys, investigations, and traces (distil-then-retire).</span>
  </a>
  <a class="sk-doc-card" href="api/index.md">
    <span class="sk-card-kicker">API</span>
    <strong>API and CLI reference</strong>
    <span>Exact CLI, file, schema, and environment behavior.</span>
  </a>
  <a class="sk-doc-card" href="configuration/index.md">
    <span class="sk-card-kicker">Configuration</span>
    <strong>Configuration</strong>
    <span>Configuration files, flags, and environment variables.</span>
  </a>
  <a class="sk-doc-card" href="integrations/index.md">
    <span class="sk-card-kicker">Integrations</span>
    <strong>Integrations</strong>
    <span>AI harness and external-system integration.</span>
  </a>
  <a class="sk-doc-card" href="security/index.md">
    <span class="sk-card-kicker">Security</span>
    <strong>Security</strong>
    <span>Security posture, credentials, and secrets handling.</span>
  </a>
  <a class="sk-doc-card" href="guides/index.md">
    <span class="sk-card-kicker">Guides</span>
    <strong>Guides</strong>
    <span>Task-oriented guides and guided learning workflows.</span>
  </a>
  <a class="sk-doc-card" href="operations/index.md">
    <span class="sk-card-kicker">Operations</span>
    <strong>Operations</strong>
    <span>Operational and developer-workflow guides, including recovery.</span>
  </a>
  <a class="sk-doc-card" href="migrations/index.md">
    <span class="sk-card-kicker">Migrations</span>
    <strong>Migrations</strong>
    <span>Version migrations, upgrade paths, and shim rules.</span>
  </a>
  <a class="sk-doc-card" href="changelog/index.md">
    <span class="sk-card-kicker">Changelog</span>
    <strong>Changelog</strong>
    <span>Release history.</span>
  </a>
</div>

## Section index

| Section | Landing page |
|---|---|
| Context | [context/index.md](context/index.md) |
| Architecture | [architecture/index.md](architecture/index.md) |
| ADRs | [adr/index.md](adr/index.md) |
| Plans | [plans/index.md](plans/index.md) |
| API | [api/index.md](api/index.md) |
| Configuration | [configuration/index.md](configuration/index.md) |
| Integrations | [integrations/index.md](integrations/index.md) |
| Security | [security/index.md](security/index.md) |
| Guides | [guides/index.md](guides/index.md) |
| Operations | [operations/index.md](operations/index.md) |
| Migrations | [migrations/index.md](migrations/index.md) |
| Changelog | [changelog/index.md](changelog/index.md) |

## Migration and archive

Use [Migrations](migrations/index.md) when moving an existing project onto the current release. 1.x and 2.x docs are preserved as a historical archive and should not be used to start a new project.
