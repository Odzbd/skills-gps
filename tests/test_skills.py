from pathlib import Path

import pytest

from skills_gps.skills import SkillMatcher

MATCHER = SkillMatcher.load(Path("data/skills.toml"))


def find(*lines):
    return {MATCHER.skills[i].name for i in MATCHER.find(lines)}


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Python, SQL and C++.", {"Python", "SQL", "C++"}),
        ("Experience with Node.js/TypeScript", {"Node.js", "TypeScript"}),
        ("CI/CD on AWS", {"CI/CD", "AWS"}),
        ("Build RESTful APIs", {"REST APIs"}),
        ("Proficiency in Microsoft Excel", {"Excel"}),
        ("You know React Native", {"React Native"}),
        ("JavaScript", {"JavaScript"}),
        ("Work with LLMs", {"LLMs"}),
    ],
)
def test_finds(line, expected):
    assert find(line) == expected


@pytest.mark.parametrize(
    "line",
    [
        "Go above and beyond",
        "Own our go to market plan",
        "Excel in a fast team",
        "Our R&D group",
        "Report to the C-suite",
        "React quickly to change",
        "The rest of the team",
    ],
)
def test_ignores_lookalikes(line):
    assert find(line) == set()


def test_ambiguous_skill_needs_another_skill_on_the_line():
    assert find("Go, Python") == {"Go", "Python"}
    assert find("Python", "Go above and beyond") == {"Python"}


def test_employer_does_not_count_toward_its_own_product():
    def made_by(token, name):
        return {MATCHER.skills[i].name for i in MATCHER.made_by(token, name)}

    assert "Snowflake" in made_by("snowflake", "Snowflake")
    assert "Elasticsearch" in made_by("elastic", "Elastic")


def test_duplicate_phrase_is_rejected():
    with pytest.raises(ValueError, match="twice"):
        SkillMatcher({"skills": {"A": {"X": ["same"], "Y": ["same"]}}})
