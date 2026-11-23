import csv

import pytest

from skills_gps.build import Job, demand, extract_jobs, write_history
from skills_gps.places import PlaceMatcher
from skills_gps.roles import RoleMatcher
from skills_gps.skills import SkillMatcher
from skills_gps.sources import Company, Posting

SKILLS = SkillMatcher({"skills": {"Code": {"Python": [], "Snowflake": []}}})
ROLES = RoleMatcher({"Engineer": "engineer"})
PLACES = PlaceMatcher({"DE": {"name": "Germany"}, "FR": {"name": "France"}})
TEXT = "<p>You will work with the team and use {} for our data in the cloud</p>"


def extract(company, *places, title="Engineer", skill="Python"):
    postings = [Posting(company.token, title, TEXT.format(skill), [p]) for p in places]
    return extract_jobs(postings, [company], SKILLS, ROLES, PLACES)


def test_same_job_in_several_places_is_counted_once_and_keeps_them_all():
    jobs = extract(Company("greenhouse", "acme", "Acme"), "Germany", "Remote, France")
    assert jobs == [Job("acme", "Engineer", (0,), frozenset({"DE", "FR"}), True)]


def test_self_mention_is_dropped():
    company = Company("ashby", "snowflake", "Snowflake")
    assert extract(company, "Germany", skill="Snowflake")[0].skills == ()


def test_demand_damps_large_employers():
    jobs = [Job("big", "Engineer", (0,))] * 100 + [Job("small", "Engineer", (1,))]
    shares = demand(jobs)
    assert shares[0] == pytest.approx(10 / 11)
    assert shares[1] == pytest.approx(1 / 11)


def test_history_reports_a_place_only_with_enough_jobs(tmp_path):
    def jobs(count, country):
        return [Job(f"c{i}", "Engineer", (0,), frozenset({country})) for i in range(count)]

    write_history(jobs(100, "DE") + jobs(99, "FR"), SKILLS, "2026-01-01", tmp_path)
    with (tmp_path / "2026-01-01.csv").open() as file:
        assert {row["place"] for row in csv.DictReader(file)} == {"All", "DE"}
