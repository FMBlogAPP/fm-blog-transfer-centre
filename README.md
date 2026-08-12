# FM Blog Transfer Centre - €0 automatic version

This repository contains the working FM Blog Transfer Centre.

## What is automatic

GitHub Actions runs four times per day and:
1. discovers clubs in the configured leagues;
2. rotates through clubs to preserve the free API allowance;
3. requests transfer data from API-Football;
4. keeps only transfers inside the configured transfer window;
5. removes duplicates;
6. stores the growing database in `data/transfers.json`;
7. commits fresh data back to this repository.

## One remaining setup step

Create a free API-Football/API-Sports account and copy your API key.

In this repository go to:

Settings -> Secrets and variables -> Actions -> New repository secret

Name the secret exactly:

`API_FOOTBALL_KEY`

Paste the API key as its value.

Do not paste the API key into HTML, JavaScript or `config.json`.

## First run

Go to:

Actions -> Update transfers -> Run workflow

After the run finishes, open `data/transfers.json`. The `meta.live` value should be `true` and the updater will begin filling the transfer database.

After that, the scheduled Action runs automatically at 00:17, 06:17, 12:17 and 18:17 UTC each day.

## Blogger

`blogger-embed.html` is already configured for this repository. Paste its contents into a Blogger Page in HTML view once the first successful update has run.

It reads transfer data directly from:

`https://raw.githubusercontent.com/FMBlogAPP/fm-blog-transfer-centre/main/data/transfers.json`

## Current coverage

The free version rotates through:
- Premier League
- La Liga
- Serie A
- Bundesliga
- Ligue 1
- Primeira Liga
- HNL

The selection is controlled by `config.json`.

## Transfer window

The current configuration tracks transfers from 1 June 2026 through 15 September 2026.

To change the window later, edit `window_start` and `window_end` in `config.json`.

## Limitations

- A €0 setup cannot provide a true real-time worldwide Opta/Transfermarkt-style feed.
- API-Football transfer checks are club/player based, so the free version rotates through configured clubs.
- Transfer fee/type is shown according to the upstream API data.
- FM relevance is an FM Blog rule-based score, not official Football Manager data.
- Player age and position enrichment is intentionally omitted in V1 to conserve API calls.
