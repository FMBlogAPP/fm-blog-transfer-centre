import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'scripts/update_transfers.py'
OLD_ROW = {'id':'9|2026-07-01|1|2|permanent','player_id':9,'player':'Existing Player','date':'2026-07-01','from_id':1,'to_id':2,'type':'Transfer','demo':False}

class Reply(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

def payload(player=10):
    return {'response':[{'player':{'id':player,'name':'New Player'},'transfers':[{'date':'2026-08-01','type':'Transfer','teams':{'in':{'id':2,'name':'B'},'out':{'id':1,'name':'A'}}}]}]}

def run_refresh(responses, *, config_changes=None, existing=True, team_count=3, source=CANDIDATE):
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp); (root/'scripts').mkdir(); (root/'data').mkdir()
        (root/'scripts/update_transfers.py').write_text(source.read_text())
        config={'season':2026,'team_discovery_season':2026,'window_start':'2026-06-01','window_end':'2026-09-15','full_sweep':True,'replace_on_complete_full_sweep':True,'teams_per_run':10,'max_calls_per_run':10,'seconds_between_calls':0,'leagues':[{'id':39,'name':'Premier League','country':'England'}]}
        config.update(config_changes or {})
        (root/'config.json').write_text(json.dumps(config))
        teams={'season':2026,'leagues':{'39':[{'id':i+1,'name':chr(65+i),'league_id':39,'league':'Premier League','country':'England'} for i in range(team_count)]}}
        (root/'data/teams.json').write_text(json.dumps(teams))
        original={'meta':{'updated_at':'2026-09-12T18:32:10Z','live':True},'transfers':[OLD_ROW] if existing else []}
        target=root/'data/transfers.json'; target.write_text(json.dumps(original))
        before=target.read_bytes(); calls=[]; stderr=io.StringIO()
        def mocked(request, **kwargs):
            calls.append(request.full_url)
            answer=responses[min(len(calls)-1,len(responses)-1)]
            if isinstance(answer,Exception): raise answer
            return Reply(json.dumps(answer).encode())
        code=0
        with patch.dict(os.environ,{'API_FOOTBALL_KEY':'test-only-not-a-real-key'}), patch('urllib.request.urlopen',mocked), patch('time.sleep'), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            try: runpy.run_path(str(root/'scripts/update_transfers.py'),run_name='__main__')
            except SystemExit as exc: code=exc.code
        return {'exit':code,'data':json.loads(target.read_text()),'unchanged':target.read_bytes()==before,'calls':len(calls),'stderr':stderr.getvalue()}

class RefreshSafety(unittest.TestCase):
    def test_all_api_failures_keep_bytes_and_timestamp(self):
        r=run_refresh([{'errors':{'subscription':'Unavailable'},'response':[]}],team_count=5)
        self.assertEqual(r['exit'],1);self.assertTrue(r['unchanged']);self.assertEqual(r['calls'],3)
    def test_one_failed_team_never_publishes_partial_replacement(self):
        r=run_refresh([payload(),{'errors':{'server':'Unavailable'}},payload()])
        self.assertEqual(r['exit'],1);self.assertTrue(r['unchanged'])
    def test_http_error_preserves_previous_data(self):
        r=run_refresh([HTTPError('https://example.test',503,'Unavailable',{},io.BytesIO(b'Unavailable'))])
        self.assertEqual(r['exit'],1);self.assertTrue(r['unchanged'])
    def test_quota_error_does_not_fake_complete_sweep(self):
        r=run_refresh([{'errors':{'requests':'You have reached the request limit'}}])
        self.assertEqual(r['exit'],1);self.assertTrue(r['unchanged']);self.assertEqual(r['calls'],1)
    def test_call_budget_exhaustion_uses_actual_checked_count(self):
        r=run_refresh([payload()],config_changes={'max_calls_per_run':1})
        self.assertEqual(r['exit'],1);self.assertTrue(r['unchanged']);self.assertIn('only 1 of 3',r['stderr'])
    def test_selected_subset_is_not_a_full_sweep(self):
        r=run_refresh([payload()],config_changes={'teams_per_run':1})
        self.assertEqual(r['exit'],1);self.assertTrue(r['unchanged'])
    def test_missing_discovery_cannot_replace_with_empty(self):
        r=run_refresh([{'response':[]}],team_count=0)
        self.assertEqual(r['exit'],1);self.assertTrue(r['unchanged'])
    def test_successful_empty_response_cannot_erase_existing_database(self):
        r=run_refresh([{'response':[]}])
        self.assertEqual(r['exit'],1);self.assertTrue(r['unchanged']);self.assertIn('empty replacement refused',r['stderr'])
    def test_verified_complete_sweep_replaces_and_records_actual_count(self):
        r=run_refresh([payload()])
        self.assertEqual(r['exit'],0);self.assertEqual(len(r['data']['transfers']),1)
        self.assertEqual(r['data']['transfers'][0]['player_id'],10);self.assertEqual(r['data']['meta']['teams_checked_last_run'],3)
        self.assertTrue(r['data']['meta']['full_sweep_complete']);self.assertEqual(r['data']['meta']['api_errors_last_run'],0)
    def test_deliberate_incremental_mode_merges_instead_of_replacing(self):
        r=run_refresh([payload()],config_changes={'full_sweep':False,'teams_per_run':1})
        self.assertEqual(r['exit'],0);self.assertEqual({x['player_id'] for x in r['data']['transfers']},{9,10})
        self.assertFalse(r['data']['meta']['full_sweep_complete']);self.assertEqual(r['data']['meta']['teams_checked_last_run'],1)
    def test_initial_verified_empty_database_is_allowed(self):
        r=run_refresh([{'response':[]}],existing=False)
        self.assertEqual(r['exit'],0);self.assertEqual(r['data']['transfers'],[])

if __name__=='__main__': unittest.main(verbosity=2)
