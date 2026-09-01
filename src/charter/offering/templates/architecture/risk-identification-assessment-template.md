# Risk Identification Assessment

Use this template to document a premortem-style risk assessment for an
architectural decision, implementation plan, or high-impact change.

## Context

- Initiative / Feature:
- Owner:
- Date:
- Scope under review:
- Related ADRs:
- Related Specs / Plans:

## Destructive Prompt

Answer this directly before listing risks:

> If this plan fails badly, what are the most likely and most damaging ways it fails?

## Failure Scenarios

| ID | Failure Scenario | Category | Impact | Likelihood | Notes |
|---|---|---|---|---|---|
| R01 | | | High / Medium / Low | High / Medium / Low | |
| R02 | | | High / Medium / Low | High / Medium / Low | |
| R03 | | | High / Medium / Low | High / Medium / Low | |

Categories may include:
- correctness
- security
- performance
- operability
- delivery
- adoption
- compliance
- organizational

## Prioritized Risks

Select:
- the 3 most likely risks
- the 2 highest-impact surprise or catastrophic risks

| Risk ID | Why Prioritized | Trigger Signal |
|---|---|---|
| R__ | | |
| R__ | | |
| R__ | | |

## Mitigation Plan

For each prioritized risk, define prevention, detection, and response.

| Risk ID | Prevention | Detection | Response | Owner |
|---|---|---|---|---|
| R__ | | | | |
| R__ | | | | |
| R__ | | | | |

## Monitoring Cadence

- Review checkpoint cadence:
- Leading indicators to watch:
- Escalation threshold:

## Decision

- Proceed / revise / defer:
- Conditions required before proceeding:
- Follow-up work packages or tasks:

## Notes

- Keep the assessment concise and actionable.
- Prefer concrete failure modes over vague concerns.
- If no material risks are identified, record why the scope is low-risk.
