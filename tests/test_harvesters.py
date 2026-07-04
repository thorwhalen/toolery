"""Tests for the agents, packages, and mcp harvesters."""

import json

from toolery import Card, catalog
from toolery import packages as packages_h
from toolery import skills as skills_h
from toolery.harvest import _project_meta, agents, mcp, packages


def test_agents_harvester(tmp_path):
    adir = tmp_path / "agents"
    adir.mkdir()
    (adir / "reviewer.md").write_text(
        "---\nname: code-reviewer\ndescription: reviews code for bugs\n"
        "tools: Read, Grep\n---\n# body\n"
    )
    (adir / "not-an-agent.md").write_text("# just a doc\nno frontmatter here\n")
    cards = list(agents(tmp_path))  # from a project root
    assert [c.name for c in cards] == ["code-reviewer"]
    assert cards[0].kind == "agent" and cards[0].tags == ("Read", "Grep")
    assert [c.name for c in agents(adir)] == ["code-reviewer"]  # from the agents dir


def test_packages_harvester(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "pyproject.toml").write_text(
        '[project]\nname = "mypkg"\ndescription = "does a useful thing"\nversion = "0.1.0"\n'
    )
    cards = list(packages(tmp_path))
    assert len(cards) == 1
    assert cards[0].name == "mypkg" and cards[0].kind == "package"
    assert cards[0].description == "does a useful thing"


def test_project_meta_readme_fallback(tmp_path):
    pkg = tmp_path / "p2"
    pkg.mkdir()
    (pkg / "pyproject.toml").write_text('[project]\nname = "p2"\n')  # no description
    (pkg / "README.md").write_text("# P2\n\nP2 is a great little library.\n")
    name, desc = _project_meta(pkg / "pyproject.toml")
    assert name == "p2"
    assert "great little library" in desc


def test_mcp_harvester(tmp_path):
    cfg = {
        "mcpServers": {
            "fs": {"command": "npx", "args": ["-y", "server-filesystem"]},
            "gh": {"command": "gh-mcp", "description": "GitHub tools"},
        }
    }
    (tmp_path / ".mcp.json").write_text(json.dumps(cfg))
    cards = {c.name: c for c in mcp(tmp_path)}
    assert set(cards) == {"fs", "gh"}
    assert cards["gh"].description == "GitHub tools"
    assert "server-filesystem" in cards["fs"].description
    assert cards["fs"].kind == "mcp"
    assert len(list(mcp(tmp_path / ".mcp.json"))) == 2  # file path works too


def test_multi_kind_catalog(tmp_path):
    sdir = tmp_path / "skills" / "s1"
    sdir.mkdir(parents=True)
    (sdir / "SKILL.md").write_text("---\nname: s1\ndescription: skill one\n---\n")
    pkg = tmp_path / "pkgs" / "pkgx"
    pkg.mkdir(parents=True)
    (pkg / "pyproject.toml").write_text(
        '[project]\nname = "pkgx"\ndescription = "package x"\n'
    )
    cat = catalog(
        skills_h(tmp_path / "skills"),
        packages_h(tmp_path / "pkgs"),
        [Card("t1", "tool", "grep", "search text")],
    )
    assert cat.kinds == {"skill": 1, "package": 1, "tool": 1}
