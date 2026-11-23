"""Turn posting HTML into clean lines."""

import html
import re
from collections import defaultdict
from collections.abc import Iterable

_BLOCK = re.compile(r"</?(?:p|div|li|ul|ol|br|h[1-6]|tr|td|section)\b[^>]*>", re.I)
_TAG = re.compile(r"<[^>]+>")
_WORD = re.compile(r"[^\W\d_]+")
_ENGLISH = frozenset("the and of to a in for with you our we is on as will be are or your".split())

ENGLISH_SHARE = 0.15
BOILERPLATE_SHARE = 0.30
BOILERPLATE_TITLES = 5
BOILERPLATE_WORDS = 8


def to_lines(source: str) -> list[str]:
    if "&lt;" in source:  # Greenhouse escapes its HTML
        source = html.unescape(source)
    text = html.unescape(_TAG.sub("", _BLOCK.sub("\n", source)))
    lines = (" ".join(line.split()) for line in text.split("\n"))
    return [line for line in lines if line]


def is_english(lines: Iterable[str]) -> bool:
    words = _WORD.findall(" ".join(lines).lower())
    return bool(words) and sum(w in _ENGLISH for w in words) / len(words) >= ENGLISH_SHARE


def boilerplate(jobs: Iterable[tuple[str, list[str]]]) -> set[str]:
    """Long lines that one employer repeats across many different job titles."""
    titles_with: dict[str, set[str]] = defaultdict(set)
    titles: set[str] = set()
    for title, lines in jobs:
        titles.add(title)
        for line in lines:
            if len(line.split()) >= BOILERPLATE_WORDS:
                titles_with[line].add(title)
    minimum = max(BOILERPLATE_TITLES, BOILERPLATE_SHARE * len(titles))
    return {line for line, seen in titles_with.items() if len(seen) >= minimum}
