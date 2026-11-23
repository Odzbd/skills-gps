"""Aggregate postings into the files the site and the history use."""

import csv
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from math import sqrt
from pathlib import Path
from typing import NamedTuple

from .places import PlaceMatcher, is_remote
from .roles import RoleMatcher
from .skills import SkillMatcher
from .sources import Company, Posting
from .text import boilerplate, is_english, to_lines

ALL_ROLES = "All roles"
ALL_PLACES = "All"
REMOTE = "Remote"
HISTORY_MIN_POSTINGS = 5
MIN_PLACE_JOBS = 100  # a place with fewer jobs is not reported


class Job(NamedTuple):
    company: str
    role: str
    skills: tuple[int, ...]
    countries: frozenset[str] = frozenset()  # empty when unknown
    remote: bool = False


def extract_jobs(
    postings: Iterable[Posting],
    companies: Iterable[Company],
    skills: SkillMatcher,
    roles: RoleMatcher,
    places: PlaceMatcher,
) -> list[Job]:
    by_company: dict[str, list[tuple[Posting, list[str]]]] = defaultdict(list)
    for posting in postings:
        lines = to_lines(posting.html)
        if is_english(lines):
            by_company[posting.company].append((posting, lines))

    jobs: list[Job] = []
    for company in companies:
        postings_here = by_company[company.token]
        ignored_lines = boilerplate((posting.title, lines) for posting, lines in postings_here)
        ignored_skills = skills.made_by(company.token, company.name)
        seen: dict[tuple[str, tuple[int, ...]], Job] = {}
        for posting, lines in postings_here:
            found = skills.find(line for line in lines if line not in ignored_lines)
            ids = tuple(sorted(found - ignored_skills))
            key = posting.title.strip().lower(), ids
            job = seen.get(key) or Job(company.token, roles.find(posting.title), ids)
            seen[key] = job._replace(  # the same job in another place
                countries=job.countries | places.countries(posting.places),
                remote=job.remote or is_remote(posting.places),
            )
        jobs += seen.values()
    return jobs


def reported_countries(jobs: Iterable[Job]) -> list[str]:
    counts = Counter(country for job in jobs for country in job.countries)
    return sorted(country for country, count in counts.items() if count >= MIN_PLACE_JOBS)


def write_site_data(
    jobs: list[Job],
    skills: SkillMatcher,
    roles: RoleMatcher,
    places: PlaceMatcher,
    date: str,
    path: Path,
) -> None:
    """Columnar and compact: the browser needs one row per job, and no job text."""
    company_ids = {token: i for i, token in enumerate(sorted({job.company for job in jobs}))}
    role_ids = {name: i for i, name in enumerate(roles.names)}
    countries = reported_countries(jobs)
    country_ids = {code: i for i, code in enumerate(countries)}
    data = {
        "date": date,
        "companies": len(company_ids),
        "roles": roles.names,
        "skills": [list(skill) for skill in skills.skills],
        "countries": [places.names[code] for code in countries],
        "jobCompany": [company_ids[job.company] for job in jobs],
        "jobRole": [role_ids[job.role] for job in jobs],
        "jobSkills": [job.skills for job in jobs],
        "jobCountries": [
            sorted(country_ids[c] for c in job.countries if c in country_ids) for job in jobs
        ],
        "jobRemote": [int(job.remote) for job in jobs],
    }
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")


def write_history(jobs: list[Job], skills: SkillMatcher, date: str, directory: Path) -> None:
    reported = set(reported_countries(jobs))
    views: dict[tuple[str, str], list[Job]] = defaultdict(list)
    for job in jobs:
        here = [ALL_PLACES, *(job.countries & reported), *([REMOTE] if job.remote else [])]
        for place in here:
            views[place, ALL_ROLES].append(job)
            views[place, job.role].append(job)

    directory.mkdir(parents=True, exist_ok=True)
    with (directory / f"{date}.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["place", "role", "skill", "postings", "demand"])
        for (place, role), view in sorted(views.items()):
            if place != ALL_PLACES and len(view) < MIN_PLACE_JOBS:
                continue
            counts = Counter(skill for job in view for skill in job.skills)
            shares = demand(view)
            for skill, count in counts.most_common():
                if count >= HISTORY_MIN_POSTINGS:
                    name = skills.skills[skill].name
                    writer.writerow([place, role, name, count, f"{shares[skill]:.4f}"])


def demand(jobs: list[Job]) -> dict[int, float]:
    """Share of jobs asking for each skill, with large employers damped."""
    sizes = Counter(job.company for job in jobs)
    weights: Counter[int] = Counter()
    total = 0.0
    for job in jobs:
        weight = 1 / sqrt(sizes[job.company])
        total += weight
        for skill in job.skills:
            weights[skill] += weight
    return {skill: weight / total for skill, weight in weights.items()}
