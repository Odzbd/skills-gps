# Skills GPS

Which skill should you learn next?

Skills GPS reads about 40,000 live job postings from about 300 employers each week and ranks the
skills they ask for. Pick a target role, tick what you already know, and it shows what to
learn next. It is a static page: no account, no server, no tracking.

## Run it

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv run skills-gps fetch
```

```bash
uv run skills-gps build
```

```bash
python3 -m http.server -d site
```

Then open <http://localhost:8000>. Fetching takes about 3 minutes and 400 MB of disk;
building takes about 35 seconds.

## Publish it

1. Push this repository to GitHub.
2. In **Settings > Pages**, set the source to **GitHub Actions**.
3. Run the **Publish** workflow once. After that it runs every Monday.

## Improve it

Everything that shapes the answer is data, not code:

| File | Change it to |
|---|---|
| `data/companies.csv` | Add or remove an employer |
| `data/skills.toml` | Add a skill, an alias, or a phrase to ignore |
| `data/roles.toml` | Change how titles map to roles |

`uv run skills-gps discover` lists frequent phrases the dictionary does not know.

```bash
uv run ruff check && uv run pytest && node --test tests/rank.test.mjs
```

## Method and limits

See [docs/PLAN.md](docs/PLAN.md). In short: the employers are tech-forward and mostly in the
US and Europe, only English postings are read, and a posting shows what employers write, not
what they test for.

## License

MIT. Postings belong to their employers and are not republished here.
