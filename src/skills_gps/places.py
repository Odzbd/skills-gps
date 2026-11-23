"""Map an employer's location text to countries.

Words are ambiguous: CA is California or Canada, Dublin is in Ireland or Ohio. Neighbours
decide. "Dublin, OH" is in the US because a state after a city overrides the city. A word
with several meanings and nothing beside it stays unknown.
"""

import re
import tomllib
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from enum import IntEnum
from pathlib import Path
from typing import NamedTuple

_SEGMENT = re.compile(r"[;|/•·&\n]|\bor\b|\band\b")
_TOKEN = re.compile(r"\w+")
_REMOTE = re.compile(
    r"(?<!not )(?<!non.)(?<!no )\b(?:remote|distributed|anywhere|work from home)\b", re.I
)


class Kind(IntEnum):
    CITY = 0
    REGION = 1
    COUNTRY = 2


class _Meaning(NamedTuple):
    kind: Kind
    country: str


class _Match(NamedTuple):
    meanings: list[_Meaning]
    part: int  # position in the comma-separated list


class PlaceMatcher:
    def __init__(self, config: dict[str, dict]):
        self.names = {code: country["name"] for code, country in config.items()}
        self._words: dict[tuple[str, ...], list[_Meaning]] = defaultdict(list)
        self._codes: dict[str, list[_Meaning]] = defaultdict(list)
        # Regions come first, so that "CA" alone after an unknown town means California.
        for code, country in config.items():
            for word in country.get("regions", []):
                self._words[_key(word)].append(_Meaning(Kind.REGION, code))
            for region in country.get("region_codes", []):
                self._codes[region].append(_Meaning(Kind.REGION, code))
        for code, country in config.items():
            for word in [country["name"], *country.get("aliases", [])]:
                self._words[_key(word)].append(_Meaning(Kind.COUNTRY, code))
            for word in [code, *country.get("codes", [])]:
                self._codes[word].append(_Meaning(Kind.COUNTRY, code))
            for word in country.get("cities", []):
                self._words[_key(word)].append(_Meaning(Kind.CITY, code))
        self._longest = max(map(len, self._words))

    @classmethod
    def load(cls, path: Path) -> "PlaceMatcher":
        with path.open("rb") as file:
            return cls(tomllib.load(file))

    def countries(self, places: Iterable[str]) -> set[str]:
        found: set[str] = set()
        for place in places:
            if place.startswith("iso:"):
                found |= {place.removeprefix("iso:")} & self.names.keys()
                continue
            for segment in _SEGMENT.split(place):
                found |= self._resolve(segment)
        return found

    def _resolve(self, segment: str) -> set[str]:
        matches = [
            _Match(meanings, number)
            for number, part in enumerate(segment.split(","))
            for meanings in self._scan(part)
        ]
        only_word = len(_TOKEN.findall(segment)) == 1
        resolved: list[tuple[_Meaning, int]] = []
        for i, match in enumerate(matches):
            if len(match.meanings) > 1 and only_word:
                continue
            before = {m.country for m, _ in resolved[-1:]}
            after = {m.country for later in matches[i + 1 : i + 2] for m in later.meanings}
            meaning = next(
                (m for near in (before, after) for m in match.meanings if m.country in near),
                match.meanings[0],
            )
            if resolved:
                previous, part = resolved[-1]
                if part == match.part - 1 and previous.kind < meaning.kind:
                    resolved.pop()  # "Dublin, OH": the state says which Dublin
            resolved.append((meaning, match.part))
        return {meaning.country for meaning, _ in resolved}

    def _scan(self, part: str) -> Iterable[list[_Meaning]]:
        tokens = _TOKEN.findall(_plain(part))
        lowered = [t.lower() for t in tokens]
        start = 0
        while start < len(tokens):
            for size in range(min(self._longest, len(tokens) - start), 0, -1):
                if meanings := self._words.get(tuple(lowered[start : start + size])):
                    yield meanings
                    start += size
                    break
            else:
                if meanings := self._codes.get(tokens[start]):
                    yield meanings
                start += 1


def is_remote(places: Iterable[str]) -> bool:
    return any(_REMOTE.search(place) for place in places)


def _key(word: str) -> tuple[str, ...]:
    return tuple(_TOKEN.findall(_plain(word).lower()))


def _plain(text: str) -> str:
    """Drop accents: São Paulo becomes Sao Paulo."""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
