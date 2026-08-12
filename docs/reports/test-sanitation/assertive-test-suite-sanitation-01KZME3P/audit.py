#!/usr/bin/env python3
"""Mission-local, deterministic test-sanitation evidence auditor.

This file is deliberately not installed.  It combines independent AST source
discovery with pytest's collection hooks; neither view is allowed to silently
stand in for the other.
"""

from __future__ import annotations

import argparse
import ast
from collections.abc import Callable, Iterable, Mapping, Sequence
import contextlib
import copy
import dataclasses
import datetime as dt
import fnmatch
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import shlex
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from typing import Any, TypeVar, cast

import pytest
import yaml

SCHEMA = "test-sanitation/v1"
NORMALIZATION_SCHEMA = "test-sanitation-normalization/v1"
TARGET_INVENTORY_SHA = "28ae75ea998c898aba57364db7a06d2088bd2af2"
SIBLING_E2E_SHA = "e278ad76552b954f9c7f4ea1e7a364978678b3ca"
FROZEN_ROUTE_AUTHORITY_HASHES = {
    "full-collection": "312a09b4b9a5ff1522fe89505480e8685ef1bbe48b8cc1b890b93b547d495d76",
    "full-parallel": "ede8cca1c22d153a1fbc0d0b89d765fda8bf3eef457dcd250ab63eda457f4bc0",
    "orphan-sweep": "51bc3f1de75f7a703cf2ba1191a87f489b262179c3dee88b3e3fa7de145a3022",
    "regression": "f0cd6b5a22bb6a19d583f2bdb02cc0d5adb82f0ec6a267b58b7eb0ea8e3f6eaf",
    "quarantine": "5e2f1c413848f5a65723ae6e2cb72e0e9412a7d536613e0425406330c2e5dcf2",
    "contract": "bd7d2a3bc9b4586c4f36cbfb72a95c1775f37b953b2955ac9bcf6371d25bdf5b",
    "architectural": "8f4bf7d0f12e095ded2a8c044f5f4d8abcde84e18661c25816f5aa5c73a62de0",
    "sibling-e2e": "d0185c8ffc5775bd68db1611de83d513ce45fcf8f537103ca4d570f41a3e41c6",
}
FROZEN_BASE_CENSUS_FILE_SHA256 = "c15ef616766752ac1d30ddac8d24b7929f4f874d45cc131392d443c1de9d5d8b"
FROZEN_BASE_CENSUS_CONTENT_SHA256 = "08ef931c46e9d6a2608baec729203442640933bf2970cc83e794bf2f78011e08"
FROZEN_BASE_RAW_RESULT_SHA256 = "67120f918ecef7e45791aa81d3c6823b1546820f478e53fa24d075f1adbfb60c"
FROZEN_BASE_RAW_RESULT_REFERENCE = f"sha256:{FROZEN_BASE_RAW_RESULT_SHA256}"
FROZEN_BASE_EXECUTION_CONTENT_SHA256 = "62d9db3a9dfbde24dc9c4e887eb840f65664afd8aa9aea3fcef28c4584cbbd93"
WP08_OWNERSHIP_TAKEOVERS = {
    ".github/workflows/ci-quality.yml": ("WP07", "WP08"),
    "docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp07-results.json": ("WP07", "WP08"),
    "tests/architectural/test_ci_quality_path_filters.py": ("WP07", "WP08"),
    "tests/conftest.py": ("WP02", "WP08"),
    "tests/specify_cli/cli/commands/test_doctor_restart_daemon_timing.py": ("WP06", "WP08"),
    "tests/sync/test_dual_write_integration.py": ("WP06", "WP08"),
    "tests/test_test_venv_bootstrap.py": ("WP02", "WP08"),
}
VERDICTS = {"KEEP", "CONSOLIDATE", "FIX_TEST", "FIX_PRODUCT", "DELETE", "TEMPORARY"}
PROFILES = {
    "inert", "duplicate", "structural", "contract", "slow", "flake",
    "dead_symbol", "route", "environmental_platform",
}
COLLECTION_STATES = {"collected", "ignored", "deselected", "error", "zero_node"}
OUTCOMES = {"passed", "failed", "error", "skipped", "xfailed", "xpassed", "not_run", None}
MEASUREMENT_OUTCOMES = {"passed", "failed", "error", "skipped", "xfailed", "xpassed", "not_run"}
GRANULARITIES = {"function", "family", "duplicate_cluster", "node"}
CENSUS_ROLES = {"base", "head"}
ROUTE_ROLES = {"owner", "coverage", "platform", "hard_gate"}
EQUIVALENCE_DIMENSIONS = {
    "production_path", "oracle", "outcome", "route_role", "cost_class", "platform", "disposition",
}
TEST_NAME = re.compile(r"^test(?:_|$)")
VOLATILE_TEMP = re.compile(
    r"(?:/private)?/var/folders/[^/]+/[^/]+/T/[^/\s'\"\]\),]+"
    r"|/tmp/[^/\s'\"\]\),]+"
)
F = TypeVar("F", bound=Callable[..., Any])


def hookimpl(**kwargs: Any) -> Callable[[F], F]:
    """Typed facade for pluggy's dynamically typed pytest decorator."""
    return cast(Callable[[F], F], pytest.hookimpl(**kwargs))


class AuditError(RuntimeError):
    """Fail-closed evidence validation error."""


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _stable(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, list):
        # List order may encode argv, precedence, parameter, or event semantics.
        # Set-like lists are sorted explicitly where they are constructed.
        return [_stable(item) for item in value]
    if isinstance(value, str):
        return VOLATILE_TEMP.sub("<TEMP_ROOT>", value)
    return value


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(_stable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode()
    # Mission evidence uses standard SHA-256 for portable file/body checksums.
    return hashlib.sha256(value).hexdigest()  # noqa: TID251


def _git_rev_parse(spec: str, *, root: Path | None = None) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", spec], cwd=root, check=False,
        capture_output=True, text=True,
    )
    value = completed.stdout.strip()
    if completed.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise AuditError(f"cannot resolve git authority {spec}")
    return value


def _frozen_candidate_members(root: Path) -> set[str]:
    """Load candidate identities from the immutable, content-addressed base census."""
    path = (
        root / "docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/"
        "raw/base-census.json"
    )
    try:
        body = path.read_bytes()
        census = json.loads(body)
        manifests = census["manifests"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise AuditError(f"cannot load frozen candidate universe: {exc}") from exc
    if _sha(body) != FROZEN_BASE_CENSUS_FILE_SHA256:
        raise AuditError("frozen candidate universe census hash drift")
    members = {
        row["member"]
        for key in ("inert_candidates", "scanner_candidates")
        for row in manifests[key]
        if isinstance(row, dict) and isinstance(row.get("member"), str)
    }
    members.update(
        row["member"]
        for group in manifests["exact_body_groups"]
        if isinstance(group, dict)
        for row in group.get("members", [])
        if isinstance(row, dict) and isinstance(row.get("member"), str)
    )
    return members


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_decorator_name(node.value)}.{node.attr}"
    return ast.dump(node, annotate_fields=False, include_attributes=False)


def _shape(node: ast.AST) -> ast.AST:
    """Return a syntax-shape tree; never label this semantic equivalence."""
    tree = ast.parse(ast.unparse(node))
    for child in ast.walk(tree):
        if isinstance(child, ast.Constant):
            child.value = f"<{type(child.value).__name__}>"
        elif isinstance(child, ast.Name) and not isinstance(child.ctx, ast.Store):
            child.id = "<name>"
        elif isinstance(child, ast.arg):
            child.arg = "<arg>"
    return tree


@dataclasses.dataclass(frozen=True)
class SourceUnit:
    id: str
    path: str
    qualname: str
    line: int
    decorators: tuple[str, ...]
    exact_body_sha256: str
    structural_shape_sha256: str
    inert_reasons: tuple[str, ...]


def _unit(
    path: str,
    qualname: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    inherited_decorators: Sequence[str] = (),
) -> SourceUnit:
    decorators = tuple(sorted({_decorator_name(item) for item in node.decorator_list} | set(inherited_decorators)))
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    # Strict duplicate identity intentionally ignores only docstrings.
    exact = ast.dump(ast.Module(body=body, type_ignores=[]), include_attributes=False)
    shape = ast.dump(_shape(ast.Module(body=node.body, type_ignores=[])), include_attributes=False)
    reasons: list[str] = []
    lowered = " ".join(decorators).lower()
    for marker in ("skip", "xfail", "quarantine", "flaky"):
        if re.search(rf"(?:^|\.){marker}(?:$|\s)", lowered):
            reasons.append(f"decorator:{marker}")
    if not body or all(isinstance(item, (ast.Pass, ast.Expr)) and (
        isinstance(item, ast.Pass)
        or (isinstance(item.value, ast.Constant) and item.value.value in (None, Ellipsis))
    ) for item in body):
        reasons.append("empty_body")
    for statement in body:
        if (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Call)
            and _decorator_name(statement.value.func) in {"skip", "pytest.skip"}
        ):
            reasons.append("body:unconditional_pytest.skip")
    return SourceUnit(
        id=f"{path}::{qualname}", path=path, qualname=qualname, line=node.lineno,
        decorators=decorators, exact_body_sha256=_sha(exact),
        structural_shape_sha256=_sha(shape), inert_reasons=tuple(sorted(set(reasons))),
    )


def discover_source(root: Path, tests_root: Path) -> tuple[list[SourceUnit], list[dict[str, str]]]:  # noqa: C901 - recursive AST forms
    units: list[SourceUnit] = []
    parse_errors: list[dict[str, str]] = []
    if not tests_root.exists():
        return units, parse_errors
    for file in sorted(tests_root.rglob("*.py")):
        rel = _rel(file, root)
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=rel)
        except (OSError, SyntaxError, UnicodeError) as exc:
            parse_errors.append({"path": rel, "error": _stable(str(exc))})
            continue
        module_markers: set[str] = set()
        for statement in tree.body:
            if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                if any(isinstance(target, ast.Name) and target.id == "pytestmark" for target in targets):
                    value = statement.value
                    if value is not None:
                        for child in ast.walk(value):
                            if isinstance(child, ast.Call):
                                module_markers.add(_decorator_name(child.func))
        def visit(body: Sequence[ast.stmt], prefix: tuple[str, ...], inherited: set[str], source_path: str = rel) -> None:
            for node in body:
                if isinstance(node, ast.ClassDef):
                    class_markers = inherited | {_decorator_name(item) for item in node.decorator_list}
                    visit(node.body, (*prefix, node.name), class_markers)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qualname = ".".join((*prefix, node.name))
                    if TEST_NAME.match(node.name):
                        units.append(_unit(source_path, qualname, node, sorted(inherited)))
                    visit(node.body, (*prefix, node.name), inherited)
                else:
                    nested_bodies = [value for value in ast.iter_child_nodes(node) if isinstance(value, ast.stmt)]
                    if nested_bodies:
                        visit(nested_bodies, prefix, inherited)

        visit(tree.body, (), module_markers)
    return sorted(units, key=lambda item: item.id), parse_errors


def discover_config(root: Path) -> dict[str, Any]:
    files = ["pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg"]
    result: dict[str, Any] = {"files": [], "collect_ignore": [], "collect_ignore_glob": []}
    for name in files:
        path = root / name
        if path.is_file():
            raw = path.read_bytes()
            result["files"].append({"path": name, "sha256": _sha(raw)})
    tests = root / "tests"
    for conftest in sorted(tests.rglob("conftest.py")) if tests.exists() else []:
        rel_parent = conftest.parent.relative_to(root)
        try:
            tree = ast.parse(conftest.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        for statement in tree.body:
            if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                continue
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            value = statement.value
            for target in targets:
                if not isinstance(target, ast.Name) or target.id not in {"collect_ignore", "collect_ignore_glob"}:
                    continue
                try:
                    values = ast.literal_eval(value) if value is not None else []
                except (ValueError, TypeError):
                    values = ["<dynamic>"]
                for item in values if isinstance(values, (list, tuple)) else [values]:
                    text = str(item)
                    if text != "<dynamic>":
                        text = (rel_parent / text).as_posix()
                    result[target.id].append(text)
    return cast(dict[str, Any], _stable(result))


class CollectionPlugin:
    def __init__(self, root: Path, tests_root: Path) -> None:
        self.root = root
        self.tests_root = tests_root
        self.nodes: list[dict[str, Any]] = []
        self.deselected: list[str] = []
        self.deselected_items: list[dict[str, Any]] = []
        self.errors: list[dict[str, str]] = []
        self.internal_errors: list[str] = []
        self.ignored: set[str] = set()

    @hookimpl(wrapper=True, tryfirst=True)
    def pytest_ignore_collect(self, collection_path: Path, config: pytest.Config) -> Any:
        del config
        result = yield
        if result is True:
            path = Path(str(collection_path))
            if self.tests_root == path or self.tests_root in path.parents:
                self.ignored.add(_rel(path, self.root))
        return result

    @hookimpl(wrapper=True, trylast=True)
    def pytest_collection_modifyitems(self, session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> Any:
        del session, config
        try:
            result = yield
        except BaseException as exc:
            self.internal_errors.append(str(_stable(repr(exc))))
            raise
        for item in items:
            path, line, source_name = item.location
            effective_markers = list(item.iter_markers())
            marker_names = {marker.name for marker in effective_markers}
            reason = None
            for marker in effective_markers:
                if marker.name in {"skip", "skipif", "xfail", "quarantine"}:
                    raw_reason = marker.kwargs.get("reason") or (marker.args[0] if marker.args else marker.name)
                    reason = _stable(repr(raw_reason))
                    break
            self.nodes.append({
                "nodeid": item.nodeid.replace("\\", "/"),
                "path": Path(path).as_posix(), "line": int(line or 0) + 1,
                "parent_source_function": source_name.split("[")[0],
                # Arguments (especially parametrize payloads) are not inventory
                # identity and can be enormous; effective marker names plus the
                # dedicated skip/xfail reason retain every required distinction.
                "markers": sorted(marker_names),
                "quarantined": "quarantine" in marker_names,
                "skip_or_xfail_reason": reason,
            })
        return result

    def pytest_deselected(self, items: list[pytest.Item]) -> None:
        for item in items:
            path, line, source_name = item.location
            nodeid = item.nodeid.replace("\\", "/")
            self.deselected.append(nodeid)
            self.deselected_items.append({
                "nodeid": nodeid, "path": Path(path).as_posix(),
                "line": int(line or 0) + 1,
                "parent_source_function": source_name.split("[")[0],
            })

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.failed:
            self.errors.append({"nodeid": report.nodeid.replace("\\", "/"), "error": _stable(str(report.longrepr))})

    def pytest_internalerror(self, excrepr: object, excinfo: object) -> None:
        del excinfo
        self.internal_errors.append(str(_stable(str(excrepr))))


def _normalize_nodeid(nodeid: str) -> str:
    return cast(str, _stable(nodeid.replace("\\", "/")))


def _atomic_write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary_path = Path(handle.name)
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


class OutcomePlugin:
    """Controller-side exact node/phase capture for a measured pytest run."""

    def __init__(self) -> None:
        self.worker_collections: dict[str, list[str]] = {}
        self.reports: list[dict[str, Any]] = []
        self.internal_errors: list[str] = []

    def pytest_xdist_node_collection_finished(self, node: Any, ids: list[str]) -> None:
        self.worker_collections[str(node.gateway.id)] = [
            _normalize_nodeid(item) for item in ids
        ]

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        worker_id = getattr(report, "worker_id", "controller")
        longrepr = "" if report.longrepr is None else str(report.longrepr)
        self.reports.append({
            "nodeid": _normalize_nodeid(report.nodeid),
            "phase": report.when,
            "outcome": report.outcome,
            "duration": report.duration,
            "wasxfail": getattr(report, "wasxfail", None),
            "worker_id": str(worker_id),
            "longrepr": longrepr,
        })

    def pytest_internalerror(self, excrepr: object, excinfo: object) -> None:
        del excinfo
        self.internal_errors.append(str(excrepr))


def _census_nodeids(census: Mapping[str, Any]) -> tuple[list[str], dict[str, str]]:
    collection = cast(Mapping[str, Any], census["collection"])
    tables = cast(Mapping[str, Any], collection["tables"])
    paths = cast(list[str], tables["paths"])
    nodes = cast(list[list[Any]], collection["nodes"])
    nodeids = [cast(str, row[0]) for row in nodes]
    node_paths = {cast(str, row[0]): paths[cast(int, row[1])] for row in nodes}
    return nodeids, node_paths


def capture_outcomes(  # noqa: C901 - capture fails closed at each phase boundary
    root: Path, census_path: Path, workload_path: Path, route_id: str, raw_output: Path,
) -> dict[str, Any]:
    """Execute one frozen route and reconcile exact phase reports to the census."""
    census = cast(dict[str, Any], json.loads(census_path.read_text(encoding="utf-8")))
    workload = cast(dict[str, Any], yaml.safe_load(workload_path.read_text(encoding="utf-8")))
    routes = cast(list[dict[str, Any]], workload["frozen_workload_dag"]["routes"])
    route = next((item for item in routes if item.get("id") == route_id), None)
    if route is None:
        raise AuditError(f"capture: unknown frozen route {route_id}")
    nodeids, node_paths = _census_nodeids(census)
    memberships = route.get("memberships", [])
    selector = cast(
        dict[str, Any],
        memberships[0].get("selector", {})
        if isinstance(memberships, list) and memberships and isinstance(memberships[0], dict)
        else {},
    )
    ignores = set(cast(list[str], selector.get("ignores", [])))
    if not ignores:
        ignores = {
            arg.split("=", 1)[1] for arg in cast(list[str], route["argv"])
            if arg.startswith("--ignore=")
        }
    excluded = sorted(nodeid for nodeid in nodeids if node_paths[nodeid] in ignores)
    expected = sorted(set(nodeids) - set(excluded))
    if len(nodeids) != len(set(nodeids)):
        raise AuditError("capture: census contains duplicate nodeids")

    plugin = OutcomePlugin()
    pytest_argv = cast(list[str], route["argv"])[1:]
    started = dt.datetime.now(dt.UTC)
    started_monotonic = time.monotonic()
    old_cwd = Path.cwd()
    old_env = {key: os.environ.get(key) for key in cast(dict[str, str], route["env"])}
    try:
        os.chdir(root / cast(str, route["cwd"]))
        os.environ.update(cast(dict[str, str], route["env"]))
        exit_code = int(pytest.main(pytest_argv, plugins=[plugin]))
    finally:
        os.chdir(old_cwd)
        for key, prior in old_env.items():
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior
    ended = dt.datetime.now(dt.UTC)
    wall_seconds = time.monotonic() - started_monotonic

    if plugin.internal_errors:
        raise AuditError(f"capture: pytest internal errors: {plugin.internal_errors[:3]}")
    if not plugin.worker_collections:
        raise AuditError("capture: xdist produced no worker collection inventories")
    expected_set = set(expected)
    first_worker_collection = next(iter(plugin.worker_collections.values()))
    for worker_id, collected in sorted(plugin.worker_collections.items()):
        if (
            len(collected) != len(set(collected))
            or set(collected) != expected_set
            or collected != first_worker_collection
        ):
            raise AuditError(
                f"capture: worker {worker_id} collection mismatch "
                f"count={len(collected)} expected={len(expected)}"
            )

    report_rows = sorted(
        plugin.reports,
        key=lambda row: (str(row["nodeid"]), str(row["phase"]), str(row["worker_id"])),
    )
    unknown_reports = sorted({str(row["nodeid"]) for row in report_rows} - expected_set)
    if unknown_reports:
        raise AuditError(f"capture: reports contain unknown nodeids: {unknown_reports[:5]}")
    raw = {
        "schema_version": SCHEMA,
        "route_id": route_id,
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "ended_at": ended.isoformat().replace("+00:00", "Z"),
        "exit_code": exit_code,
        "worker_collections": {
            worker: {"count": len(items), "ordered_nodeids_sha256": _sha(_json_bytes(items))}
            for worker, items in sorted(plugin.worker_collections.items())
        },
        "reports": report_rows,
        "internal_errors": plugin.internal_errors,
    }
    raw_bytes = _json_bytes(raw)

    reports_by_node: dict[str, list[dict[str, Any]]] = {}
    for row in report_rows:
        reports_by_node.setdefault(cast(str, row["nodeid"]), []).append(row)
    outcomes: dict[str, list[str]] = {
        name: [] for name in ("failed", "error", "skipped", "xfailed", "xpassed", "not_run")
    }
    details: list[dict[str, Any]] = []
    phase_errors: list[dict[str, Any]] = []
    for nodeid in expected:
        reports = reports_by_node.get(nodeid, [])
        if not reports:
            raise AuditError(f"capture: eligible node has no phase report: {nodeid}")
        by_phase = {cast(str, row["phase"]): row for row in reports}
        if len(by_phase) != len(reports):
            raise AuditError(f"capture: duplicate phase report for {nodeid}")
        call = by_phase.get("call")
        setup = by_phase.get("setup")
        primary = call or setup
        if primary is None:
            raise AuditError(f"capture: node has no setup/call attribution: {nodeid}")
        wasxfail = primary.get("wasxfail")
        if call is not None:
            if call["outcome"] == "failed":
                outcome = "failed"
            elif call["outcome"] == "skipped":
                outcome = "xfailed" if wasxfail else "skipped"
            elif call["outcome"] == "passed":
                outcome = "xpassed" if wasxfail else "passed"
            else:
                raise AuditError(f"capture: unknown call outcome for {nodeid}")
        elif setup is not None and setup["outcome"] == "failed":
            outcome = "error"
        elif setup is not None and setup["outcome"] == "skipped":
            outcome = "xfailed" if wasxfail else "skipped"
        else:
            raise AuditError(f"capture: no terminal outcome for {nodeid}")
        if outcome != "passed":
            outcomes[outcome].append(nodeid)
            details.append({
                "nodeid": nodeid, "outcome": outcome, "phase": cast(str, primary["phase"]),
                "longrepr_sha256": _sha(cast(str, primary["longrepr"])),
            })
        for report in reports:
            if report["phase"] in {"setup", "teardown"} and report["outcome"] == "failed":
                phase_errors.append({
                    "nodeid": nodeid, "phase": report["phase"],
                    "longrepr_sha256": _sha(cast(str, report["longrepr"])),
                })
    outcomes["not_run"] = excluded
    details.extend({
        "nodeid": nodeid, "outcome": "not_run", "phase": "route_excluded",
        "reason": f"frozen selector ignore: {node_paths[nodeid]}",
    } for nodeid in excluded)
    non_pass = sum(len(items) for items in outcomes.values())
    counts = {name: len(items) for name, items in outcomes.items()}
    counts["passed"] = len(nodeids) - non_pass
    result: dict[str, Any] = {
        "schema_version": SCHEMA,
        "base_execution": {
            "inventory_commit": census["inventory"]["commit"],
            "census_sha256": _sha(census_path.read_bytes()),
            "ordered_nodeids_sha256": _sha(_json_bytes(nodeids)),
            "collected_node_count": len(nodeids),
            "route_id": route_id,
            "workload_argv": route["argv"],
            "cwd": route["cwd"],
            "env": route["env"],
            "environment_id": route["environment_id"],
            "harness_patch_hash": None,
            "started_at": raw["started_at"], "ended_at": raw["ended_at"],
            "wall_seconds": wall_seconds, "exit_code": exit_code,
            "raw_result_path": raw_output.as_posix(),
            "raw_result_sha256": _sha(raw_bytes),
            "default_outcome": "passed", "outcome_overrides": outcomes,
            "outcome_details": sorted(details, key=lambda row: str(row["nodeid"])),
            "phase_errors": sorted(phase_errors, key=lambda row: (str(row["nodeid"]), str(row["phase"]))),
            "counts": counts,
        },
    }
    result["content_sha256"] = _sha(_json_bytes(result))
    _atomic_write_bytes(raw_output, raw_bytes)
    return cast(dict[str, Any], _stable(result))


def collect_pytest(root: Path, tests_root: Path, extra_args: Sequence[str]) -> dict[str, Any]:
    plugin = CollectionPlugin(root, tests_root)
    argv = [str(tests_root), "--collect-only", "-q", "-p", "no:cacheprovider", *extra_args]
    old = Path.cwd()
    try:
        os.chdir(root)
        # Hook data is authoritative; pytest's human node listing is intentionally
        # excluded from compact evidence.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = int(pytest.main(argv, plugins=[plugin]))
    finally:
        os.chdir(old)
    return cast(dict[str, Any], _stable({
        "argv": ["pytest", *argv], "exit_code": code,
        "nodes": sorted(plugin.nodes, key=lambda row: row["nodeid"]),
        "deselected": sorted(set(plugin.deselected)),
        "deselected_items": sorted(plugin.deselected_items, key=lambda row: row["nodeid"]),
        "collection_errors": sorted(plugin.errors, key=lambda row: row["nodeid"]),
        "internal_errors": sorted(set(plugin.internal_errors)),
        "ignored_paths": sorted(plugin.ignored),
    }))


def load_owners(root: Path) -> dict[str, str]:
    tasks = root / "kitty-specs" / "assertive-test-suite-sanitation-01KZME3P" / "tasks"
    owners: dict[str, str] = {}
    collisions: list[str] = []
    for task in sorted(tasks.glob("WP*.md")):
        wp = task.name.split("-")[0]
        text = task.read_text(encoding="utf-8")
        match = re.search(r"(?m)^owned_files:\n(?P<body>(?:^- [^\n]+\n)+)", text)
        if not match:
            continue
        for line in match.group("body").splitlines():
            path = line[2:].strip().strip("`'")
            previous = owners.get(path)
            if (
                previous and previous != wp
                and WP08_OWNERSHIP_TAKEOVERS.get(path) != (previous, wp)
            ):
                collisions.append(f"{path}: {previous}, {wp}")
            owners[path] = wp
    if collisions:
        raise AuditError("owned-file collisions: " + "; ".join(collisions))
    return owners


def _group_manifest(units: Sequence[SourceUnit], field: str, owners: Mapping[str, str]) -> list[dict[str, Any]]:
    groups: dict[str, list[SourceUnit]] = {}
    for unit in units:
        groups.setdefault(str(getattr(unit, field)), []).append(unit)
    result = []
    for fingerprint, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        rows = []
        for unit in members:
            rows.append({"member": unit.id, "path": unit.path, "owner": owners.get(unit.path)})
        result.append({"fingerprint": fingerprint, "members": rows})
    return result


def _scanner_files(root: Path, owners: Mapping[str, str]) -> list[dict[str, Any]]:
    rows = []
    architectural = root / "tests" / "architectural"
    explicit_non_arch = {
        "tests/sync/test_no_queue_drain_constructed_3030.py",
        "tests/specify_cli/coordination/test_simple_case_flat_topology.py",
        "tests/specify_cli/write_side/test_characterization_write_target.py",
    }
    candidates = set(architectural.rglob("test*.py")) if architectural.exists() else set()
    candidates.update(root / path for path in explicit_non_arch if (root / path).exists())
    repo_ast_paths: set[Path] = set()
    # AST scanners are AST parse calls over file-loaded source, not every test
    # that parses an inline snippet. Discover that precise shape under every root.
    tests_root = root / "tests"
    for path in sorted(tests_root.rglob("test*.py")) if tests_root.exists() else []:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        file_loaded_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                value = node.value
                if isinstance(value, ast.Call) and _decorator_name(value.func).endswith((".read_text", ".read_bytes")):
                    file_loaded_names.update(target.id for target in targets if isinstance(target, ast.Name))
        repo_ast = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _decorator_name(node.func) != "ast.parse" or not node.args:
                continue
            argument = node.args[0]
            direct_read = isinstance(argument, ast.Call) and _decorator_name(argument.func).endswith((".read_text", ".read_bytes"))
            if direct_read or (isinstance(argument, ast.Name) and argument.id in file_loaded_names):
                repo_ast = True
                break
        if repo_ast:
            candidates.add(path)
            repo_ast_paths.add(path)
    for path in sorted(candidates):
        rel = _rel(path, root)
        text = path.read_text(encoding="utf-8", errors="replace")
        lowered = text.lower()
        kinds = ["structural"] if rel.startswith("tests/architectural/") or rel in explicit_non_arch else []
        if path in repo_ast_paths or ("structural" in kinds and ("ast.parse" in lowered or "ast.walk" in lowered)):
            kinds.append("ast")
        if any(token in lowered for token in ("src/specify_cli", "read_text(", "read_bytes(", "rglob(", "glob(")):
            kinds.append("source")
        if any(token in lowered for token in (" in source", "not in source", "count(", "re.search", "re.findall")):
            kinds.append("text")
        rows.append({"member": rel, "path": rel, "scanner_kinds": sorted(set(kinds)), "owner": owners.get(rel)})
    return rows


def _compact_collection(collection: Mapping[str, Any]) -> dict[str, Any]:
    nodes = cast(list[dict[str, Any]], collection["nodes"])
    paths = sorted({str(node["path"]) for node in nodes})
    functions = sorted({str(node["parent_source_function"]) for node in nodes})
    marker_sets = sorted({tuple(node["markers"]) for node in nodes})
    reasons = sorted({str(node["skip_or_xfail_reason"]) for node in nodes if node["skip_or_xfail_reason"] is not None})
    path_ref = {value: index for index, value in enumerate(paths)}
    function_ref = {value: index for index, value in enumerate(functions)}
    marker_ref = {value: index for index, value in enumerate(marker_sets)}
    reason_ref = {value: index for index, value in enumerate(reasons)}
    compact_nodes = []
    for node in nodes:
        reason = node["skip_or_xfail_reason"]
        compact_nodes.append([
            node["nodeid"], path_ref[node["path"]], node["line"], function_ref[node["parent_source_function"]],
            marker_ref[tuple(node["markers"])], node["quarantined"], None if reason is None else reason_ref[str(reason)],
        ])
    return {
        "argv": collection["argv"], "exit_code": collection["exit_code"],
        "node_fields": ["nodeid", "path_ref", "line", "parent_source_function_ref", "marker_set_ref", "quarantined", "reason_ref"],
        "tables": {"paths": paths, "parent_source_functions": functions, "marker_sets": [list(row) for row in marker_sets], "reasons": reasons},
        "nodes": compact_nodes,
        "deselected": collection["deselected"], "deselected_items": collection["deselected_items"],
        "collection_errors": collection["collection_errors"], "internal_errors": collection["internal_errors"],
        "ignored_paths": collection["ignored_paths"],
    }


def _reconcile(units: Sequence[SourceUnit], collection: Mapping[str, Any], config: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    nodes = collection["nodes"]
    errors = collection["collection_errors"]
    deselected_items = cast(list[dict[str, Any]], collection.get("deselected_items", []))
    deselected_keys = {(str(row["path"]), str(row["parent_source_function"])) for row in deselected_items}
    ignored_cfg = [str(item) for item in config.get("collect_ignore", [])]
    ignored_glob = [str(item) for item in config.get("collect_ignore_glob", [])]
    ignored_observed = [str(item) for item in collection.get("ignored_paths", [])]
    rows: list[dict[str, Any]] = []
    member_counts = {str(node["nodeid"]): 0 for node in nodes}
    nodes_by_source: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for node in nodes:
        key = (str(node["path"]), str(node["parent_source_function"]))
        nodes_by_source.setdefault(key, []).append(node)
    for unit in units:
        matched = nodes_by_source.get((unit.path, unit.qualname), [])
        for node in matched:
            member_counts[str(node["nodeid"])] += 1
        path_error = any(unit.path == row["nodeid"] or unit.path.startswith(f"{row['nodeid']}/") for row in errors)
        ignored = (
            unit.path in ignored_cfg
            or any(unit.path == path or unit.path.startswith(f"{path}/") for path in ignored_observed)
            or any(fnmatch.fnmatch(unit.path, pat) for pat in ignored_glob)
        )
        matched_deselected = (unit.path, unit.qualname) in deselected_keys
        if matched:
            state = "collected"
        elif matched_deselected:
            state = "deselected"
        elif path_error:
            state = "error"
        elif ignored:
            state = "ignored"
        else:
            state = "zero_node"
        rows.append({**dataclasses.asdict(unit), "collection_state": state, "nodeids": sorted(node["nodeid"] for node in matched), "zero_node": not matched})
    bad_nodes = sorted(nodeid for nodeid, count in member_counts.items() if count != 1)
    counts = {state: sum(row["collection_state"] == state for row in rows) for state in sorted(COLLECTION_STATES)}
    return rows, {
        "source_units": len(units), "collected_nodes": len(nodes), "state_counts": counts,
        "unreconciled_or_duplicate_nodes": bad_nodes,
        "complete": (
            not bad_nodes and len(rows) == len(units)
            and int(collection["exit_code"]) in {0, 5}
            and not collection.get("internal_errors")
            and not collection.get("collection_errors")
        ),
    }


def snapshot(
    root: Path, tests_path: str, extra_args: Sequence[str], inventory_sha: str | None,
    census_role: str = "base",
) -> dict[str, Any]:
    root = root.resolve()
    if census_role not in CENSUS_ROLES:
        raise AuditError(f"unknown census role {census_role!r}")
    if census_role == "head":
        commit = _git_rev_parse(f"{inventory_sha or 'HEAD'}^{{commit}}", root=root)
        frozen_candidates = _frozen_candidate_members(root)
        inventory: dict[str, Any] = {
            "role": "head", "commit": commit, "target_commit": commit,
            "tests_tree": _git_rev_parse(f"{commit}:{tests_path}", root=root),
        }
    else:
        frozen_candidates = set()
        inventory = {
            "role": "base", "commit": inventory_sha or "WORKTREE",
            "target_commit": TARGET_INVENTORY_SHA,
        }
    tests_root = (root / tests_path).resolve()
    units, parse_errors = discover_source(root, tests_root)
    test_files = sorted(_rel(path, root) for path in tests_root.rglob("*.py")) if tests_root.exists() else []
    unit_paths = {unit.path for unit in units}
    config = discover_config(root)
    collection = collect_pytest(root, tests_root, extra_args) if tests_root.exists() else {
        "argv": ["pytest", tests_path, "--collect-only", "-q", "-p", "no:cacheprovider"],
        "exit_code": 5, "nodes": [], "deselected": [], "deselected_items": [],
        "collection_errors": [], "internal_errors": [], "ignored_paths": [],
    }
    rows, reconciliation = _reconcile(units, collection, config)
    owners = load_owners(root) if (root / "kitty-specs" / "assertive-test-suite-sanitation-01KZME3P" / "tasks").exists() else {}
    exact = _group_manifest(units, "exact_body_sha256", owners)
    collection_nodes = cast(list[dict[str, Any]], collection["nodes"])
    nodes_by_id = {node["nodeid"]: node for node in collection_nodes}
    inert = []
    for row in rows:
        reasons = set(row["inert_reasons"])
        if not reasons:
            continue
        for nodeid in row["nodeids"]:
            for marker in nodes_by_id[nodeid]["markers"]:
                if marker in {"skip", "skipif", "xfail", "quarantine", "flaky"}:
                    reasons.add(f"effective_marker:{marker}")
        inert.append({"member": row["id"], "path": row["path"], "reasons": sorted(reasons), "owner": owners.get(row["path"])})
    scanners = _scanner_files(root, owners)
    manifests = {
        "inert_candidates": inert,
        "exact_body_groups": exact,
        "promoted_semantic_groups": [],
        "structural_shape_index": {
            "group_count": len({unit.structural_shape_sha256 for unit in units}),
            "sha256": _sha("\n".join(sorted(unit.structural_shape_sha256 for unit in units))),
        },
        "scanner_candidates": scanners,
    }
    unowned: list[str] = []
    post_base_additions: list[str] = []
    for row in inert + scanners:
        if not row["owner"]:
            target = unowned if census_role == "base" or row["member"] in frozen_candidates else post_base_additions
            target.append(row["member"])
    for group in exact:
        for row in group["members"]:
            if not row["owner"]:
                target = unowned if census_role == "base" or row["member"] in frozen_candidates else post_base_additions
                target.append(row["member"])
    node_ref = {node["nodeid"]: index for index, node in enumerate(collection_nodes)}
    compact_rows = []
    for row in rows:
        compact = dict(row)
        compact["node_refs"] = [node_ref[nodeid] for nodeid in compact.pop("nodeids")]
        compact_rows.append(compact)
    evidence = {
        "schema_version": SCHEMA,
        "inventory": inventory,
        "tool": {
            "python": platform.python_implementation() + " " + platform.python_version(),
            "pytest": pytest.__version__, "pyyaml": importlib.metadata.version("PyYAML"),
            "normalization": ["JSON mapping-key ordering", "explicit set-like field sorting only", "absolute temporary roots -> <TEMP_ROOT>"],
        },
        "config": config, "source_parse_errors": parse_errors,
        "test_files": test_files,
        "zero_function_files": sorted(path for path in test_files if path not in unit_paths),
        "source_units": compact_rows, "collection": _compact_collection(collection),
        "reconciliation": reconciliation, "manifests": manifests,
        "ownership": {
            "unowned": sorted(set(unowned)),
            "post_base_additions": sorted(set(post_base_additions)),
            "complete": not unowned,
        },
        "empty_tests_root": not test_files,
    }
    evidence["content_sha256"] = _sha(_json_bytes(evidence))
    return cast(dict[str, Any], _stable(evidence))


def _keys(row: Mapping[str, Any], fields: Iterable[str], where: str, errors: list[str]) -> None:
    for field in fields:
        if field not in row:
            errors.append(f"{where}: missing field {field}")


def _str_list(value: Any, *, nonempty: bool = False) -> bool:
    return isinstance(value, list) and (not nonempty or bool(value)) and all(isinstance(item, str) for item in value)


def _hash_value(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _enum_string(value: Any, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _nonnegative_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def validate_environment(env: Mapping[str, Any], where: str, errors: list[str]) -> None:
    required = (
        "id", "os", "runner_image", "cpu_class", "python", "event", "env", "lock_hash",
        "install_command", "install_state", "workers", "cache_policy", "harness_patch_hash",
    )
    _keys(env, required, where, errors)
    scalar_fields = ("id", "os", "runner_image", "cpu_class", "python", "event", "lock_hash", "install_state", "workers", "cache_policy")
    if any(not _nonempty_string(env.get(field)) for field in scalar_fields):
        errors.append(f"{where}: scalar environment fields must be nonempty strings")
    env_map = env.get("env")
    if not isinstance(env_map, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in env_map.items()):
        errors.append(f"{where}: env must be string mapping")
    if not _str_list(env.get("install_command"), nonempty=True):
        errors.append(f"{where}: install_command must be nonempty string list")
    if not _enum_string(env.get("event"), {"local", "PR", "push", "schedule", "manual"}):
        errors.append(f"{where}: invalid event")
    if not _hash_value(env.get("lock_hash")):
        errors.append(f"{where}: lock_hash must be SHA-256")
    harness_hash = env.get("harness_patch_hash")
    if harness_hash is not None and not _hash_value(harness_hash):
        errors.append(f"{where}: harness_patch_hash must be SHA-256 or null")
    body = {key: env.get(key) for key in required if key != "id"}
    if env.get("id") != _sha(_json_bytes(body)):
        errors.append(f"{where}: id is not SHA-256 of normalized environment fields")


def _canonical_set_list(value: Any) -> bool:
    return _str_list(value) and value == sorted(set(value))


def _route_projection(route: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "id", "memberships", "argv", "cwd", "env", "environment_id",
        "base_mapping", "head_mapping", "wrapper",
    )
    return {field: route[field] for field in fields if field in route}


def _selector_from_argv(argv: Sequence[str], environment_id: str) -> dict[str, Any]:
    try:
        pytest_index = argv.index("pytest")
    except ValueError:
        pytest_index = 0
    args = list(argv[pytest_index + 1:])
    paths: list[str] = []
    markers: list[str] = []
    ignores: list[str] = []
    consumes_value = {"-m", "-p", "-k", "--tb", "--dist", "-n", "--durations"}
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "-m" and index + 1 < len(args):
            markers.append(args[index + 1])
            index += 2
            continue
        if arg == "--ignore" and index + 1 < len(args):
            ignores.append(args[index + 1])
            index += 2
            continue
        if arg.startswith("--ignore="):
            ignores.append(arg.split("=", 1)[1])
            index += 1
            continue
        if arg in consumes_value:
            index += 2
            continue
        if arg.startswith("-"):
            index += 1
            continue
        paths.append(arg)
        index += 1
    return {
        "paths": sorted(set(paths)), "markers": sorted(set(markers)),
        "ignores": sorted(set(ignores)), "environment_id": environment_id,
    }


def _git_blob(commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"], check=False, capture_output=True,
    )
    if completed.returncode != 0:
        raise AuditError(f"cannot read tracked authority {commit}:{path}")
    return completed.stdout


def _tracked_ci_step(
    provenance: Mapping[str, Any], where: str, errors: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    fields = (
        "kind", "source_commit", "source_path", "source_sha256", "job_id",
        "step_name", "step_sha256", "authority_sha256",
    )
    _keys(provenance, fields, where, errors)
    if provenance.get("source_commit") != TARGET_INVENTORY_SHA:
        errors.append(f"{where}: CI source_commit must equal immutable inventory SHA")
    source_path = provenance.get("source_path")
    if source_path != ".github/workflows/ci-quality.yml":
        errors.append(f"{where}: unexpected tracked workflow source_path")
        return None
    try:
        source = _git_blob(TARGET_INVENTORY_SHA, cast(str, source_path))
    except AuditError as exc:
        errors.append(f"{where}: {exc}")
        return None
    if provenance.get("source_sha256") != _sha(source):
        errors.append(f"{where}: tracked workflow source_sha256 mismatch")
    try:
        document = yaml.safe_load(source)
        job = cast(dict[str, Any], document["jobs"][provenance["job_id"]])
        steps = [step for step in job["steps"] if step.get("name") == provenance["step_name"]]
    except (KeyError, TypeError):
        errors.append(f"{where}: tracked job/step locator not found")
        return None
    if len(steps) != 1:
        errors.append(f"{where}: tracked step locator must be unique")
        return None
    step = cast(dict[str, Any], steps[0])
    if provenance.get("step_sha256") != _sha(_json_bytes(step)):
        errors.append(f"{where}: tracked step_sha256 mismatch")
    return cast(dict[str, Any], document), job, step


def _validate_ci_provenance(
    route: Mapping[str, Any], provenance: Mapping[str, Any], where: str, errors: list[str],
) -> None:
    authority = _tracked_ci_step(provenance, where, errors)
    if authority is None:
        return
    document, job, step = authority
    argv = cast(list[str], route.get("argv", []))
    run_lines = [
        shlex.split(line.strip()) for line in str(step.get("run", "")).splitlines()
        if line.strip() and not line.strip().startswith(("#", "if ", "echo ", "set ", "fi", "exit "))
    ]
    if sum(tokens == argv for tokens in run_lines) != 1:
        errors.append(f"{where}: route argv is not the unique tracked pytest command")
    workflow_env = document.get("env", {}) if isinstance(document, dict) else {}
    job_env = job.get("env", {})
    step_env = step.get("env", {})
    expected_env = {
        str(key): str(value) for mapping in (workflow_env, job_env, step_env)
        if isinstance(mapping, dict) for key, value in mapping.items()
    }
    if route.get("env") != expected_env:
        errors.append(f"{where}: route env does not match tracked workflow/job/step env")
    workflow_defaults = document.get("defaults", {}) if isinstance(document, dict) else {}
    job_defaults = job.get("defaults", {})
    expected_cwd = step.get("working-directory")
    for defaults in (job_defaults, workflow_defaults):
        if expected_cwd is None and isinstance(defaults, dict):
            run_defaults = defaults.get("run", {})
            if isinstance(run_defaults, dict):
                expected_cwd = run_defaults.get("working-directory")
    if route.get("cwd") != (expected_cwd or "."):
        errors.append(f"{where}: route cwd does not match tracked workflow step")
    job_if = str(job.get("if", ""))
    event_map = {
        "pull_request": "PR", "workflow_dispatch": "manual",
        "push": "push", "schedule": "schedule",
    }
    expected_events = sorted(value for key, value in event_map.items() if f"'{key}'" in job_if)
    quality_needs = cast(list[str], document["jobs"]["quality-gate"]["needs"])
    expected_required = provenance.get("job_id") in quality_needs
    memberships = route.get("memberships", [])
    if isinstance(memberships, list):
        for index, membership in enumerate(memberships):
            if not isinstance(membership, dict):
                continue
            if membership.get("events") != expected_events:
                errors.append(f"{where}: memberships[{index}] events do not match tracked job triggers")
            if membership.get("required") is not expected_required:
                errors.append(f"{where}: memberships[{index}] required does not match quality-gate.needs")
            if membership.get("selector") != _selector_from_argv(argv, cast(str, route.get("environment_id", ""))):
                errors.append(f"{where}: memberships[{index}] selector does not match tracked argv")
    if expected_required and step.get("continue-on-error") is True:
        errors.append(f"{where}: required tracked step cannot continue-on-error")


def validate_route(
    route: Mapping[str, Any], where: str, errors: list[str],
    route_authority: Mapping[str, Mapping[str, Any]],
) -> None:
    _keys(route, ("route_id", "role", "required", "events", "selector"), where, errors)
    if not _enum_string(route.get("role"), ROUTE_ROLES):
        errors.append(f"{where}: invalid route role")
    if not isinstance(route.get("required"), bool):
        errors.append(f"{where}: required must be boolean")
    route_id = route.get("route_id")
    selector = route.get("selector")
    if not _nonempty_string(route_id) or not _str_list(route.get("events")) or not isinstance(selector, dict):
        errors.append(f"{where}: route_id must be nonempty string, events string list, and selector mapping")
        return
    route_id_string = cast(str, route_id)
    authority = route_authority.get(route_id_string)
    if authority is None:
        errors.append(f"{where}: unknown frozen route_id {route_id_string}")
    selector_fields = ("paths", "markers", "ignores", "environment_id")
    _keys(selector, selector_fields, f"{where}.selector", errors)
    if any(not _str_list(selector.get(field)) for field in ("paths", "markers", "ignores")):
        errors.append(f"{where}.selector: paths, markers, and ignores must be string lists")
    selector_environment = selector.get("environment_id")
    if not _nonempty_string(selector_environment):
        errors.append(f"{where}.selector: environment_id must be nonempty string")
    elif authority is not None and selector_environment != authority.get("environment_id"):
        errors.append(f"{where}.selector: environment_id does not match frozen route")
    if authority is not None:
        frozen_memberships = authority.get("memberships")
        visible = {field: route.get(field) for field in ("role", "required", "events", "selector")}
        if not isinstance(frozen_memberships, list) or visible not in frozen_memberships:
            errors.append(f"{where}: membership fields do not match frozen route authority")


def _validate_result_field(row: Mapping[str, Any], where: str, errors: list[str]) -> None:
    _keys(row, ("result",), where, errors)
    if not _nonempty_string(row.get("result")):
        errors.append(f"{where}: result must be nonempty string")


def _validate_command_evidence(row: Mapping[str, Any], where: str, errors: list[str]) -> None:
    _keys(row, ("command", "result"), where, errors)
    command = row.get("command")
    if not (_nonempty_string(command) or _str_list(command, nonempty=True)):
        errors.append(f"{where}: command must be nonempty string or argv list")
    _validate_result_field(row, where, errors)


def _validate_authority_evidence(row: Mapping[str, Any], where: str, errors: list[str]) -> None:
    _keys(row, ("reference", "result"), where, errors)
    if not _nonempty_string(row.get("reference")):
        errors.append(f"{where}: reference must be nonempty string")
    _validate_result_field(row, where, errors)


def _validate_overlap_evidence(row: Mapping[str, Any], where: str, errors: list[str]) -> None:
    _keys(row, ("left", "right", "result"), where, errors)
    if not _nonempty_string(row.get("left")) or not _nonempty_string(row.get("right")):
        errors.append(f"{where}: left/right identities must be nonempty strings")
    _validate_result_field(row, where, errors)


def _validate_named_result_mapping(value: Any, where: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{where}: mapping required")
        return
    _keys(value, ("identity", "result"), where, errors)
    if not _nonempty_string(value.get("identity")):
        errors.append(f"{where}: identity must be nonempty string")
    _validate_result_field(value, where, errors)


def validate_causal_probe(probe: Any, where: str, errors: list[str]) -> None:
    if not isinstance(probe, dict):
        errors.append(f"{where}: causal_probe must be mapping")
        return
    fields = (
        "kind", "fault", "authority_violated", "act_reached", "intended_oracle",
        "intended_oracle_failed", "command", "environment", "raw_artifact_hash",
    )
    _keys(probe, fields, where, errors)
    if any(not _nonempty_string(probe.get(field)) for field in ("kind", "fault", "authority_violated", "intended_oracle", "command", "environment")):
        errors.append(f"{where}: causal text fields must be nonempty strings")
    if not _hash_value(probe.get("raw_artifact_hash")):
        errors.append(f"{where}: raw_artifact_hash must be SHA-256")
    if probe.get("act_reached") is not True or probe.get("intended_oracle_failed") is not True:
        errors.append(f"{where}: causal proof must reach Act and fail intended oracle")


def validate_workload(  # noqa: C901 - schema branches are intentionally explicit
    dag: Mapping[str, Any], where: str, errors: list[str], environment_ids: set[str],
    *, frozen_route_authorities: Mapping[str, str] = FROZEN_ROUTE_AUTHORITY_HASHES,
) -> None:
    _keys(dag, ("routes", "edges", "repetitions", "measurements"), where, errors)
    routes = dag.get("routes", [])
    edges = dag.get("edges", [])
    if not isinstance(routes, list) or not isinstance(edges, list) or not isinstance(dag.get("measurements"), list):
        errors.append(f"{where}: routes, edges, and measurements must be lists")
        return
    if not isinstance(dag.get("repetitions"), int) or dag.get("repetitions", 0) < 3:
        errors.append(f"{where}: repetitions must be >= 3")
    route_ids: set[str] = set()
    route_environments: dict[str, str] = {}
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            errors.append(f"{where}.routes[{index}]: mapping required")
            continue
        route_where = f"{where}.routes[{index}]"
        _keys(
            route,
            (
                "id", "memberships", "argv", "environment_id", "base_mapping",
                "head_mapping", "cwd", "env", "provenance",
            ),
            route_where, errors,
        )
        route_id = route.get("id")
        if not _nonempty_string(route_id):
            errors.append(f"{route_where}: id must be nonempty string")
            continue
        route_id_string = cast(str, route_id)
        if route_id_string in route_ids:
            errors.append(f"{route_where}: duplicate route id {route_id_string}")
        route_ids.add(route_id_string)
        if route_id_string not in frozen_route_authorities:
            errors.append(
                f"{route_where}: unknown frozen route id {route_id_string}; "
                "future HEAD routes require separately pinned tracked authority"
            )
        if not _str_list(route.get("argv"), nonempty=True):
            errors.append(f"{route_where}: argv must be nonempty string list")
        route_env = route.get("env")
        if (
            not _nonempty_string(route.get("cwd"))
            or not isinstance(route_env, dict)
            or not all(isinstance(k, str) and isinstance(v, str) for k, v in route_env.items())
        ):
            errors.append(f"{route_where}: nonempty cwd/string env mapping required")
        route_environment = route.get("environment_id")
        if not isinstance(route_environment, str) or route_environment not in environment_ids:
            errors.append(f"{route_where}: unknown environment_id")
        elif isinstance(route_environment, str):
            route_environments[route_id_string] = route_environment
        if not _nonempty_string(route.get("base_mapping")) or not _nonempty_string(route.get("head_mapping")):
            errors.append(f"{route_where}: base/head mappings must be nonempty strings")
        memberships = route.get("memberships")
        if not isinstance(memberships, list) or not memberships:
            errors.append(f"{route_where}: nonempty memberships list required")
        else:
            seen_memberships: set[str] = set()
            for membership_index, membership in enumerate(memberships):
                membership_where = f"{route_where}.memberships[{membership_index}]"
                if not isinstance(membership, dict):
                    errors.append(f"{membership_where}: mapping required")
                    continue
                _keys(membership, ("role", "required", "events", "selector"), membership_where, errors)
                if not _enum_string(membership.get("role"), ROUTE_ROLES):
                    errors.append(f"{membership_where}: invalid route role")
                if not isinstance(membership.get("required"), bool):
                    errors.append(f"{membership_where}: required must be boolean")
                if not _canonical_set_list(membership.get("events")):
                    errors.append(f"{membership_where}: events must be canonical unique sorted strings")
                member_selector = membership.get("selector")
                if not isinstance(member_selector, dict):
                    errors.append(f"{membership_where}: selector mapping required")
                else:
                    _keys(member_selector, ("paths", "markers", "ignores", "environment_id"), membership_where, errors)
                    if any(not _canonical_set_list(member_selector.get(field)) for field in ("paths", "markers", "ignores")):
                        errors.append(f"{membership_where}: selector lists must be canonical unique sorted strings")
                    if member_selector.get("environment_id") != route_environment:
                        errors.append(f"{membership_where}: selector environment_id does not match route")
                fingerprint = repr(_stable(membership))
                if fingerprint in seen_memberships:
                    errors.append(f"{membership_where}: duplicate frozen membership")
                seen_memberships.add(fingerprint)
        provenance = route.get("provenance")
        if not isinstance(provenance, dict):
            errors.append(f"{route_where}: provenance mapping required")
        else:
            _keys(provenance, ("kind", "source_commit", "authority_sha256"), f"{route_where}.provenance", errors)
            expected_authority = _sha(_json_bytes(_route_projection(route)))
            if provenance.get("authority_sha256") != expected_authority:
                errors.append(f"{route_where}.provenance: authority_sha256 does not bind complete route")
            pinned_authority = frozen_route_authorities.get(route_id_string)
            if pinned_authority is not None and provenance.get("authority_sha256") != pinned_authority:
                errors.append(f"{route_where}.provenance: authority_sha256 does not match pinned frozen route")
            if provenance.get("kind") == "tracked_ci":
                _validate_ci_provenance(route, provenance, f"{route_where}.provenance", errors)
            elif provenance.get("kind") == "frozen_command":
                repository = provenance.get("repository")
                expected_commit = TARGET_INVENTORY_SHA if repository == "primary" else SIBLING_E2E_SHA
                if repository not in {"primary", "sibling-e2e"} or provenance.get("source_commit") != expected_commit:
                    errors.append(f"{route_where}.provenance: invalid frozen command repository/commit")
                if route.get("id") == "sibling-e2e" and repository != "sibling-e2e":
                    errors.append(f"{route_where}.provenance: sibling route requires sibling authority")
                if route.get("id") != "sibling-e2e" and repository != "primary":
                    errors.append(f"{route_where}.provenance: local route requires primary authority")
                if isinstance(memberships, list):
                    expected_selector = _selector_from_argv(
                        cast(list[str], route.get("argv", [])), cast(str, route.get("environment_id", "")),
                    )
                    for membership_index, membership in enumerate(memberships):
                        if isinstance(membership, dict) and membership.get("selector") != expected_selector:
                            errors.append(
                                f"{route_where}.memberships[{membership_index}]: selector does not match frozen argv"
                            )
            else:
                errors.append(f"{route_where}.provenance: unknown provenance kind")
    expected_route_ids = set(frozen_route_authorities)
    if route_ids != expected_route_ids:
        errors.append(
            f"{where}: route id universe does not match immutable authority; "
            f"missing={sorted(expected_route_ids - route_ids)!r} unknown={sorted(route_ids - expected_route_ids)!r}"
        )
    graph: dict[Any, set[Any]] = {route_id: set() for route_id in route_ids}
    edge_ids: set[tuple[str, str]] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict) or set(edge) < {"from", "to"}:
            errors.append(f"{where}.edges[{index}]: from/to required")
            continue
        edge_from, edge_to = edge.get("from"), edge.get("to")
        if not isinstance(edge_from, str) or not isinstance(edge_to, str):
            errors.append(f"{where}.edges[{index}]: from/to strings required")
            continue
        if edge_from not in route_ids or edge_to not in route_ids:
            errors.append(f"{where}.edges[{index}]: unknown route")
        edge_id = (edge_from, edge_to)
        if edge_id in edge_ids:
            errors.append(f"{where}.edges[{index}]: duplicate dependency edge {edge_from}->{edge_to}")
        edge_ids.add(edge_id)
        graph.setdefault(edge_from, set()).add(edge_to)
    visiting: set[Any] = set()
    visited: set[Any] = set()
    def visit(node: Any) -> bool:
        if node in visiting:
            return False
        if node in visited:
            return True
        visiting.add(node)
        if not all(visit(child) for child in graph.get(node, set())):
            return False
        visiting.remove(node)
        visited.add(node)
        return True
    if not all(visit(node) for node in route_ids):
        errors.append(f"{where}: dependency graph is cyclic")
    for index, measurement in enumerate(dag.get("measurements", [])):
        if not isinstance(measurement, dict):
            errors.append(f"{where}.measurements[{index}]: mapping required")
            continue
        measurement_where = f"{where}.measurements[{index}]"
        fields = ("route_id", "environment_id", "collection", "setup", "call", "wall", "compute", "outcome", "artifact_hash")
        _keys(measurement, fields, measurement_where, errors)
        measurement_route = measurement.get("route_id")
        measurement_environment = measurement.get("environment_id")
        if not _nonempty_string(measurement_route) or measurement_route not in route_ids:
            errors.append(f"{measurement_where}: unknown route_id")
        if not _nonempty_string(measurement_environment) or measurement_environment not in environment_ids:
            errors.append(f"{measurement_where}: unknown environment_id")
        if (
            isinstance(measurement_route, str)
            and isinstance(measurement_environment, str)
            and route_environments.get(measurement_route) != measurement_environment
        ):
            errors.append(f"{measurement_where}: environment_id does not match route")
        if any(not _nonnegative_number(measurement.get(field)) for field in ("collection", "setup", "call", "wall", "compute")):
            errors.append(f"{measurement_where}: timing fields must be finite nonnegative numbers")
        if not _enum_string(measurement.get("outcome"), MEASUREMENT_OUTCOMES):
            errors.append(f"{measurement_where}: invalid outcome")
        if not _hash_value(measurement.get("artifact_hash")):
            errors.append(f"{measurement_where}: artifact_hash must be SHA-256")


def validate_census(data: Mapping[str, Any], errors: list[str]) -> None:  # noqa: C901 - fail-closed compact schema matrix
    if data.get("schema_version") != SCHEMA:
        errors.append("census: schema_version must be test-sanitation/v1")
    reconciliation = data.get("reconciliation", {})
    if not isinstance(reconciliation, dict):
        errors.append("census: reconciliation mapping required")
        return
    if not reconciliation.get("complete"):
        errors.append("census: discovery/collection reconciliation incomplete")
    if reconciliation.get("unreconciled_or_duplicate_nodes"):
        errors.append("census: node membership is missing or duplicated")
    ownership = data.get("ownership", {})
    if not isinstance(ownership, dict):
        errors.append("census: ownership mapping required")
        ownership = {}
    unowned = ownership.get("unowned")
    post_base_additions = ownership.get("post_base_additions", [])
    if not _str_list(unowned) or not _str_list(post_base_additions):
        errors.append("census: ownership partitions must be string lists")
        unowned = []
        post_base_additions = []
    if ownership.get("complete") is not (unowned == []):
        errors.append("census: candidate/group owner reconciliation incomplete")
    if set(cast(list[str], unowned)) & set(cast(list[str], post_base_additions)):
        errors.append("census: ownership partitions overlap")
    inventory = data.get("inventory", {})
    if not isinstance(inventory, dict):
        errors.append("census: inventory mapping required")
    else:
        role = inventory.get("role", "base")
        if role not in CENSUS_ROLES:
            errors.append("census: role must be base or head")
        elif role == "base":
            if (
                inventory.get("commit") != TARGET_INVENTORY_SHA
                or inventory.get("target_commit") != TARGET_INVENTORY_SHA
            ):
                errors.append("census: immutable base inventory and target commits must match target SHA")
            if post_base_additions:
                errors.append("census: base inventory cannot contain post-base additions")
        else:
            commit = inventory.get("commit")
            target_commit = inventory.get("target_commit")
            tests_tree = inventory.get("tests_tree")
            if not (
                isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit)
                and target_commit == commit
                and isinstance(tests_tree, str) and re.fullmatch(r"[0-9a-f]{40}", tests_tree)
            ):
                errors.append("census: HEAD role requires identical commit/target_commit and tests_tree authorities")
            else:
                try:
                    recorded_tree = _git_rev_parse(f"{commit}:tests")
                    current_tree = _git_rev_parse("HEAD:tests")
                except AuditError as exc:
                    errors.append(f"census: {exc}")
                else:
                    if recorded_tree != tests_tree:
                        errors.append("census: HEAD tests_tree does not match recorded commit")
                    if current_tree != tests_tree:
                        errors.append("census: current tests tree drifted from recorded HEAD census")
            try:
                frozen_candidates = _frozen_candidate_members(Path.cwd())
            except AuditError as exc:
                errors.append(f"census: {exc}")
            else:
                for member in cast(list[str], post_base_additions):
                    if member in frozen_candidates:
                        errors.append(f"census: frozen-base member misclassified as post-base addition: {member}")
    if data.get("source_parse_errors"):
        errors.append("census: source parse errors require explicit repair before inventory")
    units = data.get("source_units", [])
    collection = data.get("collection", {})
    if not isinstance(units, list) or not isinstance(collection, dict):
        errors.append("census: source_units list and collection mapping required")
        return
    test_files = data.get("test_files")
    zero_function_files = data.get("zero_function_files")
    if not _str_list(test_files) or not _str_list(zero_function_files):
        errors.append("census: test_files and zero_function_files must be string lists")
    elif not set(cast(list[str], zero_function_files)) <= set(cast(list[str], test_files)):
        errors.append("census: zero_function_files must reference test_files")
    elif data.get("empty_tests_root") is not (test_files == []):
        errors.append("census: empty_tests_root inconsistent with discovered files")
    if collection.get("exit_code") not in {0, 5} or collection.get("internal_errors") or collection.get("collection_errors"):
        errors.append("census: collection exited nonzero or recorded collection/internal errors")
    states = [row.get("collection_state") for row in units if isinstance(row, dict)]
    if not all(_enum_string(state, COLLECTION_STATES) for state in states):
        errors.append("census: invalid collection_state")
    if len(units) != reconciliation.get("source_units"):
        errors.append("census: source unit count mismatch")
    actual_states = {state: sum(isinstance(row, dict) and row.get("collection_state") == state for row in units) for state in sorted(COLLECTION_STATES)}
    if actual_states != reconciliation.get("state_counts"):
        errors.append("census: state counts do not match source rows")
    tables = collection.get("tables", {})
    nodes = collection.get("nodes", [])
    expected_fields = ["nodeid", "path_ref", "line", "parent_source_function_ref", "marker_set_ref", "quarantined", "reason_ref"]
    if collection.get("node_fields") != expected_fields or not isinstance(tables, dict) or not isinstance(nodes, list):
        errors.append("census: invalid compact collection schema")
        nodes = []
        tables = {}
    paths = tables.get("paths", []) if isinstance(tables, dict) else []
    functions = tables.get("parent_source_functions", []) if isinstance(tables, dict) else []
    marker_sets = tables.get("marker_sets", []) if isinstance(tables, dict) else []
    reasons = tables.get("reasons", []) if isinstance(tables, dict) else []
    nodeids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, list) or len(node) != len(expected_fields):
            errors.append(f"census: node[{index}] row width/type invalid")
            continue
        nodeid, path_ref, line, function_ref, marker_ref, quarantined, reason_ref = node
        if not isinstance(nodeid, str) or nodeid in nodeids:
            errors.append(f"census: node[{index}] nodeid missing/duplicate")
        nodeids.add(nodeid)
        refs_valid = (
            isinstance(path_ref, int) and 0 <= path_ref < len(paths)
            and isinstance(function_ref, int) and 0 <= function_ref < len(functions)
            and isinstance(marker_ref, int) and 0 <= marker_ref < len(marker_sets)
            and (reason_ref is None or isinstance(reason_ref, int) and 0 <= reason_ref < len(reasons))
        )
        if not refs_valid or not isinstance(line, int) or not isinstance(quarantined, bool):
            errors.append(f"census: node[{index}] invalid compact reference/type")
    if len(nodes) != reconciliation.get("collected_nodes"):
        errors.append("census: collected node count mismatch")
    membership = [0] * len(nodes)
    source_ids: set[str] = set()
    for index, row in enumerate(units):
        if not isinstance(row, dict):
            errors.append(f"census: source_units[{index}] mapping required")
            continue
        source_id = row.get("id")
        if not isinstance(source_id, str) or source_id in source_ids:
            errors.append(f"census: source_units[{index}] id missing/duplicate")
        if isinstance(source_id, str):
            source_ids.add(source_id)
        if (
            not isinstance(row.get("path"), str)
            or not isinstance(row.get("qualname"), str)
            or not isinstance(row.get("line"), int)
            or not _str_list(row.get("decorators"))
            or not _str_list(row.get("inert_reasons"))
            or not _hash_value(row.get("exact_body_sha256"))
            or not _hash_value(row.get("structural_shape_sha256"))
            or not isinstance(row.get("zero_node"), bool)
        ):
            errors.append(f"census: source_units[{index}] typed fields invalid")
        refs = row.get("node_refs")
        if not isinstance(refs, list):
            errors.append(f"census: source_units[{index}] node_refs list required")
            continue
        if row.get("collection_state") == "collected" and not refs:
            errors.append(f"census: collected source_units[{index}] has no nodes")
        if row.get("collection_state") != "collected" and refs:
            errors.append(f"census: non-collected source_units[{index}] has node refs")
        for ref in refs:
            if not isinstance(ref, int) or not 0 <= ref < len(nodes):
                errors.append(f"census: source_units[{index}] invalid node ref")
            else:
                membership[ref] += 1
    if any(count != 1 for count in membership):
        errors.append("census: every collection node must have exactly one source membership")
    ownership = data.get("ownership", {})
    if not isinstance(ownership, dict) or not isinstance(ownership.get("unowned"), list):
        errors.append("census: ownership mapping/unowned list required")
    elif ownership.get("complete") is not (ownership["unowned"] == []):
        errors.append("census: ownership.complete inconsistent with unowned list")
    expected = data.get("content_sha256")
    body = dict(data)
    body.pop("content_sha256", None)
    if expected != _sha(_json_bytes(body)):
        errors.append("census: content_sha256 mismatch")


def validate_base_execution(  # noqa: C901 - compact exact-outcome matrix is intentionally explicit
    data: Mapping[str, Any], where: str, errors: list[str], census_nodeids: Sequence[str],
    census_hashes: set[str], route_authority: Mapping[str, Mapping[str, Any]],
    environment_ids: set[str],
) -> None:
    execution = data.get("base_execution")
    if not isinstance(execution, dict):
        errors.append(f"{where}: base_execution mapping required")
        return
    fields = (
        "inventory_commit", "census_sha256", "ordered_nodeids_sha256", "collected_node_count",
        "route_id", "workload_argv", "cwd", "env", "environment_id", "harness_patch_hash",
        "started_at", "ended_at", "wall_seconds", "exit_code", "raw_result_path",
        "raw_result_sha256", "default_outcome", "outcome_overrides", "outcome_details",
        "phase_errors", "counts",
    )
    _keys(execution, fields, where, errors)
    if execution.get("inventory_commit") != TARGET_INVENTORY_SHA:
        errors.append(f"{where}: inventory_commit mismatch")
    if execution.get("census_sha256") != FROZEN_BASE_CENSUS_FILE_SHA256:
        errors.append(f"{where}: census_sha256 does not match immutable base census authority")
    if execution.get("census_sha256") not in census_hashes:
        errors.append(f"{where}: census_sha256 does not identify a validated census")
    if execution.get("ordered_nodeids_sha256") != _sha(_json_bytes(list(census_nodeids))):
        errors.append(f"{where}: ordered nodeid identity hash mismatch")
    if execution.get("collected_node_count") != len(census_nodeids):
        errors.append(f"{where}: collected node count mismatch")
    route_id = execution.get("route_id")
    route = route_authority.get(route_id) if isinstance(route_id, str) else None
    if route is None:
        errors.append(f"{where}: unknown frozen route_id")
    else:
        for evidence_field, route_field in (
            ("workload_argv", "argv"), ("cwd", "cwd"), ("env", "env"),
            ("environment_id", "environment_id"),
        ):
            if execution.get(evidence_field) != route.get(route_field):
                errors.append(f"{where}: {evidence_field} does not match frozen route")
    if execution.get("environment_id") not in environment_ids:
        errors.append(f"{where}: unknown environment_id")
    if execution.get("harness_patch_hash") is not None and not _hash_value(execution.get("harness_patch_hash")):
        errors.append(f"{where}: harness_patch_hash must be SHA-256 or null")
    parsed_timestamps: list[dt.datetime] = []
    for timestamp in ("started_at", "ended_at"):
        try:
            parsed_timestamps.append(dt.datetime.fromisoformat(str(execution.get(timestamp)).replace("Z", "+00:00")))
        except ValueError:
            errors.append(f"{where}: {timestamp} must be ISO-8601")
    if len(parsed_timestamps) == 2 and parsed_timestamps[1] < parsed_timestamps[0]:
        errors.append(f"{where}: ended_at precedes started_at")
    if len(parsed_timestamps) == 2 and _nonnegative_number(execution.get("wall_seconds")):
        elapsed = (parsed_timestamps[1] - parsed_timestamps[0]).total_seconds()
        if abs(elapsed - cast(float, execution["wall_seconds"])) > 1.0:
            errors.append(f"{where}: timestamp interval does not reconcile wall_seconds")
    if not _nonnegative_number(execution.get("wall_seconds")) or not isinstance(execution.get("exit_code"), int):
        errors.append(f"{where}: wall_seconds/exit_code invalid")
    if not _nonempty_string(execution.get("raw_result_path")) or not _hash_value(execution.get("raw_result_sha256")):
        errors.append(f"{where}: raw result path and SHA-256 required")
    if execution.get("raw_result_path") != FROZEN_BASE_RAW_RESULT_REFERENCE:
        errors.append(f"{where}: raw result reference does not match immutable capture authority")
    if execution.get("raw_result_sha256") != FROZEN_BASE_RAW_RESULT_SHA256:
        errors.append(f"{where}: raw result SHA-256 does not match immutable capture authority")
    if execution.get("default_outcome") != "passed":
        errors.append(f"{where}: default_outcome must be passed")
    overrides = execution.get("outcome_overrides")
    outcome_names = {"failed", "error", "skipped", "xfailed", "xpassed", "not_run"}
    census_set = set(census_nodeids)
    override_nodes: dict[str, str] = {}
    if not isinstance(overrides, dict) or set(overrides) != outcome_names:
        errors.append(f"{where}: exact outcome_overrides classes required")
        overrides = {}
    for outcome in sorted(outcome_names):
        nodes = overrides.get(outcome, []) if isinstance(overrides, dict) else []
        if not _canonical_set_list(nodes):
            errors.append(f"{where}: {outcome} nodeids must be canonical unique sorted strings")
            continue
        for nodeid in cast(list[str], nodes):
            if nodeid not in census_set:
                errors.append(f"{where}: unknown outcome nodeid {nodeid}")
            if nodeid in override_nodes:
                errors.append(f"{where}: duplicate outcome nodeid {nodeid}")
            override_nodes[nodeid] = outcome
    counts = execution.get("counts")
    expected_counts = {
        outcome: len(overrides.get(outcome, [])) if isinstance(overrides, dict) else 0
        for outcome in outcome_names
    }
    expected_counts["passed"] = len(census_nodeids) - len(override_nodes)
    if counts != expected_counts or sum(expected_counts.values()) != len(census_nodeids):
        errors.append(f"{where}: outcome counts do not reconcile every census node")
    details = execution.get("outcome_details")
    detail_nodes: dict[str, str] = {}
    detail_phases: dict[str, str] = {}
    if not isinstance(details, list):
        errors.append(f"{where}: outcome_details list required")
        details = []
    for index, detail in enumerate(details):
        if not isinstance(detail, dict):
            errors.append(f"{where}.outcome_details[{index}]: mapping required")
            continue
        detail_nodeid, detail_outcome = detail.get("nodeid"), detail.get("outcome")
        if not isinstance(detail_nodeid, str) or not isinstance(detail_outcome, str) or override_nodes.get(detail_nodeid) != detail_outcome:
            errors.append(f"{where}.outcome_details[{index}]: identity/outcome not in exact overrides")
            continue
        if detail_nodeid in detail_nodes:
            errors.append(f"{where}.outcome_details[{index}]: duplicate detail nodeid")
        detail_nodes[detail_nodeid] = detail_outcome
        if isinstance(detail.get("phase"), str):
            detail_phases[detail_nodeid] = detail["phase"]
        if detail_outcome == "not_run":
            if detail.get("phase") != "route_excluded" or not _nonempty_string(detail.get("reason")):
                errors.append(f"{where}.outcome_details[{index}]: not_run attribution required")
        elif not _enum_string(detail.get("phase"), {"setup", "call"}) or not _hash_value(detail.get("longrepr_sha256")):
            errors.append(f"{where}.outcome_details[{index}]: phase and longrepr SHA required")
    if set(detail_nodes) != set(override_nodes):
        errors.append(f"{where}: every non-pass node requires exactly one attribution detail")
    phase_errors = execution.get("phase_errors")
    if not isinstance(phase_errors, list):
        errors.append(f"{where}: phase_errors list required")
        phase_errors = []
    phase_error_keys: set[tuple[str, str]] = set()
    for index, phase_error in enumerate(phase_errors):
        if not isinstance(phase_error, dict):
            errors.append(f"{where}.phase_errors[{index}]: mapping required")
            continue
        if (
            phase_error.get("nodeid") not in census_set
            or not _enum_string(phase_error.get("phase"), {"setup", "teardown"})
            or not _hash_value(phase_error.get("longrepr_sha256"))
        ):
            errors.append(f"{where}.phase_errors[{index}]: exact node/phase/hash attribution required")
            continue
        phase_error_key = (cast(str, phase_error["nodeid"]), cast(str, phase_error["phase"]))
        if phase_error_key in phase_error_keys:
            errors.append(f"{where}.phase_errors[{index}]: duplicate node/phase record")
        phase_error_keys.add(phase_error_key)
        if phase_error["phase"] == "setup" and (
            override_nodes.get(cast(str, phase_error["nodeid"])) != "error"
            or detail_phases.get(cast(str, phase_error["nodeid"])) != "setup"
        ):
            errors.append(f"{where}.phase_errors[{index}]: setup error must reconcile exact error outcome")
    failure_count = expected_counts.get("failed", 0) + expected_counts.get("error", 0) + len(phase_errors)
    if execution.get("exit_code") == 0 and failure_count:
        errors.append(f"{where}: zero exit_code contradicts failed/error phase outcomes")
    elif execution.get("exit_code") == 1 and not failure_count:
        errors.append(f"{where}: nonzero exit_code lacks failed/error phase outcome")
    elif execution.get("exit_code") not in {0, 1}:
        errors.append(f"{where}: exact base execution exit_code must be 0 or 1")
    body = dict(data)
    expected_hash = body.pop("content_sha256", None)
    if not _hash_value(expected_hash) or expected_hash != _sha(_json_bytes(body)):
        errors.append(f"{where}: content_sha256 mismatch")
    if expected_hash != FROZEN_BASE_EXECUTION_CONTENT_SHA256:
        errors.append(f"{where}: content_sha256 does not match immutable base execution authority")


def _validate_temporary(row: Mapping[str, Any], where: str, profile: Any, today: dt.date, errors: list[str]) -> None:
    _keys(row, ("hic_approval", "issue", "owner", "expires"), where, errors)
    if profile != "environmental_platform":
        errors.append(f"{where}: TEMPORARY only permits environmental_platform")
    for field in ("hic_approval", "issue", "owner", "expires"):
        if not _nonempty_string(row.get(field)):
            errors.append(f"{where}: TEMPORARY {field} must be nonempty string")
    renewal = row.get("renewal", False)
    if not isinstance(renewal, bool):
        errors.append(f"{where}: TEMPORARY renewal must be boolean")
    elif renewal:
        errors.append(f"{where}: TEMPORARY cannot renew")
    expires = row.get("expires")
    if not isinstance(expires, str):
        return
    try:
        expiry = dt.date.fromisoformat(expires)
        if expiry < today or expiry > today + dt.timedelta(days=30):
            errors.append(f"{where}: TEMPORARY expiry must be today..today+30d")
    except ValueError:
        errors.append(f"{where}: invalid TEMPORARY expiry")


def _validate_evidence(  # noqa: C901 - each EvidenceBundle field has a distinct nested schema
    evidence: Mapping[str, Any], where: str, errors: list[str],
    route_authority: Mapping[str, Mapping[str, Any]], candidate_route_roles: Mapping[str, str],
) -> Any:
    _keys(evidence, ("profile",), where, errors)
    profile = evidence.get("profile")
    if not _enum_string(profile, PROFILES):
        errors.append(f"{where}: invalid evidence profile {profile!r}")
    list_fields = ("caller_evidence", "authority_evidence", "routing_evidence", "overlap_evidence")
    for field in list_fields:
        value = evidence.get(field)
        if field in evidence and (
            not isinstance(value, list) or not all(isinstance(item, dict) for item in value)
        ):
            errors.append(f"{where}.{field}: list of mapping evidence rows required")
    for field in ("base_evidence", "cost_evidence"):
        if field in evidence:
            _validate_named_result_mapping(evidence.get(field), f"{where}.{field}", errors)
    if "causal_probe" in evidence and not isinstance(evidence.get("causal_probe"), dict):
        errors.append(f"{where}.causal_probe: mapping required")
    requirements = {
        "inert": ("routing_evidence", "authority_evidence"),
        "duplicate": ("overlap_evidence", "causal_probe"),
        "structural": ("authority_evidence", "causal_probe"),
        "contract": ("caller_evidence", "authority_evidence", "causal_probe"),
        "slow": ("cost_evidence", "causal_probe"),
        "flake": ("base_evidence",),
        "dead_symbol": ("caller_evidence", "authority_evidence"),
        "route": ("routing_evidence", "cost_evidence"),
        "environmental_platform": ("base_evidence", "routing_evidence"),
    }
    required_fields = requirements.get(profile, ()) if isinstance(profile, str) else ()
    for field in required_fields:
        value = evidence.get(field)
        if field not in evidence or value in (None, [], {}):
            errors.append(f"{where}[{profile}]: nonempty {field} required")
    validators = {
        "caller_evidence": _validate_command_evidence,
        "authority_evidence": _validate_authority_evidence,
        "overlap_evidence": _validate_overlap_evidence,
    }
    for field, validator in validators.items():
        rows = evidence.get(field)
        if not isinstance(rows, list):
            continue
        for row_index, nested_row in enumerate(rows):
            if isinstance(nested_row, dict):
                validator(nested_row, f"{where}.{field}[{row_index}]", errors)
    routing_rows = evidence.get("routing_evidence")
    if isinstance(routing_rows, list):
        for row_index, nested_row in enumerate(routing_rows):
            if not isinstance(nested_row, dict):
                continue
            row_where = f"{where}.routing_evidence[{row_index}]"
            validate_route(nested_row, row_where, errors, route_authority)
            _validate_result_field(nested_row, row_where, errors)
            route_id = nested_row.get("route_id")
            role = nested_row.get("role")
            if isinstance(route_id, str) and route_id not in candidate_route_roles:
                errors.append(f"{row_where}: route_id is not a candidate RouteMembership")
            elif isinstance(route_id, str) and role != candidate_route_roles.get(route_id):
                errors.append(f"{row_where}: role does not match candidate RouteMembership")
    if "causal_probe" in evidence:
        validate_causal_probe(evidence.get("causal_probe"), f"{where}.causal_probe", errors)
    return profile


def _validate_family(  # noqa: C901 - family anti-vacuity matrix is intentionally explicit
    candidate: Mapping[str, Any], members: list[str], observations: list[Any], where: str,
    census_members: set[str], errors: list[str],
) -> None:
    dimensions_value = candidate.get("equivalence")
    if not isinstance(dimensions_value, dict):
        errors.append(f"{where}: family equivalence dimensions mapping required")
        dimensions: Mapping[str, Any] = {}
    else:
        dimensions = dimensions_value
    missing_dimensions = EQUIVALENCE_DIMENSIONS - set(dimensions)
    if missing_dimensions:
        errors.append(f"{where}: family equivalence dimensions missing {sorted(missing_dimensions)}")
    for dimension in EQUIVALENCE_DIMENSIONS:
        if dimension in dimensions and not _nonempty_string(dimensions.get(dimension)):
            errors.append(f"{where}: equivalence.{dimension} must be nonempty string")

    divergent_value = candidate.get("divergent_dimensions", [])
    if not _str_list(divergent_value):
        errors.append(f"{where}: divergent_dimensions must be string list")
        divergent: list[str] = []
    else:
        divergent = cast(list[str], divergent_value)
        if len(divergent) != len(set(divergent)):
            errors.append(f"{where}: divergent_dimensions must be unique")
        unknown = set(divergent) - EQUIVALENCE_DIMENSIONS
        if unknown:
            errors.append(f"{where}: unknown divergent dimensions {sorted(unknown)}")

    observation_rows = [obs for obs in observations if isinstance(obs, dict)]
    observed_dimensions: set[str] = set()
    if len({repr(obs.get("outcome")) for obs in observation_rows}) > 1:
        observed_dimensions.add("outcome")
    if len({
        repr(obs.get("duration", {}).get("cost_class"))
        for obs in observation_rows if isinstance(obs.get("duration"), dict)
    }) > 1:
        observed_dimensions.add("cost_class")
    if not observed_dimensions <= set(divergent):
        errors.append(f"{where}: observed divergent dimensions must be declared")

    node_rows_value = candidate.get("node_rows")
    has_divergence = bool(divergent or observed_dimensions)
    if node_rows_value is None:
        if has_divergence:
            errors.append(f"{where}: divergent family dimensions require nonempty node_rows")
        return
    if not isinstance(node_rows_value, list):
        errors.append(f"{where}: node_rows must be list")
        return
    if has_divergence and not node_rows_value:
        errors.append(f"{where}: divergent family dimensions require nonempty node_rows")
        return

    row_members: list[str] = []
    row_dimensions: dict[str, list[str]] = {dimension: [] for dimension in EQUIVALENCE_DIMENSIONS}
    for row_index, node_row in enumerate(node_rows_value):
        row_where = f"{where}.node_rows[{row_index}]"
        if not isinstance(node_row, dict):
            errors.append(f"{row_where}: mapping required")
            continue
        _keys(node_row, ("member", *sorted(EQUIVALENCE_DIMENSIONS)), row_where, errors)
        member = node_row.get("member")
        if not _nonempty_string(member):
            errors.append(f"{row_where}: member must be nonempty string")
        else:
            member_string = cast(str, member)
            row_members.append(member_string)
            if member_string not in members or member_string not in census_members:
                errors.append(f"{row_where}: member must reference candidate and census identity")
        for dimension in EQUIVALENCE_DIMENSIONS:
            value = node_row.get(dimension)
            if not _nonempty_string(value):
                errors.append(f"{row_where}: {dimension} must be nonempty string")
            else:
                row_dimensions[dimension].append(cast(str, value))
    if len(row_members) != len(set(row_members)):
        errors.append(f"{where}: node_rows contain duplicate member identities")
    if set(row_members) != set(members) or len(row_members) != len(members):
        errors.append(f"{where}: node_rows must cover every candidate member exactly once")
    for dimension, values in row_dimensions.items():
        if len(values) != len(members):
            continue
        if dimension in divergent:
            if len(set(values)) < 2:
                errors.append(f"{where}: divergent dimension {dimension} must vary across node_rows")
        elif dimension in dimensions and any(value != dimensions[dimension] for value in values):
            errors.append(f"{where}: node_rows disagree with equivalence.{dimension}")


def validate_disposition(  # noqa: C901 - fail-closed schema matrix
    row: Mapping[str, Any], index: int, today: dt.date, errors: list[str],
    census_members: set[str], environment_ids: set[str], census_nodes: set[str],
    census_member_nodes: Mapping[str, set[str]], census_member_states: Mapping[str, str],
    route_authority: Mapping[str, Mapping[str, Any]],
) -> None:
    where = f"dispositions[{index}]"
    _keys(row, ("candidate", "evidence", "verdict", "state", "action", "survivor", "issue", "owner", "expires", "hic_approval", "review"), where, errors)
    verdict, state = row.get("verdict"), row.get("state")
    if not _enum_string(verdict, VERDICTS):
        errors.append(f"{where}: unknown verdict {verdict!r}")
    if state == "terminal" and isinstance(verdict, str) and verdict in {"FIX_TEST", "FIX_PRODUCT"}:
        errors.append(f"{where}: FIX_* cannot be terminal")
    if not _enum_string(state, {"pending", "terminal"}):
        errors.append(f"{where}: state must be pending or terminal")
    if not _nonempty_string(row.get("action")):
        errors.append(f"{where}: action must be nonempty string")
    if row.get("survivor") is not None and not isinstance(row.get("survivor"), str):
        errors.append(f"{where}: survivor must be string or null")
    for field in ("issue", "owner", "expires", "hic_approval"):
        if row.get(field) is not None and not isinstance(row.get(field), str):
            errors.append(f"{where}: {field} must be string or null")
    candidate_value = row.get("candidate", {})
    evidence_value = row.get("evidence", {})
    if not isinstance(candidate_value, dict):
        errors.append(f"{where}.candidate: mapping required")
        candidate: Mapping[str, Any] = {}
    else:
        candidate = candidate_value
    if not isinstance(evidence_value, dict):
        errors.append(f"{where}.evidence: mapping required")
        evidence: Mapping[str, Any] = {}
    else:
        evidence = evidence_value
    candidate_fields = (
        "id", "members", "granularity", "source_paths", "production_paths", "oracle", "contract_claim",
        "authority", "duplicate_group", "route_memberships", "platforms", "observations",
    )
    _keys(candidate, candidate_fields, f"{where}.candidate", errors)
    if not _nonempty_string(candidate.get("id")):
        errors.append(f"{where}: candidate id must be nonempty string")
    members_value = candidate.get("members")
    if not _str_list(members_value, nonempty=True):
        errors.append(f"{where}: members must be nonempty string list")
        candidate_members: list[str] = []
    else:
        candidate_members = cast(list[str], members_value)
    for member in candidate_members:
        if member not in census_members:
            errors.append(f"{where}: stale/unknown census member {member}")
    for field in ("source_paths", "production_paths", "authority", "platforms"):
        value = candidate.get(field)
        if field in candidate and not _str_list(value, nonempty=field in {"source_paths", "platforms"}):
            errors.append(f"{where}: {field} must be string list")
    for field in ("oracle", "contract_claim", "duplicate_group"):
        if candidate.get(field) is not None and not isinstance(candidate.get(field), str):
            errors.append(f"{where}: {field} must be string or null")
    if not _enum_string(candidate.get("granularity"), GRANULARITIES):
        errors.append(f"{where}: invalid granularity")
    memberships = candidate.get("route_memberships", [])
    if not isinstance(memberships, list):
        errors.append(f"{where}.route_memberships: list required")
        memberships = []
    candidate_route_roles: dict[str, str] = {}
    for route_index, route in enumerate(memberships):
        if isinstance(route, dict):
            validate_route(route, f"{where}.routes[{route_index}]", errors, route_authority)
            route_id = route.get("route_id")
            role = route.get("role")
            if isinstance(route_id, str) and isinstance(role, str):
                if route_id in candidate_route_roles:
                    errors.append(f"{where}.routes[{route_index}]: duplicate candidate route_id {route_id}")
                else:
                    candidate_route_roles[route_id] = role
        else:
            errors.append(f"{where}.routes[{route_index}]: mapping required")
    if sum(isinstance(item, dict) and item.get("role") == "owner" for item in memberships) != 1:
        errors.append(f"{where}: exactly one owner route required")
    profile = _validate_evidence(
        evidence, f"{where}.evidence", errors, route_authority, candidate_route_roles,
    )
    allowed_candidate_nodes: set[str] = set()
    for member in candidate_members:
        allowed_candidate_nodes.update(census_member_nodes.get(member, set()))
    observations = candidate.get("observations", [])
    if not isinstance(observations, list):
        errors.append(f"{where}.observations: list required")
        observations = []
    elif not observations:
        errors.append(f"{where}.observations: at least one observation required")
    for obs_index, obs in enumerate(observations):
        if not isinstance(obs, dict):
            errors.append(f"{where}.observations[{obs_index}]: mapping required")
            continue
        collection_state = obs.get("collection_state")
        outcome = obs.get("outcome")
        if not _enum_string(collection_state, COLLECTION_STATES) or not (
            outcome is None or _enum_string(outcome, cast(set[str], OUTCOMES - {None}))
        ):
            errors.append(f"{where}.observations[{obs_index}]: invalid state/outcome")
        observation_fields = (
            "environment_id", "nodeid", "collection_state", "outcome", "skip_reason",
            "markers", "duration", "artifact_hash",
        )
        _keys(obs, observation_fields, f"{where}.observations[{obs_index}]", errors)
        if not isinstance(obs.get("environment_id"), str) or obs.get("environment_id") not in environment_ids:
            errors.append(f"{where}.observations[{obs_index}]: unknown environment_id")
        if obs.get("nodeid") is not None and not isinstance(obs.get("nodeid"), str):
            errors.append(f"{where}.observations[{obs_index}]: nodeid must be string/null")
        observation_nodeid = obs.get("nodeid")
        if isinstance(observation_nodeid, str):
            if observation_nodeid not in census_nodes:
                errors.append(f"{where}.observations[{obs_index}]: nodeid absent from census")
            if observation_nodeid not in allowed_candidate_nodes:
                errors.append(f"{where}.observations[{obs_index}]: nodeid does not belong to candidate members")
            if not _enum_string(collection_state, {"collected", "deselected"}):
                errors.append(f"{where}.observations[{obs_index}]: non-null nodeid requires collected/deselected state")
        elif observation_nodeid is None:
            if not _enum_string(collection_state, {"zero_node", "ignored", "error"}):
                errors.append(f"{where}.observations[{obs_index}]: nodeid null only for source-only states")
            elif not any(census_member_states.get(member) == collection_state for member in candidate_members):
                errors.append(f"{where}.observations[{obs_index}]: null node state does not match candidate source state")
        if obs.get("skip_reason") is not None and not isinstance(obs.get("skip_reason"), str):
            errors.append(f"{where}.observations[{obs_index}]: skip_reason must be string/null")
        if not _str_list(obs.get("markers")) or not _hash_value(obs.get("artifact_hash")):
            errors.append(f"{where}.observations[{obs_index}]: markers/string list and SHA artifact required")
        duration = obs.get("duration")
        if not isinstance(duration, dict) or not {"collection", "setup", "call", "cost_class"} <= set(duration):
            errors.append(f"{where}.observations[{obs_index}]: typed duration fields required")
        elif any(not _nonnegative_number(duration.get(phase)) for phase in ("collection", "setup", "call")) or not _nonempty_string(duration.get("cost_class")):
            errors.append(f"{where}.observations[{obs_index}]: invalid duration values")
        markers = obs.get("markers")
        skip_like = isinstance(outcome, str) and outcome in {"skipped", "xfailed"}
        quarantined = isinstance(markers, list) and "quarantine" in markers
        if (skip_like or quarantined) and not obs.get("skip_reason"):
            errors.append(f"{where}.observations[{obs_index}]: skip_reason required")
    if verdict == "KEEP":
        if not _str_list(candidate.get("production_paths"), nonempty=True):
            errors.append(f"{where}.KEEP: nonempty production_paths required")
        if not _str_list(candidate.get("authority"), nonempty=True):
            errors.append(f"{where}.KEEP: nonempty authority required")
        if not _nonempty_string(candidate.get("oracle")) or not _nonempty_string(candidate.get("contract_claim")):
            errors.append(f"{where}.KEEP: nonempty oracle and contract_claim required")
        validate_causal_probe(evidence.get("causal_probe"), f"{where}.KEEP.causal_probe", errors)
    if verdict == "CONSOLIDATE" and state == "terminal":
        survivor = row.get("survivor")
        if not _nonempty_string(survivor):
            errors.append(f"{where}: terminal consolidation requires nonempty survivor")
        elif cast(str, survivor) not in candidate_members:
            errors.append(f"{where}: survivor must reference candidate member")
        if len(candidate_members) < 2:
            errors.append(f"{where}: terminal consolidation needs deleted and surviving members")
    if verdict == "TEMPORARY":
        _validate_temporary(row, where, profile, today, errors)
    review = row.get("review", {})
    if isinstance(review, dict):
        review_fields = ("implementer", "independent_reviewer", "verdict", "timestamp")
        _keys(review, review_fields, f"{where}.review", errors)
        if any(not _nonempty_string(review.get(field)) for field in review_fields):
            errors.append(f"{where}.review: fields must be nonempty strings")
        try:
            dt.datetime.fromisoformat(str(review.get("timestamp")).replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{where}.review: invalid timestamp")
    else:
        errors.append(f"{where}.review: mapping required")
    if isinstance(candidate.get("granularity"), str) and candidate.get("granularity") in {"family", "duplicate_cluster"}:
        _validate_family(candidate, candidate_members, observations, where, census_members, errors)


def _collect_census_authority(  # noqa: C901 - compact collected/deselected authority has distinct forms
    data: Mapping[str, Any], census_members: set[str], census_nodes: set[str],
    member_nodes: dict[str, set[str]], member_states: dict[str, str],
) -> None:
    collection = data.get("collection", {})
    if not isinstance(collection, dict):
        return
    compact_nodes = collection.get("nodes", [])
    if not isinstance(compact_nodes, list):
        compact_nodes = []
    nodeids_by_ref: list[str | None] = []
    for compact_row in compact_nodes:
        nodeid = compact_row[0] if isinstance(compact_row, list) and compact_row and isinstance(compact_row[0], str) else None
        nodeids_by_ref.append(nodeid)
        if nodeid is not None:
            census_nodes.add(nodeid)
            census_members.add(nodeid)
            member_nodes[nodeid] = {nodeid}
            member_states[nodeid] = "collected"
    deselected_by_source: dict[tuple[str, str], set[str]] = {}
    deselected_items = collection.get("deselected_items", [])
    if isinstance(deselected_items, list):
        for item in deselected_items:
            if not isinstance(item, dict):
                continue
            nodeid, path, source = item.get("nodeid"), item.get("path"), item.get("parent_source_function")
            if not all(isinstance(value, str) for value in (nodeid, path, source)):
                continue
            nodeid_string = cast(str, nodeid)
            census_nodes.add(nodeid_string)
            census_members.add(nodeid_string)
            member_nodes[nodeid_string] = {nodeid_string}
            member_states[nodeid_string] = "deselected"
            deselected_by_source.setdefault((cast(str, path), cast(str, source)), set()).add(nodeid_string)
    units = data.get("source_units", [])
    if not isinstance(units, list):
        return
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("id"), str):
            continue
        member = cast(str, unit["id"])
        census_members.add(member)
        resolved: set[str] = set()
        refs = unit.get("node_refs", [])
        if isinstance(refs, list):
            for ref in refs:
                if isinstance(ref, int) and 0 <= ref < len(nodeids_by_ref) and nodeids_by_ref[ref] is not None:
                    resolved.add(cast(str, nodeids_by_ref[ref]))
        path, qualname = unit.get("path"), unit.get("qualname")
        if isinstance(path, str) and isinstance(qualname, str):
            resolved.update(deselected_by_source.get((path, qualname), set()))
        member_nodes[member] = resolved
        state = unit.get("collection_state")
        if isinstance(state, str):
            member_states[member] = state


def _collect_route_authority(
    data: Mapping[str, Any], path: Path, route_authority: dict[str, Mapping[str, Any]],
    route_locations: dict[str, str], errors: list[str],
) -> None:
    workload = data.get("frozen_workload_dag")
    if not isinstance(workload, dict) or not isinstance(workload.get("routes"), list):
        return
    for route_index, route in enumerate(workload["routes"]):
        if not isinstance(route, dict) or not isinstance(route.get("id"), str):
            continue
        route_id = cast(str, route["id"])
        location = f"{path}.frozen_workload_dag.routes[{route_index}]"
        if route_id in route_locations:
            errors.append(f"{location}: duplicate global frozen route id {route_id}; first at {route_locations[route_id]}")
            continue
        route_locations[route_id] = location
        route_authority[route_id] = route


def _document_key(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _normalization_source(
    documents: Sequence[tuple[Path, dict[str, Any]]], key: str,
) -> dict[str, Any] | None:
    return next((data for path, data in documents if _document_key(path) == key), None)


def _normalization_pointer(data: Any, pointer: str) -> Any:
    value = data
    for part in pointer.split("."):
        if not isinstance(value, dict) or part not in value:
            raise AuditError(f"normalization pointer not found: {pointer}")
        value = value[part]
    return value


def _replace_scalar(value: Any, old: str, new: str) -> tuple[Any, int]:
    if value == old:
        return new, 1
    if isinstance(value, list):
        replaced: list[Any] = []
        count = 0
        for item in value:
            normalized, item_count = _replace_scalar(item, old, new)
            replaced.append(normalized)
            count += item_count
        return replaced, count
    if isinstance(value, dict):
        replaced_mapping: dict[str, Any] = {}
        count = 0
        for key, item in value.items():
            normalized, item_count = _replace_scalar(item, old, new)
            replaced_mapping[key] = normalized
            count += item_count
        return replaced_mapping, count
    return value, 0


def _base_observation_index(
    documents: Sequence[tuple[Path, dict[str, Any]]],
) -> tuple[dict[str, dict[str, Any]], str, dict[str, Any], str]:
    census_entry = next(
        (
            (path, data) for path, data in documents
            if "source_units" in data
            and isinstance(data.get("inventory"), dict)
            and cast(dict[str, Any], data["inventory"]).get("role", "base") == "base"
        ),
        None,
    )
    workload = next((data for _, data in documents if isinstance(data.get("frozen_workload_dag"), dict)), None)
    execution_entry = next((entry for entry in documents if "base_execution" in entry[1]), None)
    if census_entry is None or workload is None or execution_entry is None:
        raise AuditError("normalization requires base census, workload, and exact base execution documents")
    census_path, census = census_entry
    collection = cast(dict[str, Any], census["collection"])
    tables = cast(dict[str, Any], collection["tables"])
    marker_sets = cast(list[list[str]], tables["marker_sets"])
    reasons = cast(list[str], tables["reasons"])
    index: dict[str, dict[str, Any]] = {}
    execution = cast(dict[str, Any], execution_entry[1]["base_execution"])
    default_outcome = cast(str, execution["default_outcome"])
    overrides = cast(dict[str, list[str]], execution["outcome_overrides"])
    outcomes = {
        nodeid: outcome
        for outcome, nodeids in overrides.items()
        for nodeid in nodeids
    }
    for compact in cast(list[list[Any]], collection["nodes"]):
        nodeid = cast(str, compact[0])
        reason_ref = compact[6]
        index[nodeid] = {
            "markers": marker_sets[cast(int, compact[4])],
            "skip_reason": reasons[reason_ref] if isinstance(reason_ref, int) else None,
            "outcome": outcomes.get(nodeid, default_outcome),
        }
    routes = cast(dict[str, Any], workload["frozen_workload_dag"])["routes"]
    full_parallel = next(route for route in routes if route.get("id") == "full-parallel")
    route_membership = dict(cast(list[dict[str, Any]], full_parallel["memberships"])[0])
    route_membership["route_id"] = "full-parallel"
    return index, _sha(census_path.read_bytes()), route_membership, _sha(execution_entry[0].read_bytes())


def _normalized_observation(
    member: str, node_index: Mapping[str, Mapping[str, Any]], route: Mapping[str, Any],
    artifact_hash: str,
) -> dict[str, Any]:
    observed = node_index.get(member)
    if observed is None:
        raise AuditError(f"normalization member absent from base census: {member}")
    selector = cast(dict[str, Any], route["selector"])
    outcome = observed["outcome"]
    return {
        "environment_id": selector["environment_id"], "nodeid": member,
        "collection_state": "collected", "outcome": outcome,
        "skip_reason": observed["skip_reason"], "markers": observed["markers"],
        "duration": {"collection": 0.0, "setup": 0.0, "call": 0.0, "cost_class": "unknown"},
        "artifact_hash": artifact_hash,
    }


def _wp08_review(source: str) -> dict[str, str]:
    return {
        "implementer": "implementer-ivan/WP08",
        "independent_reviewer": "reviewer-renata/pending",
        "verdict": f"root-arbiter-normalization:{source}",
        "timestamp": "2026-08-11T00:00:00Z",
    }


def _validate_normalization_authority(  # noqa: C901 - content authorities have distinct validation branches
    record_path: Path, record: Mapping[str, Any],
    documents: Sequence[tuple[Path, dict[str, Any]]], errors: list[str],
) -> None:
    if record.get("schema_version") != NORMALIZATION_SCHEMA:
        errors.append(f"{record_path}: invalid normalization schema")
    body = dict(record)
    expected = body.pop("content_sha256", None)
    if not _hash_value(expected) or expected != _sha(_json_bytes(body)):
        errors.append(f"{record_path}: normalization content_sha256 mismatch")
    if record.get("mission") != "assertive-test-suite-sanitation-01KZME3P" or record.get("work_package") != "WP08":
        errors.append(f"{record_path}: normalization mission/WP authority mismatch")
    authority = record.get("authority")
    if not isinstance(authority, dict) or authority.get("no_fourth_cycle") is not True or authority.get("review_cycle_cap") != 3:
        errors.append(f"{record_path}: normalization must record the three-cycle arbiter cap")
    document_map = {_document_key(path): path for path, _ in documents}
    for section in ("source_documents", "raw_artifacts", "integration_surfaces"):
        rows = record.get(section)
        if not isinstance(rows, list) or not rows:
            errors.append(f"{record_path}: nonempty {section} required")
            continue
        for index, row in enumerate(rows):
            where = f"{record_path}.{section}[{index}]"
            if not isinstance(row, dict) or not _nonempty_string(row.get("path")) or not _hash_value(row.get("sha256")):
                errors.append(f"{where}: path and sha256 required")
                continue
            source_path = Path(cast(str, row["path"]))
            if source_path.is_absolute() or ".." in source_path.parts:
                errors.append(f"{where}: repository-relative non-traversing path required")
                continue
            if section == "source_documents" and source_path.as_posix() not in document_map:
                errors.append(f"{where}: normalized source document was not supplied")
                continue
            resolved = document_map.get(source_path.as_posix(), source_path)
            if not resolved.is_file() or _sha(resolved.read_bytes()) != row["sha256"]:
                errors.append(f"{where}: content-addressed source drift")
    historical = record.get("historical_blobs")
    if not isinstance(historical, list) or not historical:
        errors.append(f"{record_path}: historical_blobs required")
    else:
        for index, row in enumerate(historical):
            where = f"{record_path}.historical_blobs[{index}]"
            if not isinstance(row, dict) or any(not _nonempty_string(row.get(field)) for field in ("commit", "path", "git_blob", "sha256")):
                errors.append(f"{where}: commit/path/git_blob/sha256 required")
                continue
            try:
                blob_id = _git_rev_parse(f"{row['commit']}:{row['path']}")
                blob = _git_blob(cast(str, row["commit"]), cast(str, row["path"]))
            except AuditError as exc:
                errors.append(f"{where}: {exc}")
                continue
            if blob_id != row["git_blob"] or _sha(blob) != row["sha256"]:
                errors.append(f"{where}: historical git blob authority drift")


def _drop_normalized_candidates(
    source: dict[str, Any], operation: Mapping[str, Any], errors: list[str],
) -> None:
    ids = operation.get("candidate_ids")
    rows = source.get("dispositions")
    if not isinstance(ids, list) or not _str_list(ids, nonempty=True) or not isinstance(rows, list):
        errors.append(f"normalization {operation.get('id')}: invalid drop_candidates operation")
        return
    expected = set(cast(list[str], ids))
    found = {
        cast(str, cast(dict[str, Any], row.get("candidate", {})).get("id"))
        for row in rows if isinstance(row, dict) and isinstance(row.get("candidate"), dict)
        and cast(dict[str, Any], row["candidate"]).get("id") in expected
    }
    if found != expected:
        errors.append(f"normalization {operation.get('id')}: candidate set drift; expected={sorted(expected)} found={sorted(found)}")
        return
    source["dispositions"] = [
        row for row in rows
        if not isinstance(row, dict) or not isinstance(row.get("candidate"), dict)
        or cast(dict[str, Any], row["candidate"]).get("id") not in expected
    ]


def _patch_wp02_destructive_venv_test(
    source: dict[str, Any], operation: Mapping[str, Any],
    surface_hashes: Mapping[str, str], errors: list[str],
) -> None:
    """Delete the reviewed survivor once integrated xdist proves it destructive."""
    rows = source.get("dispositions")
    candidate_id = operation.get("candidate_id")
    member = operation.get("member")
    survivor = operation.get("survivor")
    survivor_path = operation.get("survivor_path")
    historical_commit = operation.get("historical_commit")
    historical_path = operation.get("historical_path")
    if (
        not isinstance(rows, list) or not isinstance(candidate_id, str)
        or not isinstance(member, str) or not isinstance(survivor, str)
        or not isinstance(survivor_path, str)
        or surface_hashes.get(survivor_path) != operation.get("survivor_sha256")
        or not isinstance(historical_commit, str) or not isinstance(historical_path, str)
    ):
        errors.append("normalization wp02 destructive venv test: invalid authority")
        return
    try:
        historical_blob = _git_blob(historical_commit, historical_path)
        historical_blob_id = _git_rev_parse(f"{historical_commit}:{historical_path}")
    except AuditError as exc:
        errors.append(f"normalization wp02 destructive venv test: {exc}")
        return
    if (
        historical_blob_id != operation.get("historical_blob")
        or _sha(historical_blob) != operation.get("historical_sha256")
        or b"shutil.rmtree(venv_path, ignore_errors=True)" not in historical_blob
        or b"ThreadPoolExecutor(max_workers=2)" not in historical_blob
    ):
        errors.append("normalization wp02 destructive venv test: historical source drift")
        return
    matches = [
        row for row in rows if isinstance(row, dict)
        and isinstance(row.get("candidate"), dict)
        and cast(dict[str, Any], row["candidate"]).get("id") == candidate_id
    ]
    if len(matches) != 1:
        errors.append(f"normalization wp02 destructive venv test: expected one {candidate_id} row")
        return
    row = matches[0]
    candidate = cast(dict[str, Any], row["candidate"])
    if (
        row.get("verdict") != "KEEP"
        or candidate.get("members") != [member]
        or candidate.get("source_paths") != [historical_path]
    ):
        errors.append("normalization wp02 destructive venv test: reviewed KEEP authority drift")
        return
    evidence = row.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("normalization wp02 destructive venv test: evidence mapping missing")
        return
    candidate["authority"] = [
        *cast(list[str], candidate.get("authority", [])),
        "tasks/WP08-aggregate-closure.md:T044",
    ]
    evidence["caller_evidence"] = [
        *cast(list[dict[str, Any]], evidence.get("caller_evidence", [])),
        {
            "command": (
                "SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest -q -n2 --dist loadfile "
                "tests/integration/test_pytest_venv_concurrency.py "
                "tests/e2e/test_charter_epic_golden_path.py::test_charter_epic_golden_path "
                "tests/e2e/test_upgrade_post_state.py::test_upgrade_then_branch_context_does_not_gate"
            ),
            "result": (
                "2 passed, 1 setup error: the destructive worker removed the shared published venv "
                "while its peer traversed it; integrated full run also produced two missing-executable failures."
            ),
        },
    ]
    evidence["causal_probe"] = {
        "kind": "integrated parallel destructive-cache order probe",
        "fault": "Run the legacy shared-cache deletion test beside live E2E consumers.",
        "authority_violated": "FR-013 atomic publication must remain available to every live consumer.",
        "act_reached": True,
        "intended_oracle": "No consumer observes removal or partial traversal of the published venv.",
        "intended_oracle_failed": True,
        "command": "focused two-worker destructive-order probe",
        "environment": "macOS 15.7.7 arm64; CPython 3.11.15; integrated HEAD; two xdist workers",
        "raw_artifact_hash": operation.get("order_probe_sha256"),
    }
    row["verdict"] = "DELETE"
    row["action"] = (
        "DELETE_TEST completed; remove the 84-second shared-cache destroy/rebuild test. "
        "The spawned lease-state survivor and fresh-clone parallel starts cover the contract without invalidating peers."
    )
    row["survivor"] = survivor
    row["review"] = _wp08_review(cast(str, operation["id"]))


def _patch_wp07_current_route(
    source: dict[str, Any], operation: Mapping[str, Any],
    surface_hashes: Mapping[str, str], errors: list[str],
) -> None:
    """Reconcile capped WP07 route evidence with the post-review #2782 redesign."""
    rows = source.get("dispositions")
    candidate_id = operation.get("candidate_id")
    workflow_path = operation.get("workflow_path")
    test_path = operation.get("test_path")
    if (
        not isinstance(rows, list) or not isinstance(candidate_id, str)
        or not isinstance(workflow_path, str) or not isinstance(test_path, str)
        or surface_hashes.get(workflow_path) != operation.get("workflow_sha256")
        or surface_hashes.get(test_path) != operation.get("test_sha256")
    ):
        errors.append("normalization wp07 current route: invalid content-addressed authority")
        return
    matches = [
        row for row in rows if isinstance(row, dict)
        and isinstance(row.get("candidate"), dict)
        and cast(dict[str, Any], row["candidate"]).get("id") == candidate_id
    ]
    if len(matches) != 1:
        errors.append(f"normalization wp07 current route: expected one {candidate_id} row")
        return
    workflow = Path(workflow_path).read_text(encoding="utf-8")
    test_source = Path(test_path).read_text(encoding="utf-8")
    retired = "test_issue_2782_sync_strict_json_ingress_skip.py"
    if (
        "python -m pytest tests/ -m regression" not in workflow
        or 'if [ "$ec" -eq 5 ]' not in workflow
        or "REGRESSION_PATHS" in workflow
        or retired in workflow
        or "_CORE_MISC_CAUSAL_NODE" not in test_source
        or f'assert "{retired}" not in regression' not in test_source
    ):
        errors.append("normalization wp07 current route: integrated generic/empty-capable route drift")
        return
    row = matches[0]
    evidence = row.get("evidence")
    if not isinstance(evidence, dict) or not isinstance(evidence.get("causal_probe"), dict):
        errors.append("normalization wp07 current route: legacy causal evidence missing")
        return
    causal = cast(dict[str, Any], evidence["causal_probe"])
    # The capped shard left its unquoted ``#2782`` text YAML-truncated to
    # ``"The exact"``. Pin that parsed legacy body before replacing it.
    if causal.get("intended_oracle") != "The exact" or "regression-tests" not in str(causal.get("fault")):
        errors.append("normalization wp07 current route: legacy authority no longer matches reviewed shard")
        return
    candidate = cast(dict[str, Any], row["candidate"])
    candidate["authority"] = [
        *cast(list[str], candidate.get("authority", [])), workflow_path, test_path,
    ]
    routing = evidence.get("routing_evidence")
    if isinstance(routing, list) and routing and isinstance(routing[0], dict):
        routing[0]["result"] = (
            "Current-main reconciliation retains the blocking generic regression marker route, "
            "accepts an empty marker set via pytest exit 5, and removes the deleted #2782 literal owner."
        )
    evidence["causal_probe"] = {
        "kind": "live replacement-union route fault",
        "fault": "Remove the current non-empty arch-adversarial gates from the parsed replacement union.",
        "authority_violated": "The exact legacy core-misc node set must remain covered by the union of live replacement routes.",
        "act_reached": True,
        "intended_oracle": "The live CI path-filter guard node becomes missing from the replacement union.",
        "intended_oracle_failed": True,
        "command": (
            ".venv/bin/pytest -q -p no:cacheprovider "
            "tests/architectural/test_ci_quality_path_filters.py::"
            "test_live_core_misc_replacement_union_covers_legacy_selection"
        ),
        "environment": "macOS 15.7.7 arm64; CPython 3.11.15; current-main integrated WP08 lane",
        "raw_artifact_hash": cast(str, operation["test_sha256"]),
    }
    row["action"] = (
        "Delete the recursive eight-subprocess implementation; preserve its boundary with one live universe "
        "and a causal non-empty route fault. Keep regression generic, blocking, and empty-capable."
    )


def _patch_wp10(
    source: dict[str, Any], operation: Mapping[str, Any],
    documents: Sequence[tuple[Path, dict[str, Any]]], errors: list[str],
) -> None:
    rows = source.get("dispositions")
    if not isinstance(rows, list):
        errors.append("normalization wp10: dispositions list missing")
        return
    candidate_id = operation.get("candidate_id")
    source_path = operation.get("source")
    stale_probe = operation.get("stale_probe_sha256")
    if not isinstance(source_path, str) or not isinstance(stale_probe, str) or (
        Path(source_path).read_text(encoding="utf-8").count(stale_probe)
        != operation.get("expected_serialized_probe_occurrences")
    ):
        errors.append("normalization wp10: serialized stale-probe occurrence drift")
        return
    matches = [
        row for row in rows if isinstance(row, dict) and isinstance(row.get("candidate"), dict)
        and cast(dict[str, Any], row["candidate"]).get("id") == candidate_id
    ]
    if len(matches) != 1:
        errors.append(f"normalization wp10: expected one {candidate_id} row, found {len(matches)}")
        return
    candidate = cast(dict[str, Any], matches[0]["candidate"])
    members = candidate.get("members")
    observations = candidate.get("observations")
    stale_member = operation.get("stale_member")
    if not isinstance(members, list) or members.count(stale_member) != 1 or not isinstance(observations, list):
        errors.append("normalization wp10: stale classifier identity drift")
        return
    candidate["members"] = [operation["canonical_member"] if member == stale_member else member for member in members]
    stale_observations = [row for row in observations if isinstance(row, dict) and row.get("nodeid") == stale_member]
    if len(stale_observations) != 1:
        errors.append("normalization wp10: stale classifier observation drift")
        return
    stale_observations[0]["nodeid"] = operation["canonical_observation"]
    normalized, probe_count = _replace_scalar(source, stale_probe, cast(str, operation["current_probe_sha256"]))
    normalized, results_count = _replace_scalar(normalized, cast(str, operation["stale_results_sha256"]), cast(str, operation["current_results_sha256"]))
    if probe_count != operation.get("expected_loaded_probe_references") or results_count != 1:
        errors.append(f"normalization wp10: stale hash occurrence drift probe={probe_count} results={results_count}")
        return
    source.clear()
    source.update(cast(dict[str, Any], normalized))
    rows = source.get("dispositions")
    if not isinstance(rows, list):
        errors.append("normalization wp10: normalized dispositions list missing")
        return
    omitted_member = operation.get("omitted_exact_member")
    omitted_observation = operation.get("omitted_exact_observation")
    survivor = operation.get("omitted_exact_survivor")
    if not all(isinstance(value, str) for value in (omitted_member, omitted_observation, survivor)):
        errors.append("normalization wp10: omitted exact-member authority is incomplete")
        return
    represented = {
        member for row in rows if isinstance(row, dict)
        for member in cast(dict[str, Any], row.get("candidate", {})).get("members", [])
    }
    if omitted_member in represented or omitted_observation in represented:
        errors.append("normalization wp10: omitted exact member is already represented")
        return
    try:
        node_index, _, route, execution_hash = _base_observation_index(documents)
        observation = _normalized_observation(cast(str, omitted_observation), node_index, route, execution_hash)
    except AuditError as exc:
        errors.append(f"normalization wp10: {exc}")
        return
    rows.append({
        "candidate": {
            "id": f"WP08-WP10-exact-omission-{_sha(cast(str, omitted_member))[:16]}",
            "members": [omitted_member], "granularity": "node",
            "source_paths": [cast(str, omitted_member).split("::", 1)[0]],
            "production_paths": ["src/specify_cli"],
            "oracle": None, "contract_claim": None,
            "authority": [
                "kitty-specs/assertive-test-suite-sanitation-01KZME3P/tasks/WP10-cli-architecture-consolidation/final-review.md",
                "kitty-specs/assertive-test-suite-sanitation-01KZME3P/spec.md#FR-007",
            ],
            "duplicate_group": "WP10-authored-applies-edge-duplicate",
            "route_memberships": [copy.deepcopy(route)],
            "platforms": ["linux", "macOS", "windows"],
            "observations": [observation],
        },
        "evidence": {
            "profile": "duplicate",
            "overlap_evidence": [{
                "left": cast(str, omitted_member), "right": cast(str, survivor),
                "result": "The allowlist-empty shape assertion is dominated by the live shipped-tree authored-applies-edge survivor.",
            }],
            "causal_probe": {
                "kind": "WP10-authored-applies-edge-dominance",
                "fault": "Author an applies edge in a shipped mission fragment.",
                "authority_violated": "No shipped mission fragment may author an applies edge.",
                "act_reached": True,
                "intended_oracle": "The survivor identifies the authored edge in the shipped tree.",
                "intended_oracle_failed": True,
                "command": f".venv/bin/pytest -q {cast(str, omitted_member).split('::', 1)[0]}",
                "environment": "WP10 reviewed mission environment; exact base identity supplied by immutable census",
                "raw_artifact_hash": execution_hash,
            },
        },
        "verdict": "DELETE", "state": "terminal",
        "action": "Delete the dominated empty-allowlist shape assertion; retain the live shipped-tree authored-edge survivor.",
        "survivor": survivor, "issue": "#3284", "owner": None,
        "expires": None, "hic_approval": None,
        "review": _wp08_review("WP10-final-review-exact-member-omission"),
    })


def _synthesize_wp05_survivors(
    source: dict[str, Any], operation: Mapping[str, Any],
    documents: Sequence[tuple[Path, dict[str, Any]]], raw_hashes: Mapping[str, str],
    errors: list[str],
) -> None:
    rows = source.get("dispositions")
    evidence_path = operation.get("evidence_artifact")
    if not isinstance(rows, list) or not isinstance(evidence_path, str) or evidence_path not in raw_hashes:
        errors.append("normalization wp05: invalid survivor-map authority")
        return
    try:
        raw = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
        survivor_rows = _normalization_pointer(raw, cast(str, operation["pointer"]))
        node_index, _, route, execution_hash = _base_observation_index(documents)
    except (AuditError, KeyError, json.JSONDecodeError, OSError) as exc:
        errors.append(f"normalization wp05: {exc}")
        return
    required = {
        "path", "nodeid", "production_surface", "authority", "fault",
        "act_assertion", "command", "raw_artifact_hash",
    }
    if not isinstance(survivor_rows, list) or len(survivor_rows) != operation.get("expected_paths"):
        errors.append("normalization wp05: survivor path count drift")
        return
    if any(not isinstance(row, dict) or not required <= set(row) for row in survivor_rows):
        errors.append("normalization wp05: survivor proof schema drift")
        return
    paths = [cast(str, row["path"]) for row in survivor_rows]
    nodeids = [cast(str, row["nodeid"]) for row in survivor_rows]
    if len(paths) != len(set(paths)) or len(nodeids) != len(set(nodeids)):
        errors.append("normalization wp05: survivor identities must be unique")
        return
    existing_paths = {
        path for row in rows if isinstance(row, dict)
        for path in cast(dict[str, Any], row.get("candidate", {})).get("source_paths", [])
    }
    overlap = existing_paths & set(paths)
    if overlap:
        errors.append(f"normalization wp05: retained scanner paths already represented: {sorted(overlap)}")
        return
    for proof in survivor_rows:
        member = cast(str, proof["nodeid"])
        path = cast(str, proof["path"])
        if member not in node_index or member.split("::", 1)[0] != path:
            errors.append(f"normalization wp05: survivor identity absent or substituted: {member}")
            continue
        rows.append({
            "candidate": {
                "id": f"WP08-WP05-survivor-{_sha(path)[:16]}",
                "members": [member], "granularity": "node", "source_paths": [path],
                "production_paths": [cast(str, proof["production_surface"])],
                "oracle": cast(str, proof["act_assertion"]),
                "contract_claim": f"Retained structural scanner catches: {proof['fault']}",
                "authority": [cast(str, proof["authority"]), evidence_path],
                "duplicate_group": None, "route_memberships": [copy.deepcopy(route)],
                "platforms": ["linux", "macOS", "windows"],
                "observations": [_normalized_observation(member, node_index, route, execution_hash)],
            },
            "evidence": {
                "profile": "structural",
                "authority_evidence": [{
                    "reference": cast(str, proof["authority"]),
                    "result": f"WP05 cycle-3 survivor proof retains this exact scanner path; result-set sha256={raw_hashes[evidence_path]}.",
                }],
                "causal_probe": {
                    "kind": "WP05-reviewed-survivor-fault", "fault": cast(str, proof["fault"]),
                    "authority_violated": cast(str, proof["authority"]), "act_reached": True,
                    "intended_oracle": cast(str, proof["act_assertion"]), "intended_oracle_failed": True,
                    "command": cast(str, proof["command"]),
                    "environment": "WP05 cycle-3 reviewed mission environment",
                    "raw_artifact_hash": cast(str, proof["raw_artifact_hash"]),
                },
            },
            "verdict": "KEEP", "state": "terminal",
            "action": "Retain the exact reviewed WP05 structural scanner survivor.",
            "survivor": None, "issue": "#3284", "owner": None,
            "expires": None, "hic_approval": None,
            "review": _wp08_review("WP05-cycle-3-content-addressed-survivor-map"),
        })


def _append_wp07_scanner_paths(
    source: dict[str, Any], operation: Mapping[str, Any],
    documents: Sequence[tuple[Path, dict[str, Any]]], raw_hashes: Mapping[str, str],
    errors: list[str],
) -> None:
    rows = source.get("dispositions")
    paths = operation.get("paths")
    evidence_path = operation.get("evidence_artifact")
    route_manifest = operation.get("route_manifest")
    if (
        not isinstance(rows, list) or not _str_list(paths, nonempty=True)
        or not isinstance(evidence_path, str) or evidence_path not in raw_hashes
        or not isinstance(route_manifest, str) or route_manifest not in raw_hashes
    ):
        errors.append("normalization wp07: invalid retained-route authority")
        return
    try:
        node_index, _, route, execution_hash = _base_observation_index(documents)
    except AuditError as exc:
        errors.append(f"normalization wp07: {exc}")
        return
    existing_paths = {
        path for row in rows if isinstance(row, dict)
        for path in cast(dict[str, Any], row.get("candidate", {})).get("source_paths", [])
    }
    overlap = existing_paths & set(cast(list[str], paths))
    if overlap:
        errors.append(f"normalization wp07: retained scanner paths already represented: {sorted(overlap)}")
        return
    for path in cast(list[str], paths):
        members = sorted(nodeid for nodeid in node_index if nodeid.split("::", 1)[0] == path)
        if not members:
            errors.append(f"normalization wp07: retained route path absent from base census: {path}")
            continue
        member = members[0]
        route_evidence = copy.deepcopy(route)
        route_evidence["result"] = "Reviewed WP07 route manifest preserves blocking narrow-route ownership for this scanner path."
        rows.append({
            "candidate": {
                "id": f"WP08-WP07-route-survivor-{_sha(path)[:16]}",
                "members": [member], "granularity": "node", "source_paths": [path],
                "production_paths": [".github/workflows/ci-quality.yml"],
                "oracle": "Workflow selectors, marker completeness, quarantine isolation, and blocking suite-job semantics remain enforced.",
                "contract_claim": "Every retained routing architecture scanner owns a current blocking CI contract.",
                "authority": [
                    "kitty-specs/assertive-test-suite-sanitation-01KZME3P/contracts/ci-routing.md",
                    route_manifest,
                ],
                "duplicate_group": None, "route_memberships": [copy.deepcopy(route)],
                "platforms": ["linux", "macOS", "windows"],
                "observations": [_normalized_observation(member, node_index, route, execution_hash)],
            },
            "evidence": {
                "profile": "route", "routing_evidence": [route_evidence],
                "cost_evidence": {
                    "identity": evidence_path,
                    "result": (
                        "WP07 bounded focused validation passed 47 nodes; "
                        f"results sha256={raw_hashes[evidence_path]}; "
                        f"route-manifest sha256={raw_hashes[route_manifest]}."
                    ),
                },
                "causal_probe": {
                    "kind": "WP07-blocking-route-contract-fault",
                    "fault": f"Remove the blocking workflow ownership or selector for {path}.",
                    "authority_violated": "Every retained routing scanner must remain selected by a blocking CI route.",
                    "act_reached": True,
                    "intended_oracle": "The focused routing architecture suite reports the missing or non-blocking route.",
                    "intended_oracle_failed": True,
                    "command": (
                        ".venv/bin/pytest -q tests/architectural/test_marker_job_completeness.py "
                        "tests/architectural/test_quarantine_marker.py "
                        "tests/architectural/test_suite_jobs_gate_blocking.py"
                    ),
                    "environment": "WP07 cycle-3 reviewed mission environment",
                    "raw_artifact_hash": raw_hashes[evidence_path],
                },
            },
            "verdict": "KEEP", "state": "terminal",
            "action": "Retain the reviewed proportional CI-routing architecture scanner.",
            "survivor": None, "issue": "#3284", "owner": None,
            "expires": None, "hic_approval": None,
            "review": _wp08_review("WP07-cycle-3-route-scanner-map"),
        })


def _append_wp06_omissions(
    source: dict[str, Any], operation: Mapping[str, Any],
    documents: Sequence[tuple[Path, dict[str, Any]]], raw_hashes: Mapping[str, str],
    errors: list[str],
) -> None:
    rows = source.get("dispositions")
    members = operation.get("members")
    evidence_artifact = operation.get("evidence_artifact")
    if not isinstance(rows, list) or not _str_list(members, nonempty=True) or evidence_artifact not in raw_hashes:
        errors.append("normalization wp06: invalid omitted-member authority")
        return
    try:
        node_index, _, route, execution_hash = _base_observation_index(documents)
    except AuditError as exc:
        errors.append(f"normalization wp06: {exc}")
        return
    existing = {
        member for row in rows if isinstance(row, dict)
        for member in cast(dict[str, Any], row.get("candidate", {})).get("members", [])
    }
    overlap = existing & set(cast(list[str], members))
    if overlap:
        errors.append(f"normalization wp06: omitted members already present: {sorted(overlap)}")
        return
    for member in cast(list[str], members):
        candidate_id = f"WP08-WP06-omission-{_sha(member)[:16]}"
        rows.append({
            "candidate": {
                "id": candidate_id, "members": [member], "granularity": "node",
                "source_paths": [member.split("::", 1)[0]], "production_paths": [],
                "oracle": None, "contract_claim": None,
                "authority": [
                    "kitty-specs/assertive-test-suite-sanitation-01KZME3P/tasks/WP06-baseline-red-adjudication/arbiter-decision.md",
                    "kitty-specs/assertive-test-suite-sanitation-01KZME3P/spec.md#FR-007",
                ],
                "duplicate_group": "WP06-reachability-zero-signal-omissions",
                "route_memberships": [copy.deepcopy(route)],
                "platforms": ["linux", "macOS", "windows"],
                "observations": [_normalized_observation(member, node_index, route, execution_hash)],
            },
            "evidence": {
                "profile": "dead_symbol",
                "caller_evidence": [{
                    "command": f"rg -n --fixed-strings {shlex.quote(member.rsplit('::', 1)[-1])} tests/doctrine/drg/test_reachability.py",
                    "result": "The node asserted only reachability membership/count/meta shape and owned no distinct production caller boundary.",
                }],
                "authority_evidence": [{
                    "reference": cast(str, evidence_artifact),
                    "result": (
                        f"WP06 cycle-3 review and root arbiter classify {member} as a valid "
                        f"zero-signal deletion; raw_sha256={raw_hashes[cast(str, evidence_artifact)]}."
                    ),
                }],
            },
            "verdict": "DELETE", "state": "terminal",
            "action": "Terminally record the approved omitted reachability membership/count/meta-pin deletion; do not restore it.",
            "survivor": None, "issue": "#3284", "owner": None,
            "expires": None, "hic_approval": None,
            "review": _wp08_review("WP06-final-review-omission-assignment"),
        })


def _wp09_structural_evidence(
    outcome: str, family: str, successor: str | None, screening: Mapping[str, Any],
    evidence_path: str, evidence_hash: str,
) -> tuple[dict[str, Any], str, str | None]:
    authority = str(screening.get("authority") or "spec.md FR-006/FR-007 current-authority absence")
    oracle = str(screening.get("oracle") or "no distinct live observable oracle")
    if outcome == "KEEP_EXACT":
        evidence = {
            "profile": "structural",
            "authority_evidence": [{"reference": authority, "result": f"Nonzero live corpus: {screening.get('corpus')}"}],
            "causal_probe": {
                "kind": "WP09-controlled-fault-family", "fault": f"plausible authority violation for {family}",
                "authority_violated": authority, "act_reached": True,
                "intended_oracle": oracle, "intended_oracle_failed": True,
                "command": f"Replay controlled_fault_proofs from {evidence_path}",
                "environment": "WP09 reviewed CPython 3.11 mission environment",
                "raw_artifact_hash": evidence_hash,
            },
        }
        return evidence, "KEEP", None
    if outcome in {"FOLD_TO_SURVIVOR", "FOLD_TO_EXTERNAL_SURVIVOR"}:
        evidence = {
            "profile": "duplicate",
            "overlap_evidence": [{
                "left": family, "right": successor or "reviewed external survivor",
                "result": f"WP09 frozen map classifies this member as {outcome}; the named successor owns the live boundary.",
            }],
            "causal_probe": {
                "kind": "WP09-successor-controlled-fault", "fault": f"remove or violate successor for {family}",
                "authority_violated": authority, "act_reached": True,
                "intended_oracle": oracle, "intended_oracle_failed": True,
                "command": f"Replay controlled_fault_proofs and cycle_3_reconciliation from {evidence_path}",
                "environment": "WP09 reviewed CPython 3.11 mission environment",
                "raw_artifact_hash": evidence_hash,
            },
        }
        return evidence, "DELETE", successor
    evidence = {
        "profile": "dead_symbol",
        "caller_evidence": [{
            "command": f"Replay cycle_3_reconciliation family {family} from {evidence_path}",
            "result": "No distinct production caller or live bug-catching boundary remained.",
        }],
        "authority_evidence": [{
            "reference": authority,
            "result": f"WP09 final review classified {family} as obsolete shape/self-test/history with no unique authority; raw_sha256={evidence_hash}.",
        }],
    }
    return evidence, "DELETE", None


def _synthesize_wp09(
    source: dict[str, Any], operation: Mapping[str, Any],
    documents: Sequence[tuple[Path, dict[str, Any]]], raw_hashes: Mapping[str, str],
    errors: list[str],
) -> None:
    evidence_path = operation.get("evidence_artifact")
    if not isinstance(evidence_path, str) or evidence_path not in raw_hashes:
        errors.append("normalization wp09: evidence artifact is not content-addressed")
        return
    try:
        raw = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
        map_rows = _normalization_pointer(raw, cast(str, operation["map_pointer"]))
        map_fields = _normalization_pointer(raw, cast(str, operation["map_fields_pointer"]))
        node_index, _, route, execution_hash = _base_observation_index(documents)
    except (AuditError, KeyError, json.JSONDecodeError, OSError) as exc:
        errors.append(f"normalization wp09: {exc}")
        return
    if not isinstance(map_rows, list) or not isinstance(map_fields, list) or map_fields != [
        "frozen_nodeid", "outcome", "family", "successor_or_equivalent",
    ]:
        errors.append("normalization wp09: frozen map schema drift")
        return
    mapped = [dict(zip(cast(list[str], map_fields), row, strict=True)) for row in map_rows if isinstance(row, list)]
    members = [row.get("frozen_nodeid") for row in mapped]
    if (
        len(mapped) != operation.get("expected_members")
        or len(members) != len(set(members))
        or not all(isinstance(member, str) and member in node_index for member in members)
    ):
        errors.append("normalization wp09: frozen identity totality/source drift")
        return
    outcomes = {"KEEP_EXACT", "DELETE_NO_UNIQUE_BOUNDARY", "FOLD_TO_SURVIVOR", "FOLD_TO_EXTERNAL_SURVIVOR"}
    if any(row.get("outcome") not in outcomes for row in mapped):
        errors.append("normalization wp09: unknown terminal outcome")
        return
    screenings = source.get("screening")
    if not isinstance(screenings, list):
        errors.append("normalization wp09: screening list missing")
        return
    screening_by_path = {
        row["path"]: row for row in screenings if isinstance(row, dict) and isinstance(row.get("path"), str)
    }
    if source.get("dispositions") not in (None, []):
        errors.append("normalization wp09: legacy source unexpectedly has dispositions")
        return
    normalized_rows: list[dict[str, Any]] = []
    errors_before_rows = len(errors)
    for mapped_row in mapped:
        member = cast(str, mapped_row["frozen_nodeid"])
        path = member.split("::", 1)[0]
        screening = screening_by_path.get(path)
        if screening is None:
            errors.append(f"normalization wp09: no screening authority for {path}")
            continue
        outcome = cast(str, mapped_row["outcome"])
        family = cast(str, mapped_row["family"])
        successor_value = mapped_row.get("successor_or_equivalent")
        successor = successor_value if isinstance(successor_value, str) else None
        evidence, verdict, terminal_survivor = _wp09_structural_evidence(
            outcome, family, successor, screening, evidence_path, raw_hashes[evidence_path],
        )
        keep = verdict == "KEEP"
        oracle = str(screening.get("oracle") or "") if keep else None
        authority = str(screening.get("authority") or "spec.md FR-006/FR-007")
        normalized_rows.append({
            "candidate": {
                "id": f"WP08-WP09-{_sha(member)[:16]}", "members": [member],
                "granularity": "node", "source_paths": [path],
                "production_paths": [f"live corpus: {screening.get('corpus')}"] if keep else [],
                "oracle": oracle, "contract_claim": f"WP09 structural authority: {oracle}" if keep else None,
                "authority": [authority], "duplicate_group": family,
                "route_memberships": [copy.deepcopy(route)],
                "platforms": ["linux", "macOS", "windows"],
                "observations": [_normalized_observation(member, node_index, route, execution_hash)],
            },
            "evidence": evidence, "verdict": verdict, "state": "terminal",
            "action": (
                "Retain exact reviewed WP09 live guard." if keep
                else f"Delete reviewed WP09 legacy member; terminal family={family}."
            ),
            "survivor": terminal_survivor, "issue": "#1931", "owner": None,
            "expires": None, "hic_approval": None,
            "review": _wp08_review("WP09-cycle-3-content-addressed-map"),
        })
    if len(errors) != errors_before_rows:
        return
    deleted = sum(row["verdict"] == "DELETE" for row in normalized_rows)
    if deleted != operation.get("expected_terminal_deletions"):
        errors.append("normalization wp09: terminal-deletion arithmetic drift")
        return
    expected_members = operation.get("expected_members")
    expected_current = operation.get("expected_current")
    expected_net_removed = operation.get("expected_net_removed")
    if not all(isinstance(value, int) for value in (expected_members, expected_current, expected_net_removed)):
        errors.append("normalization wp09: net-reduction authorities must be integers")
        return
    if cast(int, expected_members) - cast(int, expected_current) != expected_net_removed:
        errors.append("normalization wp09: net-reduction arithmetic drift")
        return
    source["dispositions"] = normalized_rows


def _backfill_approved_review_metadata(
    documents: Sequence[tuple[Path, dict[str, Any]]], operation: Mapping[str, Any],
    errors: list[str],
) -> None:
    status_commit = operation.get("status_commit")
    status_path = operation.get("status_path")
    packages = operation.get("packages")
    if not isinstance(status_commit, str) or not isinstance(status_path, str) or not isinstance(packages, dict):
        errors.append("normalization review metadata: commit/path/packages authority required")
        return
    try:
        status = json.loads(_git_blob(status_commit, status_path))
    except (AuditError, json.JSONDecodeError) as exc:
        errors.append(f"normalization review metadata: {exc}")
        return
    work_packages = status.get("work_packages") if isinstance(status, dict) else None
    if not isinstance(work_packages, dict):
        errors.append("normalization review metadata: status work_packages mapping missing")
        return
    expected_packages = {
        "WP02", "WP03", "WP04", "WP05", "WP06", "WP07", "WP09",
        "WP10", "WP11", "WP12", "WP13", "WP14", "WP15",
    }
    if set(packages) != expected_packages or not all(isinstance(value, str) for value in packages.values()):
        errors.append("normalization review metadata: exact approved package/source map drift")
        return
    for wp, source_key_value in sorted(packages.items()):
        source_key = cast(str, source_key_value)
        source = _normalization_source(documents, source_key)
        authority = work_packages.get(wp)
        if source is None or not isinstance(authority, dict):
            errors.append(f"normalization review metadata: missing {wp} source/status authority")
            continue
        rows = source.get("dispositions")
        profile = authority.get("agent_profile")
        event_id = authority.get("last_event_id")
        transition_at = authority.get("last_transition_at")
        notes = authority.get("notes")
        if (
            authority.get("lane") != "approved" or profile != "reviewer-renata"
            or not all(isinstance(value, str) and value for value in (event_id, transition_at))
            or not isinstance(notes, list) or not notes or not isinstance(rows, list) or not rows
        ):
            errors.append(f"normalization review metadata: {wp} is not a complete approved reviewer authority")
            continue
        reviewer_actor = authority.get("agent")
        if not isinstance(reviewer_actor, str) or not reviewer_actor:
            reviewer_actor = "root-arbiter"
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"normalization review metadata: {wp} dispositions[{index}] must be mapping")
                continue
            previous = row.get("review")
            implementer = previous.get("implementer") if isinstance(previous, dict) else None
            if not isinstance(implementer, str) or not implementer:
                errors.append(f"normalization review metadata: {wp} dispositions[{index}] implementer missing")
                continue
            row["review"] = {
                "implementer": implementer,
                "independent_reviewer": f"{profile}/{reviewer_actor}",
                "verdict": f"runtime-approved:{event_id}",
                "timestamp": transition_at,
            }


def _apply_normalization(  # noqa: C901 - each content-addressed operation is dispatched explicitly
    documents: Sequence[tuple[Path, dict[str, Any]]], errors: list[str],
) -> list[tuple[Path, dict[str, Any]]]:
    normalized = [(path, copy.deepcopy(data)) for path, data in documents]
    records = [(path, data) for path, data in normalized if data.get("schema_version") == NORMALIZATION_SCHEMA]
    if not records:
        return normalized
    if len(records) != 1:
        errors.append("exactly one normalization authority is permitted")
        return normalized
    record_path, record = records[0]
    _validate_normalization_authority(record_path, record, normalized, errors)
    raw_rows = record.get("raw_artifacts")
    raw_hashes = {
        row["path"]: row["sha256"]
        for row in raw_rows if isinstance(row, dict) and isinstance(row.get("path"), str)
        and isinstance(row.get("sha256"), str)
    } if isinstance(raw_rows, list) else {}
    surface_rows = record.get("integration_surfaces")
    surface_hashes = {
        row["path"]: row["sha256"]
        for row in surface_rows if isinstance(row, dict) and isinstance(row.get("path"), str)
        and isinstance(row.get("sha256"), str)
    } if isinstance(surface_rows, list) else {}
    operations = record.get("operations")
    if not isinstance(operations, list) or not operations:
        errors.append(f"{record_path}: normalization operations required")
        return normalized
    operation_ids = [row.get("id") for row in operations if isinstance(row, dict)]
    if len(operation_ids) != len(operations) or len(operation_ids) != len(set(operation_ids)):
        errors.append(f"{record_path}: operation ids must be unique nonempty mappings")
        return normalized
    for operation in operations:
        if not isinstance(operation, dict) or not _nonempty_string(operation.get("id")):
            continue
        kind = operation.get("kind")
        if kind == "backfill_approved_review_metadata":
            _backfill_approved_review_metadata(normalized, operation, errors)
            continue
        source_key = operation.get("source")
        source = _normalization_source(normalized, source_key) if isinstance(source_key, str) else None
        if source is None:
            errors.append(f"normalization {operation.get('id')}: supplied source document missing")
            continue
        if kind == "drop_candidates":
            _drop_normalized_candidates(source, operation, errors)
        elif kind == "patch_wp02_destructive_venv_test":
            _patch_wp02_destructive_venv_test(
                source, operation, surface_hashes, errors,
            )
        elif kind == "patch_wp10":
            _patch_wp10(source, operation, normalized, errors)
        elif kind == "synthesize_wp05_survivors":
            _synthesize_wp05_survivors(source, operation, normalized, raw_hashes, errors)
        elif kind == "append_wp06_omissions":
            _append_wp06_omissions(source, operation, normalized, raw_hashes, errors)
        elif kind == "append_wp07_scanner_paths":
            _append_wp07_scanner_paths(source, operation, normalized, raw_hashes, errors)
        elif kind == "patch_wp07_current_route":
            _patch_wp07_current_route(source, operation, surface_hashes, errors)
        elif kind == "synthesize_wp09_node_map":
            _synthesize_wp09(source, operation, normalized, raw_hashes, errors)
        else:
            errors.append(f"normalization {operation.get('id')}: unknown operation kind {kind!r}")
    return normalized


def _validate_candidate_universe(  # noqa: C901 - each manifest class has a different identity grain
    census: Mapping[str, Any], member_shards: Mapping[str, set[str]],
    census_member_nodes: Mapping[str, set[str]], path_shards: Mapping[str, set[str]],
    errors: list[str],
) -> dict[str, Any]:
    manifests = census.get("manifests")
    if not isinstance(manifests, dict):
        errors.append("candidate universe: base census manifests mapping required")
        return {"enforced": True, "valid": False, "classes": {}}

    def member_status(member: str) -> str:
        direct = member_shards.get(member, set())
        nodes = census_member_nodes.get(member, set())
        node_owners = [member_shards.get(node, set()) for node in sorted(nodes)]
        owners = set(direct)
        for node_owner in node_owners:
            owners.update(node_owner)
        structurally_covered = bool(direct) or bool(nodes) and all(node_owners)
        if not structurally_covered:
            return "missing"
        return "covered" if len(owners) == 1 else "ambiguous"

    class_members: dict[str, list[str]] = {"inert": [], "exact": [], "promoted": []}
    inert = manifests.get("inert_candidates")
    if isinstance(inert, list):
        class_members["inert"] = [
            row["member"] for row in inert if isinstance(row, dict) and isinstance(row.get("member"), str)
        ]
    exact = manifests.get("exact_body_groups")
    if isinstance(exact, list):
        class_members["exact"] = [
            member["member"] for group in exact if isinstance(group, dict)
            for member in group.get("members", [])
            if isinstance(member, dict) and isinstance(member.get("member"), str)
        ]
    promoted = manifests.get("promoted_semantic_groups")
    if isinstance(promoted, list):
        class_members["promoted"] = [
            member["member"] for group in promoted if isinstance(group, dict)
            for member in group.get("members", [])
            if isinstance(member, dict) and isinstance(member.get("member"), str)
        ]
    class_counts: dict[str, dict[str, int]] = {}
    for label, expected_members in class_members.items():
        missing = [member for member in expected_members if member_status(member) == "missing"]
        ambiguous = [member for member in expected_members if member_status(member) == "ambiguous"]
        class_counts[label] = {
            "expected": len(expected_members), "covered": len(expected_members) - len(missing) - len(ambiguous),
            "missing": len(missing), "ambiguous": len(ambiguous),
        }
        if missing:
            errors.append(
                f"candidate universe: {label} missing terminal coverage count={len(missing)} sample={missing[:8]}"
            )
        if ambiguous:
            errors.append(
                f"candidate universe: {label} duplicated/mixed-grain coverage count={len(ambiguous)} sample={ambiguous[:8]}"
            )
    scanners = manifests.get("scanner_candidates")
    scanner_paths = [
        row["member"] for row in scanners if isinstance(row, dict) and isinstance(row.get("member"), str)
    ] if isinstance(scanners, list) else []
    scanner_missing = [path for path in scanner_paths if not path_shards.get(path)]
    scanner_duplicated = [path for path in scanner_paths if len(path_shards.get(path, set())) > 1]
    if scanner_missing:
        errors.append(
            f"candidate universe: scanner paths missing terminal shard count={len(scanner_missing)} sample={scanner_missing[:8]}"
        )
    if scanner_duplicated:
        errors.append(
            "candidate universe: scanner paths span multiple terminal shards "
            f"count={len(scanner_duplicated)} sample={scanner_duplicated[:8]}"
        )
    class_counts["scanner"] = {
        "expected": len(scanner_paths),
        "covered": len(scanner_paths) - len(scanner_missing) - len(scanner_duplicated),
        "missing": len(scanner_missing), "ambiguous": len(scanner_duplicated),
    }
    return {
        "enforced": True,
        "valid": all(row["missing"] == 0 and row["ambiguous"] == 0 for row in class_counts.values()),
        "classes": class_counts,
        "terminal_member_identities": len(member_shards),
        "terminal_source_paths": len(path_shards),
    }


def validate_documents(paths: Sequence[Path], today: dt.date) -> tuple[list[str], dict[str, Any]]:  # noqa: C901 - heterogeneous document fail-closed dispatch
    errors: list[str] = []
    members: dict[str, str] = {}
    candidate_ids: dict[str, str] = {}
    loaded: list[str] = []
    documents: list[tuple[Path, dict[str, Any]]] = []
    disposition_count = 0
    for path in paths:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{path}: cannot load: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path}: top-level mapping required")
            continue
        loaded.append(path.as_posix())
        documents.append((path, data))
    documents = _apply_normalization(documents, errors)
    census_members: set[str] = set()
    census_nodes: set[str] = set()
    census_nodeids: list[str] = []
    census_hashes: set[str] = set()
    census_member_nodes: dict[str, set[str]] = {}
    census_member_states: dict[str, str] = {}
    environment_ids: set[str] = set()
    environment_locations: dict[str, str] = {}
    route_authority: dict[str, Mapping[str, Any]] = {}
    route_locations: dict[str, str] = {}
    base_census_document: Mapping[str, Any] | None = None
    terminal_member_shards: dict[str, set[str]] = {}
    terminal_path_shards: dict[str, set[str]] = {}
    enforce_candidate_universe = any(
        isinstance(data.get("candidate_universe"), dict)
        and cast(dict[str, Any], data["candidate_universe"]).get("enforce") is True
        for _, data in documents
    )
    universe_summary: dict[str, Any] = {"enforced": False}
    for path, data in documents:
        if "source_units" in data and "reconciliation" in data:
            validate_census(data, errors)
            inventory = data.get("inventory", {})
            role = inventory.get("role", "base") if isinstance(inventory, dict) else "base"
            if role == "base" and path.name == "base-census.json":
                if _sha(path.read_bytes()) != FROZEN_BASE_CENSUS_FILE_SHA256:
                    errors.append(f"{path}: bytes do not match immutable base census authority")
                if data.get("content_sha256") != FROZEN_BASE_CENSUS_CONTENT_SHA256:
                    errors.append(f"{path}: content does not match immutable base census authority")
            document_nodeids, _ = _census_nodeids(data)
            if role == "base":
                base_census_document = data
                if census_nodeids and census_nodeids != document_nodeids:
                    errors.append(f"{path}: multiple base census node universes disagree")
                census_nodeids = document_nodeids
                census_hashes.add(_sha(path.read_bytes()))
                _collect_census_authority(
                    data, census_members, census_nodes, census_member_nodes, census_member_states,
                )
        _collect_route_authority(data, path, route_authority, route_locations, errors)
        environments = data.get("run_environments", data.get("environments", []))
        if isinstance(environments, dict):
            environments = list(environments.values())
        if not isinstance(environments, list):
            errors.append("environments must be list or mapping")
            environments = []
        for env_index, env in enumerate(environments):
            if isinstance(env, dict) and isinstance(env.get("id"), str):
                env_id = env["id"]
                location = f"{path}.environments[{env_index}]"
                if env_id in environment_locations:
                    errors.append(f"{location}: duplicate environment id {env_id}; first at {environment_locations[env_id]}")
                else:
                    environment_locations[env_id] = location
                environment_ids.add(env_id)
    for path, data in documents:
        environments = data.get("run_environments", data.get("environments", []))
        if isinstance(environments, dict):
            environments = list(environments.values())
        if not isinstance(environments, list):
            environments = []
        for env_index, env in enumerate(environments):
            if isinstance(env, dict):
                validate_environment(env, f"{path}.environments[{env_index}]", errors)
            else:
                errors.append(f"{path}.environments[{env_index}]: mapping required")
        workload = data.get("frozen_workload_dag")
        if workload is not None:
            if isinstance(workload, dict):
                validate_workload(workload, f"{path}.frozen_workload_dag", errors, environment_ids)
            else:
                errors.append(f"{path}.frozen_workload_dag: mapping required")
        if "base_execution" in data:
            validate_base_execution(
                data, f"{path}.base_execution", errors, census_nodeids, census_hashes,
                route_authority, environment_ids,
            )
        rows = data.get("dispositions", [])
        if not isinstance(rows, list):
            errors.append(f"{path}: dispositions must be list")
            continue
        if rows and data.get("schema_version") != SCHEMA:
            errors.append(f"{path}: schema_version must be {SCHEMA}")
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"{path}: dispositions[{index}] must be mapping")
                continue
            validate_disposition(
                row, index, today, errors, census_members, environment_ids, census_nodes,
                census_member_nodes, census_member_states, route_authority,
            )
            disposition_count += 1
            candidate = row.get("candidate", {})
            candidate_id = candidate.get("id") if isinstance(candidate, dict) else None
            if isinstance(candidate_id, str):
                location = f"{path}: dispositions[{index}]"
                if candidate_id in candidate_ids:
                    errors.append(f"duplicate candidate id {candidate_id}: {candidate_ids[candidate_id]} and {location}")
                else:
                    candidate_ids[candidate_id] = location
            candidate_members = candidate.get("members", []) if isinstance(candidate, dict) else []
            if not isinstance(candidate_members, list):
                candidate_members = []
            for member in candidate_members:
                if not isinstance(member, str):
                    errors.append(f"{path}: candidate member must be string")
                    continue
                if member in members:
                    errors.append(f"duplicate deep membership {member}: {members[member]} and {path}")
                members[member] = path.as_posix()
                if row.get("state") == "terminal" and row.get("verdict") not in {"FIX_TEST", "FIX_PRODUCT"}:
                    terminal_member_shards.setdefault(member, set()).add(_document_key(path))
            if (
                isinstance(candidate, dict) and row.get("state") == "terminal"
                and row.get("verdict") not in {"FIX_TEST", "FIX_PRODUCT"}
            ):
                source_paths = candidate.get("source_paths")
                if isinstance(source_paths, list):
                    for source_path in source_paths:
                        if isinstance(source_path, str):
                            terminal_path_shards.setdefault(source_path, set()).add(_document_key(path))
    if enforce_candidate_universe:
        if base_census_document is None:
            errors.append("candidate universe: immutable base census required")
        else:
            universe_summary = _validate_candidate_universe(
                base_census_document, terminal_member_shards, census_member_nodes,
                terminal_path_shards, errors,
            )
    return sorted(errors), {
        "documents": loaded, "dispositions": disposition_count, "unique_members": len(members),
        "candidate_universe": universe_summary,
    }


def aggregate(paths: Sequence[Path]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    source_files: list[dict[str, str]] = []
    documents: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(paths):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            raise AuditError(f"{path}: cannot load: {exc}") from exc
        if not isinstance(data, dict):
            raise AuditError(f"{path}: top-level mapping required")
        source_files.append({"path": path.as_posix(), "sha256": _sha(path.read_bytes())})
        documents.append((path, data))
    normalization_errors: list[str] = []
    documents = _apply_normalization(documents, normalization_errors)
    if normalization_errors:
        raise AuditError("normalization invalid: " + "; ".join(sorted(normalization_errors)))
    for path, data in documents:
        dispositions = data.get("dispositions", [])
        if not isinstance(dispositions, list) or not all(isinstance(row, dict) for row in dispositions):
            raise AuditError(f"{path}: dispositions must be a list of mappings")
        for index, row in enumerate(cast(list[dict[str, Any]], dispositions)):
            if not isinstance(row.get("candidate"), dict):
                raise AuditError(f"{path}: dispositions[{index}].candidate must be mapping")
            rows.append(row)
    rows.sort(key=lambda row: str(cast(dict[str, Any], row["candidate"]).get("id", "")))
    result = {"schema_version": SCHEMA, "generated_from": source_files, "dispositions": rows}
    result["content_sha256"] = _sha(_json_bytes(result))
    return cast(dict[str, Any], _stable(result))


def selftest() -> dict[str, Any]:  # noqa: C901 - independent adversarial probes stay visible
    """Exercise anti-vacuity cases in disposable runtime fixture trees."""
    with tempfile.TemporaryDirectory(prefix="sanitation-audit-") as temporary:
        root = Path(temporary)
        tests = root / "tests"
        tests.mkdir()
        (tests / "conftest.py").write_text(
            "import pytest\n"
            "collect_ignore = ['test_static_ignore.py']\n"
            "def pytest_ignore_collect(collection_path, config):\n"
            "    return True if collection_path.name == 'test_dynamic_ignore.py' else None\n",
            encoding="utf-8",
        )
        (tests / "test_cases.py").write_text(
            "import pytest\n"
            "@pytest.mark.inherited\n"
            "@pytest.mark.selected\n"
            "class TestOne:\n"
            "    def test_same(self): assert True\n"
            "class TestTwo:\n"
            "    @pytest.mark.parametrize('value', [1, 2])\n"
            "    def test_same(self, value): assert value\n"
            "def test_duplicate_a(): assert 1 == 1\n"
            "def test_duplicate_b(): assert 1 == 1\n"
            "def factory():\n"
            "    def test_nested(): assert True\n"
            "    return test_nested\n",
            encoding="utf-8",
        )
        (tests / "helper.py").write_text("def test_zero_node(): assert True\n", encoding="utf-8")
        (tests / "test_static_ignore.py").write_text("def test_static(): assert True\n", encoding="utf-8")
        (tests / "test_dynamic_ignore.py").write_text("def test_dynamic(): assert True\n", encoding="utf-8")
        (tests / "test_error.py").write_text(
            "raise RuntimeError('planted collection error')\ndef test_error(): assert True\n", encoding="utf-8",
        )
        first = snapshot(root, "tests", [], "SELFTEST")
        second = snapshot(root, "tests", [], "SELFTEST")
        if _json_bytes(first) != _json_bytes(second):
            raise AuditError("selftest: identical snapshots differ")
        units = {row["id"]: row for row in first["source_units"]}
        one = units["tests/test_cases.py::TestOne.test_same"]
        two = units["tests/test_cases.py::TestTwo.test_same"]
        compact_collection = first["collection"]
        marker_sets = compact_collection["tables"]["marker_sets"]
        checks = {
            "byte_identical": True,
            "zero_node": units["tests/helper.py::test_zero_node"]["collection_state"] == "zero_node",
            "static_ignore": units["tests/test_static_ignore.py::test_static"]["collection_state"] == "ignored",
            "dynamic_ignore": units["tests/test_dynamic_ignore.py::test_dynamic"]["collection_state"] == "ignored",
            "collection_error": units["tests/test_error.py::test_error"]["collection_state"] == "error",
            "same_name_membership": len(one["node_refs"]) == 1 and len(two["node_refs"]) == 2,
            "inherited_marker": any(
                marker == "inherited"
                for node_ref in one["node_refs"]
                for marker in marker_sets[compact_collection["nodes"][node_ref][4]]
            ),
            "exact_duplicate": bool(first["manifests"]["exact_body_groups"]),
            "unowned_fails": first["ownership"]["complete"] is False,
            "recursive_nested_once": list(units).count("tests/test_cases.py::factory.test_nested") == 1,
        }
        atomic_probe = root / "atomic-raw.json"
        _atomic_write_bytes(atomic_probe, b"raw-evidence\n")
        checks["outcome_raw_atomic_write"] = (
            atomic_probe.read_bytes() == b"raw-evidence\n"
            and not list(root.glob(".atomic-raw.json.*"))
        )
        invalid_capture_census = copy.deepcopy(first)
        fabricated_capture_node = copy.deepcopy(invalid_capture_census["collection"]["nodes"][0])
        fabricated_capture_node[0] = "tests/test_cases.py::test_fabricated_capture_identity"
        invalid_capture_census["collection"]["nodes"].append(fabricated_capture_node)
        invalid_capture_census_path = root / "invalid-capture-census.json"
        invalid_capture_census_path.write_bytes(_json_bytes(invalid_capture_census))
        invalid_capture_workload_path = root / "invalid-capture-workload.yaml"
        invalid_capture_workload_path.write_text(yaml.safe_dump({
            "frozen_workload_dag": {"routes": [{
                "id": "invalid-capture", "cwd": ".", "env": {},
                "argv": ["pytest", "tests/test_cases.py", "-n", "2", "-p", "no:cacheprovider"],
                "environment_id": "selftest", "memberships": [{"selector": {"ignores": []}}],
            }]},
        }), encoding="utf-8")
        invalid_capture_raw_path = root / "invalid-capture-raw.json"
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                capture_outcomes(
                    root, invalid_capture_census_path, invalid_capture_workload_path,
                    "invalid-capture", invalid_capture_raw_path,
                )
            invalid_capture_failed_closed = False
        except AuditError as error:
            invalid_capture_failed_closed = "collection mismatch" in str(error)
        checks["outcome_validation_failure_leaves_raw_absent"] = (
            invalid_capture_failed_closed and not invalid_capture_raw_path.exists()
        )
        selected = snapshot(root, "tests", ["-m", "selected", "--ignore=tests/test_error.py"], "SELFTEST-SELECT")
        selected_units = {row["id"]: row for row in selected["source_units"]}
        checks["deselected_class_parameter_family"] = (
            selected_units["tests/test_cases.py::TestTwo.test_same"]["collection_state"] == "deselected"
            and selected["reconciliation"]["state_counts"]["deselected"] >= 1
        )
        empty = root / "empty"
        (empty / "tests").mkdir(parents=True)
        empty_snapshot = snapshot(empty, "tests", [], "SELFTEST-EMPTY")
        checks["explicit_empty_census"] = (
            empty_snapshot["empty_tests_root"] is True
            and empty_snapshot["reconciliation"]["source_units"] == 0
            and empty_snapshot["collection"]["exit_code"] == 5
        )
        zero_file = root / "zero-file"
        (zero_file / "tests").mkdir(parents=True)
        (zero_file / "tests" / "test_empty.py").write_text("VALUE = 1\n", encoding="utf-8")
        zero_file_snapshot = snapshot(zero_file, "tests", [], "SELFTEST-ZERO-FILE")
        checks["zero_function_file_not_empty_root"] = (
            zero_file_snapshot["empty_tests_root"] is False
            and zero_file_snapshot["zero_function_files"] == ["tests/test_empty.py"]
        )
        for hook_name, hook_source in {
            "collection": "def pytest_collection(session): raise RuntimeError('collection crash')\n",
            "modifyitems": "def pytest_collection_modifyitems(session, config, items): raise RuntimeError('modify crash')\n",
        }.items():
            crash_root = root / f"crash-{hook_name}"
            (crash_root / "tests").mkdir(parents=True)
            (crash_root / "tests" / "conftest.py").write_text(hook_source, encoding="utf-8")
            (crash_root / "tests" / "test_case.py").write_text("def test_case(): assert True\n", encoding="utf-8")
            crashed = snapshot(crash_root, "tests", [], f"SELFTEST-{hook_name}")
            checks[f"{hook_name}_crash_fails_closed"] = (
                crashed["collection"]["exit_code"] not in {0, 5}
                and bool(crashed["collection"]["internal_errors"])
                and crashed["reconciliation"]["complete"] is False
            )
        shard = {
            "schema_version": SCHEMA,
            "dispositions": [{
                "candidate": {
                    "members": ["duplicate-member"], "granularity": "family",
                    "divergent_dimensions": ["outcome"],
                },
            }],
        }
        shard_a, shard_b = root / "a.yaml", root / "b.yaml"
        shard_a.write_text(yaml.safe_dump(shard), encoding="utf-8")
        shard_b.write_text(yaml.safe_dump(shard), encoding="utf-8")
        duplicate_errors, _ = validate_documents([shard_a, shard_b], dt.date.today())
        checks["duplicate_deep_membership_fails"] = any("duplicate deep membership" in error for error in duplicate_errors)
        checks["divergent_family_fails"] = any("divergent family dimensions require nonempty node_rows" in error for error in duplicate_errors)
        empty_shard = root / "empty-shard.yaml"
        empty_shard.write_text(yaml.safe_dump({"schema_version": SCHEMA, "dispositions": []}), encoding="utf-8")
        checks["aggregate_empty_shard"] = aggregate([empty_shard])["dispositions"] == []
        malformed = root / "malformed.yaml"
        malformed.write_text(
            yaml.safe_dump({"schema_version": SCHEMA, "dispositions": [{"candidate": "bad", "evidence": [], "verdict": "KEEP", "state": "terminal"}]}),
            encoding="utf-8",
        )
        malformed_errors, _ = validate_documents([malformed], dt.date.today())
        checks["malformed_shard_fails_without_crash"] = bool(malformed_errors)
        aggregate_bad = root / "aggregate-bad.yaml"
        aggregate_bad.write_text(yaml.safe_dump({"dispositions": "abc"}), encoding="utf-8")
        try:
            aggregate([aggregate_bad])
            checks["aggregate_malformed_controlled_error"] = False
        except AuditError:
            checks["aggregate_malformed_controlled_error"] = True
        aggregate_bad_candidate = root / "aggregate-bad-candidate.yaml"
        aggregate_bad_candidate.write_text(yaml.safe_dump({"dispositions": [{"candidate": "bad"}]}), encoding="utf-8")
        try:
            aggregate([aggregate_bad_candidate])
            checks["aggregate_malformed_candidate_controlled_error"] = False
        except AuditError:
            checks["aggregate_malformed_candidate_controlled_error"] = True
        workload_bad = root / "workload-bad.yaml"
        workload_bad.write_text(yaml.safe_dump({
            "frozen_workload_dag": {
                "repetitions": 3,
                "routes": [
                    {"id": "dup", "argv": "pytest", "environment_id": "missing", "base_mapping": "x", "head_mapping": "x", "cwd": ".", "env": {}},
                    {"id": "dup", "argv": ["pytest"], "environment_id": "missing", "base_mapping": "x", "head_mapping": "x", "cwd": ".", "env": {}},
                ],
                "edges": [{"from": "dup"}], "measurements": [],
            },
        }), encoding="utf-8")
        workload_errors, _ = validate_documents([workload_bad], dt.date.today())
        checks["workload_duplicate_argv_env_edge_rejected"] = all(
            any(fragment in error for error in workload_errors)
            for fragment in ("duplicate route", "argv must", "unknown environment", "from/to required")
        )
        ledger_bad = root / "ledger-bad.yaml"
        common_duration = {"collection": 0, "setup": 0, "call": 1, "cost_class": "fast"}
        def malicious_observation(nodeid: str, outcome: str) -> dict[str, Any]:
            return {
                "environment_id": "missing", "nodeid": nodeid,
                "collection_state": "collected", "outcome": outcome,
                "skip_reason": None, "markers": [], "duration": common_duration,
                "artifact_hash": "0" * 64,
            }
        ledger_bad.write_text(yaml.safe_dump({"schema_version": SCHEMA, "dispositions": [{
            "candidate": {
                "id": "bad", "members": ["stale-member"], "granularity": "family",
                "source_paths": "tests/x.py", "production_paths": [], "oracle": "oracle",
                "contract_claim": "claim", "authority": ["authority"], "duplicate_group": None,
                "route_memberships": [], "platforms": {"linux": True},
                "observations": [
                    malicious_observation("n1", "passed"),
                    malicious_observation("n2", "failed"),
                ],
                "equivalence": {
                    "production_path": "x", "oracle": "x", "outcome": "same",
                    "route_role": "owner", "cost_class": "fast",
                    "platform": "linux", "disposition": "KEEP",
                },
            },
            "evidence": {"profile": "inert", "routing_evidence": ["x"], "authority_evidence": ["x"]},
            "verdict": "KEEP", "state": "terminal", "action": "keep",
            "review": {"implementer": "a", "independent_reviewer": "b", "verdict": "approved", "timestamp": "2026-08-10T00:00:00Z"},
        }]}), encoding="utf-8")
        ledger_errors, _ = validate_documents([ledger_bad], dt.date.today())
        checks["ledger_types_refs_keep_family_rejected"] = all(
            any(fragment in error for error in ledger_errors)
            for fragment in ("source_paths must", "platforms must", "stale/unknown", "causal_probe", "divergent family")
        )

        valid_environment_body: dict[str, Any] = {
            "os": "selftest-os", "runner_image": "selftest-runner", "cpu_class": "selftest-cpu",
            "python": "CPython 3.13.1", "event": "local", "env": {}, "lock_hash": "1" * 64,
            "install_command": ["uv", "sync", "--frozen"], "install_state": "clean",
            "workers": "serial", "cache_policy": "disabled", "harness_patch_hash": None,
        }
        valid_environment = {"id": _sha(_json_bytes(valid_environment_body)), **valid_environment_body}
        environment_errors: list[str] = []
        validate_environment(valid_environment, "environment", environment_errors)
        checks["valid_empty_environment"] = environment_errors == []
        environment_id = cast(str, valid_environment["id"])

        member_a = "tests/test_schema.py::test_a"
        member_b = "tests/test_schema.py::test_b"
        census_identities = {member_a, member_b}
        valid_observation: dict[str, Any] = {
            "environment_id": environment_id, "nodeid": member_a, "collection_state": "collected",
            "outcome": "passed", "skip_reason": None, "markers": [],
            "duration": {"collection": 0.0, "setup": 0.0, "call": 0.01, "cost_class": "fast"},
            "artifact_hash": "2" * 64,
        }
        valid_disposition: dict[str, Any] = {
            "candidate": {
                "id": "schema-candidate", "members": [member_a], "granularity": "function",
                "source_paths": ["tests/test_schema.py"], "production_paths": [], "oracle": None,
                "contract_claim": None, "authority": ["selftest-authority"], "duplicate_group": None,
                "route_memberships": [{
                    "route_id": "selftest", "role": "owner", "required": True, "events": [],
                    "selector": {"paths": ["tests/"], "markers": [], "ignores": [], "environment_id": environment_id},
                }],
                "platforms": ["selftest-os"], "observations": [valid_observation],
            },
            "evidence": {
                "profile": "inert", "routing_evidence": [{
                    "route_id": "selftest", "role": "owner", "required": True, "events": [],
                    "selector": {"paths": ["tests/"], "markers": [], "ignores": [], "environment_id": environment_id},
                    "result": "selected by frozen route",
                }],
                "authority_evidence": [{"reference": "selftest-authority", "result": "current authority"}],
            },
            "verdict": "DELETE", "state": "terminal", "action": "delete", "survivor": None,
            "issue": None, "owner": None, "expires": None, "hic_approval": None,
            "review": {
                "implementer": "selftest", "independent_reviewer": "reviewer", "verdict": "approved",
                "timestamp": "2026-08-10T00:00:00Z",
            },
        }

        synthetic_nodes = {member_a, member_b}
        synthetic_member_nodes = {member_a: {member_a}, member_b: {member_b}}
        synthetic_member_states = {member_a: "collected", member_b: "collected"}
        synthetic_membership = copy.deepcopy(valid_disposition["candidate"]["route_memberships"][0])
        synthetic_membership.pop("route_id")
        synthetic_route_authority: dict[str, Mapping[str, Any]] = {
            "selftest": {
                "environment_id": environment_id, "env": {},
                "memberships": [synthetic_membership],
            },
        }

        def disposition_errors(row: dict[str, Any]) -> list[str]:
            found: list[str] = []
            validate_disposition(
                row, 0, dt.date(2026, 8, 10), found, census_identities, {environment_id},
                synthetic_nodes, synthetic_member_nodes, synthetic_member_states, synthetic_route_authority,
            )
            return found

        checks["valid_empty_markers"] = disposition_errors(copy.deepcopy(valid_disposition)) == []
        invalid_action = copy.deepcopy(valid_disposition)
        invalid_action["action"] = ["delete"]
        checks["action_type_rejected"] = any("action must" in error for error in disposition_errors(invalid_action))
        invalid_survivor = copy.deepcopy(valid_disposition)
        invalid_survivor["survivor"] = [member_a]
        checks["survivor_type_rejected"] = any("survivor must" in error for error in disposition_errors(invalid_survivor))

        evidence_bad_values: dict[str, Any] = {
            "caller_evidence": {}, "authority_evidence": {}, "routing_evidence": {},
            "overlap_evidence": {}, "base_evidence": [], "causal_probe": [], "cost_evidence": [],
        }
        for field, bad_value in evidence_bad_values.items():
            invalid_evidence = copy.deepcopy(valid_disposition)
            invalid_evidence["evidence"][field] = bad_value
            checks[f"evidence_type_{field}_rejected"] = any(
                field in error for error in disposition_errors(invalid_evidence)
            )
        scalar_evidence_member = copy.deepcopy(valid_disposition)
        scalar_evidence_member["evidence"]["authority_evidence"] = ["bare-reference"]
        checks["evidence_scalar_member_rejected"] = any(
            "list of mapping evidence rows" in error for error in disposition_errors(scalar_evidence_member)
        )
        vacuous_values: dict[str, Any] = {
            "caller_evidence": [{}], "authority_evidence": [{}], "routing_evidence": [{}],
            "overlap_evidence": [{}], "base_evidence": {}, "cost_evidence": {},
        }
        for field, vacuous_value in vacuous_values.items():
            vacuous_evidence = copy.deepcopy(valid_disposition)
            vacuous_evidence["evidence"][field] = vacuous_value
            checks[f"evidence_vacuous_{field}_rejected"] = any(
                field in error for error in disposition_errors(vacuous_evidence)
            )
        nested_bad_values: dict[str, Any] = {
            "caller_evidence": [{"command": 123, "result": {}}],
            "authority_evidence": [{"reference": 123, "result": []}],
            "routing_evidence": [{"route_id": 123, "role": [], "required": "yes", "events": {}, "selector": [], "result": 0}],
            "overlap_evidence": [{"left": 1, "right": [], "result": {}}],
            "base_evidence": {"identity": [], "result": {}},
            "cost_evidence": {"identity": 123, "result": []},
        }
        for field, bad_value in nested_bad_values.items():
            invalid_nested = copy.deepcopy(valid_disposition)
            invalid_nested["evidence"][field] = bad_value
            checks[f"evidence_nested_{field}_rejected"] = any(
                field in error for error in disposition_errors(invalid_nested)
            )
        fabricated_observation = copy.deepcopy(valid_disposition)
        fabricated_observation["candidate"]["observations"][0]["nodeid"] = "tests/not-in-census.py::test_fabricated"
        checks["fabricated_observation_node_rejected"] = any(
            "nodeid absent from census" in error for error in disposition_errors(fabricated_observation)
        )
        wrong_member_observation = copy.deepcopy(valid_disposition)
        wrong_member_observation["candidate"]["observations"][0]["nodeid"] = member_b
        checks["observation_candidate_membership_rejected"] = any(
            "does not belong to candidate members" in error for error in disposition_errors(wrong_member_observation)
        )
        null_collected_observation = copy.deepcopy(valid_disposition)
        null_collected_observation["candidate"]["observations"][0]["nodeid"] = None
        checks["null_collected_observation_rejected"] = any(
            "nodeid null only for source-only states" in error for error in disposition_errors(null_collected_observation)
        )
        unknown_candidate_route = copy.deepcopy(valid_disposition)
        unknown_candidate_route["candidate"]["route_memberships"][0]["route_id"] = "missing-route"
        checks["unknown_candidate_route_rejected"] = any(
            "unknown frozen route_id" in error for error in disposition_errors(unknown_candidate_route)
        )
        mismatched_route_environment = copy.deepcopy(valid_disposition)
        mismatched_route_environment["candidate"]["route_memberships"][0]["selector"]["environment_id"] = "missing-env"
        checks["candidate_route_environment_rejected"] = any(
            "environment_id does not match frozen route" in error
            for error in disposition_errors(mismatched_route_environment)
        )
        route_field_mutations: dict[str, Callable[[dict[str, Any]], None]] = {
            "role": lambda membership: membership.update(role="coverage"),
            "required": lambda membership: membership.update(required=False),
            "events": lambda membership: membership.update(events=["schedule"]),
            "selector_paths": lambda membership: membership["selector"].update(paths=["tests/fabricated/"]),
            "selector_markers": lambda membership: membership["selector"].update(markers=["fabricated"]),
            "selector_ignores": lambda membership: membership["selector"].update(ignores=["tests/fabricated.py"]),
        }
        for field, mutate in route_field_mutations.items():
            invalid_membership = copy.deepcopy(valid_disposition)
            mutate(invalid_membership["candidate"]["route_memberships"][0])
            checks[f"candidate_route_{field}_authority_rejected"] = any(
                "membership fields do not match frozen route authority" in error
                for error in disposition_errors(invalid_membership)
            )
        mismatched_evidence_role = copy.deepcopy(valid_disposition)
        mismatched_evidence_role["evidence"]["routing_evidence"][0]["role"] = "coverage"
        checks["evidence_route_role_rejected"] = any(
            "role does not match candidate" in error for error in disposition_errors(mismatched_evidence_role)
        )
        unknown_evidence_route = copy.deepcopy(valid_disposition)
        unknown_evidence_route["evidence"]["routing_evidence"][0]["route_id"] = "missing-route"
        checks["unknown_evidence_route_rejected"] = any(
            "unknown frozen route_id" in error for error in disposition_errors(unknown_evidence_route)
        )
        mismatched_evidence_environment = copy.deepcopy(valid_disposition)
        mismatched_evidence_environment["evidence"]["routing_evidence"][0]["selector"]["environment_id"] = "missing-env"
        checks["evidence_route_environment_rejected"] = any(
            "environment_id does not match frozen route" in error
            for error in disposition_errors(mismatched_evidence_environment)
        )
        source_only_observation = copy.deepcopy(valid_disposition)
        source_only_observation["candidate"]["observations"][0].update({
            "nodeid": None, "collection_state": "zero_node", "outcome": "not_run",
        })
        source_only_errors: list[str] = []
        validate_disposition(
            source_only_observation, 0, dt.date(2026, 8, 10), source_only_errors,
            census_identities, {environment_id}, synthetic_nodes,
            {member_a: set(), member_b: {member_b}},
            {member_a: "zero_node", member_b: "collected"}, synthetic_route_authority,
        )
        checks["valid_source_only_null_observation"] = source_only_errors == []

        valid_temporary = copy.deepcopy(valid_disposition)
        valid_temporary.update({
            "verdict": "TEMPORARY", "action": "temporary exception", "issue": "ISSUE-1", "owner": "owner",
            "expires": "2026-08-20", "hic_approval": "one-time approval", "renewal": False,
        })
        valid_temporary["evidence"] = {
            "profile": "environmental_platform",
            "base_evidence": {"identity": "environmental failure", "result": "reproduced"},
            "routing_evidence": copy.deepcopy(valid_disposition["evidence"]["routing_evidence"]),
        }
        checks["valid_temporary"] = disposition_errors(valid_temporary) == []
        for field, bad_value in {
            "hic_approval": ["approval"], "issue": {"id": "ISSUE-1"}, "owner": ["owner"],
            "expires": ["2026-08-20"], "renewal": "false",
        }.items():
            invalid_temporary = copy.deepcopy(valid_temporary)
            invalid_temporary[field] = bad_value
            checks[f"temporary_{field}_type_rejected"] = any(
                field in error for error in disposition_errors(invalid_temporary)
            )

        family = copy.deepcopy(valid_disposition)
        family["candidate"].update({
            "members": [member_a, member_b], "granularity": "family",
            "observations": [
                valid_observation,
                {**valid_observation, "nodeid": member_b, "outcome": "failed"},
            ],
            "equivalence": {
                "production_path": "src/schema.py", "oracle": "result", "outcome": "mixed",
                "route_role": "owner", "cost_class": "fast", "platform": "selftest-os",
                "disposition": "DELETE",
            },
            "divergent_dimensions": ["outcome"],
        })
        node_row_base = {
            "production_path": "src/schema.py", "oracle": "result", "route_role": "owner",
            "cost_class": "fast", "platform": "selftest-os", "disposition": "DELETE",
        }
        family["candidate"]["node_rows"] = [
            {"member": member_a, **node_row_base, "outcome": "passed"},
            {"member": member_b, **node_row_base, "outcome": "failed"},
        ]
        checks["valid_divergent_family_expansion"] = disposition_errors(family) == []
        invalid_dimension = copy.deepcopy(family)
        invalid_dimension["candidate"]["equivalence"]["oracle"] = ["result"]
        checks["equivalence_dimension_type_rejected"] = any(
            "equivalence.oracle" in error for error in disposition_errors(invalid_dimension)
        )
        empty_rows = copy.deepcopy(family)
        empty_rows["candidate"]["node_rows"] = []
        checks["divergent_empty_node_rows_rejected"] = any(
            "nonempty node_rows" in error for error in disposition_errors(empty_rows)
        )
        empty_row = copy.deepcopy(family)
        empty_row["candidate"]["node_rows"] = [{}]
        checks["divergent_empty_node_row_rejected"] = any(
            "member must" in error for error in disposition_errors(empty_row)
        )
        missing_member_row = copy.deepcopy(family)
        missing_member_row["candidate"]["node_rows"] = missing_member_row["candidate"]["node_rows"][:1]
        checks["divergent_member_coverage_rejected"] = any(
            "cover every candidate member" in error for error in disposition_errors(missing_member_row)
        )
        missing_dimension_row = copy.deepcopy(family)
        del missing_dimension_row["candidate"]["node_rows"][0]["platform"]
        checks["divergent_dimension_coverage_rejected"] = any(
            "missing field platform" in error for error in disposition_errors(missing_dimension_row)
        )
        unknown_member_row = copy.deepcopy(family)
        unknown_member_row["candidate"]["node_rows"][0]["member"] = "tests/test_schema.py::test_unknown"
        checks["divergent_unknown_identity_rejected"] = any(
            "candidate and census identity" in error for error in disposition_errors(unknown_member_row)
        )
        nonvarying_rows = copy.deepcopy(family)
        nonvarying_rows["candidate"]["node_rows"][1]["outcome"] = "passed"
        checks["divergent_dimension_must_vary"] = any(
            "must vary" in error for error in disposition_errors(nonvarying_rows)
        )

        duplicate_environments = root / "duplicate-environments.yaml"
        duplicate_environments.write_text(yaml.safe_dump({"environments": [valid_environment, valid_environment]}), encoding="utf-8")
        duplicate_environment_errors, _ = validate_documents([duplicate_environments], dt.date.today())
        checks["duplicate_environment_id_rejected"] = any(
            "duplicate environment id" in error for error in duplicate_environment_errors
        )
        duplicate_candidates = root / "duplicate-candidates.yaml"
        duplicate_candidates.write_text(yaml.safe_dump({
            "schema_version": SCHEMA, "environments": [valid_environment],
            "dispositions": [valid_disposition, valid_disposition],
        }), encoding="utf-8")
        duplicate_candidate_errors, _ = validate_documents([duplicate_candidates], dt.date.today())
        checks["duplicate_candidate_id_rejected"] = any(
            "duplicate candidate id" in error for error in duplicate_candidate_errors
        )

        report_root = Path(__file__).resolve().parent
        committed_census_path = report_root / "raw" / "base-census.json"
        committed_workload_path = report_root / "raw" / "base-workloads.yaml"
        committed_summary_path = report_root / "raw" / "base-full-suite-summary.txt"
        committed_census = cast(dict[str, Any], json.loads(committed_census_path.read_text(encoding="utf-8")))
        committed_workload = cast(dict[str, Any], yaml.safe_load(committed_workload_path.read_text(encoding="utf-8")))
        temp_root_nodeids = [
            cast(str, row[0]) for row in committed_census["collection"]["nodes"]
            if "<TEMP_ROOT>" in row[0]
        ]
        raw_temp_nodeids = [
            nodeid.replace("<TEMP_ROOT>", root.as_posix())
            for nodeid in temp_root_nodeids
        ]
        normalization_plugin = OutcomePlugin()
        normalization_plugin.pytest_xdist_node_collection_finished(
            SimpleNamespace(gateway=SimpleNamespace(id="gw-normalization")), raw_temp_nodeids,
        )
        for nodeid in raw_temp_nodeids:
            normalization_plugin.pytest_runtest_logreport(cast(Any, SimpleNamespace(
                nodeid=nodeid, worker_id="gw-normalization", longrepr=None,
                when="call", outcome="passed", duration=0.0,
            )))
        checks["outcome_collection_temp_root_normalization"] = (
            len(temp_root_nodeids) == 6
            and normalization_plugin.worker_collections["gw-normalization"] == temp_root_nodeids
        )
        checks["outcome_report_temp_root_normalization"] = (
            [row["nodeid"] for row in normalization_plugin.reports] == temp_root_nodeids
        )
        inert_manifest = committed_census["manifests"]["inert_candidates"][0]
        committed_member = cast(str, inert_manifest["member"])
        source_row = next(row for row in committed_census["source_units"] if row["id"] == committed_member)
        committed_node_ref = cast(list[int], source_row["node_refs"])[0]
        compact_node = cast(list[Any], committed_census["collection"]["nodes"][committed_node_ref])
        committed_nodeid = cast(str, compact_node[0])
        marker_ref = cast(int, compact_node[4])
        reason_ref = compact_node[6]
        committed_markers = cast(list[str], committed_census["collection"]["tables"]["marker_sets"][marker_ref])
        committed_reason = (
            cast(str, committed_census["collection"]["tables"]["reasons"][reason_ref])
            if isinstance(reason_ref, int) else "; ".join(cast(list[str], inert_manifest["reasons"]))
        )
        full_collection_route = next(
            route for route in committed_workload["frozen_workload_dag"]["routes"]
            if route["id"] == "full-collection"
        )
        committed_environment_id = cast(str, full_collection_route["environment_id"])
        committed_selector = {
            "paths": ["tests/"], "markers": [], "ignores": ["tests/sync/test_orphan_sweep.py"],
            "environment_id": committed_environment_id,
        }
        committed_membership = {
            "route_id": "full-collection", "role": "owner", "required": True,
            "events": ["local"], "selector": committed_selector,
        }
        committed_positive: dict[str, Any] = {
            "candidate": {
                "id": "selftest-committed-inert-delete", "members": [committed_member], "granularity": "function",
                "source_paths": [cast(str, source_row["path"])], "production_paths": [], "oracle": None,
                "contract_claim": None, "authority": ["WP03 inert-state adjudication"], "duplicate_group": None,
                "route_memberships": [committed_membership], "platforms": ["macOS"],
                "observations": [{
                    "environment_id": committed_environment_id, "nodeid": committed_nodeid,
                    "collection_state": "collected", "outcome": "skipped", "skip_reason": committed_reason,
                    "markers": committed_markers,
                    "duration": {"collection": 0.0, "setup": 0.0, "call": 0.0, "cost_class": "not_run"},
                    "artifact_hash": _sha(committed_census_path.read_bytes()),
                }],
            },
            "evidence": {
                "profile": "inert",
                "routing_evidence": [{**committed_membership, "result": "present in frozen full collection route"}],
                "authority_evidence": [{
                    "reference": "kitty-specs/assertive-test-suite-sanitation-01KZME3P/tasks/WP03-inert-test-states.md",
                    "result": "assigned inert-state authority for adjudication",
                }],
            },
            "verdict": "DELETE", "state": "terminal", "action": "delete after inert adjudication",
            "survivor": None, "issue": None, "owner": None, "expires": None, "hic_approval": None,
            "review": {
                "implementer": "selftest", "independent_reviewer": "selftest-reviewer", "verdict": "approved",
                "timestamp": "2026-08-10T00:00:00Z",
            },
        }
        committed_positive_shard = root / "committed-positive-delete.yaml"
        committed_positive_shard.write_text(
            yaml.safe_dump({"schema_version": SCHEMA, "dispositions": [committed_positive]}), encoding="utf-8",
        )
        committed_positive_errors, _ = validate_documents(
            [committed_census_path, committed_workload_path, committed_positive_shard], dt.date(2026, 8, 10),
        )
        checks["committed_positive_delete_valid"] = committed_positive_errors == []

        committed_summary = cast(dict[str, Any], json.loads(committed_summary_path.read_text(encoding="utf-8")))
        committed_nodeids, _ = _census_nodeids(committed_census)
        committed_route_authority = {
            cast(str, route["id"]): route
            for route in committed_workload["frozen_workload_dag"]["routes"]
        }
        committed_environment_ids = {
            cast(str, environment["id"]) for environment in committed_workload["run_environments"]
        }

        def base_execution_errors(document: dict[str, Any]) -> list[str]:
            found: list[str] = []
            validate_base_execution(
                document, "base-execution", found, committed_nodeids,
                {_sha(committed_census_path.read_bytes())}, committed_route_authority,
                committed_environment_ids,
            )
            return found

        def rehash_execution(document: dict[str, Any]) -> None:
            document.pop("content_sha256", None)
            document["content_sha256"] = _sha(_json_bytes(document))

        checks["valid_exact_base_execution"] = base_execution_errors(copy.deepcopy(committed_summary)) == []
        aggregate_only = {"schema_version": SCHEMA, "base_execution": {"counts": {"passed": 37444}}}
        rehash_execution(aggregate_only)
        checks["base_execution_aggregate_only_rejected"] = any(
            "exact outcome_overrides" in error for error in base_execution_errors(aggregate_only)
        )
        count_mismatch = copy.deepcopy(committed_summary)
        count_mismatch["base_execution"]["counts"]["passed"] += 1
        rehash_execution(count_mismatch)
        checks["base_execution_count_mismatch_rejected"] = any(
            "counts do not reconcile" in error for error in base_execution_errors(count_mismatch)
        )
        unknown_outcome = copy.deepcopy(committed_summary)
        unknown_node = "tests/fabricated.py::test_unknown"
        unknown_outcome["base_execution"]["outcome_overrides"]["failed"].append(unknown_node)
        unknown_outcome["base_execution"]["outcome_overrides"]["failed"].sort()
        unknown_outcome["base_execution"]["outcome_details"].append({
            "nodeid": unknown_node, "outcome": "failed", "phase": "call", "longrepr_sha256": "0" * 64,
        })
        unknown_outcome["base_execution"]["outcome_details"].sort(key=lambda row: row["nodeid"])
        unknown_outcome["base_execution"]["counts"]["failed"] += 1
        unknown_outcome["base_execution"]["counts"]["passed"] -= 1
        rehash_execution(unknown_outcome)
        checks["base_execution_unknown_node_rejected"] = any(
            "unknown outcome nodeid" in error for error in base_execution_errors(unknown_outcome)
        )
        duplicate_outcome = copy.deepcopy(committed_summary)
        duplicate_node = duplicate_outcome["base_execution"]["outcome_overrides"]["failed"][0]
        duplicate_outcome["base_execution"]["outcome_overrides"]["skipped"].append(duplicate_node)
        duplicate_outcome["base_execution"]["outcome_overrides"]["skipped"].sort()
        rehash_execution(duplicate_outcome)
        checks["base_execution_duplicate_node_rejected"] = any(
            "duplicate outcome nodeid" in error for error in base_execution_errors(duplicate_outcome)
        )
        unaccounted = copy.deepcopy(committed_summary)
        unaccounted["base_execution"]["default_outcome"] = "not_run"
        rehash_execution(unaccounted)
        checks["base_execution_unaccounted_default_rejected"] = any(
            "default_outcome must be passed" in error for error in base_execution_errors(unaccounted)
        )
        raw_sha_tamper = copy.deepcopy(committed_summary)
        raw_sha_tamper["base_execution"]["raw_result_sha256"] = "0" * 64
        rehash_execution(raw_sha_tamper)
        checks["base_execution_resigned_raw_sha_rejected"] = any(
            "raw result SHA-256 does not match immutable capture authority" in error
            for error in base_execution_errors(raw_sha_tamper)
        )
        raw_path_tamper = copy.deepcopy(committed_summary)
        raw_path_tamper["base_execution"]["raw_result_path"] = "sha256:" + "0" * 64
        rehash_execution(raw_path_tamper)
        checks["base_execution_resigned_raw_path_rejected"] = any(
            "raw result reference does not match immutable capture authority" in error
            for error in base_execution_errors(raw_path_tamper)
        )
        timestamp_tamper = copy.deepcopy(committed_summary)
        timestamp_tamper["base_execution"]["started_at"] = "2026-08-11T08:17:59.453215Z"
        timestamp_tamper["base_execution"]["ended_at"] = "2026-08-11T08:43:38.174467Z"
        rehash_execution(timestamp_tamper)
        checks["base_execution_resigned_timestamps_rejected"] = any(
            "content_sha256 does not match immutable base execution authority" in error
            for error in base_execution_errors(timestamp_tamper)
        )
        exit_code_tamper = copy.deepcopy(committed_summary)
        exit_code_tamper["base_execution"]["exit_code"] = 0
        rehash_execution(exit_code_tamper)
        checks["base_execution_resigned_exit_code_rejected"] = all(
            any(fragment in error for error in base_execution_errors(exit_code_tamper))
            for fragment in (
                "zero exit_code contradicts failed/error phase outcomes",
                "content_sha256 does not match immutable base execution authority",
            )
        )
        phase_removal_tamper = copy.deepcopy(committed_summary)
        phase_removal_tamper["base_execution"]["phase_errors"] = []
        rehash_execution(phase_removal_tamper)
        checks["base_execution_resigned_phase_removal_rejected"] = any(
            "content_sha256 does not match immutable base execution authority" in error
            for error in base_execution_errors(phase_removal_tamper)
        )
        duplicate_phase_tamper = copy.deepcopy(committed_summary)
        duplicate_phase_tamper["base_execution"]["phase_errors"].append(
            copy.deepcopy(duplicate_phase_tamper["base_execution"]["phase_errors"][0])
        )
        rehash_execution(duplicate_phase_tamper)
        checks["base_execution_resigned_duplicate_phase_rejected"] = all(
            any(fragment in error for error in base_execution_errors(duplicate_phase_tamper))
            for fragment in (
                "duplicate node/phase record",
                "content_sha256 does not match immutable base execution authority",
            )
        )
        identity_tamper = copy.deepcopy(committed_summary)
        phase_error_nodes = {
            row["nodeid"] for row in identity_tamper["base_execution"]["phase_errors"]
        }
        replaced_failed = next(
            nodeid for nodeid in identity_tamper["base_execution"]["outcome_overrides"]["failed"]
            if nodeid not in phase_error_nodes
        )
        overridden_nodes = {
            nodeid
            for nodeids in identity_tamper["base_execution"]["outcome_overrides"].values()
            for nodeid in nodeids
        }
        replacement_passed = next(nodeid for nodeid in committed_nodeids if nodeid not in overridden_nodes)
        failed_nodes = identity_tamper["base_execution"]["outcome_overrides"]["failed"]
        failed_nodes[failed_nodes.index(replaced_failed)] = replacement_passed
        failed_nodes.sort()
        detail = next(
            row for row in identity_tamper["base_execution"]["outcome_details"]
            if row["nodeid"] == replaced_failed
        )
        detail["nodeid"] = replacement_passed
        identity_tamper["base_execution"]["outcome_details"].sort(key=lambda row: row["nodeid"])
        rehash_execution(identity_tamper)
        checks["base_execution_resigned_failed_identity_rejected"] = any(
            "content_sha256 does not match immutable base execution authority" in error
            for error in base_execution_errors(identity_tamper)
        )

        combined_bypass = copy.deepcopy(committed_positive)
        combined_bypass["candidate"]["observations"][0]["nodeid"] = "tests/not-in-census.py::test_fabricated"
        combined_bypass["candidate"]["route_memberships"][0]["route_id"] = "does-not-exist"
        combined_bypass["evidence"]["authority_evidence"] = [{}]
        combined_bypass["evidence"]["routing_evidence"] = [{}]
        combined_bypass_shard = root / "committed-combined-bypass.yaml"
        combined_bypass_shard.write_text(
            yaml.safe_dump({"schema_version": SCHEMA, "dispositions": [combined_bypass]}), encoding="utf-8",
        )
        combined_errors, _ = validate_documents(
            [committed_census_path, committed_workload_path, combined_bypass_shard], dt.date(2026, 8, 10),
        )
        checks["combined_relational_bypass_rejected"] = all(
            any(fragment in error for error in combined_errors)
            for fragment in (
                "nodeid absent from census", "nodeid does not belong", "unknown frozen route_id",
                "authority_evidence[0]", "routing_evidence[0]",
            )
        )

        def committed_workload_errors(document: dict[str, Any]) -> list[str]:
            found: list[str] = []
            validate_workload(
                document["frozen_workload_dag"], "committed-workload", found,
                committed_environment_ids,
            )
            return found

        fabricated_owner_workload = copy.deepcopy(committed_workload)
        fabricated_owner_route = copy.deepcopy(
            fabricated_owner_workload["frozen_workload_dag"]["routes"][0]
        )
        fabricated_owner_route.update({
            "id": "fabricated-owner", "argv": ["false"], "cwd": "fabricated-cwd",
            "env": {"FAKE": "1"}, "base_mapping": "fabricated-base",
            "head_mapping": "fabricated-head",
        })
        fabricated_owner_route["memberships"][0]["selector"] = _selector_from_argv(
            fabricated_owner_route["argv"], fabricated_owner_route["environment_id"],
        )
        fabricated_owner_route["provenance"] = {
            "kind": "frozen_command", "repository": "primary",
            "source_commit": TARGET_INVENTORY_SHA,
            "authority_sha256": _sha(_json_bytes(_route_projection(fabricated_owner_route))),
        }
        fabricated_owner_workload["frozen_workload_dag"]["routes"].append(fabricated_owner_route)
        fabricated_owner_errors = committed_workload_errors(fabricated_owner_workload)
        checks["workload_self_signed_unknown_owner_rejected"] = all(
            any(fragment in error for error in fabricated_owner_errors)
            for fragment in ("unknown frozen route id fabricated-owner", "route id universe")
        )
        renamed_route_workload = copy.deepcopy(committed_workload)
        renamed_regression = next(
            route for route in renamed_route_workload["frozen_workload_dag"]["routes"]
            if route["id"] == "regression"
        )
        renamed_regression["id"] = "fabricated-regression"
        renamed_regression["provenance"]["authority_sha256"] = _sha(
            _json_bytes(_route_projection(renamed_regression))
        )
        for edge in renamed_route_workload["frozen_workload_dag"]["edges"]:
            for field in ("from", "to"):
                if edge[field] == "regression":
                    edge[field] = "fabricated-regression"
        renamed_route_errors = committed_workload_errors(renamed_route_workload)
        checks["workload_self_signed_renamed_route_rejected"] = all(
            any(fragment in error for error in renamed_route_errors)
            for fragment in ("unknown frozen route id fabricated-regression", "route id universe")
        )

        valid_route = {
            "id": "route", "argv": ["pytest"], "environment_id": environment_id,
            "base_mapping": "tests/", "head_mapping": "tests/", "cwd": ".", "env": {},
            "memberships": [{
                "role": "owner", "required": True, "events": ["local"],
                "selector": {"paths": [], "markers": [], "ignores": [], "environment_id": environment_id},
            }],
        }
        valid_route["provenance"] = {
            "kind": "frozen_command", "repository": "primary", "source_commit": TARGET_INVENTORY_SHA,
            "authority_sha256": _sha(_json_bytes(_route_projection(valid_route))),
        }
        valid_measurement = {
            "route_id": "route", "environment_id": environment_id, "collection": 1.0, "setup": 2.0,
            "call": 3.0, "wall": 4.0, "compute": 6.0, "outcome": "passed", "artifact_hash": "3" * 64,
        }

        def find_workload_errors(dag: dict[str, Any]) -> list[str]:
            found: list[str] = []
            validate_workload(
                dag, "workload", found, {environment_id},
                frozen_route_authorities={
                    "route": cast(
                        str, cast(dict[str, Any], valid_route["provenance"])["authority_sha256"],
                    ),
                },
            )
            return found

        valid_workload: dict[str, Any] = {
            "routes": [valid_route], "edges": [], "repetitions": 3, "measurements": [valid_measurement],
        }
        checks["valid_typed_measurement"] = find_workload_errors(valid_workload) == []
        local_provenance_mutations = {
            "kind": "fabricated",
            "repository": "sibling-e2e",
            "source_commit": "0" * 40,
            "authority_sha256": "0" * 64,
        }
        for field, bad_value in local_provenance_mutations.items():
            invalid_local_provenance = copy.deepcopy(valid_workload)
            invalid_local_provenance["routes"][0]["provenance"][field] = bad_value
            checks[f"local_provenance_{field}_rejected"] = bool(
                find_workload_errors(invalid_local_provenance)
            )
        workload_field_mutations: dict[str, Callable[[dict[str, Any]], None]] = {
            "argv": lambda route: route.update(argv=["false"]),
            "cwd": lambda route: route.update(cwd="fabricated-cwd"),
            "env": lambda route: route.update(env={"FAKE": "1"}),
            "base_mapping": lambda route: route.update(base_mapping="fabricated-base"),
            "head_mapping": lambda route: route.update(head_mapping="fabricated-head"),
            "role": lambda route: route["memberships"][0].update(role="coverage"),
            "required": lambda route: route["memberships"][0].update(required=False),
            "events": lambda route: route["memberships"][0].update(events=["schedule"]),
            "selector_paths": lambda route: route["memberships"][0]["selector"].update(paths=["tests/fake/"]),
            "selector_markers": lambda route: route["memberships"][0]["selector"].update(markers=["fake"]),
            "selector_ignores": lambda route: route["memberships"][0]["selector"].update(ignores=["tests/fake.py"]),
            "selector_environment": lambda route: route["memberships"][0]["selector"].update(environment_id="missing"),
        }
        for field, mutate in workload_field_mutations.items():
            invalid_workload = copy.deepcopy(valid_workload)
            mutate(invalid_workload["routes"][0])
            checks[f"workload_{field}_authority_rejected"] = any(
                "authority_sha256 does not bind complete route" in error
                for error in find_workload_errors(invalid_workload)
            )

        committed_environment_ids = {
            cast(str, environment["id"]) for environment in committed_workload["run_environments"]
        }
        regression_route = next(
            route for route in committed_workload["frozen_workload_dag"]["routes"]
            if route["id"] == "regression"
        )

        def ci_route_errors(route: dict[str, Any]) -> list[str]:
            found: list[str] = []
            validate_workload(
                {"routes": [route], "edges": [], "repetitions": 3, "measurements": []},
                "ci-workload", found, committed_environment_ids,
                frozen_route_authorities={"regression": FROZEN_ROUTE_AUTHORITY_HASHES["regression"]},
            )
            return found

        checks["valid_tracked_ci_provenance"] = ci_route_errors(copy.deepcopy(regression_route)) == []
        provenance_mutations = {
            "kind": "frozen_command",
            "source_commit": "0" * 40,
            "source_path": ".github/workflows/fabricated.yml",
            "source_sha256": "0" * 64,
            "job_id": "fabricated-job",
            "step_name": "fabricated step",
            "step_sha256": "0" * 64,
            "authority_sha256": "0" * 64,
        }
        for field, bad_value in provenance_mutations.items():
            invalid_ci = copy.deepcopy(regression_route)
            invalid_ci["provenance"][field] = bad_value
            checks[f"ci_provenance_{field}_rejected"] = bool(ci_route_errors(invalid_ci))
        fabricated_ci_command = copy.deepcopy(regression_route)
        fabricated_ci_command["argv"] = ["python", "-m", "pytest", "tests/fabricated.py", "-q"]
        fabricated_ci_command["memberships"][0]["selector"] = _selector_from_argv(
            fabricated_ci_command["argv"], fabricated_ci_command["environment_id"],
        )
        fabricated_ci_command["provenance"]["authority_sha256"] = _sha(
            _json_bytes(_route_projection(fabricated_ci_command))
        )
        checks["ci_recomputed_hash_fabricated_command_rejected"] = any(
            "unique tracked pytest command" in error for error in ci_route_errors(fabricated_ci_command)
        )
        fabricated_ci_required = copy.deepcopy(regression_route)
        fabricated_ci_required["memberships"][0]["required"] = False
        fabricated_ci_required["provenance"]["authority_sha256"] = _sha(
            _json_bytes(_route_projection(fabricated_ci_required))
        )
        checks["ci_recomputed_hash_required_rejected"] = any(
            "required does not match quality-gate.needs" in error for error in ci_route_errors(fabricated_ci_required)
        )
        fabricated_ci_events = copy.deepcopy(regression_route)
        fabricated_ci_events["memberships"][0]["events"] = ["schedule"]
        fabricated_ci_events["provenance"]["authority_sha256"] = _sha(
            _json_bytes(_route_projection(fabricated_ci_events))
        )
        checks["ci_recomputed_hash_events_rejected"] = any(
            "events do not match tracked job triggers" in error for error in ci_route_errors(fabricated_ci_events)
        )
        quarantine_environment_id = next(
            cast(str, route["environment_id"])
            for route in committed_workload["frozen_workload_dag"]["routes"]
            if route["id"] == "quarantine"
        )

        def mutate_ci_environment(route: dict[str, Any]) -> None:
            route.update(environment_id=quarantine_environment_id)
            route["memberships"][0]["selector"].update(environment_id=quarantine_environment_id)

        recomputed_ci_mutations: dict[str, tuple[Callable[[dict[str, Any]], None], tuple[str, ...]]] = {
            "role": (
                lambda route: route["memberships"][0].update(role="coverage"),
                ("pinned frozen route",),
            ),
            "selector_paths": (
                lambda route: route["memberships"][0]["selector"].update(paths=["tests/fabricated/"]),
                ("pinned frozen route", "selector does not match tracked argv"),
            ),
            "selector_markers": (
                lambda route: route["memberships"][0]["selector"].update(markers=["fabricated"]),
                ("pinned frozen route", "selector does not match tracked argv"),
            ),
            "selector_ignores": (
                lambda route: route["memberships"][0]["selector"].update(ignores=["tests/fabricated.py"]),
                ("pinned frozen route", "selector does not match tracked argv"),
            ),
            "selector_environment": (
                lambda route: route["memberships"][0]["selector"].update(environment_id=quarantine_environment_id),
                ("pinned frozen route", "selector does not match tracked argv"),
            ),
            "cwd": (
                lambda route: route.update(cwd="fabricated-cwd"),
                ("pinned frozen route", "cwd does not match tracked workflow step"),
            ),
            "env": (
                lambda route: route.update(env={"PWHEADLESS": "1", "FABRICATED": "1"}),
                ("pinned frozen route", "env does not match tracked workflow/job/step env"),
            ),
            "base_mapping": (
                lambda route: route.update(base_mapping="fabricated-base"),
                ("pinned frozen route",),
            ),
            "head_mapping": (
                lambda route: route.update(head_mapping="fabricated-head"),
                ("pinned frozen route",),
            ),
            "environment_id": (
                mutate_ci_environment,
                ("pinned frozen route",),
            ),
            "wrapper": (
                lambda route: route.update(wrapper="fabricated wrapper"),
                ("pinned frozen route",),
            ),
        }
        for field, (mutate, fragments) in recomputed_ci_mutations.items():
            invalid_ci_route = copy.deepcopy(regression_route)
            mutate(invalid_ci_route)
            invalid_ci_route["provenance"]["authority_sha256"] = _sha(
                _json_bytes(_route_projection(invalid_ci_route))
            )
            invalid_ci_errors = ci_route_errors(invalid_ci_route)
            checks[f"ci_recomputed_hash_{field}_rejected"] = all(
                any(fragment in error for error in invalid_ci_errors)
                for fragment in fragments
            )
        duplicate_edges = copy.deepcopy(valid_workload)
        duplicate_edges["edges"] = [{"from": "route", "to": "route"}, {"from": "route", "to": "route"}]
        checks["duplicate_dag_edge_rejected"] = any("duplicate dependency edge" in error for error in find_workload_errors(duplicate_edges))
        for field in ("collection", "setup", "call", "wall", "compute"):
            invalid_measurement = copy.deepcopy(valid_workload)
            invalid_measurement["measurements"][0][field] = "1"
            checks[f"measurement_{field}_rejected"] = any(
                "timing fields" in error for error in find_workload_errors(invalid_measurement)
            )
        for field, bad_value, fragment in (
            ("outcome", ["passed"], "invalid outcome"),
            ("artifact_hash", {"sha": "3" * 64}, "artifact_hash must"),
            ("environment_id", "missing", "unknown environment_id"),
            ("route_id", "missing", "unknown route_id"),
        ):
            invalid_measurement = copy.deepcopy(valid_workload)
            invalid_measurement["measurements"][0][field] = bad_value
            checks[f"measurement_{field}_rejected"] = any(
                fragment in error for error in find_workload_errors(invalid_measurement)
            )

        universe = {
            "manifests": {
                "inert_candidates": [{"member": "tests/test_a.py::test_inert"}],
                "exact_body_groups": [{"members": [{"member": "tests/test_b.py::test_exact"}]}],
                "promoted_semantic_groups": [{"members": [{"member": "tests/test_c.py::test_promoted"}]}],
                "scanner_candidates": [{"member": "tests/test_scanner.py"}],
            },
        }
        universe_members = {
            "tests/test_a.py::test_inert": {"WP-A"},
            "tests/test_b.py::test_exact": {"WP-B"},
            "tests/test_c.py::test_promoted": {"WP-C"},
        }

        def universe_errors(
            member_owners: Mapping[str, set[str]], path_owners: Mapping[str, set[str]],
        ) -> list[str]:
            found: list[str] = []
            _validate_candidate_universe(universe, member_owners, {}, path_owners, found)
            return found

        checks["candidate_universe_complete_positive"] = not universe_errors(
            universe_members, {"tests/test_scanner.py": {"WP-S"}},
        )
        omitted_universe = dict(universe_members)
        del omitted_universe["tests/test_b.py::test_exact"]
        checks["candidate_universe_omission_rejected"] = any(
            "exact missing terminal coverage" in error
            for error in universe_errors(omitted_universe, {"tests/test_scanner.py": {"WP-S"}})
        )
        substituted_universe = dict(omitted_universe)
        substituted_universe["tests/test_b.py::test_substituted"] = {"WP-B"}
        checks["candidate_universe_substitution_rejected"] = any(
            "exact missing terminal coverage" in error
            for error in universe_errors(substituted_universe, {"tests/test_scanner.py": {"WP-S"}})
        )
        duplicated_universe = dict(universe_members)
        duplicated_universe["tests/test_b.py::test_exact"] = {"WP-B", "WP-X"}
        checks["candidate_universe_duplicate_owner_rejected"] = any(
            "duplicated/mixed-grain coverage" in error
            for error in universe_errors(duplicated_universe, {"tests/test_scanner.py": {"WP-S"}})
        )
        checks["candidate_universe_scanner_duplicate_rejected"] = any(
            "scanner paths span multiple terminal shards" in error
            for error in universe_errors(universe_members, {"tests/test_scanner.py": {"WP-S", "WP-X"}})
        )

        normalization_path = report_root / "raw" / "legacy-shard-normalization.yaml"
        normalization_record = cast(dict[str, Any], yaml.safe_load(normalization_path.read_text(encoding="utf-8")))
        normalization_documents: list[tuple[Path, dict[str, Any]]] = [(normalization_path, normalization_record)]
        for source_authority in cast(list[dict[str, str]], normalization_record["source_documents"]):
            source_path = Path(source_authority["path"])
            normalization_documents.append(
                (source_path, cast(dict[str, Any], yaml.safe_load(source_path.read_text(encoding="utf-8"))))
            )
        normalization_content_tamper = copy.deepcopy(normalization_record)
        normalization_content_tamper["content_sha256"] = "0" * 64
        normalization_content_errors: list[str] = []
        _validate_normalization_authority(
            normalization_path, normalization_content_tamper, normalization_documents,
            normalization_content_errors,
        )
        checks["normalization_content_hash_tamper_rejected"] = any(
            "normalization content_sha256 mismatch" in error for error in normalization_content_errors
        )
        normalization_source_tamper = copy.deepcopy(normalization_record)
        normalization_source_tamper["source_documents"][0]["sha256"] = "0" * 64
        normalization_source_body = dict(normalization_source_tamper)
        normalization_source_body.pop("content_sha256", None)
        normalization_source_tamper["content_sha256"] = _sha(_json_bytes(normalization_source_body))
        normalization_source_errors: list[str] = []
        _validate_normalization_authority(
            normalization_path, normalization_source_tamper, normalization_documents,
            normalization_source_errors,
        )
        checks["normalization_source_hash_tamper_rejected"] = any(
            "content-addressed source drift" in error for error in normalization_source_errors
        )

        head_provenance_tamper = copy.deepcopy(committed_census)
        head_commit = _git_rev_parse("HEAD")
        head_provenance_tamper["inventory"] = {
            "role": "head", "commit": head_commit, "target_commit": head_commit,
            "tests_tree": "0" * 40,
        }
        head_provenance_errors: list[str] = []
        validate_census(head_provenance_tamper, head_provenance_errors)
        checks["head_tests_tree_tamper_rejected"] = any(
            "HEAD tests_tree does not match recorded commit" in error for error in head_provenance_errors
        )
        if not all(checks.values()):
            raise AuditError("selftest failures: " + ", ".join(key for key, value in checks.items() if not value))
        return {"valid": True, "checks": checks}


def _write(path: Path | None, value: Any, yaml_output: bool = False) -> None:
    text = yaml.safe_dump(_stable(value), sort_keys=True, allow_unicode=True) if yaml_output else _json_bytes(value).decode()
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def _md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _closure_authority(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise AuditError(f"cannot load closure authority: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != "test-sanitation-closure/v1":
        raise AuditError("closure authority schema mismatch")
    body = dict(data)
    expected = body.pop("content_sha256", None)
    if not _hash_value(expected) or expected != _sha(_json_bytes(body)):
        raise AuditError("closure authority content_sha256 mismatch")
    required = {
        "mission", "evidence_commit", "generated_at", "environment", "artifacts",
        "inventory", "dispositions", "performance", "known_red_diff", "gates",
        "platforms", "fresh_starts", "issues", "criteria", "review",
    }
    if not required <= set(data):
        raise AuditError(f"closure authority missing fields: {sorted(required - set(data))}")
    for field in ("issues", "criteria", "gates", "platforms", "fresh_starts"):
        if not isinstance(data[field], list):
            raise AuditError(f"closure authority {field} must be a list")
    issue_ids = [row.get("issue") for row in data["issues"] if isinstance(row, dict)]
    expected_issues = {"#1931", "#2309", "#2316", "#2342", "#2645", "#2782", "#3184", "#3283", "#3284"}
    if set(issue_ids) != expected_issues or len(issue_ids) != len(expected_issues):
        raise AuditError("closure authority must terminalize all nine exact issue ids once")
    criterion_ids = [row.get("criterion_id") for row in data["criteria"] if isinstance(row, dict)]
    if len(criterion_ids) != len(set(criterion_ids)) or not criterion_ids:
        raise AuditError("closure authority criteria must have unique nonempty ids")
    return data


def _render_issue_matrix(data: Mapping[str, Any]) -> str:
    lines = [
        "---", "doc_status: active", f"updated: '{str(data['generated_at'])[:10]}'", "---", "",
        "# Test Sanitation Issue Matrix", "",
        f"Generated from content-addressed closure authority for `{data['evidence_commit']}`.", "",
        "| Issue | Tracker state | Mission verdict | Evidence | Owner | Follow-up |", "|---|---|---|---|---|---|",
    ]
    for row in cast(list[dict[str, Any]], data["issues"]):
        lines.append("| " + " | ".join(_md_cell(row[field]) for field in (
            "issue", "tracker_state", "verdict", "evidence", "owner", "follow_up",
        )) + " |")
    lines.extend(["", "Tracker state is current metadata, not the verdict authority; evidence determines each terminal mission action.", ""])
    return "\n".join(lines)


def _render_workflow_evidence(data: Mapping[str, Any]) -> str:
    lines = [
        "---", "doc_status: active", f"updated: '{str(data['generated_at'])[:10]}'", "---", "",
        "# Test Sanitation Workflow Evidence", "",
        f"Evidence commit: `{data['evidence_commit']}`  ",
        f"Environment: {_md_cell(data['environment'])}", "",
        "## Repository and cross-repository gates", "",
        "| Gate | Command | Result | Duration | Exit | Artifact |", "|---|---|---|---:|---:|---|",
    ]
    for row in cast(list[dict[str, Any]], data["gates"]):
        lines.append("| " + " | ".join(_md_cell(row[field]) for field in (
            "name", "command", "result", "duration_seconds", "exit_code", "artifact",
        )) + " |")
    lines.extend(["", "## Integrated platform evidence", "", "| Platform | Workflow/job | Commit | Result | URL |", "|---|---|---|---|---|"])
    for row in cast(list[dict[str, Any]], data["platforms"]):
        lines.append("| " + " | ".join(_md_cell(row[field]) for field in (
            "platform", "job", "commit", "result", "url",
        )) + " |")
    lines.extend(["", "## Fresh-clone starts", "", "| Run | Commit | Publication/body proof | Result | Artifact |", "|---:|---|---|---|---|"])
    for row in cast(list[dict[str, Any]], data["fresh_starts"]):
        lines.append("| " + " | ".join(_md_cell(row[field]) for field in (
            "run", "commit", "body_proof", "result", "artifact",
        )) + " |")
    lines.append("")
    return "\n".join(lines)


def _render_final_report(data: Mapping[str, Any]) -> str:
    inventory = cast(dict[str, Any], data["inventory"])
    dispositions = cast(dict[str, Any], data["dispositions"])
    performance = cast(dict[str, Any], data["performance"])
    known_red = cast(dict[str, Any], data["known_red_diff"])
    review = cast(dict[str, Any], data["review"])
    lines = [
        "---", "doc_status: active", f"updated: '{str(data['generated_at'])[:10]}'", "---", "",
        "# Assertive Test-Suite Sanitation — Final Report", "",
        f"Closure state: **{data.get('closure_state', 'unknown')}**  ",
        f"Evidence commit: `{data['evidence_commit']}`  ",
        f"Generated: `{data['generated_at']}`", "",
        "## Outcome", "",
        str(data.get("outcome", "")), "",
        "## Before / after inventory", "",
        "| Metric | Repaired planning base | Integrated HEAD | Delta |", "|---|---:|---:|---:|",
    ]
    for metric in ("python_test_files", "source_units", "collected_nodes", "python_test_loc", "exact_duplicate_groups", "inert_candidates", "scanner_candidates"):
        row = cast(dict[str, Any], inventory[metric])
        lines.append(f"| {metric} | {row['base']} | {row['head']} | {row['delta']} |")
    lines.extend([
        "", "## Terminal disposition ledger", "",
        f"The generated aggregate contains **{dispositions['rows']}** rows over **{dispositions['unique_members']}** unique identities: "
        f"{dispositions['verdicts']}. No `FIX_*`, `TEMPORARY`, expired, renewed, ambiguous, or unowned frozen candidate remains.", "",
        f"Aggregate SHA-256: `{cast(dict[str, Any], data['artifacts'])['aggregate_sha256']}`  ",
        f"HEAD census SHA-256: `{cast(dict[str, Any], data['artifacts'])['head_census_sha256']}`", "",
        "## Performance criteria", "",
        "| Measure | Base | HEAD | Change | Verdict |", "|---|---:|---:|---:|---|",
    ])
    for row in cast(list[dict[str, Any]], performance["measurements"]):
        lines.append("| " + " | ".join(_md_cell(row[field]) for field in ("measure", "base", "head", "change", "verdict")) + " |")
    lines.extend(["", str(performance["summary"]), "", "## Repaired-base vs integrated-HEAD outcomes", "", str(known_red["summary"]), ""])
    for label in ("resolved", "shared", "head_only"):
        lines.append(f"- **{label}:** {_md_cell(known_red[label])}")
    lines.extend(["", "## Acceptance criteria", "", "| Criterion | Result | Evidence / rationale |", "|---|---|---|"])
    for row in cast(list[dict[str, Any]], data["criteria"]):
        lines.append(f"| {_md_cell(row['criterion_id'])} | {_md_cell(row['pass_fail'])} | {_md_cell(row['notes'])} |")
    lines.extend([
        "", "## Workflow deviations and review", "",
        f"- Review cap: {review['review_cycle_cap']}; fourth cycles prohibited and not opened.",
        f"- Arbiter normalization: {review['normalization']}.",
        f"- Independent WP approvals: {review['independent_approvals']}.",
        f"- Remaining closure blockers: {review['blockers']}.", "",
        "See `issue-matrix.md` and `workflow-evidence.md` for terminal issue and gate details.", "",
    ])
    return "\n".join(lines)


def render_closure(
    authority: Path, report_output: Path, issue_output: Path,
    mission_issue_output: Path, acceptance_output: Path, workflow_output: Path,
) -> dict[str, Any]:
    data = _closure_authority(authority)
    report = _render_final_report(data)
    issue = _render_issue_matrix(data)
    workflow = _render_workflow_evidence(data)
    acceptance = {
        "mission_slug": data["mission"], "mission_number": "",
        "mission_type": "software-dev", "overall_verdict": data.get("overall_verdict", "pending"),
        "criteria": data["criteria"], "negative_invariants": data.get("negative_invariants", []),
    }
    for path, text_value in (
        (report_output, report), (issue_output, issue),
        (mission_issue_output, issue), (workflow_output, workflow),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text_value, encoding="utf-8")
    _write(acceptance_output, acceptance)
    return {
        "valid": True,
        "outputs": {
            str(path): _sha(path.read_bytes())
            for path in (report_output, issue_output, mission_issue_output, acceptance_output, workflow_output)
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snap = commands.add_parser("snapshot")
    snap.add_argument("--root", type=Path, default=Path.cwd())
    snap.add_argument("--tests", "--tests-path", dest="tests_path", default="tests")
    snap.add_argument("--inventory-sha")
    snap.add_argument("--census-role", choices=sorted(CENSUS_ROLES), default="base")
    snap.add_argument("--output", type=Path)
    snap.add_argument("pytest_args", nargs=argparse.REMAINDER)
    val = commands.add_parser("validate")
    val.add_argument("paths", nargs="+", type=Path)
    val.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    val.add_argument("--output", type=Path)
    agg = commands.add_parser("aggregate")
    agg.add_argument("paths", nargs="+", type=Path)
    agg.add_argument("--output", type=Path)
    capture = commands.add_parser("capture-outcomes")
    capture.add_argument("census", type=Path)
    capture.add_argument("workload", type=Path)
    capture.add_argument("--root", type=Path, default=Path.cwd())
    capture.add_argument("--route", default="full-parallel")
    capture.add_argument("--raw-output", type=Path, required=True)
    capture.add_argument("--output", type=Path, required=True)
    closure = commands.add_parser("render-closure")
    closure.add_argument("authority", type=Path)
    closure.add_argument("--report-output", type=Path, required=True)
    closure.add_argument("--issue-output", type=Path, required=True)
    closure.add_argument("--mission-issue-output", type=Path, required=True)
    closure.add_argument("--acceptance-output", type=Path, required=True)
    closure.add_argument("--workflow-output", type=Path, required=True)
    commands.add_parser("selftest")
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            result = snapshot(
                args.root, args.tests_path, args.pytest_args, args.inventory_sha,
                args.census_role,
            )
            reconciliation = result["reconciliation"]
            ownership = result["ownership"]
            if not reconciliation["complete"] or not ownership["complete"]:
                raise AuditError(
                    "snapshot incomplete: "
                    f"unreconciled_nodes={len(reconciliation['unreconciled_or_duplicate_nodes'])}; "
                    f"unowned_candidates={len(ownership['unowned'])}; "
                    f"unreconciled_sample={reconciliation['unreconciled_or_duplicate_nodes'][:5]}; "
                    f"unowned_sample={ownership['unowned'][:5]}"
                )
            _write(args.output, result)
        elif args.command == "validate":
            errors, summary = validate_documents(args.paths, args.today)
            result = {"valid": not errors, "errors": errors, **summary}
            _write(args.output, result)
            return 0 if not errors else 1
        elif args.command == "aggregate":
            result = aggregate(args.paths)
            errors, _ = validate_documents(args.paths, dt.date.today())
            if errors:
                raise AuditError("aggregate inputs invalid: " + "; ".join(errors))
            _write(args.output, result, yaml_output=True)
        elif args.command == "capture-outcomes":
            result = capture_outcomes(
                args.root, args.census, args.workload, args.route, args.raw_output,
            )
            _write(args.output, result)
        elif args.command == "render-closure":
            _write(None, render_closure(
                args.authority, args.report_output, args.issue_output,
                args.mission_issue_output, args.acceptance_output, args.workflow_output,
            ))
        else:
            _write(None, selftest())
    except AuditError as exc:
        print(f"audit: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
