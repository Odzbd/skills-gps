"""Map a job title to a role. The first matching pattern wins."""

import re
import tomllib
from pathlib import Path

OTHER = "Other"


class RoleMatcher:
    def __init__(self, patterns: dict[str, str]):
        self.names = [*patterns, OTHER]
        self._patterns = [(n, re.compile(rf"\b(?:{p})\b", re.I)) for n, p in patterns.items()]

    @classmethod
    def load(cls, path: Path) -> "RoleMatcher":
        with path.open("rb") as file:
            return cls(tomllib.load(file))

    def find(self, title: str) -> str:
        return next((name for name, pattern in self._patterns if pattern.search(title)), OTHER)
