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
