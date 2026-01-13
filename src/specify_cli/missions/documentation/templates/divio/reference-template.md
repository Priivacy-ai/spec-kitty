---
type: reference
divio_category: information-oriented
target_audience: all-users
purpose: technical-description
outcome: user-knows-what-exists
---

# Reference: {API/CLI/CONFIG_NAME}

> **Divio Type**: Reference (Information-Oriented)
> **Target Audience**: All users looking up technical details
> **Purpose**: Provide accurate, complete technical description
> **Outcome**: User finds the information they need

## Overview

{Brief description of what this reference documents}

**Quick Navigation**:
- [{Section 1}](#{section-anchor})
- [{Section 2}](#{section-anchor})
- [{Section 3}](#{section-anchor})

## {API Class/CLI Command/Config Section}

### Syntax

```{language}
{canonical-syntax}
```

### Description

{Neutral, factual description of what this does}

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `{param1}` | `{type}` | Yes | - | {Description} |
| `{param2}` | `{type}` | No | `{default}` | {Description} |
| `{param3}` | `{type}` | No | `{default}` | {Description} |

### Return Value

**Type**: `{return-type}`

**Description**: {What is returned}

**Possible values**:
- `{value1}`: {When this is returned}
- `{value2}`: {When this is returned}

### Exceptions / Errors

| Error | Condition | Resolution |
|-------|-----------|------------|
| `{ErrorType}` | {When it occurs} | {How to handle} |
| `{ErrorType}` | {When it occurs} | {How to handle} |

### Examples

**Basic usage**:
```{language}
{basic-example}
```

**With options**:
```{language}
{example-with-options}
```

**Advanced usage**:
```{language}
{advanced-example}
```

### Notes

- {Important implementation detail}
- {Edge case or limitation}
- {Performance consideration}

### See Also

- [{Related API/command}](#{anchor})
- [{Related concept}](../explanation/{link})

---

## {Next API Class/CLI Command/Config Section}

{Repeat the structure above for each item being documented}

---

## Constants / Enumerations

### `{ConstantName}`

**Type**: `{type}`
**Value**: `{value}`
**Description**: {What it represents}

**Usage**:
```{language}
{usage-example}
```

---

## Type Definitions

### `{TypeName}`

```{language}
{type-definition}
```

**Properties**:

| Property | Type | Description |
|----------|------|-------------|
| `{prop1}` | `{type}` | {Description} |
| `{prop2}` | `{type}` | {Description} |

**Example**:
```{language}
{example-usage}
```

---

## Version History

### Version {X.Y.Z}
- Added: `{new-feature}`
- Changed: `{modified-behavior}`
- Deprecated: `{old-feature}` (use `{new-feature}` instead)
- Removed: `{removed-feature}`

### Version {X.Y.Z}
- {Changes in this version}

---

## Write the Docs Best Practices (Remove this section before publishing)

**Reference Principles**:
- ✅ Information-oriented: Describe facts accurately
- ✅ Structure around code organization (classes, modules, commands)
- ✅ Consistent format for all similar items
- ✅ Complete and accurate
- ✅ Neutral tone (no opinions or recommendations)
- ✅ Include examples for every item
- ✅ Do not explain how to use (that's How-To) or why (that's Explanation)

**Accessibility**:
- ✅ Proper heading hierarchy
- ✅ Alt text for diagrams/screenshots
- ✅ Tables for structured data
- ✅ Syntax highlighting for code
- ✅ Descriptive link text

**Inclusivity**:
- ✅ Diverse example names
- ✅ Gender-neutral language
- ✅ No cultural assumptions

**Reference-Specific Guidelines**:
- Alphabetical or logical ordering
- Every public API/command documented
- Parameters/options in consistent format (tables work well)
- Examples for typical usage
- Don't bury the lead - most important info first
- Link to related reference items
- Version history for deprecations/changes
- Autogenerate from code when possible (JSDoc, Sphinx, rustdoc)
