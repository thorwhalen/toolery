"""Core data model for toolery: the normalized asset ``Card``.

Every asset the catalog knows about — a Claude skill, an agent spec, an MCP tool,
a research report, a package — is projected onto one uniform record, the
:class:`Card`, so that a single search surface can range over all of them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

_EMPTY: Mapping = MappingProxyType({})


@dataclass(frozen=True)
class Card:
    """A normalized record for one catalogued asset.

    The card is the *cheap* unit of discovery: small, uniform, and searchable.
    The full asset (a file, a package, a tool schema) is referenced by
    ``content_ref``/``source_uri`` and loaded on demand.

    >>> c = Card(id='x', kind='skill', name='CSV deduper',
    ...          description='remove duplicate rows from a csv', tags=('data',))
    >>> c.text
    'CSV deduper\\nremove duplicate rows from a csv\\ndata'
    >>> c.kind
    'skill'
    """

    id: str
    kind: str
    name: str
    description: str = ""
    tags: tuple[str, ...] = ()
    source_uri: str | None = None
    content_ref: str | None = None
    extra: Mapping = field(default_factory=lambda: _EMPTY)

    @property
    def text(self) -> str:
        """The searchable text surface of the card (name, description, tags)."""
        parts = [self.name, self.description, " ".join(self.tags)]
        return "\n".join(p for p in parts if p)

    def to_dict(self) -> dict:
        """A plain-dict view of the card (JSON-friendly, ``extra`` flattened out)."""
        return {
            "id": self.id,
            "kind": self.kind,
            "name": self.name,
            "description": self.description,
            "tags": list(self.tags),
            "source_uri": self.source_uri,
            "content_ref": self.content_ref,
            "extra": dict(self.extra),
        }
