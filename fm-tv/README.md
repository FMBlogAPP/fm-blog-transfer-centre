# FM Blog FM TV

A lightweight YouTube video hub for FootballManagerBlog.org.

## Architecture

YouTube Data API v3 -> GitHub Actions -> `fm-tv/data/videos.json` -> Blogger embed.

The Blogger page does not load YouTube iframes on initial page load. It fetches one JSON file and thumbnail images. A privacy-enhanced YouTube iframe is only inserted after a visitor clicks a video.

## Files

- `config.json` - creator list, feed limits and category keyword rules
- `scripts/update_youtube.py` - YouTube Data API updater
- `data/videos.json` - generated public feed consumed by Blogger
- `blogger-embed.html` - paste into the Blogger page in HTML view
- `.github/workflows/update-fm-tv.yml` - hourly updater

## Required GitHub secret

Create a repository Actions secret named:

`YOUTUBE_API_KEY`

The key must have YouTube Data API v3 enabled in Google Cloud.

## Blogger installation

1. Run the `Update FM TV` workflow once after adding the secret.
2. Open `fm-tv/data/videos.json` and confirm it contains videos.
3. Open `fm-tv/blogger-embed.html`.
4. Copy the complete file into the FM YouTubers Hub page using Blogger HTML view.
5. Publish/update the page.

## Adding or removing creators

Edit `fm-tv/config.json`. Each creator can use a YouTube `handle` or a direct `channelId`.

Example:

```json
{"name":"Creator Name","handle":"CreatorHandle","featured":true}
```

The workflow also runs when `config.json` changes.

## Feed behaviour

- Updates hourly
- Retrieves the latest uploads from each configured creator
- Enriches videos with duration and public statistics
- Excludes videos shorter than 150 seconds
- Keeps videos from the last 45 days
- Calculates a velocity-style trending score using views and video age
- Categorises videos from title and description keywords
- Displays the real YouTube player only after click
