# The Gherkin Scenario Language

Reference for **Gherkin, the language** — the plain-text DSL for writing
behavioural scenarios. This guide covers the notation only. It is deliberately
**not** stack-specific: the runners that execute Gherkin (Cucumber, behave,
SpecFlow, Behat, Godog, and others) each bind steps to code in their own way and
are out of scope here. Author scenarios per the
[Given-When-Then Authoring](../styleguides/given-when-then-authoring.styleguide.yaml)
styleguide; this guide is the grammar those scenarios are written in.

## The Building Blocks

A Gherkin file (`.feature`) is a small, line-oriented document. Each significant
line starts with a keyword.

| Keyword | Role |
|---------|------|
| `Feature:` | Names the capability the file describes; free-text description lines may follow. |
| `Background:` | Steps run before **every** scenario in the feature — the shared `Given` context. |
| `Scenario:` | One concrete behaviour, written as a sequence of steps. |
| `Scenario Outline:` | A scenario template parameterised by `<placeholders>`, expanded once per row of an `Examples` table. |
| `Given` | A precondition / starting context. |
| `When` | The single trigger — the action under test. |
| `Then` | The expected, observable outcome. |
| `And` / `But` | Continue the previous step's phase without repeating its keyword. |
| `Examples:` | A table of rows that drive a `Scenario Outline`. |
| `@tag` | A label on a `Feature` or `Scenario`, used to group or select scenarios. |
| `"""` (doc string) | A multi-line text argument attached to a step. |
| `\| … \|` (data table) | A tabular argument attached to a step. |
| `#` | A comment line. |

## A Complete Feature

```gherkin
@payments
Feature: Account withdrawals
  As an account holder
  I want to withdraw funds
  So that I can access my money

  Background:
    Given a registered account holder

  Scenario: A withdrawal within balance succeeds
    Given an account with a balance of 100 EUR
    When the holder withdraws 30 EUR
    Then the balance is 70 EUR
    And a withdrawal receipt is issued

  Scenario: A withdrawal above balance is refused
    Given an account with a balance of 20 EUR
    When the holder withdraws 30 EUR
    Then the withdrawal is refused
    But the balance is unchanged
```

## Scenario Outline and Examples

A `Scenario Outline` writes the behaviour once and runs it for each row of the
`Examples` table. `<placeholder>` tokens in the steps are substituted from the
matching table column.

```gherkin
  Scenario Outline: Withdrawal is refused when it exceeds the balance
    Given an account with a balance of <balance> EUR
    When the holder withdraws <amount> EUR
    Then the withdrawal is <result>

    Examples:
      | balance | amount | result   |
      | 100     | 30     | accepted |
      | 20      | 30     | refused  |
      | 0       | 1      | refused  |
```

## Step Arguments: Doc Strings and Data Tables

A step can carry a larger argument. A **doc string** attaches multi-line text; a
**data table** attaches rows of values.

```gherkin
  Scenario: A welcome note is stored verbatim
    Given a new customer "Ada"
    When a welcome note is recorded:
      """
      Welcome, Ada.
      Your account is ready.
      """
    Then the stored note matches the recorded text

  Scenario: Several items are added to a cart
    Given an empty cart
    When the customer adds:
      | item      | quantity |
      | notebook  | 2        |
      | pen       | 5        |
    Then the cart contains 7 items
```

## And / But

`And` and `But` continue the phase of the step above them — they are readability
sugar, not new phases. `But` reads naturally for a contrasting `Then`. Neither
introduces a second trigger: a scenario still has exactly one `When`.

```gherkin
    Given a verified customer
    And a cart of in-stock items      # a second Given fact
    When they check out
    Then the order is accepted
    And a confirmation email is queued  # a second Then observation
    But no payment is captured yet
```

## Scope Boundary — Language, Not Runner

Everything above is the Gherkin **language**. What Gherkin does **not** define:

- **Step definitions / bindings** — the glue that maps a `Given …` line to code
  is a *runner* concern (Cucumber step defs, behave `@given`, SpecFlow bindings).
- **Execution, reporting, hooks, tags-as-filters** — how scenarios are run,
  which tags select them, before/after hooks, and output formats are all
  runner-specific.
- **Parameter typing / expression syntax** — Cucumber Expressions, regexes, and
  transform registries belong to the runner, not the language.

Write scenarios in the language; choose and configure a runner separately.
