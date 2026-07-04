"""Search backends for toolery.

A *search backend* is any callable ``(query, cards, *, limit) -> [(card, score), ...]``.
The default, :func:`lexical_search`, is a zero-dependency token-overlap scorer so
that ``toolery`` works out of the box with no models, services, or API keys. A
semantic backend built on the ``ir`` retrieval substrate plugs into the same seam
(see the ``search_backend`` argument of :class:`toolery.catalog.Catalog`).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Protocol, runtime_checkable

from .base import Card

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    """Lowercase alphanumeric tokens of ``text``.

    >>> _tokens('CSV-deduper, v2!')
    ['csv', 'deduper', 'v2']
    """
    return _WORD.findall(text.lower())


@runtime_checkable
class SearchBackend(Protocol):
    """Callable protocol every search backend satisfies."""

    def __call__(
        self, query: str, cards: Sequence[Card], *, limit: int
    ) -> list[tuple[Card, float]]: ...


def lexical_search(
    query: str, cards: Iterable[Card], *, limit: int = 10
) -> list[tuple[Card, float]]:
    """Rank ``cards`` against ``query`` by token overlap, with name/phrase boosts.

    Precision-favoring: a card is only returned if it shares a query token or
    contains the whole query as a substring — so an empty or irrelevant query
    yields nothing rather than noise.

    >>> cards = [
    ...     Card('a', 'skill', 'CSV deduper', 'removes duplicate rows from csv'),
    ...     Card('b', 'skill', 'PDF reader', 'extract text from pdf files'),
    ... ]
    >>> [(c.name, round(s, 2)) for c, s in lexical_search('dedupe csv', cards)]
    [('CSV deduper', 0.75)]
    """
    q = set(_tokens(query))
    if not q:
        return []
    q_lower = query.lower().strip()
    scored: list[tuple[Card, float]] = []
    for card in cards:
        toks = set(_tokens(card.text))
        overlap = len(q & toks)
        phrase = bool(q_lower) and q_lower in card.text.lower()
        if not overlap and not phrase:
            continue
        score = overlap / len(q)
        if phrase:
            score += 0.5
        if q & set(_tokens(card.name)):
            score += 0.25
        scored.append((card, score))
    scored.sort(key=lambda cs: (cs[1], cs[0].name), reverse=True)
    return scored[:limit]
