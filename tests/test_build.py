import pytest

from skills_gps.build import Job, demand, extract_jobs
from skills_gps.roles import RoleMatcher
from skills_gps.skills import SkillMatcher
from skills_gps.sources import Company, Posting

SKILLS = SkillMatcher({"skills": {"Code": {"Python": [], "Snowflake": []}}})
ROLES = RoleMatcher({"Engineer": "engineer"})
TEXT = "<p>You will work with the team and use {} for our data in the cloud</p>"


def extract(company, *titles, skill="Python"):
    postings = [Posting(company.token, title, TEXT.format(skill)) for title in titles]
    return extract_jobs(postings, [company], SKILLS, ROLES)


def test_same_job_in_several_cities_is_counted_once():
    jobs = extract(Company("greenhouse", "acme", "Acme"), "Engineer", "Engineer ")
    assert jobs == [Job("acme", "Engineer", (0,))]


def test_self_mention_is_dropped():
    company = Company("ashby", "snowflake", "Snowflake")
    assert extract(company, "Engineer", skill="Snowflake")[0].skills == ()


def test_demand_damps_large_employers():
    jobs = [Job("big", "Engineer", (0,))] * 100 + [Job("small", "Engineer", (1,))]
    shares = demand(jobs)
    assert shares[0] == pytest.approx(10 / 11)
    assert shares[1] == pytest.approx(1 / 11)
