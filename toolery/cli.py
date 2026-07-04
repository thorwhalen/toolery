"""Command-line interface for toolery (argh dispatch).

Follows the argh SSOT pattern: functions in ``_dispatch_funcs`` become subcommands.
"""

from __future__ import annotations


def search(query, source, *, kind="doc", limit=10, pattern="**/*.md", semantic=False):
    """Search a folder corpus of documents (SOURCE) for QUERY, ranked best-first.

    With --semantic, use the ir embedding backend (needs ``pip install 'toolery[ir]'``).
    Example: ``toolery search "dedupe csv" ~/notes``
    """
    from .catalog import catalog
    from .harvest import folder
    from .search import lexical_search

    backend = lexical_search
    if semantic:
        from .ir_backend import IrBackend

        backend = IrBackend()
    cat = catalog(folder(source, kind=kind, pattern=pattern), search_backend=backend)
    hits = cat.search(query, limit=limit)
    if not hits:
        print(f"No matches for {query!r} in {source} ({len(cat)} docs scanned).")
        return
    for card, score in hits:
        print(f"{score:6.2f}  [{card.kind}] {card.name}")
        if card.source_uri:
            print(f"          {card.source_uri}")


def _browse(harvester, source, query, limit):
    """List (or search) whatever ``harvester`` yields from ``source``, one line per card."""
    from .catalog import catalog

    cat = catalog(harvester(source))
    pairs = (
        [(c, 1.0) for c in cat.cards] if not query else cat.search(query, limit=limit)
    )
    if not cat:
        print(f"(nothing harvested from {source})")
        return
    for card, _score in pairs[:limit]:
        blurb = card.description[:88] + ("…" if len(card.description) > 88 else "")
        print(f"{card.name}  —  {blurb}")


def skills(root, query="", *, limit=10):
    """List (or, with QUERY, search) Claude Agent Skills (SKILL.md) under ROOT."""
    from . import harvest

    _browse(harvest.skills, root, query, limit)


def agents(root, query="", *, limit=10):
    """List (or search) Claude Code subagent specs (.claude/agents/*.md) under ROOT."""
    from . import harvest

    _browse(harvest.agents, root, query, limit)


def packages(root, query="", *, limit=10):
    """List (or search) Python packages (dirs with pyproject.toml) under ROOT."""
    from . import harvest

    _browse(harvest.packages, root, query, limit)


_dispatch_funcs = [search, skills, agents, packages]


if __name__ == "__main__":
    import argh

    argh.dispatch_commands(_dispatch_funcs)
