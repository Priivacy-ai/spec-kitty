---
title: 'Calibration Report: documentation'
description: 'Calibration report for the documentation mission: the §4.5.1 inequality check per step, finding no edge changes required against the calibration overlay.'
doc_status: active
updated: '2026-04-27'
---
# Calibration Report: documentation

**Mission**: documentation  
**Date**: 2026-04-27  
**Overlay**: `.kittify/doctrine/overlays/calibration-documentation.yaml`  
**Status**: No edge changes required — all steps pass §4.5.1

---

## Summary

All 7 steps pass the §4.5.1 inequality. The shipped `src/doctrine/graph.yaml` provides complete context. Transitive extras (e.g. `connascence-analysis`, `easy-to-change`, `language-driven-design` via `DIRECTIVE_001 → requires` for the `design` step; acceptance testing tactics via `DIRECTIVE_037 → suggests`) are classified as `known_irrelevant`.

---

## Step-by-Step Findings

### Step: audit

| Column | Value |
|---|---|
| **Step id** | audit |
| **Action id** | `action:documentation/audit` |
| **Profile id** | `agent_profile:curator-carla` |
| **Resolved DRG artifact URNs** | `directive:DIRECTIVE_003`, `directive:DIRECTIVE_037`, `tactic:acceptance-test-first`†, `tactic:adr-drafting-workflow`†, `tactic:atdd-adversarial-acceptance`†, `tactic:premortem-risk-identification`†, `tactic:requirements-validation-workflow`, `tactic:usage-examples-sync`† |
| **Scope edges involved** | `directive:DIRECTIVE_003`, `directive:DIRECTIVE_037`, `tactic:requirements-validation-workflow` |
| **Missing context** | none |
| **Irrelevant / too-broad context** | none (†transitive from `DIRECTIVE_037 → suggests`) |
| **Recommended DRG edge changes** | none |
| **Before/after evidence** | Before: 8 URNs. After: unchanged. |

---

### Step: design

| Column | Value |
|---|---|
| **Step id** | design |
| **Action id** | `action:documentation/design` |
| **Profile id** | `agent_profile:curator-carla` |
| **Resolved DRG artifact URNs** | `directive:DIRECTIVE_001`, `directive:DIRECTIVE_003`, `directive:DIRECTIVE_010`, `tactic:adr-drafting-workflow`, `tactic:connascence-analysis`†, `tactic:easy-to-change`†, `tactic:language-driven-design`†, `tactic:premortem-risk-identification`†, `tactic:requirements-validation-workflow` |
| **Scope edges involved** | `directive:DIRECTIVE_001`, `directive:DIRECTIVE_003`, `directive:DIRECTIVE_010`, `tactic:adr-drafting-workflow`, `tactic:requirements-validation-workflow` |
| **Missing context** | none |
| **Irrelevant / too-broad context** | none (†transitive from `DIRECTIVE_001 → requires`) |
| **Recommended DRG edge changes** | none |
| **Before/after evidence** | Before: 9 URNs. After: unchanged. |

---

### Step: discover

| Column | Value |
|---|---|
| **Step id** | discover |
| **Action id** | `action:documentation/discover` |
| **Profile id** | `agent_profile:curator-carla` |
| **Resolved DRG artifact URNs** | `directive:DIRECTIVE_003`, `directive:DIRECTIVE_010`, `tactic:adr-drafting-workflow`†, `tactic:premortem-risk-identification`, `tactic:requirements-validation-workflow` |
| **Scope edges involved** | `directive:DIRECTIVE_003`, `directive:DIRECTIVE_010`, `tactic:premortem-risk-identification`, `tactic:requirements-validation-workflow` |
| **Missing context** | none |
| **Irrelevant / too-broad context** | none |
| **Recommended DRG edge changes** | none |
| **Before/after evidence** | Before: 5 URNs. After: unchanged. |

---

### Step: generate

| Column | Value |
|---|---|
| **Step id** | generate |
| **Action id** | `action:documentation/generate` |
| **Profile id** | `agent_profile:curator-carla` |
| **Resolved DRG artifact URNs** | `directive:DIRECTIVE_010`, `directive:DIRECTIVE_037`, `tactic:acceptance-test-first`†, `tactic:atdd-adversarial-acceptance`†, `tactic:requirements-validation-workflow`, `tactic:usage-examples-sync`† |
| **Scope edges involved** | `directive:DIRECTIVE_010`, `directive:DIRECTIVE_037`, `tactic:requirements-validation-workflow` |
| **Missing context** | none |
| **Irrelevant / too-broad context** | none |
| **Recommended DRG edge changes** | none |
| **Before/after evidence** | Before: 6 URNs. After: unchanged. |

---

### Step: publish

| Column | Value |
|---|---|
| **Step id** | publish |
| **Action id** | `action:documentation/publish` |
| **Profile id** | `agent_profile:curator-carla` |
| **Resolved DRG artifact URNs** | `directive:DIRECTIVE_010`, `directive:DIRECTIVE_037`, `tactic:acceptance-test-first`†, `tactic:atdd-adversarial-acceptance`†, `tactic:requirements-validation-workflow`, `tactic:usage-examples-sync`† |
| **Scope edges involved** | `directive:DIRECTIVE_010`, `directive:DIRECTIVE_037`, `tactic:requirements-validation-workflow` |
| **Missing context** | none |
| **Irrelevant / too-broad context** | none |
| **Recommended DRG edge changes** | none |
| **Before/after evidence** | Before: 6 URNs. After: unchanged. |

---

### Step: validate

| Column | Value |
|---|---|
| **Step id** | validate |
| **Action id** | `action:documentation/validate` |
| **Profile id** | `agent_profile:curator-carla` |
| **Resolved DRG artifact URNs** | `directive:DIRECTIVE_010`, `directive:DIRECTIVE_037`, `tactic:acceptance-test-first`†, `tactic:atdd-adversarial-acceptance`†, `tactic:premortem-risk-identification`, `tactic:requirements-validation-workflow`, `tactic:usage-examples-sync`† |
| **Scope edges involved** | `directive:DIRECTIVE_010`, `directive:DIRECTIVE_037`, `tactic:premortem-risk-identification`, `tactic:requirements-validation-workflow` |
| **Missing context** | none |
| **Irrelevant / too-broad context** | none |
| **Recommended DRG edge changes** | none |
| **Before/after evidence** | Before: 7 URNs. After: unchanged. |

---

### Step: retrospect

| Column | Value |
|---|---|
| **Step id** | retrospect |
| **Action id** | `action:documentation/retrospect` |
| **Profile id** | `agent_profile:retrospective-facilitator` |
| **Resolved DRG artifact URNs** | `agent_profile:retrospective-facilitator`, `directive:DIRECTIVE_003/010/018`, `styleguide:kitty-glossary-writing`, `tactic:adr-drafting-workflow`, `tactic:autonomous-operation-protocol`, `tactic:glossary-curation-interview`, `tactic:premortem-risk-identification`, `tactic:requirements-validation-workflow`, `tactic:stopping-conditions` |
| **Scope edges involved** | Full retrospect scope |
| **Missing context** | none |
| **Irrelevant / too-broad context** | none |
| **Recommended DRG edge changes** | none |
| **Before/after evidence** | Before: 11 URNs. After: unchanged. |
