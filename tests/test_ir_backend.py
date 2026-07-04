"""Tests for the optional ir-backed semantic search backend.

Skipped entirely when ``ir`` is not installed. When it is, the ``"light"`` embedder
makes these run hermetically (pure numpy, no model download, no network).
"""

import pytest

pytest.importorskip("ir")

from toolery import Card, Catalog  # noqa: E402
from toolery.ir_backend import IrBackend, IrFederatedBackend, _fingerprint  # noqa: E402


def _cards():
    return [
        Card(
            "deploy", "doc", "Deploy guide", "how to deploy the web app to production"
        ),
        Card(
            "test", "skill", "Test runner", "runs the pytest suite and reports failures"
        ),
        Card("db", "doc", "DB notes", "postgres database schema and migrations"),
    ]


def test_ir_backend_ranks_semantically():
    cat = Catalog(_cards(), search_backend=IrBackend(embedder="light"))
    hits = cat.search("how do I deploy the application", limit=3)
    assert hits, "expected at least one hit"
    assert hits[0][0].id == "deploy"
    assert hits[0][1] > 0  # positive similarity for a real match


def test_ir_backend_precision_and_empty():
    backend = IrBackend(embedder="light")
    cat = Catalog(_cards(), search_backend=backend)
    assert cat.search("", limit=3) == []  # empty query -> nothing
    # every returned hit is above the min_score floor
    assert all(score > 0 for _c, score in cat.search("run the tests", limit=3))


def test_ir_backend_rebuilds_only_on_change():
    backend = IrBackend(embedder="light")
    cat = Catalog(_cards(), search_backend=backend)
    cat.search("deploy", limit=1)
    fp1 = backend._fp
    cat.search("database", limit=1)  # same cards -> no rebuild
    assert backend._fp == fp1


def test_fingerprint_is_order_independent():
    a, b = _cards()[0], _cards()[1]
    assert _fingerprint([a, b]) == _fingerprint([b, a])


def _multi_kind_cards():
    return [
        Card(
            "pdf-reader",
            "skill",
            "PDF reader",
            "read and extract text from pdf documents",
        ),
        Card("web-scraper", "skill", "Web scraper", "scrape and download web pages"),
        Card(
            "guide-pdf",
            "doc",
            "PDF guide",
            "how to open pdf files and pull out their text",
        ),
        Card("guide-db", "doc", "DB guide", "connect to sql databases and run queries"),
    ]


def test_federated_backend_searches_across_kinds():
    backend = IrFederatedBackend(embedder="light", mode="dense")
    cat = Catalog(_multi_kind_cards(), search_backend=backend)
    # two corpora were built (one per kind: skill, doc)
    hits = cat.search("extract text from a pdf", limit=5)
    assert hits, "expected federated hits"
    assert hits[0][0].id in {"pdf-reader", "guide-pdf"}  # pdf item wins across corpora
    assert all(isinstance(score, float) for _c, score in hits)


def test_federated_backend_empty_and_single_kind():
    backend = IrFederatedBackend(embedder="light", mode="dense")
    cat = Catalog(_multi_kind_cards(), search_backend=backend)
    assert cat.search("", limit=3) == []  # empty query -> nothing
    # single-kind catalog still works (one corpus in the federation)
    solo = Catalog(
        [Card("x", "tool", "grep", "search text with regular expression patterns")],
        search_backend=IrFederatedBackend(embedder="light", mode="dense"),
    )
    assert solo.search("regex text search", limit=3)
