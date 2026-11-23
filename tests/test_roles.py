from pathlib import Path

import pytest

from skills_gps.roles import OTHER, RoleMatcher

ROLES = RoleMatcher.load(Path("data/roles.toml"))


@pytest.mark.parametrize(
    ("title", "role"),
    [
        ("Senior Software Engineer, Payments", "Software engineer"),
        ("Staff Machine Learning Engineer", "Machine learning engineer"),
        ("Data Scientist II", "Data scientist"),
        ("Senior Data Engineer", "Data engineer"),
        ("Product Data Analyst", "Data analyst"),
        ("Site Reliability Engineer", "DevOps & SRE"),
        ("Frontend Engineer", "Frontend engineer"),
        ("Senior iOS Engineer", "Mobile engineer"),
        ("Embedded Software Engineer", "Embedded & firmware engineer"),
        ("Mechanical Engineer", "Hardware & mechanical engineer"),
        ("Security Engineer, Detection", "Security engineer"),
        ("Solutions Architect", "Solutions engineer"),
        ("Product Manager, Growth", "Product manager"),
        ("Product Designer", "Designer & UX researcher"),
        ("Product Marketing Manager", "Product marketing"),
        ("Content Marketing Manager", "Marketing & content"),
        ("Technical Program Manager", "Program & project manager"),
        ("Enterprise Account Executive", "Sales & account executive"),
        ("Customer Success Manager", "Customer success & support"),
        ("Senior Accountant", "Finance & accounting"),
        ("Technical Recruiter", "Recruiting & HR"),
        ("Commercial Counsel", "Legal & compliance"),
        ("Registered Nurse", "Health & life sciences"),
        ("Quantitative Researcher", "Quant researcher & trader"),
        ("Technical Recruiter (Contract)", "Recruiting & HR"),
        ("Product Manager, Driver Experience", "Product manager"),
        ("Dog Walker", OTHER),
    ],
)
def test_title_to_role(title, role):
    assert ROLES.find(title) == role
