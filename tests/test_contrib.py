"""Tests for the contrib ecosystem presets and config-driven catalog."""

import pytest

from toolery import contrib


def _make_project(tmp_path):
    proj_claude = tmp_path / "proj" / ".claude"
    (proj_claude / "skills" / "s1").mkdir(parents=True)
    (proj_claude / "skills" / "s1" / "SKILL.md").write_text(
        "---\nname: s1\ndescription: skill one\n---\n"
    )
    (proj_claude / "agents").mkdir(parents=True)
    (proj_claude / "agents" / "a1.md").write_text(
        "---\nname: a1\ndescription: agent one\n---\n"
    )
    pkgs = tmp_path / "pkgs"
    (pkgs / "px").mkdir(parents=True)
    (pkgs / "px" / "pyproject.toml").write_text(
        '[project]\nname = "px"\ndescription = "package x"\n'
    )
    return proj_claude, pkgs


def test_everything_presets(tmp_path):
    proj_claude, pkgs = _make_project(tmp_path)
    cat = contrib.everything(
        claude_roots=[str(proj_claude)],
        package_roots=[str(pkgs)],
        home=str(tmp_path / "no-such-home"),  # don't scan the real ~/.claude
    )
    assert cat.kinds == {"skill": 1, "agent": 1, "package": 1}


def test_from_config(tmp_path):
    pytest.importorskip("tomllib")
    proj_claude, pkgs = _make_project(tmp_path)
    cfg = tmp_path / "sources.toml"
    cfg.write_text(
        f'[claude]\nroots = ["{proj_claude}"]\n[packages]\nroots = ["{pkgs}"]\n'
    )
    cat = contrib.from_config(cfg)
    assert cat.kinds == {"skill": 1, "agent": 1, "package": 1}


def test_from_config_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        contrib.from_config(tmp_path / "nope.toml")


def test_cards_from_ref(tmp_path, monkeypatch):
    mod = tmp_path / "toolery_ref_probe.py"
    mod.write_text(
        "def cards():\n"
        "    return [{'name': 'a', 'kind': 'k', 'description': 'd', 'path': '/tmp/a'}]\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    cards = list(contrib._cards_from_ref("toolery_ref_probe:cards"))
    assert len(cards) == 1
    assert cards[0].name == "a" and cards[0].kind == "k"
    assert cards[0].content_ref == "/tmp/a"
