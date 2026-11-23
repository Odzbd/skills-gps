import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from .build import extract_jobs, write_history, write_site_data
from .places import PlaceMatcher
from .roles import RoleMatcher
from .skills import SkillMatcher, tokenize
from .sources import Posting, fetch_all, load_companies
from .text import is_english, to_lines

COMPANIES = Path("data/companies.csv")
SKILLS = Path("data/skills.toml")
ROLES = Path("data/roles.toml")
PLACES = Path("data/places.toml")
HISTORY = Path("data/history")
CACHE = Path(".cache/postings.jsonl")
SITE_DATA = Path("site/data.json")

MAX_FAILED_SHARE = 0.2


def fetch() -> None:
    """Download every posting to the local cache."""
    companies = load_companies(COMPANIES)
    postings, failures = fetch_all(companies)
    for failure in failures:
        print(f"failed: {failure}", file=sys.stderr)
    if len(failures) > MAX_FAILED_SHARE * len(companies):
        sys.exit(f"{len(failures)} of {len(companies)} boards failed; nothing was written")
    CACHE.parent.mkdir(exist_ok=True)
    with CACHE.open("w", encoding="utf-8") as file:
        for posting in postings:
            file.write(json.dumps(posting) + "\n")
    print(f"{len(postings):,} postings from {len(companies) - len(failures)} employers")


def build() -> None:
    """Turn the cache into the site data and a history snapshot."""
    skills, roles, places = (
        SkillMatcher.load(SKILLS),
        RoleMatcher.load(ROLES),
        PlaceMatcher.load(PLACES),
    )
    jobs = extract_jobs(_cached(), load_companies(COMPANIES), skills, roles, places)
    if not jobs:
        sys.exit("no usable postings in the cache")
    date = datetime.now(UTC).date().isoformat()
    write_site_data(jobs, skills, roles, places, date, SITE_DATA)
    write_history(jobs, skills, date, HISTORY)
    skilled = sum(bool(job.skills) for job in jobs) / len(jobs)
    placed = sum(bool(job.countries) or job.remote for job in jobs) / len(jobs)
    print(f"{len(jobs):,} jobs; {skilled:.0%} mention a known skill, {placed:.0%} have a place")


def discover() -> None:
    """List capitalised phrases that many employers use and the dictionary lacks."""
    known = SkillMatcher.load(SKILLS)
    employers: dict[str, set[str]] = defaultdict(set)
    for posting in _cached():
        lines = to_lines(posting.html)
        if not is_english(lines):
            continue
        for line in lines:
            tokens = tokenize(line)[1:]  # the first word is capitalised anyway
            for size in (1, 2):
                for start in range(len(tokens) - size + 1):
                    words = tokens[start : start + size]
                    if all(w[0].isupper() for w in words):
                        employers[" ".join(words)].add(posting.company)
    counts = Counter({phrase: len(who) for phrase, who in employers.items()})
    unknown = (item for item in counts.most_common() if not known.made_by("", item[0]))
    for phrase, count in list(unknown)[:400]:
        print(f"{count:4}  {phrase}")


def _cached() -> list[Posting]:
    if not CACHE.exists():
        sys.exit("run `skills-gps fetch` first")
    with CACHE.open(encoding="utf-8") as file:
        return [Posting(*json.loads(line)) for line in file]


def main() -> None:
    commands = {f.__name__: f for f in (fetch, build, discover)}
    parser = argparse.ArgumentParser(prog="skills-gps")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, command in commands.items():
        subparsers.add_parser(name, help=command.__doc__)
    commands[parser.parse_args().command]()
