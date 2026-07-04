"""Tests for toolery's card model, lexical search, catalog facade, and harvesters."""

from toolery import Card, Catalog, catalog, lexical_search
from toolery.harvest import _parse_frontmatter, skills


def test_card_text_and_dict():
    c = Card("i", "kind", "Name", "desc here", tags=("a", "b"))
    assert c.text == "Name\ndesc here\na b"
    d = c.to_dict()
    assert d["tags"] == ["a", "b"] and d["kind"] == "kind"


def test_lexical_ranking_and_precision():
    cards = [
        Card("a", "skill", "CSV deduper", "removes duplicate rows from csv"),
        Card("b", "skill", "PDF reader", "extract text from pdf files"),
    ]
    assert [c.name for c, _ in lexical_search("deduplicate csv", cards)] == ["CSV deduper"]
    assert lexical_search("", cards) == []  # empty query -> nothing
    assert lexical_search("quantum tunneling", cards) == []  # irrelevant -> nothing


def test_catalog_facade_and_kinds():
    cat = catalog([Card("x", "tool", "grep", "search text with patterns")])
    assert isinstance(cat, Catalog)
    assert cat.search("pattern search")[0][0].name == "grep"
    assert cat.kinds == {"tool": 1}
    assert len(cat) == 1


def test_folder_harvester(tmp_path):
    (tmp_path / "a.md").write_text("# Alpha\n\nAlpha does the first thing.\n")
    (tmp_path / "b.md").write_text(
        "---\nname: Beta\ndescription: beta blurb\n---\nbody\n"
    )
    cat = catalog(str(tmp_path))
    assert sorted(c.name for c in cat) == ["Alpha", "Beta"]
    beta = next(c for c in cat if c.name == "Beta")
    assert beta.description == "beta blurb"
    assert cat.search("first thing")[0][0].name == "Alpha"


def test_skills_harvester(tmp_path):
    d = tmp_path / "my-skill"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does a helpful thing\n"
        "allowed-tools: Bash, Read\n---\n# body\n"
    )
    cards = list(skills(tmp_path))
    assert len(cards) == 1
    assert cards[0].kind == "skill" and cards[0].name == "my-skill"
    assert cards[0].tags == ("Bash", "Read")
    assert cards[0].description == "does a helpful thing"


def test_parse_frontmatter_folded():
    meta, body = _parse_frontmatter(
        "---\nname: x\ndescription: >\n  line one\n  line two\n---\nB"
    )
    assert meta["name"] == "x"
    assert meta["description"] == "line one line two"
    assert body.strip() == "B"
