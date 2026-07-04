"""An ``ir``-backed semantic search backend for toolery.

Optional — requires the ``ir`` package (``pip install 'toolery[ir]'``). It embeds each
card's text with ``ir``'s retrieval substrate and answers queries by vector similarity,
rebuilding the index only when the catalog's cards change (content-fingerprinted).

The default embedder (a MiniLM sentence-transformer) gives real semantic matching;
``embedder="light"`` uses ``ir``'s pure-numpy hashing embedder — no model download, no
network — which is what the tests use.

Drop it into any :class:`toolery.Catalog` in place of the default lexical backend::

    from toolery import Catalog
    from toolery.ir_backend import IrBackend

    cat = Catalog(cards, search_backend=IrBackend())        # MiniLM semantics
    cat = Catalog(cards, search_backend=IrBackend(embedder="light"))  # hermetic
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from .base import Card


def _require_ir():
    """Import ``ir`` or raise an actionable error naming the extra to install."""
    try:
        import ir
    except ImportError as e:  # pragma: no cover - only hit without ir installed
        raise ImportError(
            "toolery's semantic backend needs the 'ir' package. "
            "Install it with:  pip install 'toolery[ir]'"
        ) from e
    return ir


def _fingerprint(cards: list[Card]) -> str:
    """Order-independent content signature of a card set (id + searchable text)."""
    digest = hashlib.sha256()
    for cid, text in sorted((c.id, c.text) for c in cards):
        digest.update(cid.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(text.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


class IrBackend:
    """Semantic search backend delegating to the ``ir`` retrieval substrate.

    Satisfies the ``(query, cards, *, limit) -> [(card, score), ...]`` search-backend
    contract, so it is a drop-in for :class:`toolery.Catalog`'s ``search_backend``. The
    ``ir`` corpus is built lazily on first search and cached, and rebuilt only when the
    cards change. Only hits above ``min_score`` are returned (precision-favoring).

    Args (keyword-only):
        name: corpus name handed to ``ir``.
        embedder: ``"default"`` (MiniLM) for real semantics, ``"light"`` for a
            hermetic pure-numpy hashing embedder (no download/network).
        mode: ``ir`` retrieval mode — ``"dense"``, ``"lexical"``, or ``"hybrid"``.
        persist: if True, use ``ir``'s file-backed store (incremental across runs)
            instead of the default in-memory store.
        min_score: drop hits at or below this similarity (default 0.0).
    """

    def __init__(
        self,
        *,
        name: str = "toolery",
        embedder: str = "default",
        mode: str = "dense",
        persist: bool = False,
        min_score: float = 0.0,
    ):
        self._ir = _require_ir()
        self._name = name
        self._embedder = embedder
        self._mode = mode
        self._persist = persist
        self._min_score = min_score
        self._corpus = None
        self._fp: str | None = None
        self._by_id: dict[str, Card] = {}

    def _build(self, cards: list[Card]) -> None:
        ir = self._ir
        self._by_id = {c.id: c for c in cards}
        kinds = {c.id: c.kind for c in cards}
        source = ir.CorpusSource.from_mapping(
            {c.id: c.text for c in cards},
            name=self._name,
            metadata_of=lambda aid, raw: {"kind": kinds.get(aid, "")},
        )
        store = None if self._persist else ir.CorpusStore.memory()
        self._corpus = ir.build(source, store=store, embedder=self._embedder)

    def __call__(
        self, query: str, cards: Iterable[Card], *, limit: int = 10
    ) -> list[tuple[Card, float]]:
        cards = list(cards)
        if not cards or not query.strip():
            return []
        fp = _fingerprint(cards)
        if fp != self._fp or self._corpus is None:
            self._build(cards)
            self._fp = fp
        hits = self._corpus.search(query, k=limit, mode=self._mode)
        results: list[tuple[Card, float]] = []
        for hit in hits:
            score = float(hit.score)
            card = self._by_id.get(hit.artifact_id)
            if card is not None and score > self._min_score:
                results.append((card, score))
        return results


class IrFederatedBackend:
    """Federated semantic backend: one ``ir`` corpus **per card kind**, searched together.

    Delegates to ``ir.discover([...])``, which gates each per-kind corpus on its own
    (raw-score) abstention floor, fuses across corpora with Reciprocal Rank Fusion, then
    applies distractor-robust selection — so heterogeneous kinds (skills vs. packages vs.
    docs), whose similarity scores live on different scales, compare fairly. This is the
    multi-corpus discovery the catalog is designed around.

    Same drop-in contract as :class:`IrBackend`. Args (keyword-only):
        name: prefix for the per-kind corpus names.
        embedder: ``"default"`` (MiniLM) or ``"light"`` (hermetic hashing).
        mode: ``ir`` mode — ``"dense"`` (warning-free), ``"lexical"``, or ``"hybrid"``.
        min_score: federated abstention floor — ``None``, ``"auto"``, or a
            ``{corpus_name: float|"auto"|None}`` mapping (a bare float is invalid here).
        max_k: cap on committed results (defaults to the per-call ``limit``).
    """

    def __init__(
        self,
        *,
        name: str = "toolery",
        embedder: str = "default",
        mode: str = "dense",
        min_score=None,
        max_k: int | None = None,
    ):
        self._ir = _require_ir()
        self._name = name
        self._embedder = embedder
        self._mode = mode
        self._min_score = min_score
        self._max_k = max_k
        self._corpora = None
        self._fp: str | None = None
        self._by_id: dict[str, Card] = {}

    def _build(self, cards: list[Card]) -> None:
        ir = self._ir
        self._by_id = {c.id: c for c in cards}
        by_kind: dict[str, list[Card]] = {}
        for card in cards:
            by_kind.setdefault(card.kind, []).append(card)
        corpora = []
        for kind, kind_cards in sorted(by_kind.items()):
            source = ir.CorpusSource.from_mapping(
                {c.id: c.text for c in kind_cards},
                name=f"{self._name}-{kind}",
                metadata_of=lambda aid, raw, _k=kind: {"kind": _k},
            )
            corpora.append(
                ir.build(source, store=ir.CorpusStore.memory(), embedder=self._embedder)
            )
        self._corpora = corpora

    def __call__(
        self, query: str, cards: Iterable[Card], *, limit: int = 10
    ) -> list[tuple[Card, float]]:
        cards = list(cards)
        if not cards or not query.strip():
            return []
        fp = _fingerprint(cards)
        if fp != self._fp or self._corpora is None:
            self._build(cards)
            self._fp = fp
        result = self._ir.discover(
            self._corpora,
            query,
            k=max(limit, 10),
            max_k=self._max_k or limit,
            mode=self._mode,
            min_score=self._min_score,
        )
        out: list[tuple[Card, float]] = []
        for disclosure in result.results:
            card = self._by_id.get(disclosure.artifact_id)
            if card is not None:
                out.append((card, float(disclosure.score)))
        return out
