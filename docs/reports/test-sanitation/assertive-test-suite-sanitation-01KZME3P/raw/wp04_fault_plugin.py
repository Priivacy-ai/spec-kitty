"""Replayable live-authority fault injection for WP04 causal probes.

Loaded only by ``wp04-replay.py``. Each selected test reaches its normal Act;
the production binding/property/constant named in ``wp04-replay-spec.json`` is
temporarily replaced for that one call phase, then restored exactly.
"""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any
from collections.abc import Callable

import pytest


_SPEC = json.loads(Path(__file__).with_name("wp04-replay-spec.json").read_text())
_CAMPAIGN = os.environ.get("WP04_REPLAY_CAMPAIGN", "")
_ACTIONS = {entry["nodeid"]: entry for entry in _SPEC["campaigns"].get(_CAMPAIGN, [])}


def _fault(*_args: Any, **_kwargs: Any) -> None:
    raise AssertionError("WP04_REPLAY_FAULT: live authority perturbed")


async def _async_fault(*_args: Any, **_kwargs: Any) -> None:
    raise AssertionError("WP04_REPLAY_FAULT: live async authority perturbed")


def _matching_action(nodeid: str) -> dict[str, Any] | None:
    matches = [entry for prefix, entry in _ACTIONS.items() if nodeid == prefix or nodeid.startswith(prefix + "[")]
    if len(matches) > 1:
        raise AssertionError(f"ambiguous WP04 replay mapping for {nodeid}")
    return matches[0] if matches else None


def _resolve(module: ModuleType, dotted: str) -> tuple[Any, str]:
    parts = dotted.split(".")
    owner: Any = module
    for part in parts[:-1]:
        owner = getattr(owner, part)
    return owner, parts[-1]


def _replace_attr(owner: Any, name: str, value: Any) -> Callable[[], None]:
    original = inspect.getattr_static(owner, name) if inspect.isclass(owner) else getattr(owner, name)
    setattr(owner, name, value)

    def undo() -> None:
        setattr(owner, name, original)

    return undo


def _apply(item: pytest.Item, action: dict[str, Any]) -> Callable[[], None]:
    kind = action["kind"]
    if kind == "binding":
        owner, name = _resolve(item.module, action["binding"])
        original = getattr(owner, name)
        replacement = _async_fault if inspect.iscoroutinefunction(original) else _fault
        return _replace_attr(owner, name, replacement)
    if kind == "property":
        owner, name = _resolve(item.module, action["binding"])
        return _replace_attr(owner, name, property(lambda _self: _fault()))
    if kind == "value":
        owner, name = _resolve(item.module, action["binding"])
        return _replace_attr(owner, name, tuple(action["value"]))
    if kind == "module_present":
        module_name = action["module"]
        sentinel = ModuleType(module_name)
        original = sys.modules.get(module_name)
        sys.modules[module_name] = sentinel

        def undo() -> None:
            if original is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = original

        return undo
    if kind == "reload_export":
        original_reload = item.module.importlib.reload

        def faulty_reload(module: ModuleType) -> SimpleNamespace:
            original_reload(module)
            return SimpleNamespace(MissionStepInput=object())

        item.module.importlib.reload = faulty_reload

        def undo() -> None:
            item.module.importlib.reload = original_reload

        return undo
    raise AssertionError(f"unknown WP04 replay action: {kind}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):
    action = _matching_action(item.nodeid)
    undo = _apply(item, action) if action else None
    try:
        yield
    finally:
        if undo is not None:
            undo()


def pytest_collection_finish(session: pytest.Session) -> None:
    selected = [item.nodeid for item in session.items]
    missing = [prefix for prefix in _ACTIONS if not any(node == prefix or node.startswith(prefix + "[") for node in selected)]
    if missing:
        raise pytest.UsageError(f"WP04 replay selected-node mapping missing from collection: {missing}")
