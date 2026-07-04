"""toolery — a searchable catalog over any corpus of tools, skills, agents, and components.

Point ``toolery`` at a collection of heterogeneous assets — Claude skills, agent
specs, MCP tools, docs, or packages — and get one searchable catalog: ask *"what do
I already have for X?"* and get a ranked answer, not fifty schemas.

Everything is projected onto a uniform :class:`Card`; a pluggable ``search_backend``
answers queries (the default is a zero-dependency lexical scorer, so it works out of
the box; a semantic backend built on the ``ir`` retrieval substrate drops into the
same seam).

>>> import toolery
>>> cat = toolery.catalog([
...     toolery.Card('a', 'tool', 'csvdedupe', 'remove duplicate rows from a csv'),
...     toolery.Card('b', 'tool', 'pdfread', 'extract text from pdf files'),
... ])
>>> [c.name for c, score in cat.search('deduplicate csv rows')]
['csvdedupe']
"""

from .base import Card
from .catalog import Catalog, catalog
from .harvest import folder, skills
from .search import SearchBackend, lexical_search

__version__ = "0.0.1"

__all__ = [
    "Card",
    "Catalog",
    "catalog",
    "folder",
    "skills",
    "lexical_search",
    "SearchBackend",
]
