#!/usr/bin/env python3
"""Build the small, backwards-compatible FM TV search catalogue.

Rows are positional according to ``fields``. ``channelIndex`` references the
shared ``channels`` array; thumbnail and watch URLs are derived from the video
ID by the client instead of repeating them thousands of times. The existing
videos.json and archive.json remain available to older page versions.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    'id', 'title', 'channelIndex', 'publishedAt', 'durationSeconds', 'views',
    'views24h', 'category', 'gameVersion', 'topics', 'isFm', 'description',
]
DESCRIPTION_LIMIT = 80
VERSION = re.compile(r'\b(?:fm|football\s+manager)\s*[-:]?\s*(?:20)?(\d{2})\b', re.I)
FM_TITLE = re.compile(r'\b(?:fm(?:\s*(?:20)?\d{2})?|football\s+manager)\b', re.I)
OTHER_GAME = re.compile(
    r'\b(?:proper\s+football\s+boss|footy\s+manager|(?:ea\s+sports\s+)?fc\s*2[4-9]'
    r'|fifa\s*(?:20)?\d{2}|football\s+chairman|we\s+are\s+football'
    r'|soccer\s+manager|football\s+life\s*(?:20)?\d{2}|efootball'
    r'|pro\s+evolution\s+soccer)\b', re.I,
)
TOPICS = {
    'Tactics': r'\b(?:tactic\w*|formation\w*|gegenpress\w*|tiki[ -]taka)\b',
    'Rebuilds': r'\b(?:rebuild\w*|road\s+to\s+glory|rtg|takeover)\b',
    'Wonderkids': r'\b(?:wonderkid\w*|young\s+players|prospect\w*|hidden\s+gems)\b',
    'Experiments': r'\b(?:experiment\w*|simulation\w*|simulated|what\s+if|(?:100|50|20)\s+years)\b',
    'Saves': r'\b(?:episode\w*|ep\.?\s*\d+|career\w*|save\w*|journeyman|glory\s+hunter|park\s+to\s+prem|pentagon|zero\s+to\s+hero)\b',
    'News': r'\b(?:update\w*|patch\w*|feature\w*|release\w*|beta|announcement\w*|news|preview\w*)\b',
    'Guides': r'\b(?:guide\w*|tutorial\w*|how\s+to|beginner\w*|tips)\b',
    'Training': r'\b(?:training|development|developing)\b',
}


def classify_video(video):
    """Classify the title, never a channel's promotional description.

    Unknown titles from the curated FM channels stay included. Only an explicit
    other-game title is excluded, and an explicit Football Manager comparison
    stays included. This avoids hiding save episodes with non-descriptive names.
    """
    title = str(video.get('title') or '')
    legacy = str(video.get('category') or '')
    version = VERSION.search(title)
    game_version = 'FM' + version.group(1) if version else ''
    if not game_version and re.fullmatch(r'FM\d{2}', legacy):
        game_version = legacy
    topics = [name for name, pattern in TOPICS.items() if re.search(pattern, title, re.I)]
    if legacy in TOPICS and legacy not in topics:
        topics.append(legacy)
    is_fm = not bool(OTHER_GAME.search(title) and not FM_TITLE.search(title))
    return {'gameVersion': game_version, 'topics': topics, 'isFm': is_fm}


def build_catalog(recent, archive):
    # Keep every unique upload. Recent data owns 24h growth and current counts.
    videos = {}
    channels = {}
    for feed in (archive, recent):
        for channel in feed.get('channels', []):
            if channel.get('id'):
                channels[channel['id']] = channel
        for video in feed.get('videos', []):
            if video.get('id'):
                videos[video['id']] = video
    ordered = sorted(videos.values(), key=lambda video: video.get('publishedAt', ''), reverse=True)
    # Preserve a video even if its channel disappeared from the current config.
    for video in ordered:
        cid = video.get('channelId') or ''
        if cid not in channels:
            channels[cid] = {
                'id': cid, 'name': video.get('channelName') or 'FM creator',
                'avatar': video.get('channelAvatar') or '',
                'channelUrl': video.get('channelUrl') or f'https://www.youtube.com/channel/{cid}',
            }
    channel_fields = ('id', 'name', 'avatar', 'subscriberCount', 'channelUrl', 'handle', 'featured')
    public_channels = [{key: c.get(key) for key in channel_fields} for c in sorted(
        channels.values(), key=lambda c: (-(c.get('subscriberCount') or 0), c.get('name', '').casefold())
    )]
    channel_indices = {channel['id']: index for index, channel in enumerate(public_channels)}
    rows = []
    for video in ordered:
        values = {
            **video,
            **classify_video(video),
            'channelIndex': channel_indices[video.get('channelId') or ''],
            'description': re.sub(r'\s+', ' ', str(video.get('description') or '')).strip()[:DESCRIPTION_LIMIT],
        }
        rows.append([values.get(field) for field in FIELDS])
    return {
        'schemaVersion': 1,
        'generatedAt': max(str(recent.get('generatedAt') or ''), str(archive.get('generatedAt') or '')),
        'windowDays': max(recent.get('windowDays') or 0, archive.get('windowDays') or 0),
        'videoCount': len(rows), 'channelCount': len(public_channels),
        'channels': public_channels, 'fields': FIELDS, 'videos': rows,
    }


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


def write_catalog(data_dir=None):
    data_dir = Path(data_dir) if data_dir is not None else ROOT / 'data'
    catalog = build_catalog(read_json(data_dir / 'videos.json'), read_json(data_dir / 'archive.json'))
    if not catalog['videos']:
        raise ValueError('Refusing to replace the catalogue with an empty feed.')
    destination = data_dir / 'catalog.json'
    temporary = destination.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(catalog, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    temporary.replace(destination)
    return destination, catalog


if __name__ == '__main__':
    path, payload = write_catalog()
    print(f"Wrote {payload['videoCount']} videos in {path.stat().st_size:,} bytes to {path}")
