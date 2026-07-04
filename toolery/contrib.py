"""Convenience presets: build a catalog over your usual asset locations in one call.

General for any user — pass roots explicitly, or keep them in a local config file. To pull
in a custom source (for example a private skill index), list a ``"module:function"``
reference in the config's ``[harvesters] refs``; toolery imports it lazily. Nothing here
hardcodes a personal path, so it stays useful for everyone while you dogfood it on your own
ecosystem: your paths live in ``~/.config/toolery/sources.toml`` on your machine, not in code.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Iterable, Iterator
from pathlib import Path

from . import harvest
from .base import Card
from .catalog import Catalog, catalog


def _existing_roots(roots, *, home, include_home, subdir) -> Iterator[Path]:
    candidates = [Path(r).expanduser() for r in roots]
    if include_home:
        candidates.append(Path(home).expanduser() / subdir)
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key not in seen and path.exists():
            seen.add(key)
            yield path


def claude_skills(*roots, home="~", include_home=True) -> Iterator[Card]:
    """Skill cards from each of ``roots`` and (by default) ``~/.claude``."""
    for root in _existing_roots(
        roots, home=home, include_home=include_home, subdir=".claude"
    ):
        yield from harvest.skills(root)


def claude_agents(*roots, home="~", include_home=True) -> Iterator[Card]:
    """Subagent cards from each of ``roots`` and (by default) ``~/.claude``."""
    for root in _existing_roots(
        roots, home=home, include_home=include_home, subdir=".claude"
    ):
        yield from harvest.agents(root)


def python_packages(*roots) -> Iterator[Card]:
    """Package cards from each root (a folder containing packages)."""
    for root in roots:
        yield from harvest.packages(Path(root).expanduser())


def everything(
    *, home="~", claude_roots=(), package_roots=(), search_backend=None
) -> Catalog:
    """One catalog over your Claude skills + subagents and your Python packages.

    ``claude_roots``/``package_roots`` are extra locations to scan; ``~/.claude`` is
    always included for Claude assets (pass ``home`` to relocate). Supply a
    ``search_backend`` (e.g. ``IrBackend()`` / ``IrFederatedBackend()``) for semantics.
    """
    sources: list[Iterable[Card]] = [
        claude_skills(*claude_roots, home=home),
        claude_agents(*claude_roots, home=home),
    ]
    sources += [python_packages(root) for root in package_roots]
    kw = {} if search_backend is None else {"search_backend": search_backend}
    return catalog(*sources, **kw)


def _default_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "toolery" / "sources.toml"


def _cards_from_ref(ref: str) -> Iterator[Card]:
    """Import a ``"module:function"`` ref and yield its cards (``Card``s or card dicts)."""
    mod_name, _, fn_name = ref.partition(":")
    fn = getattr(importlib.import_module(mod_name), fn_name)
    for item in fn():
        if isinstance(item, Card):
            yield item
        elif isinstance(item, dict):
            ref_path = item.get("path") or item.get("skill_path")
            yield Card(
                id=str(item.get("id") or item.get("name") or ""),
                kind=item.get("kind", "custom"),
                name=item.get("name", ""),
                description=item.get("description", ""),
                tags=tuple(item.get("tags", ())),
                source_uri=item.get("source_uri") or ref_path,
                content_ref=item.get("content_ref") or ref_path,
            )


def from_config(path=None, *, search_backend=None) -> Catalog:
    """Build a catalog from a TOML config of sources.

    Schema (every section optional)::

        [claude]
        roots = ["~/.claude", "~/work/project"]
        [packages]
        roots = ["~/proj/mine", "~/proj/theirs"]
        [harvesters]
        refs = ["mymod:my_cards"]   # "module:function" -> iterable of Card or card dicts

    Your personal paths live in this file on your machine, not in any committed code.
    Reading the config needs Python 3.11+ (``tomllib``).
    """
    path = Path(path).expanduser() if path else _default_config_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"No toolery sources config at {path}. "
            "Create it — see toolery.contrib.from_config for the schema."
        )
    try:
        import tomllib
    except ModuleNotFoundError as e:  # pragma: no cover - Python 3.10 only
        raise RuntimeError(
            "from_config needs Python 3.11+ (tomllib) to read the TOML config."
        ) from e
    cfg = tomllib.loads(path.read_text())
    sources: list[Iterable[Card]] = []
    claude_roots = cfg.get("claude", {}).get("roots", [])
    if claude_roots:
        sources.append(claude_skills(*claude_roots, include_home=False))
        sources.append(claude_agents(*claude_roots, include_home=False))
    for root in cfg.get("packages", {}).get("roots", []):
        sources.append(python_packages(root))
    for ref in cfg.get("harvesters", {}).get("refs", []):
        sources.append(_cards_from_ref(ref))
    kw = {} if search_backend is None else {"search_backend": search_backend}
    return catalog(*sources, **kw)
