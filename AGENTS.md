# AGENTS.md — toolery

Canonical agent instructions for `toolery`. `CLAUDE.md` imports this; other agent hosts
(Cursor, Copilot, Codex, Gemini) read it directly.

## What toolery is

A searchable, self-maintaining **catalog over any corpus of heterogeneous assets** — Claude
skills, subagent specs, MCP tools, docs, and Python packages. Point it at your stuff, ask
*"what do I have for X"*, get a ranked answer. Zero-dependency lexical search by default;
optional `ir`-backed semantic + federated search; optional MCP `search` tool for agents.

## Install

```bash
pip install toolery              # core (lexical; only dep is argh)
pip install 'toolery[ir]'        # + semantic / federated search (the `ir` substrate)
pip install 'toolery[mcp]'       # + MCP server exposure (py2mcp)
```

## Use it (the common paths)

```python
import toolery
cat = toolery.catalog("~/notes")                 # harvest a folder of docs
cat.search("dedup a csv")                        # -> ranked [(Card, score), ...]

from toolery import contrib                       # your whole ecosystem, one call
contrib.everything(package_roots=["~/proj"]).search("embeddings")
```

CLI: `toolery search|skills|agents|packages|discover|mine|index|serve`.
- `toolery mine "<q>"` — search your configured ecosystem (`~/.config/toolery/sources.toml`).
- `toolery serve` — expose your catalog as a single MCP `search` tool.

## Core model (one paragraph)

Every asset becomes a `Card` (`id, kind, name, description, tags, source_uri, content_ref`).
A `Catalog` answers queries through a pluggable **`search_backend`** — default `lexical_search`
(zero deps); `IrBackend` (semantic); `IrFederatedBackend` (one `ir` corpus per kind, fused
with RRF + calibrated abstention). Harvesters (`folder, skills, agents, packages, mcp`) are
just generators of `Card`s, so a new asset kind is one function.

## Module map (for contributors)

| Module | Responsibility |
|---|---|
| `toolery/base.py` | the `Card` dataclass |
| `toolery/search.py` | `lexical_search` + the `SearchBackend` protocol |
| `toolery/harvest.py` | harvesters: `folder`, `skills`, `agents`, `packages`, `mcp` |
| `toolery/catalog.py` | `Catalog` + the `catalog()` facade |
| `toolery/ir_backend.py` | `IrBackend`, `IrFederatedBackend` (optional — needs `ir`) |
| `toolery/contrib.py` | ecosystem presets + config-driven `from_config` |
| `toolery/mcp_server.py` | `search_tool`, `make_server`, `serve` (optional — needs `py2mcp`) |
| `toolery/cli.py` | argh CLI (`_dispatch_funcs`) |

## Conventions

- Functional; dataclasses for data; keyword-only args from the 3rd position; generators over lists.
- Optional deps (`ir`, `py2mcp`) are **lazy-imported** inside `_require_*()`; the core stays
  dependency-light. Their tests `importorskip` and use hermetic settings (`embedder="light"`).
- Every module has a top-level docstring; simple doctests where practical.
- A new **search backend** is a callable `(query, cards, *, limit) -> [(Card, score)]`.
- A new **asset kind** is a harvester generator yielding `Card`s.

## Build & test

```bash
pip install -e ".[dev]"
pytest --doctest-modules toolery tests
ruff format toolery && ruff check toolery
```

## Release

wads CI **auto-publishes to PyPI on every merge to `main`** (it bumps the version and tags
itself). So develop on a **branch**, open a PR / merge when ready; put `[skip ci]` in a commit
message to skip a release. Never commit secrets or absolute local paths.
