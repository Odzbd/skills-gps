"""Aggregate postings into the files the site and the history use."""

import csv
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from math import sqrt
from pathlib import Path
from typing import NamedTuple

from .roles import RoleMatcher
from .skills import SkillMatcher
from .sources import Company, Posting
from .text import boilerplate, is_english, to_lines

ALL_ROLES = "All roles"
HISTORY_MIN_POSTINGS = 5


class Job(NamedTuple):
    company: str
    role: str
    skills: tuple[int, ...]


def extract_jobs(
    postings: Iterable[Posting],
    companies: Iterable[Company],
    skills: SkillMatcher,
    roles: RoleMatcher,
) -> list[Job]:
    by_company: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
    for posting in postings:
        lines = to_lines(posting.html)
        if is_english(lines):
            by_company[posting.company].append((posting.title, lines))

    jobs: list[Job] = []
    for company in companies:
        postings_here = by_company[company.token]
        ignored_lines = boilerplate(postings_here)
        ignored_skills = skills.made_by(company.token, company.name)
        seen: dict[tuple[str, tuple[int, ...]], Job] = {}
        for title, lines in postings_here:
            found = skills.find(line for line in lines if line not in ignored_lines)
            ids = tuple(sorted(found - ignored_skills))
            seen[title.strip().lower(), ids] = Job(company.token, roles.find(title), ids)
        jobs += seen.values()
    return jobs


def write_site_data(jobs: list[Job], skills: SkillMatcher, roles: RoleMatcher,
                    date: str, path: Path) -> None:
    """Columnar and compact: the browser needs one row per job, and no job text."""
    company_ids = {token: i for i, token in enumerate(sorted({job.company for job in jobs}))}
    role_ids = {name: i for i, name in enumerate(roles.names)}
    data = {
        "date": date,
        "companies": len(company_ids),
        "roles": roles.names,
        "skills": [list(skill) for skill in skills.skills],
        "jobCompany": [company_ids[job.company] for job in jobs],
        "jobRole": [role_ids[job.role] for job in jobs],
        "jobSkills": [job.skills for job in jobs],
    }
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")


def write_history(jobs: list[Job], skills: SkillMatcher, date: str, directory: Path) -> None:
    by_role: dict[str, list[Job]] = defaultdict(list)
    for job in jobs:
        by_role[ALL_ROLES].append(job)
        by_role[job.role].append(job)

    directory.mkdir(parents=True, exist_ok=True)
    with (directory / f"{date}.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["role", "skill", "postings", "demand"])
        for role, role_jobs in sorted(by_role.items()):
            counts = Counter(skill for job in role_jobs for skill in job.skills)
            shares = demand(role_jobs)
            for skill, count in counts.most_common():
                if count >= HISTORY_MIN_POSTINGS:
                    name = skills.skills[skill].name
                    writer.writerow([role, name, count, f"{shares[skill]:.4f}"])


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
