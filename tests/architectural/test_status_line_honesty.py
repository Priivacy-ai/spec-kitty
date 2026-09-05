"""#3723 — the status-line honesty architectural ratchet.

Six diagnostics reported healthy while the thing they described was broken
because each status surface *hand-rolled* its own green banner alongside — never
derived from — the detail it printed. The fix routes every auth/health line
through the one typed authority ``specify_cli.auth.verdict``. This guard keeps it
that way, modelled on ``test_verdict_vocab_single_source.py``'s AST
negative+positive+allowlist shape (evasion by splitting literals across lines
must still fail — it is a module-level AST scan, not a same-line grep).

Three checks:

1. **Positive (genuine routing).** Each surviving status surface must import
   from ``specify_cli.auth.verdict`` AND reference one of its verdict symbols
   (call or type annotation). A surface that merely stops spelling ``Authenticated``
   without adopting the authority fails this — same anti-evasion shape as the
   vocab guard's positive check.
2. **Structural invariant.** ``HealthVerdict`` keeps its 3-member ``Health``
   Literal and exposes ``headline`` as a computed *property*, never a settable
   field. This makes "a banner that contradicts the detail" a compile-shaped
   impossibility (rule 3), so the negative check only has to prove no surface
   hand-rolls the banner literal.
3. **Negative (no hand-rolled claim).** No surface module may author an
authenticated-claim string literal (``Authenticated`` / ``No problems
detected``) outside the one allowlisted, verdict-gated
   render site. Docstrings are skipped (comments/docstrings mentioning the words
   must not trip it — the vocab guard's cycle-1 lesson).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.fast]

#: The canonical authority — excluded from every scan (it is the source of the
#: verdict vocabulary, not a consumer of it).
_VERDICT_RELPATH = "src/specify_cli/auth/verdict.py"

#: The surviving status surfaces from #3723. Each must genuinely route through the
#: verdict authority (positive check) and must not hand-roll a banner (negative).
_SURFACES: tuple[str, ...] = (
    "src/specify_cli/cli/commands/_auth_status.py",
    "src/specify_cli/cli/commands/_auth_doctor.py",
)

#: The verdict authority's public symbols that count as "routing through it".
_VERDICT_SYMBOLS: frozenset[str] = frozenset({"HealthVerdict", "evaluate_auth_verdict", "auth_verdict_from_flags"})

#: Authenticated-claim tokens a surface must never author as a bare literal —
#: they must come from ``HealthVerdict.headline`` (or, for the all-clear, be
#: gated on a verdict's ``ok`` state at an allowlisted render site).
_CLAIM_TOKENS: frozenset[str] = frozenset({"Authenticated", "No problems detected"})

#: The ONE legitimate, verdict-gated all-clear render site: ``auth doctor`` prints
#: "No problems detected." only when ``report.auth_verdict.state == 'ok'`` and no
#: finding was raised (enforced in ``render_report`` + ``test_auth_doctor_report``).
#: Pinned exactly by :func:`test_allowlist_is_pinned`; it may not silently grow.
_ALLOWLIST: dict[str, frozenset[str]] = {
    "src/specify_cli/cli/commands/_auth_doctor.py": frozenset({"No problems detected"}),
}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "src" / "specify_cli").is_dir():
            return parent
    raise AssertionError("could not locate repo root from test file")


def _parse(root: Path, relpath: str) -> ast.Module:
    path = root / relpath
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _docstring_node_ids(tree: ast.AST) -> set[int]:
    """``id()`` of every docstring Constant node (module/class/function body[0]).

    Docstrings are ``ast.Constant`` too, so a scan that did not exclude them would
    false-positive on prose that merely mentions "Authenticated"."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                ids.add(id(body[0].value))
    return ids


def _code_string_constants(tree: ast.Module) -> list[str]:
    """Every code-level string constant, EXCLUDING docstrings."""
    skip = _docstring_node_ids(tree)
    return [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip]


def _bound_verdict_names(tree: ast.Module) -> set[str]:
    """Local names bound to a verdict symbol via ``from ...auth.verdict import X``
    (handles ``as`` aliasing)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "specify_cli.auth.verdict":
            for alias in node.names:
                if alias.name in _VERDICT_SYMBOLS:
                    names.add(alias.asname or alias.name)
    return names


def _references_name(tree: ast.Module, names: set[str]) -> bool:
    """True iff any ``ast.Name`` with an id in *names* appears in *tree* — this
    covers both calls (``evaluate_auth_verdict(...)``) and type annotations
    (``auth_verdict: HealthVerdict``), so a surface that only annotates a field
    with the type still counts as genuine routing."""
    return any(isinstance(node, ast.Name) and node.id in names for node in ast.walk(tree))


def _routes_through_verdict(tree: ast.Module) -> bool:
    bound = _bound_verdict_names(tree)
    return bool(bound) and _references_name(tree, bound)


# ---------------------------------------------------------------------------
# Check 1 — positive: each surface genuinely routes through the authority
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relpath", _SURFACES)
def test_surface_routes_through_verdict_authority(relpath: str) -> None:
    root = _repo_root()
    tree = _parse(root, relpath)
    assert _routes_through_verdict(tree), (
        f"{relpath} must import from specify_cli.auth.verdict AND reference a "
        f"verdict symbol {sorted(_VERDICT_SYMBOLS)} — it may not hand-roll an "
        "auth/health status line."
    )


def test_positive_check_rejects_import_without_reference(tmp_path: Path) -> None:
    """Anti-evasion: importing the symbol but never using it is NOT routing."""
    (tmp_path / "m.py").write_text(
        "from specify_cli.auth.verdict import HealthVerdict\n\n_NOTE = 'unused'\n",
        encoding="utf-8",
    )
    tree = ast.parse((tmp_path / "m.py").read_text(encoding="utf-8"))
    assert not _routes_through_verdict(tree)


def test_positive_check_rejects_same_named_local_without_import(tmp_path: Path) -> None:
    """Anti-evasion: a same-named local callable without the real import fails."""
    (tmp_path / "m.py").write_text(
        "def evaluate_auth_verdict(x):\n    return x\n\n\nevaluate_auth_verdict(1)\n",
        encoding="utf-8",
    )
    tree = ast.parse((tmp_path / "m.py").read_text(encoding="utf-8"))
    assert not _routes_through_verdict(tree)


# ---------------------------------------------------------------------------
# Check 2 — structural invariant on HealthVerdict
# ---------------------------------------------------------------------------


def _healthverdict_classdef(tree: ast.Module) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "HealthVerdict":
            return node
    raise AssertionError("HealthVerdict class not found in the verdict authority")


def test_health_literal_is_exactly_three_members() -> None:
    """``Health`` stays a 3-member tri-state — guards against a 4th 'warn' value
    sneaking back to blur ok/unknown/fail."""
    tree = _parse(_repo_root(), _VERDICT_RELPATH)
    literals: set[str] | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "Health" for t in node.targets) and isinstance(node.value, ast.Subscript):
            elts = node.value.slice
            values = elts.elts if isinstance(elts, ast.Tuple) else [elts]
            literals = {v.value for v in values if isinstance(v, ast.Constant) and isinstance(v.value, str)}
    assert literals == {"ok", "unknown", "fail"}, literals


def test_headline_is_a_property_not_a_settable_field() -> None:
    """``headline`` is a computed property; there is NO settable banner field —
    a caller cannot author a headline that disagrees with the detail (rule 3)."""
    tree = _parse(_repo_root(), _VERDICT_RELPATH)
    cls = _healthverdict_classdef(tree)

    # No dataclass field named ``headline`` (would be an AnnAssign in the body).
    field_names = {node.target.id for node in cls.body if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)}
    assert "headline" not in field_names, "headline must not be a settable field"
    # ``state`` is the tri-state field, annotated with the Health alias.
    assert "state" in field_names

    # ``headline`` is defined as a @property method (not a settable field).
    headline_props = [
        node
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == "headline" and any(isinstance(d, ast.Name) and d.id == "property" for d in node.decorator_list)
    ]
    assert headline_props, "headline must be a @property, not a settable field"


# ---------------------------------------------------------------------------
# Check 3 — negative: no hand-rolled authenticated-claim literal
# ---------------------------------------------------------------------------


def _claim_offenders(root: Path, relpath: str) -> set[str]:
    """Claim tokens authored as bare code literals in *relpath*, minus its
    allowlist. Substring match (so ``"  No problems detected."`` counts) over
    code-only string constants (docstrings excluded)."""
    tree = _parse(root, relpath)
    permitted = _ALLOWLIST.get(relpath, frozenset())
    found: set[str] = set()
    for literal in _code_string_constants(tree):
        for token in _CLAIM_TOKENS:
            if token in literal and token not in permitted:
                found.add(token)
    return found


@pytest.mark.parametrize("relpath", _SURFACES)
def test_surface_has_no_hand_rolled_claim(relpath: str) -> None:
    root = _repo_root()
    offenders = _claim_offenders(root, relpath)
    assert not offenders, (
        f"{relpath} authors hand-rolled authenticated-claim literal(s) "
        f"{sorted(offenders)} outside a HealthVerdict — render verdict.headline "
        "instead (or gate an all-clear on verdict.state == 'ok' and allowlist it)."
    )


def test_negative_check_skips_docstrings(tmp_path: Path) -> None:
    """A docstring mentioning the claim word must NOT trip the negative check."""
    (tmp_path / "m.py").write_text(
        '"""This module talks about being Authenticated in prose."""\n\nX = 1\n',
        encoding="utf-8",
    )
    tree = ast.parse((tmp_path / "m.py").read_text(encoding="utf-8"))
    assert not any(t in c for c in _code_string_constants(tree) for t in _CLAIM_TOKENS)


def test_negative_check_catches_split_literal(tmp_path: Path) -> None:
    """Module-level AST scan: a claim literal is caught wherever it sits (not a
    same-line grep)."""
    (tmp_path / "m.py").write_text(
        "def a():\n    return 'x'\n\n\ndef b():\n    return '[green]Authenticated[/green]'\n",
        encoding="utf-8",
    )
    tree = ast.parse((tmp_path / "m.py").read_text(encoding="utf-8"))
    assert any("Authenticated" in c for c in _code_string_constants(tree))


# ---------------------------------------------------------------------------
# Allowlist is pinned (empty-checked): it may not silently absorb regressions
# ---------------------------------------------------------------------------


def test_allowlist_is_pinned() -> None:
    """The allowlist holds exactly one documented, verdict-gated render site.

    Any other entry — or any additional token — is a regression: a surface would
    be exempted from the negative check without the reviewer seeing it here."""
    expected = {
        "src/specify_cli/cli/commands/_auth_doctor.py": frozenset({"No problems detected"}),
    }
    assert expected == _ALLOWLIST
