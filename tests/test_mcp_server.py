"""Tests for the optional MCP server exposure.

``search_tool`` is hermetic; ``make_server`` (the py2mcp binding) is gated on py2mcp.
"""

import pytest

from toolery import Card, Catalog
from toolery.mcp_server import search_tool


def _catalog():
    return Catalog(
        [
            Card(
                "pdf",
                "skill",
                "PDF reader",
                "extract text from pdf documents",
                tags=("io",),
            ),
            Card("web", "tool", "web scraper", "download and parse web pages"),
        ]
    )


def test_search_tool_shapes_results():
    tool = search_tool(_catalog())
    out = tool("read text from a pdf", limit=5)
    assert isinstance(out, list) and out
    rec = out[0]
    assert rec["name"] == "PDF reader" and rec["kind"] == "skill"
    assert isinstance(rec["score"], float)
    assert "extra" not in rec  # dropped for a lean tool payload
    assert set(rec) >= {"id", "kind", "name", "description", "source_uri", "score"}


def test_search_tool_empty_query():
    assert search_tool(_catalog())("", limit=3) == []


def test_make_server_builds_single_tool():
    pytest.importorskip("py2mcp")
    from toolery.mcp_server import make_server

    server = make_server(_catalog(), name="toolery-test")
    assert server.name == "toolery-test"  # FastMCP server built and named
