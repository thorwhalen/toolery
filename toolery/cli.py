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


def skills(root, query="", *, limit=10):
    """List (or, with QUERY, search) Claude Agent Skills (SKILL.md) under ROOT."""
    from . import harvest
    from .catalog import catalog

    cat = catalog(harvest.skills(root))
    pairs = (
        [(c, 1.0) for c in cat.cards] if not query else cat.search(query, limit=limit)
    )
    for card, _score in pairs[:limit]:
        blurb = card.description[:88] + ("…" if len(card.description) > 88 else "")
        print(f"{card.name}  —  {blurb}")


_dispatch_funcs = [search, skills]


if __name__ == "__main__":
    import argh

    argh.dispatch_commands(_dispatch_funcs)
