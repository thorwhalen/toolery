# toolery

A searchable, self-maintaining catalog over any corpus of tools, skills, agents, and components.

Point `toolery` at a collection of heterogeneous assets — Claude skills, agent specs,
MCP tools, docs, or packages — and get **one** searchable catalog: ask *"what do I
already have for X?"* and get a ranked answer, not fifty schemas.

```
pip install toolery
```

## Quick start

Search a folder of notes/docs from the command line:

```bash
toolery search "dedupe a csv" ~/my/notes
```

Or from Python — the simplest thing that works, with zero configuration:

```python
import toolery

cat = toolery.catalog("~/my/notes")        # harvest a folder of markdown
for card, score in cat.search("parse pdf"):
    print(score, card.name, card.source_uri)
```

Out of the box the search is a fast, dependency-free lexical scorer, so nothing to
install, no models, no API keys.

## Any corpus, any asset kind

A catalog is built from **sources**. A source is a folder, a built-in *harvester*, or
bare cards:

```python
import toolery

cat = toolery.catalog(
    toolery.skills("~/.claude/skills"),     # Claude Agent Skills (SKILL.md)
    toolery.agents("~/.claude"),            # subagent specs (.claude/agents/*.md)
    toolery.packages("~/my/projects"),      # Python packages (pyproject.toml)
    toolery.mcp("~/my/project"),            # configured MCP servers (.mcp.json)
    "~/my/notes",                           # a folder of docs
    [toolery.Card("grep", "tool", "grep", "search text with patterns")],
)
cat.search("find text in files")
cat.by_kind("skill")
cat.kinds                                   # {'skill': 42, 'agent': 9, 'package': 210, ...}
```

Built-in harvesters: `folder`, `skills`, `agents`, `packages`, `mcp` — each just a
generator of `Card`s, so adding a new asset kind is one small function. The CLI mirrors
them: `toolery skills|agents|packages <root>` (add `--query` to search).

Everything is projected onto one uniform record, the `Card`
(`id, kind, name, description, tags, source_uri, content_ref`). Supporting a new
asset kind (agent specs, MCP tool schemas, packages) is just another generator that
yields `Card`s — nothing else changes.

## Bring your own search

`catalog(...)` and `Catalog(...)` accept a `search_backend` — any callable
`(query, cards, *, limit) -> [(card, score), ...]`. The default,
`toolery.lexical_search`, needs no dependencies. A semantic backend built on the
[`ir`](https://github.com/thorwhalen/ir) retrieval substrate drops into the same seam,
so you can start lexical and upgrade to embeddings without changing your calling code.

```python
from toolery import Catalog, lexical_search, IrBackend

cat = Catalog(cards, search_backend=lexical_search)   # zero-dependency default
cat = Catalog(cards, search_backend=IrBackend())      # embeddings — pip install 'toolery[ir]'
```

`IrBackend` embeds each card and answers by vector similarity, rebuilding only when the
cards change. Pass `embedder="light"` for a hermetic, no-download hashing embedder, or the
default MiniLM for real semantic matching. From the CLI: add `--semantic` to `toolery search`.

## Status

Early (`0.x`). In place: the `Card`/catalog model; harvesters for folders, skills,
agents, packages, and MCP servers; a zero-dependency lexical backend; an optional
`ir`-backed **semantic** backend (`toolery[ir]`); and the CLI. Next: `ir.discover([...])`
federation across per-kind corpora, a `toolery.contrib` ecosystem preset, and persistent
indexing for large corpora.
