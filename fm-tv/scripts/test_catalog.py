"""Regression checks for FM TV taxonomy and the recent/archive merge."""
import json
import tempfile
import unittest
from pathlib import Path

from catalog import build_catalog, classify_video, write_catalog


class CatalogTests(unittest.TestCase):
    def test_version_and_topic_are_independent(self):
        result = classify_video({'title': 'FM27 USA Wonderkid Watch', 'category': 'FM27'})
        self.assertEqual(result['gameVersion'], 'FM27')
        self.assertIn('Wonderkids', result['topics'])
        self.assertTrue(result['isFm'])

    def test_multiple_topics(self):
        result = classify_video({'title': 'Breaking down the biggest FM27 changes: Training & Tactics', 'category': 'FM27'})
        self.assertEqual(result['gameVersion'], 'FM27')
        self.assertIn('Training', result['topics'])
        self.assertIn('Tactics', result['topics'])

    def test_old_console_and_mobile_versions(self):
        for title, version in [('FM 24 Console tactics', 'FM24'), ('Football Manager 2023 Mobile guide', 'FM23'), ('FM 2012 save', 'FM12')]:
            with self.subTest(title=title):
                result = classify_video({'title': title})
                self.assertEqual(result['gameVersion'], version)
                self.assertTrue(result['isFm'])

    def test_other_games_are_explicitly_separate(self):
        for title in ["Let's Play PROPER FOOTBALL BOSS | Demo First Look", 'First Look at Footy Manager', 'FC 27 CLUBS LIVE']:
            with self.subTest(title=title):
                self.assertFalse(classify_video({'title': title, 'description': 'I also play FM27 Football Manager'})['isFm'])

    def test_unknown_save_titles_and_fm_comparisons_stay(self):
        for title in ['Our Form Makes No Sense', 'Is Footy Manager better than FM27?']:
            with self.subTest(title=title):
                self.assertTrue(classify_video({'title': title})['isFm'])

    def test_channel_promotion_does_not_change_topics_or_version(self):
        result = classify_video({'title': 'A dramatic final', 'description': 'FM27 wonderkids tactics rebuild guide'})
        self.assertEqual(result['gameVersion'], '')
        self.assertEqual(result['topics'], [])

    def test_merge_preserves_new_and_old_and_prefers_recent_counts(self):
        channel = {'id': 'ch', 'name': 'Creator', 'subscriberCount': 100}
        old = {'id': 'same', 'title': 'FM26 Tactics', 'channelId': 'ch', 'publishedAt': '2026-10-19T10:00:00Z', 'views': 10}
        recent = {'generatedAt': '2026-10-21T02:00:00Z', 'channels': [channel], 'videos': [dict(old, views=20, views24h=10), dict(old, id='new')]}
        archive = {'generatedAt': '2026-10-20T02:00:00Z', 'channels': [channel], 'videos': [old, dict(old, id='older')]}
        result = build_catalog(recent, archive)
        rows = {row[0]: dict(zip(result['fields'], row)) for row in result['videos']}
        self.assertEqual(set(rows), {'same', 'new', 'older'})
        self.assertEqual(rows['same']['views'], 20)
        self.assertEqual(rows['same']['views24h'], 10)
        self.assertEqual(result['generatedAt'], recent['generatedAt'])
        self.assertEqual(result['channels'][rows['new']['channelIndex']]['id'], 'ch')

    def test_retired_channel_videos_are_not_discarded(self):
        result = build_catalog({}, {'videos': [{'id': 'old', 'channelId': 'retired', 'channelName': 'Retired creator'}]})
        self.assertEqual(result['videoCount'], 1)
        self.assertEqual(result['channels'][0]['name'], 'Retired creator')

    def test_empty_import_cannot_overwrite_last_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'catalog.json'
            path.write_text('{"last":"good"}')
            with self.assertRaises(ValueError):
                write_catalog(folder)
            self.assertEqual(json.loads(path.read_text()), {'last': 'good'})

    def test_actual_catalog_covers_every_recent_video_and_is_small(self):
        data = Path(__file__).resolve().parents[1] / 'data'
        if not (data / 'videos.json').exists() or not (data / 'archive.json').exists():
            self.skipTest('Local snapshot is not present')
        recent = json.loads((data / 'videos.json').read_text())
        archive = json.loads((data / 'archive.json').read_text())
        result = build_catalog(recent, archive)
        ids = {row[0] for row in result['videos']}
        self.assertTrue({video['id'] for video in recent['videos']}.issubset(ids))
        self.assertTrue({video['id'] for video in archive['videos']}.issubset(ids))
        # Size budget scales with actual rows, not a magic fixed test snapshot.
        encoded = json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode()
        self.assertLess(len(encoded), len(result['videos']) * 270 + 60000)


if __name__ == '__main__':
    unittest.main()
