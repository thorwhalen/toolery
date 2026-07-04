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

from . import contrib
from .base import Card
from .catalog import Catalog, catalog
from .harvest import agents, folder, mcp, packages, skills
from .ir_backend import IrBackend, IrFederatedBackend
from .mcp_server import make_server, search_tool
from .search import SearchBackend, lexical_search

from importlib.metadata import PackageNotFoundError as _PkgNotFound
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("toolery")
except _PkgNotFound:  # running from a source tree that isn't installed
    __version__ = "0.0.0"

__all__ = [
    "Card",
    "Catalog",
    "catalog",
    "folder",
    "skills",
    "agents",
    "packages",
    "mcp",
    "lexical_search",
    "SearchBackend",
    "IrBackend",
    "IrFederatedBackend",
    "make_server",
    "search_tool",
    "contrib",
]
