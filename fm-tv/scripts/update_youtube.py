#!/usr/bin/env python3
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"
OUTPUT_PATH = ROOT / "data" / "videos.json"
API_BASE = "https://www.googleapis.com/youtube/v3"


def load_json(path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def api_get(endpoint, key, **params):
    params["key"] = key
    url = f"{API_BASE}/{endpoint}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "FM-Blog-FM-TV/1.0"})
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"YouTube API HTTP {exc.code} for {endpoint}: {body[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"YouTube API connection error for {endpoint}: {exc}") from exc


def parse_iso8601_duration(value):
    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?",
        value or "",
    )
    if not match:
        return 0
    parts = {k: int(v or 0) for k, v in match.groupdict().items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]


def format_duration(seconds):
    if seconds >= 3600:
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}"
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def parse_datetime(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def choose_thumbnail(thumbnails, fallback_id):
    for key in ("maxres", "standard", "high", "medium", "default"):
        url = (thumbnails or {}).get(key, {}).get("url")
        if url:
            return url
    return f"https://i.ytimg.com/vi/{fallback_id}/hqdefault.jpg"


def categorise(title, description, categories):
    haystack = f" {title} {description} ".lower()
    for category in categories:
        for keyword in category.get("keywords", []):
            if keyword.lower() in haystack:
                return category["name"]
    return "FM Videos"


def resolve_channel(config_channel, api_key):
    params = {"part": "snippet,contentDetails", "maxResults": 1}
    if config_channel.get("channelId"):
        params["id"] = config_channel["channelId"]
    elif config_channel.get("handle"):
        params["forHandle"] = config_channel["handle"].lstrip("@")
    else:
        raise ValueError(f"Channel entry needs channelId or handle: {config_channel}")

    data = api_get("channels", api_key, **params)
    items = data.get("items", [])
    if not items:
        raise RuntimeError(f"Channel not found: {config_channel.get('name') or config_channel.get('handle')}")

    item = items[0]
    snippet = item.get("snippet", {})
    uploads = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not uploads:
        raise RuntimeError(f"Uploads playlist missing for {snippet.get('title', item.get('id'))}")

    return {
        "id": item["id"],
        "name": config_channel.get("name") or snippet.get("title") or item["id"],
        "youtubeName": snippet.get("title") or config_channel.get("name") or item["id"],
        "handle": config_channel.get("handle"),
        "avatar": choose_thumbnail(snippet.get("thumbnails", {}), item["id"]),
        "uploadsPlaylist": uploads,
        "featured": bool(config_channel.get("featured")),
        "channelUrl": f"https://www.youtube.com/channel/{item['id']}"
    }


def fetch_upload_ids(channel, api_key, limit):
    data = api_get(
        "playlistItems",
        api_key,
        part="contentDetails,snippet",
        playlistId=channel["uploadsPlaylist"],
        maxResults=min(max(limit, 1), 50),
    )
    ids = []
    for item in data.get("items", []):
        video_id = item.get("contentDetails", {}).get("videoId") or item.get("snippet", {}).get("resourceId", {}).get("videoId")
        if video_id:
            ids.append(video_id)
    return ids


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def main():
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("ERROR: YOUTUBE_API_KEY is not set.", file=sys.stderr)
        return 2

    config = load_json(CONFIG_PATH)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=int(config.get("maxAgeDays", 45)))
    per_channel = int(config.get("maxVideosPerChannel", 10))
    max_feed = int(config.get("maxFeedVideos", 120))
    min_duration = int(config.get("minDurationSeconds", 150))

    channels = []
    video_to_channel = {}
    all_video_ids = []

    for channel_config in config.get("channels", []):
        try:
            channel = resolve_channel(channel_config, api_key)
            ids = fetch_upload_ids(channel, api_key, per_channel)
            channels.append(channel)
            for video_id in ids:
                video_to_channel[video_id] = channel
                all_video_ids.append(video_id)
            print(f"OK {channel['name']}: {len(ids)} uploads")
        except Exception as exc:
            print(f"WARN {channel_config.get('name', channel_config.get('handle', 'unknown'))}: {exc}", file=sys.stderr)
        time.sleep(0.05)

    videos = []
    seen = set()
    unique_video_ids = [vid for vid in all_video_ids if not (vid in seen or seen.add(vid))]

    for batch in chunks(unique_video_ids, 50):
        data = api_get(
            "videos",
            api_key,
            part="snippet,contentDetails,statistics,status",
            id=",".join(batch),
            maxResults=50,
        )
        for item in data.get("items", []):
            if item.get("status", {}).get("privacyStatus") != "public":
                continue

            snippet = item.get("snippet", {})
            published_raw = snippet.get("publishedAt")
            if not published_raw:
                continue
            published = parse_datetime(published_raw)
            if published < cutoff:
                continue

            duration_seconds = parse_iso8601_duration(item.get("contentDetails", {}).get("duration"))
            if duration_seconds < min_duration:
                continue

            video_id = item["id"]
            channel = video_to_channel.get(video_id)
            if not channel:
                continue

            stats = item.get("statistics", {})
            views = int(stats.get("viewCount", 0) or 0)
            likes = int(stats.get("likeCount", 0) or 0)
            comments = int(stats.get("commentCount", 0) or 0)
            age_hours = max((now - published).total_seconds() / 3600.0, 0.25)
            trending_score = views / math.pow(age_hours + 2.0, 0.68)

            title = snippet.get("title", "Untitled video")
            description = snippet.get("description", "")
            category = categorise(title, description, config.get("categories", []))

            videos.append({
                "id": video_id,
                "title": title,
                "description": description[:420],
                "publishedAt": published_raw,
                "duration": format_duration(duration_seconds),
                "durationSeconds": duration_seconds,
                "views": views,
                "likes": likes,
                "comments": comments,
                "trendingScore": round(trending_score, 2),
                "category": category,
                "thumbnail": choose_thumbnail(snippet.get("thumbnails", {}), video_id),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "embedUrl": f"https://www.youtube-nocookie.com/embed/{video_id}?autoplay=1&rel=0",
                "channelId": channel["id"],
                "channelName": channel["name"],
                "channelAvatar": channel["avatar"],
                "channelUrl": channel["channelUrl"],
                "featuredCreator": channel["featured"]
            })

    videos.sort(key=lambda video: video["publishedAt"], reverse=True)
    videos = videos[:max_feed]

    category_names = []
    for video in videos:
        if video["category"] not in category_names:
            category_names.append(video["category"])

    public_channels = [{k: v for k, v in channel.items() if k != "uploadsPlaylist"} for channel in channels]

    payload = {
        "generatedAt": now.isoformat().replace("+00:00", "Z"),
        "channelCount": len(public_channels),
        "videoCount": len(videos),
        "categories": category_names,
        "channels": public_channels,
        "videos": videos,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = OUTPUT_PATH.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    temp_path.replace(OUTPUT_PATH)

    print(f"Wrote {len(videos)} videos from {len(public_channels)} channels to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
