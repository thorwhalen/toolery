"""Expose a toolery catalog's search as an MCP server — one search tool for agents.

Optional — needs ``pip install 'toolery[mcp]'`` (py2mcp). Instead of handing an agent a
schema per asset, this gives it a single ``search`` tool over your whole catalog: the
"one search tool, not fifty schemas" idea made concrete. Point any MCP host at the
``toolery serve`` command (see ``toolery.cli``).
"""

from __future__ import annotations

from .catalog import Catalog


def _require_py2mcp():
    """Import ``py2mcp`` or raise an actionable error naming the extra to install."""
    try:
        import py2mcp
    except ImportError as e:  # pragma: no cover - only without the extra installed
        raise ImportError(
            "toolery's MCP server needs the 'py2mcp' package. "
            "Install it with:  pip install 'toolery[mcp]'"
        ) from e
    return py2mcp


def search_tool(catalog: Catalog):
    """Return a ``search(query, limit=10)`` function (an MCP-shaped tool) bound to ``catalog``.

    Its signature and docstring become the MCP tool schema and description.
    """

    def search(query: str, limit: int = 10) -> list[dict]:
        """Search the catalog of assets (skills, agents, tools, docs, packages) for a task.

        Returns the best-matching assets, each as a dict with id, kind, name, description,
        source_uri, and a relevance score. Use it to find what is already available before
        building something new.
        """
        results = []
        for card, score in catalog.search(query, limit=limit):
            record = card.to_dict()
            record.pop("extra", None)
            record["score"] = round(float(score), 4)
            results.append(record)
        return results

    return search


def make_server(catalog: Catalog, *, name: str = "toolery"):
    """Build (but don't run) an MCP server exposing ``catalog``'s search as one tool."""
    py2mcp = _require_py2mcp()
    return py2mcp.mk_mcp_server([search_tool(catalog)], name=name)


def serve(catalog: Catalog, *, name: str = "toolery", transport: str = "stdio") -> None:
    """Serve ``catalog``'s search as an MCP server (blocks until the host disconnects)."""
    make_server(catalog, name=name).run(transport=transport)
