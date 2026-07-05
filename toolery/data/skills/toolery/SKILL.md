---
name: toolery
description: >-
  Use the toolery package to build a searchable catalog over a corpus of heterogeneous
  assets — Claude skills, subagent specs, MCP tools, docs, and Python packages — and find
  what you already have. Trigger when the user says "what do I have for X", "find my
  skill/agent/tool/package for ...", "search my ecosystem / notes / packages", "catalog my
  assets", "which of my tools does ...", "give my agent one search tool (MCP)", or wants
  lexical / semantic / federated search over a folder or their whole project ecosystem.
  Covers the catalog() / mine / discover / serve workflows, the lexical vs ir-semantic vs
  federated backends, and the ~/.config/toolery/sources.toml ecosystem preset.
metadata:
  audience: users
---

# toolery — find what you already have

`toolery` turns any corpus of assets into one searchable catalog. Reach for it when the user
is hunting for an asset they *know* they have (a skill, agent, tool, doc, or package) but
can't name or locate — or wants to search a folder or their whole ecosystem.

## Install

```bash
pip install toolery              # lexical (zero deps)
pip install 'toolery[ir]'        # + semantic / federated search
pip install 'toolery[mcp]'       # + MCP server
```

## Pick the workflow

**Search one folder / corpus**
```python
import toolery
cat = toolery.catalog("~/notes")            # or a list of toolery.Card(...)
for card, score in cat.search("parse a pdf"):
    print(score, card.kind, card.name, card.source_uri)
```
CLI: `toolery search "parse a pdf" ~/notes` (add `--semantic` for embeddings).

**Search a project's Claude assets / packages by kind**
```bash
toolery skills   ~/.claude --query "diagnose"
toolery packages ~/proj    --query "embeddings"
toolery discover "check project health" ~/proj --kinds skill,agent,doc
```

**Search your WHOLE ecosystem** (configure once, search forever)
`~/.config/toolery/sources.toml`:
```toml
[claude]
roots = ["~/.claude", "~/work/project"]
[packages]
roots = ["~/proj/mine", "~/proj/theirs"]
[harvesters]
refs = ["mymod:my_cards"]   # optional: a "module:function" -> Card/dict source of your own
```
Then: `toolery mine "which of my tools parses pdfs?"` (add `--semantic`, `--persist`).
For speed on a big corpus, warm a persistent index first: `toolery index`.

**Give an agent ONE search tool (MCP)**
```bash
toolery serve            # stdio MCP server exposing a single `search` tool
toolery serve --http     # or Streamable HTTP
```
Point the agent host's MCP config at that command — one tool over everything.

## Backends (relevance vs. setup)

- default **lexical** — zero deps, great for name/keyword hits.
- **`--semantic`** (`toolery[ir]`) — embeddings; better for fuzzy / conceptual queries.
- **federated** (`IrFederatedBackend`, used by `discover` / `mine`) — one corpus per kind,
  RRF-fused so skills, packages, and docs compare fairly.

## Gotchas

- Semantic / MCP features need the extras; without them the tool errors with the exact
  `pip install` command to run.
- `mine` needs `~/.config/toolery/sources.toml`; `from_config` errors with the schema if absent.
- Results are precision-favoring: an irrelevant query returns **nothing**, not noise.
