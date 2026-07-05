---
name: toolery-dev
description: >-
  Develop, extend, and maintain the toolery package (a searchable catalog over heterogeneous
  assets, built on the ir retrieval substrate). Use when contributing to toolery — adding a
  harvester (new asset kind), adding a search backend, working on the ir or MCP integrations,
  running its tests, or cutting a release. Covers the Card / Catalog / search_backend
  architecture, the harvest -> catalog -> search flow, the pluggable-backend seam, the
  optional-dependency (ir, py2mcp) lazy-import + importorskip test pattern, and the wads
  auto-publish-on-merge release flow.
metadata:
  audience: developers
---

# toolery-dev — contributing to toolery

Read [`AGENTS.md`](../../../../AGENTS.md) first for the full module map and conventions. This
skill is the how-to for the common contributor tasks.

## Architecture in one breath

`Card` (`base.py`) is the normalized asset record. Harvesters (`harvest.py`) yield `Card`s.
`Catalog` (`catalog.py`) holds them and searches through a pluggable `search_backend`
(`search.py`: `lexical_search`; `ir_backend.py`: `IrBackend`, `IrFederatedBackend`).
`contrib.py` is ecosystem presets; `mcp_server.py` exposes search as an MCP tool; `cli.py` is
argh dispatch.

## Add a new asset kind (harvester)

Write a generator in `harvest.py` that yields `Card`s, export it in `__init__.py`, add a CLI
subcommand in `cli.py` if useful (mirror `skills`), and add a tmp-dir test. Nothing else changes:
```python
def widgets(root, *, kind="widget"):
    for path in sorted(Path(root).expanduser().glob("**/*.widget")):
        yield Card(id=str(path.name), kind=kind, name=path.stem,
                   description=path.read_text(errors="ignore")[:200], source_uri=str(path))
```

## Add a search backend

A backend is any callable `(query, cards, *, limit) -> [(Card, score)]` (the `SearchBackend`
protocol). Use it as `Catalog(cards, search_backend=...)`. For a heavy backend (like the ir
ones), lazy-import the dep inside `_require_x()` and fingerprint-cache the built index so it
only rebuilds when the cards change.

## Optional dependencies (the rule)

`ir` and `py2mcp` are **never** imported at module top — only inside `_require_ir()` /
`_require_py2mcp()`, which raise an actionable `pip install 'toolery[ir]'` error. Their tests
`pytest.importorskip(...)` and use the hermetic `embedder="light"` (pure numpy, no network),
so CI (which doesn't install the extras) **skips** them and stays green. Keep the core's only
runtime dep = `argh`.

## Test & lint

```bash
pip install -e ".[dev]"
pip install ir py2mcp                 # to actually RUN the optional-dep tests locally
pytest --doctest-modules toolery tests
ruff format toolery && ruff check toolery
```

## Release

wads CI **auto-publishes to PyPI on merge to `main`** (it bumps the version and tags itself).
So: develop on a **branch** (branch CI runs tests, skips publish), merge to `main` to release.
`[skip ci]` in a commit message skips the publish. Never commit secrets or absolute local paths.
