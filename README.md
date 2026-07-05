# toolery

A searchable, self-maintaining catalog over any corpus of tools, skills, agents, and components.

> **For humans:** you have better things to do than read a README. Point your coding agent at
> toolery's skill — `gh skill install thorwhalen/toolery toolery` — and say *"catalog my stuff
> and find me X."* It takes it from there.
>
> **For agents, engineers, and control freaks:** welcome, the rest of this README is yours —
> and there's an [`AGENTS.md`](AGENTS.md) with the canonical brief + module map.

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

For a **multi-kind** catalog, `IrFederatedBackend` builds one `ir` corpus per kind and searches
them together via `ir.discover([...])` — per-kind abstention floors + Reciprocal Rank Fusion, so
skills, packages, and docs (whose similarity scores live on different scales) compare fairly:

```python
from toolery import Catalog, IrFederatedBackend

cat = Catalog(mixed_kind_cards, search_backend=IrFederatedBackend())
```

The CLI exposes it as `toolery discover "<query>" <root> --kinds skill,agent,doc,package`.

## Catalog your whole ecosystem

`toolery.contrib` builds a catalog over your usual asset locations in one call:

```python
from toolery import contrib

cat = contrib.everything(package_roots=["~/proj/mine"])   # + your ~/.claude skills & agents
cat.search("thing I half-remember writing")
```

Keep your locations in `~/.config/toolery/sources.toml` and search them all from the CLI:

```toml
[claude]
roots = ["~/.claude", "~/work/project"]
[packages]
roots = ["~/proj/mine", "~/proj/theirs"]
[harvesters]
refs = ["mymod:my_cards"]   # "module:function" -> your own Card/dict source (e.g. a private index)
```

```bash
toolery mine "which of my tools parses pdfs?"              # lexical
toolery mine "which of my tools parses pdfs?" --semantic   # ir federated (toolery[ir])
```

For a large corpus, warm a persistent on-disk index once (incremental via ir's ledger, so
only changed assets are re-embedded) and reuse it across runs:

```bash
toolery index                                   # build/refresh the on-disk index
toolery mine "…" --semantic --persist           # reuse it — fast
```

Your paths and any private-source `refs` live in that local file — nothing personal is baked
into the package.

## Give an agent one search tool (MCP)

Instead of exposing a schema per asset, serve your whole catalog as a single MCP `search`
tool (needs `pip install 'toolery[mcp]'`):

```bash
toolery serve            # stdio MCP server over your ~/.config/toolery/sources.toml
toolery serve --http     # or Streamable HTTP
```

Point your agent host's MCP config at that command and the agent gets **one** `search`
tool over everything — the "one search tool, not fifty schemas" idea, made concrete. In
Python:

```python
from toolery import make_server, contrib

make_server(contrib.everything(package_roots=["~/proj"])).run(transport="stdio")
```

## Skills (this package is AI-enabled)

toolery ships agent skills — install into any agent host with
[`gh skill`](https://github.com/github/gh-skill):

```bash
gh skill install thorwhalen/toolery toolery        # consumer: drive toolery to find your assets
gh skill install thorwhalen/toolery toolery-dev    # developer: extend & maintain toolery
```

They also ride along inside the wheel (`toolery/data/skills/`) and mirror to `.claude/skills/`
for Claude Code. Canonical agent instructions live in [`AGENTS.md`](AGENTS.md) (`CLAUDE.md` is
a thin shim over it).

## Status

Early (`0.x`). In place: the `Card`/catalog model; harvesters for folders, skills,
agents, packages, and MCP servers; a zero-dependency lexical backend; an optional
`ir`-backed **semantic** backend (`toolery[ir]`), plus federated multi-kind discovery
(`IrFederatedBackend` / `toolery discover`); a `contrib` ecosystem preset (`toolery mine`);
persistent incremental indexing (`toolery index` / `--persist`); MCP exposure as a single
`search` tool (`toolery serve`); and the CLI. Also integrated into `opsward` (`opsward find`).
Next: progressive-disclosure loading.
