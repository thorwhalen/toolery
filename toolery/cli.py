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


def discover(
    query, root, *, limit=10, kinds="skill,agent,doc", embedder="default", persist=False
):
    """Federated semantic search across multiple asset KINDS under ROOT (needs toolery[ir]).

    Harvests each of KINDS (comma-separated: skill,agent,doc,package,mcp), builds one ir
    corpus per kind, and searches them together with RRF fusion + abstention. Example:
    ``toolery discover "parse a pdf" ~/proj --kinds skill,doc,package``
    """
    from . import harvest
    from .catalog import catalog
    from .ir_backend import IrFederatedBackend

    harvesters = {
        "skill": harvest.skills,
        "agent": harvest.agents,
        "doc": harvest.folder,
        "package": harvest.packages,
        "mcp": harvest.mcp,
    }
    sources = [
        harvesters[k.strip()](root) for k in kinds.split(",") if k.strip() in harvesters
    ]
    cat = catalog(
        *sources,
        search_backend=IrFederatedBackend(
            embedder=embedder, persist=persist, name="toolery-discover"
        ),
    )
    hits = cat.search(query, limit=limit)
    if not hits:
        print(
            f"No confident matches for {query!r} in {root} ({len(cat)} assets scanned)."
        )
        return
    for card, score in hits:
        print(f"{score:6.3f}  [{card.kind}] {card.name}")
        if card.source_uri:
            print(f"          {card.source_uri}")


def mine(query, *, config=None, limit=10, semantic=False, persist=False):
    """Search across YOUR configured ecosystem (~/.config/toolery/sources.toml) for QUERY.

    Configure sources once (see toolery.contrib.from_config); with --semantic, search via
    the ir federated backend (needs ``pip install 'toolery[ir]'``); with --persist, reuse
    an on-disk index (incremental across runs — warm it first with ``toolery index``).
    """
    from .contrib import from_config

    backend = None
    if semantic:
        from .ir_backend import IrFederatedBackend

        backend = IrFederatedBackend(persist=persist, name="toolery-mine")
    cat = from_config(config, search_backend=backend)
    hits = cat.search(query, limit=limit)
    if not hits:
        print(f"No matches for {query!r} across your {len(cat)} configured assets.")
        return
    for card, score in hits:
        print(f"{score:6.3f}  [{card.kind}] {card.name}")
        if card.source_uri:
            print(f"          {card.source_uri}")


def index(config=None, *, embedder="default"):
    """Build or refresh the on-disk semantic index for your configured sources.

    Warms ir's persistent index (incremental via the ledger) so later ``toolery mine
    --semantic --persist`` is fast. Needs ``pip install 'toolery[ir]'``.
    """
    from .contrib import from_config
    from .ir_backend import IrFederatedBackend

    backend = IrFederatedBackend(embedder=embedder, persist=True, name="toolery-mine")
    cat = from_config(config, search_backend=backend)
    cat.search("warm the index", limit=1)  # triggers the incremental per-kind build
    counts = ", ".join(f"{k}: {n}" for k, n in sorted(cat.kinds.items()))
    print(f"Indexed {len(cat)} assets ({counts}). Persistent index refreshed.")


def serve(config=None, *, http=False, name="toolery"):
    """Serve your ecosystem's search as an MCP server exposing a single `search` tool.

    Builds a catalog from ~/.config/toolery/sources.toml (see toolery.contrib.from_config)
    and serves it over stdio (or --http). Point your agent host's MCP config at this
    command so the agent gets one search tool over everything. Needs ``toolery[mcp]``.
    """
    from .contrib import from_config
    from .mcp_server import serve as _serve

    cat = from_config(config)
    _serve(cat, name=name, transport="http" if http else "stdio")


_dispatch_funcs = [search, skills, agents, packages, discover, mine, index, serve]


if __name__ == "__main__":
    import argh

    argh.dispatch_commands(_dispatch_funcs)
