"""NFR-001 architectural guard + T006 source guards for the review-claim gate.

Three invariants, each with a *firing* negative control so the gate is a real
scan, not a tautology:

1. **NFR-001** — actor/role in the claim-resolution surface come ONLY from the
   canonical reduction, never from WP-file frontmatter (scoped to actor/role;
   the ``get_wp_lane`` lane-genesis fallback is permitted and out of scope).
2. **T006(b)** — ``_check_no_review_conflict`` is allow-only: its body contains
   NO reject / ``return False`` branch (a dormant reject branch is invisible to
   behavioural tests when ``current_actor`` is ``None``).
3. **T006(a)** — no guard/FSM test re-asserts the role-free distinct-actor block
   (the "already claimed for review" message on the ``validate_transition`` /
   ``can_transition_to`` surface).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src" / "specify_cli"


# A frontmatter read that sources actor/role: the token ``frontmatter`` within
# ~40 chars of ``actor``/``role`` in either order. ``lane`` is intentionally NOT
# matched (the get_wp_lane genesis fallback is permitted).
_FRONTMATTER_ACTOR_ROLE = re.compile(
    r"frontmatter[^\n]{0,40}?\b(?:role|actor)\b"
    r"|\b(?:role|actor)\b[^\n]{0,40}?frontmatter",
    re.IGNORECASE,
)


def _frontmatter_actor_role_reads(text: str) -> list[str]:
    return [m.group(0) for m in _FRONTMATTER_ACTOR_ROLE.finditer(text)]


def _function_source(path: Path, qualname: str) -> str:
    """Return the source segment of ``qualname`` (``A.b`` or ``f``) in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parts = qualname.split(".")

    def _find(nodes: list[ast.stmt], names: list[str]) -> ast.AST | None:
        head, rest = names[0], names[1:]
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == head:
                if not rest:
                    return node
                return _find(list(ast.iter_child_nodes(node)), rest)  # type: ignore[arg-type]
        return None

    node = _find(list(ast.iter_child_nodes(tree)), parts)
    assert node is not None, f"{qualname} not found in {path}"
    return ast.get_source_segment(path.read_text(encoding="utf-8"), node) or ""


# The claim-resolution surface: the aggregate seam and the lifecycle re-claim,
# plus the two reduction-backed reads they delegate to.
_CLAIM_RESOLUTION_SURFACE: tuple[tuple[str, str], ...] = (
    ("status/aggregate.py", "MissionStatus.transition"),
    ("status/aggregate.py", "MissionStatus._resolve_current_lane"),
    ("status/work_package_lifecycle.py", "start_review_status"),
    ("coordination/status_service.py", "wp_lane_actor_from_events"),
    ("coordination/status_transition.py", "read_current_wp_state_transactional"),
)


def test_nfr001_claim_surface_never_reads_actor_role_from_frontmatter() -> None:
    for rel, qualname in _CLAIM_RESOLUTION_SURFACE:
        source = _function_source(_SRC / rel, qualname)
        offenders = _frontmatter_actor_role_reads(source)
        assert not offenders, (
            f"{rel}:{qualname} resolves actor/role from frontmatter (NFR-001 violation): {offenders}"
        )


def test_nfr001_detector_fires_on_planted_frontmatter_read() -> None:
    """Negative control: the detector MUST fire on a planted frontmatter read."""
    planted = 'self.role = frontmatter.get("role")\nactor = wp_frontmatter["actor"]'
    assert _frontmatter_actor_role_reads(planted), (
        "NFR-001 detector is vacuous — it did not fire on a planted frontmatter actor/role read"
    )


# ---------------------------------------------------------------------------
# T006(b) — _check_no_review_conflict has no reject / return False branch.
# ---------------------------------------------------------------------------


def _check_no_review_conflict_body() -> str:
    return _function_source(_SRC / "status" / "wp_state.py", "_check_no_review_conflict")


def test_check_no_review_conflict_is_allow_only_no_reject_branch() -> None:
    body = _check_no_review_conflict_body()
    # Split off the docstring so prose describing the removed behaviour does not
    # trip the literal scan.
    module = ast.parse(body)
    func = module.body[0]
    assert isinstance(func, ast.FunctionDef)
    executable = [n for n in func.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
    code = "\n".join(ast.unparse(n) for n in executable)
    # ``ast.unparse`` renders a tuple return as ``return (True, None)`` — scan for
    # the bare ``False`` literal (a reject verdict) rather than a source spelling.
    assert "False" not in code, (
        f"_check_no_review_conflict must be allow-only (no reject/False branch); found in:\n{code}"
    )
    assert "already claimed" not in code, (
        "_check_no_review_conflict must not carry the old block message"
    )
    # It must actually return an allow tuple.
    assert "True, None" in code


def test_allow_only_detector_fires_on_planted_reject_branch() -> None:
    """Negative control: the reject-branch scan MUST fire on a planted block."""
    planted = ast.parse(
        "def f(ctx):\n"
        "    if ctx.current_actor:\n"
        "        return False, 'already claimed'\n"
        "    return True, None\n"
    )
    func = planted.body[0]
    assert isinstance(func, ast.FunctionDef)
    code = "\n".join(ast.unparse(n) for n in func.body)
    assert "False" in code and "already claimed" in code


# ---------------------------------------------------------------------------
# T006(a) — no guard/FSM test re-asserts the role-free distinct-actor block.
# ---------------------------------------------------------------------------

_GUARD_FSM_TEST_FILES: tuple[str, ...] = (
    "tests/specify_cli/status/test_wp_state.py",
    "tests/status/test_transitions.py",
    "tests/unit/status/test_review_claim_transition.py",
)


def test_no_guard_test_reasserts_role_free_distinct_actor_block() -> None:
    """The guard/FSM surfaces are allow-only; no test may assert the old block.

    The genuine reject lives ONLY at the ``in_review`` re-claim lifecycle test
    (``WorkPackageClaimConflict``), so the "already claimed" block message must
    not appear as an expectation on the ``validate_transition`` /
    ``can_transition_to`` guard surfaces.
    """
    for rel in _GUARD_FSM_TEST_FILES:
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "already claimed" not in text, (
            f"{rel} re-asserts the role-free distinct-actor block ('already claimed'); "
            "the guard is allow-only — move reject coverage to the in_review re-claim test"
        )
