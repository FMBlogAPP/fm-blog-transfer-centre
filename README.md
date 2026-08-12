# FM Blog Transfer Centre - €0 automatic version

This project uses API-Football's free API allowance, GitHub Actions for scheduled updates, a public JSON data file in GitHub, and Blogger for the actual interface.

## What is automatic

After the one-time setup, GitHub Actions:
1. discovers clubs in the configured leagues;
2. rotates through clubs so the free API allowance is not exhausted;
3. requests transfer data;
4. filters transfers to the configured transfer window;
5. de-duplicates deals;
6. stores the growing transfer database in `data/transfers.json`;
7. commits fresh data back to the repository.

The default workflow runs four times per day.

## One-time setup

### 1. Create a PUBLIC GitHub repository

Create a repository such as:

`fm-blog-transfer-centre`

Upload all files from this package.

Public is required for the simplest €0 setup and for Blogger to read the JSON without authentication.

### 2. Get a free API-Football key

Create a free API-Football/API-Sports account and copy the API key.

Do NOT paste the key into HTML or `config.json`.

### 3. Add the key to GitHub

Repository:

Settings -> Secrets and variables -> Actions -> New repository secret

Name:

`API_FOOTBALL_KEY`

Value:

your API key

### 4. Run it once

GitHub -> Actions -> Update transfers -> Run workflow

After it completes, check:

`data/transfers.json`

The `meta.live` value should be `true`.

### 5. Point Blogger at the JSON

Open `blogger-embed-template.html`.

Replace:

`__RAW_DATA_URL__`

with the raw GitHub URL for `data/transfers.json`, for example:

`https://raw.githubusercontent.com/YOUR_USERNAME/fm-blog-transfer-centre/main/data/transfers.json`

Then paste the result into a Blogger Page in HTML view.

## Coverage and free-tier strategy

The transfer endpoint is polled per club. The default config rotates through:
- Premier League
- La Liga
- Serie A
- Bundesliga
- Ligue 1
- Primeira Liga
- HNL

`teams_per_run` is set to 22 and the Action runs four times per day. That leaves some headroom under a 100-call/day free allowance while league discovery is happening.

More leagues = slower refresh per club.
Fewer leagues = fresher data.

For FM Blog I recommend keeping the big five leagues + Portugal + HNL as the free version.

## Change the transfer window

Edit `config.json`:

```json
"window_start": "2026-06-01",
"window_end": "2026-09-15"
```

For January, change those dates to the January window you want to track.

## Important limitations

- €0 cannot provide an Opta/Transfermarkt-style global feed in real time.
- API-Football's transfer endpoint is queried by club/player, so this project rotates through clubs.
- Fee/type depends on what the upstream API supplies.
- The FM relevance score is rule-based and is not official Football Manager data.
- Player age/position enrichment is deliberately omitted in V1 to preserve API calls.
- Scheduled GitHub Actions in a public repo can be disabled after long repository inactivity. During an active transfer window, the updater's own data commits create repository activity.

## Local preview

From the project folder:

`python -m http.server 8000`

then open:

`http://localhost:8000`

The sample file is intentionally not live until the API updater runs.
