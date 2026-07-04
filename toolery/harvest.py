"""Harvesters: turn a source of raw assets into normalized :class:`~toolery.base.Card` s.

A *harvester* is any iterable of ``Card`` s. Built-in harvesters cover the most
common corpora:

- :func:`folder` — any tree of markdown/text documents (the general case).
- :func:`skills` — Claude Agent Skills (``SKILL.md`` with YAML frontmatter).

New asset kinds (agent specs, MCP tool schemas, packages) are added by writing
another generator that yields ``Card`` s — nothing else in the stack changes.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from .base import Card

_FM_KEY = re.compile(r"^([A-Za-z0-9_-]+)\s*:(.*)$")
_FOLD = {">", ">-", "|", "|-", ""}


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split ``---`` YAML frontmatter from a document body (minimal, dep-free).

    Handles simple ``key: value`` and folded (``key: >``) scalars — enough for
    the ``name``/``description`` an asset card needs.

    >>> meta, body = _parse_frontmatter('---\\nname: foo\\ndescription: does foo\\n---\\nBody')
    >>> meta['name'], meta['description'], body.strip()
    ('foo', 'does foo', 'Body')
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block, body = text[3:end], text[end + 4 :]
    meta: dict[str, str] = {}
    key: str | None = None
    buf: list[str] = []
    for line in block.splitlines():
        m = _FM_KEY.match(line)
        if m and not line[0].isspace():
            if key is not None:
                meta[key] = " ".join(buf).strip()
            key, raw = m.group(1).strip(), m.group(2).strip()
            buf = [] if raw in _FOLD else [raw.strip("'\"")]
        elif key is not None and line.strip():
            buf.append(line.strip())
    if key is not None:
        meta[key] = " ".join(buf).strip()
    return meta, body


def _title_and_blurb(text: str, *, fallback: str) -> tuple[str, str]:
    """Derive a name and a short description from a markdown/text document."""
    meta, body = _parse_frontmatter(text)
    name = meta.get("name")
    desc = meta.get("description")
    lines = body.splitlines()
    if not name:
        for line in lines:
            if line.startswith("#"):
                name = line.lstrip("#").strip()
                break
        name = name or next((l.strip() for l in lines if l.strip()), fallback)
    if not desc:
        para: list[str] = []
        for line in lines:
            if line.startswith("#") or not line.strip():
                if para:
                    break
                continue
            para.append(line.strip())
            if sum(map(len, para)) > 240:
                break
        desc = " ".join(para)[:400]
    return name or fallback, desc or ""


def folder(root, *, kind: str = "doc", pattern: str = "**/*.md") -> Iterator[Card]:
    """Harvest markdown/text documents under ``root`` into cards.

    The card ``id`` is the path relative to ``root``; ``name`` and ``description``
    are read from frontmatter when present, else derived from the first heading
    and paragraph. ``pattern`` is a :meth:`pathlib.Path.glob` pattern (recursive
    by default via ``**``).
    """
    root = Path(root).expanduser()
    for path in sorted(root.glob(pattern)):
        if not path.is_file():
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        name, desc = _title_and_blurb(text, fallback=path.stem)
        yield Card(
            id=str(path.relative_to(root)),
            kind=kind,
            name=name,
            description=desc,
            source_uri=str(path),
            content_ref=str(path),
        )


def skills(root, *, kind: str = "skill") -> Iterator[Card]:
    """Harvest Claude Agent Skills (``SKILL.md`` files) under ``root`` into cards."""
    root = Path(root).expanduser()
    for skill_md in sorted(root.rglob("SKILL.md")):
        try:
            meta, _ = _parse_frontmatter(skill_md.read_text(errors="ignore"))
        except OSError:
            continue
        name = meta.get("name") or skill_md.parent.name
        tools = meta.get("allowed-tools", "")
        tags = tuple(t.strip() for t in tools.split(",") if t.strip())
        yield Card(
            id=name,
            kind=kind,
            name=name,
            description=meta.get("description", ""),
            tags=tags,
            source_uri=str(skill_md),
            content_ref=str(skill_md),
            extra={k: v for k, v in meta.items() if k not in {"name", "description"}},
        )


def agents(root, *, kind="agent"):
    """Harvest Claude Code subagent specs (``.claude/agents/*.md``) under ``root``.

    Agent specs declare a YAML-frontmatter ``name``; ``.md`` files without one are
    skipped. Pass a project root (finds ``**/agents/*.md``) or an ``agents`` dir directly.
    """
    root = Path(root).expanduser()
    paths = set(root.glob("*.md")) if root.name == "agents" else set()
    paths |= set(root.glob("**/agents/*.md"))
    for path in sorted(paths):
        try:
            meta, _ = _parse_frontmatter(path.read_text(errors="ignore"))
        except OSError:
            continue
        name = meta.get("name")
        if not name:
            continue
        tags = tuple(t.strip() for t in meta.get("tools", "").split(",") if t.strip())
        yield Card(
            id=name,
            kind=kind,
            name=name,
            description=meta.get("description", ""),
            tags=tags,
            source_uri=str(path),
            content_ref=str(path),
            extra={k: v for k, v in meta.items() if k not in {"name", "description"}},
        )


_PROJECT_SECTION = re.compile(r"(?ms)^\[project\]\s*(.*?)(?=^\[|\Z)")


def _project_meta(pyproject: Path) -> tuple[str, str]:
    """``(name, description)`` from a ``pyproject.toml`` (tomllib, else regex + README)."""
    try:
        text = pyproject.read_text(errors="ignore")
    except OSError:
        return "", ""
    name = desc = ""
    try:
        import tomllib

        proj = tomllib.loads(text).get("project", {})
        name, desc = proj.get("name") or "", proj.get("description") or ""
    except Exception:
        pass
    if not name:  # py3.10 has no tomllib, or a non-PEP621 layout
        section = _PROJECT_SECTION.search(text)
        scope = section.group(1) if section else text

        def scalar(key):
            m = re.search(rf'(?m)^{key}\s*=\s*["\']([^"\']*)["\']', scope)
            return m.group(1) if m else ""

        name, desc = scalar("name"), scalar("description")
    if name and not desc:  # fall back to the README's first paragraph
        readme = pyproject.parent / "README.md"
        if readme.is_file():
            _, desc = _title_and_blurb(readme.read_text(errors="ignore"), fallback=name)
    return name, desc


def packages(root, *, kind="package"):
    """Harvest Python packages (dirs with a ``pyproject.toml``) under ``root``.

    Scans ``root/pyproject.toml`` and ``root/*/pyproject.toml`` (the common
    folder-of-packages layout); name/description come from the ``[project]`` table.
    """
    root = Path(root).expanduser()
    seen: set[str] = set()
    pyprojects = sorted({*root.glob("pyproject.toml"), *root.glob("*/pyproject.toml")})
    for pyproject in pyprojects:
        name, desc = _project_meta(pyproject)
        if not name or name in seen:
            continue
        seen.add(name)
        yield Card(
            id=name,
            kind=kind,
            name=name,
            description=desc,
            source_uri=str(pyproject.parent),
            content_ref=str(pyproject),
        )


def mcp(source, *, kind="mcp"):
    """Harvest configured MCP servers from an MCP config (``.mcp.json`` or similar).

    ``source`` may be the config file itself or a directory containing a ``.mcp.json``.
    """
    import json

    path = Path(source).expanduser()
    if path.is_dir():
        for candidate in (".mcp.json", ".cursor/mcp.json", "mcp.json"):
            if (path / candidate).is_file():
                path = path / candidate
                break
    try:
        data = json.loads(path.read_text(errors="ignore"))
    except (OSError, ValueError):
        return
    servers = data.get("mcpServers") or data.get("servers") or {}
    for name, spec in servers.items():
        if isinstance(spec, dict):
            endpoint = spec.get("command") or spec.get("url") or ""
            args = " ".join(spec.get("args", []) or [])
            desc = (spec.get("description") or f"{endpoint} {args}").strip()
        else:
            desc = str(spec)
        yield Card(
            id=name,
            kind=kind,
            name=name,
            description=desc,
            source_uri=str(path),
            content_ref=str(path),
        )
