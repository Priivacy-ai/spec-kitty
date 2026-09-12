---
work_package_id: WPB2
title: Implement a three-way merge helper
---

## Objective

Add a `merge_frontmatter()` helper that combines two frontmatter mappings.

## Acceptance Criteria

- `merge_frontmatter(a, b)` returns a mapping where `b`'s keys win on conflict.
- Unit tests cover the empty, disjoint, and conflicting cases and pass in the
  diff.
- The helper mentions merge and CI in its docstring, but its correctness is
  fully verifiable by the tests shipped in this WP.
