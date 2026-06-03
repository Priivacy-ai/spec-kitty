---
name: spk-team-connectors
description: "Operate Spec Kitty connector integrations and route connector work across tracker, sync, SaaS, and external services."
---

# spk-team-connectors

Use this skill when Spec Kitty work involves external connectors, integration
configuration, connector sync, or hosted service routing.

## Flow

1. Identify the connector and owning service.
2. Confirm whether data flows through tracker, sync, SaaS, or an external API.
3. Use `spk-team-auth` for credentials, `spk-team-sync` for sync transport, and
   `spk-team-tracker` for tracker-bound state.
4. Keep connector configuration out of mission specs unless it changes product
   behavior.

## Rule

Treat connector work as integration operations, not generic mission authoring.
