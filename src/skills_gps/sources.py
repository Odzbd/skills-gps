"""Fetch postings from public job-board APIs."""

import csv
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

USER_AGENT = "skills-gps (weekly job-skill statistics)"
TIMEOUT_SECONDS = 90
ATTEMPTS = 3
WORKERS = 6


class Company(NamedTuple):
    board: str
    token: str
    name: str


class Posting(NamedTuple):
    company: str
    title: str
    html: str


class FetchError(Exception):
    """A board could not be read after every attempt."""


def greenhouse(token: str) -> Iterator[tuple[str, str]]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    for job in _get_json(url)["jobs"]:
        yield job["title"], job.get("content") or ""


def ashby(token: str) -> Iterator[tuple[str, str]]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
    for job in _get_json(url)["jobs"]:
        if job.get("isListed", True):
            yield job["title"], job.get("descriptionHtml") or ""


def lever(token: str) -> Iterator[tuple[str, str]]:
    for job in _get_json(f"https://api.lever.co/v0/postings/{token}?mode=json"):
        sections = [job.get("description") or ""]
        for item in job.get("lists", []):
            sections += [item.get("text") or "", item.get("content") or ""]
        sections.append(job.get("additional") or "")
        yield job["text"], "<br>".join(sections)


BOARDS: dict[str, Callable[[str], Iterator[tuple[str, str]]]] = {
    "greenhouse": greenhouse,
    "ashby": ashby,
    "lever": lever,
}


def load_companies(path: Path) -> list[Company]:
    with path.open(newline="", encoding="utf-8") as file:
        return [Company(**row) for row in csv.DictReader(file)]


def fetch_all(companies: list[Company]) -> tuple[list[Posting], list[str]]:
    """Return every posting, plus one message per company that failed."""
    postings: list[Posting] = []
    failures: list[str] = []
    with ThreadPoolExecutor(WORKERS) as pool:
        for company, result in zip(companies, pool.map(_fetch, companies), strict=True):
            if isinstance(result, FetchError):
                failures.append(f"{company.board}/{company.token}: {result}")
            else:
                postings += result
    return postings, failures


def _fetch(company: Company) -> list[Posting] | FetchError:
    try:
        return [Posting(company.token, *job) for job in BOARDS[company.board](company.token)]
    except FetchError as error:
        return error
    except (KeyError, TypeError) as error:
        return FetchError(f"unexpected response: {error!r}")


def _get_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return json.load(response)
        except (OSError, ValueError) as error:
            gone = isinstance(error, urllib.error.HTTPError) and error.code in (404, 410)
            if gone or attempt == ATTEMPTS:
                raise FetchError(str(error)) from error
            time.sleep(2**attempt)
