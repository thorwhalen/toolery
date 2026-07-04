"""The :class:`Catalog` — a searchable collection of cards, and the ``catalog`` facade.

``Catalog`` holds normalized cards and answers queries through a pluggable
``search_backend`` (default: the zero-dependency :func:`~toolery.search.lexical_search`).
The :func:`catalog` function is the one-liner entry point: hand it folders, skill
roots, harvester iterables, or bare cards, and get a ready-to-search catalog.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from pathlib import Path

from .base import Card
from .harvest import folder
from .search import SearchBackend, lexical_search


def _as_cards(source) -> Iterator[Card]:
    """Coerce a source into cards: a Card, a path/str (folder), or an iterable of cards."""
    if isinstance(source, Card):
        yield source
    elif isinstance(source, (str, os.PathLike)):
        yield from folder(source)
    elif isinstance(source, Iterable):
        for item in source:
            if not isinstance(item, Card):
                raise TypeError(f"source iterable must yield Card, got {type(item)}")
            yield item
    else:
        raise TypeError(f"cannot harvest cards from {type(source)}")


class Catalog:
    """A searchable catalog of :class:`~toolery.base.Card` s.

    >>> cat = Catalog([
    ...     Card('a', 'skill', 'CSV deduper', 'removes duplicate rows from csv'),
    ...     Card('b', 'skill', 'PDF reader', 'extract text from pdf files'),
    ... ])
    >>> len(cat)
    2
    >>> [c.name for c, _ in cat.search('deduplicate a csv')]
    ['CSV deduper']
    >>> [c.name for c in cat.by_kind('skill')]
    ['CSV deduper', 'PDF reader']
    """

    def __init__(
        self,
        cards: Iterable[Card] = (),
        *,
        search_backend: SearchBackend = lexical_search,
    ):
        self._cards: dict[str, Card] = {c.id: c for c in cards}
        self._search_backend = search_backend

    @property
    def cards(self) -> list[Card]:
        """All cards in the catalog."""
        return list(self._cards.values())

    def search(self, query: str, *, limit: int = 10) -> list[tuple[Card, float]]:
        """Ranked ``(card, score)`` results for ``query`` via the search backend."""
        return self._search_backend(query, self.cards, limit=limit)

    def by_kind(self, kind: str) -> list[Card]:
        """All cards of a given ``kind``."""
        return [c for c in self._cards.values() if c.kind == kind]

    @property
    def kinds(self) -> dict[str, int]:
        """Mapping of ``kind`` to the number of cards of that kind."""
        counts: dict[str, int] = {}
        for c in self._cards.values():
            counts[c.kind] = counts.get(c.kind, 0) + 1
        return counts

    def __len__(self) -> int:
        return len(self._cards)

    def __iter__(self) -> Iterator[Card]:
        return iter(self._cards.values())

    def __repr__(self) -> str:
        return f"{type(self).__name__}({len(self)} cards, kinds={self.kinds})"


def catalog(*sources, search_backend: SearchBackend = lexical_search) -> Catalog:
    """Build a :class:`Catalog` from one or more sources.

    A *source* is a folder path (harvested as markdown), a harvester iterable of
    cards (e.g. :func:`toolery.skills`), or bare :class:`~toolery.base.Card` s.

    >>> cat = catalog([Card('x', 'tool', 'grep', 'search text with patterns')])
    >>> cat.search('pattern search')[0][0].name
    'grep'
    """
    cards: list[Card] = []
    for source in sources:
        cards.extend(_as_cards(source))
    return Catalog(cards, search_backend=search_backend)
