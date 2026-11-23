"""Find skills in text by looking up token n-grams in a dictionary."""

import re
import tomllib
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import NamedTuple

_TOKEN = re.compile(r"\.?\w+[+#]*")
MASK = -1  # dictionary entry that hides a phrase from shorter matches


class Skill(NamedTuple):
    name: str
    group: str


class _Entry(NamedTuple):
    skill: int
    exact: str | None  # required spelling, or None when case does not matter


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text)


class SkillMatcher:
    def __init__(self, config: dict):
        self.skills: list[Skill] = []
        self._entries: dict[tuple[str, ...], _Entry] = {}
        self._needs_context: set[int] = set()
        self._makers: dict[int, set[str]] = {}
        for phrase in config.get("mask", []):
            self._add(phrase, MASK, case=False)
        for group, members in config["skills"].items():
            for name, options in members.items():
                self._add_skill(group, name, options)
        self._longest = max(map(len, self._entries))

    @classmethod
    def load(cls, path: Path) -> "SkillMatcher":
        with path.open("rb") as file:
            return cls(tomllib.load(file))

    def find(self, lines: Iterable[str]) -> set[int]:
        """Skills mentioned. Ambiguous ones count only beside another skill."""
        found: set[int] = set()
        for line in lines:
            in_line = set(self._scan(line))
            if len(in_line) < 2:
                in_line -= self._needs_context
            found |= in_line
        return found

    def made_by(self, token: str, name: str) -> set[int]:
        """Skills named after, or made by, this employer."""
        makers = {skill for skill, tokens in self._makers.items() if token in tokens}
        return makers | set(self._scan(name))

    def _add_skill(self, group: str, name: str, options: list[str] | dict) -> None:
        if isinstance(options, list):
            options = {"aliases": options}
        skill = len(self.skills)
        self.skills.append(Skill(name, group))
        if options.get("context"):
            self._needs_context.add(skill)
        if makers := options.get("makers"):
            self._makers[skill] = set(makers)
        if options.get("named", True):
            self._add(name, skill, case=options.get("case", False))
        for alias in options.get("aliases", []):
            self._add(alias, skill, case=False)

    def _add(self, phrase: str, skill: int, *, case: bool) -> None:
        tokens = tokenize(phrase)
        spelling = " ".join(tokens)
        key = tuple(t.lower() for t in tokens)
        entry = _Entry(skill, spelling if case else None)
        if self._entries.setdefault(key, entry).skill != skill:
            raise ValueError(f"{phrase!r} is listed twice")
        if not case and skill != MASK and len(key[-1]) > 2 and not key[-1].endswith("s"):
            self._entries.setdefault((*key[:-1], key[-1] + "s"), entry)

    def _scan(self, line: str) -> Iterator[int]:
        tokens = tokenize(line)
        lowered = [t.lower() for t in tokens]
        start = 0
        while start < len(tokens):
            for size in range(min(self._longest, len(tokens) - start), 0, -1):
                entry = self._entries.get(tuple(lowered[start : start + size]))
                if entry is None:
                    continue
                if entry.exact and entry.exact != " ".join(tokens[start : start + size]):
                    continue
                if entry.skill != MASK:
                    yield entry.skill
                start += size
                break
            else:
                start += 1
