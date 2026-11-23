# Plan

## The question

> Which skill should I learn next?

Everything in this project exists to answer that. A feature that does not change
the answer does not ship.

## Decisions

| Topic | Decision | Why |
|---|---|---|
| Data source | Public job-board APIs of Greenhouse, Ashby and Lever | First-party text, documented public reads, no keys, no scraping. LinkedIn and Indeed prohibit automated access. |
| Sample | A curated employer list, `data/companies.csv` | Auditable and extendable by pull request. |
| Skill extraction | A dictionary, `data/skills.toml`, matched on token n-grams | Free, deterministic, testable. Every number can be traced to a phrase. |
| Storage | None. Files only | A weekly batch of ~40k postings does not need a database. |
| Backend | None. The browser does the ranking | One small JSON file; no server to pay for, scale or secure. |
| Frontend | Plain HTML, CSS and JavaScript | One page. A framework would be larger than the app. |
| Hosting | GitHub Pages, rebuilt weekly by GitHub Actions | Free, public, and unattended. |
| Accounts | None. Choices live in the URL and browser storage | Nothing personal is collected, and any view can be shared as a link. |

Rejected: scraping (terms, fragility), aggregator APIs (reposts, truncated text,
redistribution limits), LLM extraction (cost, drift, hard to audit), Postgres and
an API server (nothing to serve).

## Architecture

```
companies.csv ─> fetch ─> .cache/postings.jsonl ─> build ─> site/data.json ─> browser
                                                    │
                        skills, roles, places.toml ─┘└────> data/history/DATE.csv
```

| Module | Job |
|---|---|
| `sources.py` | One adapter per job board; returns `Posting` records |
| `text.py` | HTML to lines, boilerplate removal, language check |
| `skills.py` | Load the dictionary, extract skills |
| `roles.py` | Map a job title to a role |
| `places.py` | Map location text to countries and a remote flag |
| `build.py` | De-duplicate, aggregate, write outputs |
| `cli.py` | `fetch`, `build`, `discover` |
| `site/` | The public page |

## Method

**Cleaning.** Four things distort naive keyword counts, so each is handled:

1. *Company boilerplate.* "We build payments for..." appears in every posting of
   one employer. A line found in over 30% of an employer's postings is dropped.
2. *Self-mentions.* Snowflake's own postings do not count as demand for Snowflake.
3. *Duplicates.* Same employer, title and skills in five cities is one posting that
   keeps all its countries.
4. *Ambiguous words.* "Go", "R" and "Excel" need exact case and, where needed,
   another skill on the same line. Phrases like "go to market" and "R&D" are masked.

**Demand.** The share of postings asking for a skill, each posting weighted by
`1 / sqrt(employer's postings in view)`. Otherwise a few giant employers would
decide the ranking for everyone.

**Priority.** Where demand and your profile meet:

```
overlap  = skills shared with you / the smaller of (job's skills, your skills)
near     = demand, with each job also weighted by overlap
priority = (demand + near) / 2
```

With no skills selected, this equals demand. Skills you have are excluded. The equal
split is a judgement: demand alone gives everyone the same answer, and `near` alone
keeps you inside your current niche. A multiplicative boost was tried first and
rejected: on real data it left the top of the list unchanged for every profile tested.

**Match.** The average share of listed skills you already have, across the role.

**Location.** Text is split into places, then matched against `data/places.toml`.
Neighbouring words settle ambiguity: a state or country after a city overrides it, so
"Dublin, OH" is in the US, and "CA" is California or Canada depending on what precedes it.
Unclear text stays unknown and counts only under All locations. A country needs 100 jobs to
be listed; a view with fewer than 100 is marked as a small sample.

Checked on 2026-11-23: 98% of jobs have a country or are remote. In a random sample of 100
postings, 1 was wrong and 2 were left unknown. Against Lever's own country codes, the text
parser agreed on 3,729 of 3,736.

## How each field is used

| Field | Now | Later |
|---|---|---|
| Job title | Maps to a role; the main filter | Seniority (junior / senior / lead) |
| Company name | Weighting, boilerplate and self-mention removal, "asked by N employers" | Industry filter |
| Description | Skill extraction | Knowledge, experience |
| Location | Country and remote filter; snapshots per country | Salary comparison |
| Salary | - | Median pay with vs. without a skill, *within* a role and region |

Salary is last on purpose. Many postings omit it, and a raw "skill premium" mostly
measures seniority and city. It is only honest after those two are controlled.

## Roadmap

| Phase | Adds | Done when |
|---|---|---|
| **1. Skills (MVP)** | Ranked skills per role, personal priority, roles per skill | Public page, weekly refresh |
| **2. Location** (done) | Country and remote filter | 90% mapped, 95% correct on a sample |
| 3. Required vs. nice-to-have | Must-haves weigh more than bonuses | 90%+ precise on a labelled sample |
| 4. Seniority | Junior, mid, senior and lead views | Same bar |
| 5. Trend | Change against snapshots in `data/history/` | 8+ weekly snapshots exist |
| 6. Experience | Years required | Same bar |
| 7. Knowledge | Degrees, certifications, domains | Same bar |
| 8. Salary | Controlled pay difference | Ranges are parsed for 30%+ of the role |

History is recorded from the first run because it cannot be recovered later.

## Limits

- Employers are tech-forward and mostly US or Europe. This is not the whole labour
  market. Government, small business and most blue-collar work are missing.
- English postings only.
- Remote is recorded per job, not per country. A job that is remote in Canada and on site
  in London counts as remote in both.
- A dictionary cannot see a skill it does not list. `skills-gps discover` surfaces
  frequent unknown phrases for review.
- A posting shows what employers *write*, not what they test for or pay for.

## Responsible use

One request per employer per week, with an identifying user agent. Job text is never
published: only role, employer and matched skills leave the build.
Publishing derived counts is a different thing from republishing postings, but the
boards' terms can change; removing an employer is a one-line edit.
