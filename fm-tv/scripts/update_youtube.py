#!/usr/bin/env python3
import json, math, os, re, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'config.json'
DATA_DIR = ROOT / 'data'
API_BASE = 'https://www.googleapis.com/youtube/v3'
MODE = os.environ.get('FM_TV_MODE', 'recent').strip().lower()
if MODE not in {'recent','archive'}: MODE='recent'
OUTPUT_PATH = DATA_DIR / ('archive.json' if MODE=='archive' else 'videos.json')
SNAPSHOT_PATH = DATA_DIR / 'view-snapshots.json'

def load_json(path, default=None):
    try:
        with path.open('r', encoding='utf-8') as fh: return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {} if default is None else default

def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(',',':'))
        fh.write('\n')
    tmp.replace(path)

def api_get(endpoint, key, **params):
    params['key']=key
    req=Request(f"{API_BASE}/{endpoint}?{urlencode(params)}", headers={'User-Agent':'FM-Blog-FM-TV/3.0'})
    try:
        with urlopen(req, timeout=30) as response: return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        body=exc.read().decode('utf-8',errors='replace')
        raise RuntimeError(f'YouTube API HTTP {exc.code} for {endpoint}: {body[:500]}') from exc
    except URLError as exc: raise RuntimeError(f'YouTube API connection error for {endpoint}: {exc}') from exc

def parse_dt(v): return datetime.fromisoformat(v.replace('Z','+00:00'))
def parse_duration(v):
    m=re.fullmatch(r'P(?:(?P<days>\d+)D)?T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?',v or '')
    if not m:return 0
    p={k:int(x or 0) for k,x in m.groupdict().items()}
    return p['days']*86400+p['hours']*3600+p['minutes']*60+p['seconds']
def fmt_duration(s):
    if s>=3600:
        h,r=divmod(s,3600);m,sec=divmod(r,60);return f'{h}:{m:02d}:{sec:02d}'
    m,sec=divmod(s,60);return f'{m}:{sec:02d}'
def thumb(ts,fallback):
    for k in ('maxres','standard','high','medium','default'):
        u=(ts or {}).get(k,{}).get('url')
        if u:return u
    return f'https://i.ytimg.com/vi/{fallback}/hqdefault.jpg'
def categorise(title,cats):
    h=f' {title} '.lower()
    for c in cats:
        if any(k.lower() in h for k in c.get('keywords',[])): return c['name']
    return 'FM Videos'
def label(c): return c.get('name') or c.get('handle') or c.get('channelId') or 'unknown'

def resolve_channel(c,key):
    params={'part':'snippet,contentDetails,statistics','maxResults':1}
    if c.get('channelId'): params['id']=c['channelId']
    elif c.get('handle'): params['forHandle']=c['handle'].lstrip('@')
    else: raise ValueError('channelId or handle required')
    items=api_get('channels',key,**params).get('items',[])
    if not items: raise RuntimeError(f'Channel not found: {label(c)}')
    item=items[0]; sn=item.get('snippet',{}); st=item.get('statistics',{})
    uploads=item.get('contentDetails',{}).get('relatedPlaylists',{}).get('uploads')
    if not uploads: raise RuntimeError('Uploads playlist missing')
    hidden=bool(st.get('hiddenSubscriberCount',False))
    subs=None if hidden else int(st.get('subscriberCount',0) or 0)
    return {'id':item['id'],'name':c.get('name') or sn.get('title') or item['id'],'youtubeName':sn.get('title') or c.get('name') or item['id'],
            'handle':c.get('handle'),'avatar':thumb(sn.get('thumbnails',{}),item['id']),'description':sn.get('description','')[:4000],
            'subscriberCount':subs,'subscriberCountHidden':hidden,'youtubeVideoCount':int(st.get('videoCount',0) or 0),
            'uploadsPlaylist':uploads,'featured':bool(c.get('featured')),'channelUrl':f"https://www.youtube.com/channel/{item['id']}"}

def fetch_upload_ids(ch,key,limit,cutoff):
    ids=[];token=None
    while len(ids)<limit:
        p={'part':'contentDetails,snippet','playlistId':ch['uploadsPlaylist'],'maxResults':min(50,limit-len(ids))}
        if token:p['pageToken']=token
        data=api_get('playlistItems',key,**p); stop=False
        for item in data.get('items',[]):
            pub=item.get('contentDetails',{}).get('videoPublishedAt') or item.get('snippet',{}).get('publishedAt')
            if pub:
                try:
                    if parse_dt(pub)<cutoff: stop=True; break
                except ValueError: pass
            vid=item.get('contentDetails',{}).get('videoId') or item.get('snippet',{}).get('resourceId',{}).get('videoId')
            if vid:ids.append(vid)
            if len(ids)>=limit:break
        if stop or len(ids)>=limit:break
        token=data.get('nextPageToken')
        if not token:break
    return ids

def chunks(a,n):
    for i in range(0,len(a),n):yield a[i:i+n]

def apply_daily_views(videos, now):
    history=load_json(SNAPSHOT_PATH, {'snapshots':[]}).get('snapshots',[])
    valid=[]
    for snap in history:
        try:
            dt=parse_dt(snap['capturedAt'])
            if now-dt <= timedelta(hours=36): valid.append((dt,snap))
        except Exception: pass
    target=now-timedelta(hours=24)
    candidates=[(dt,s) for dt,s in valid if timedelta(hours=20)<=now-dt<=timedelta(hours=30)]
    baseline=min(candidates,key=lambda x:abs((x[0]-target).total_seconds())) if candidates else None
    baseline_dt, baseline_snap=(baseline if baseline else (None,None))
    base_views=(baseline_snap or {}).get('views',{})
    for v in videos:
        dv=None
        if baseline_snap:
            if v['id'] in base_views: dv=max(0,int(v['views'])-int(base_views[v['id']]))
            else:
                try:
                    if parse_dt(v['publishedAt'])>=baseline_dt: dv=int(v['views'])
                except Exception: pass
        v['views24h']=dv
    current={'capturedAt':now.isoformat().replace('+00:00','Z'),'views':{v['id']:int(v['views']) for v in videos}}
    snapshots=[s for _,s in valid]
    snapshots.append(current)
    snapshots=snapshots[-40:]
    write_json(SNAPSHOT_PATH,{'updatedAt':current['capturedAt'],'snapshots':snapshots})
    return baseline_dt

def select_featured(videos, baseline_dt):
    if not videos:return None,'Featured'
    if baseline_dt:
        eligible=[v for v in videos if v.get('views24h') is not None]
        if eligible:
            w=max(eligible,key=lambda v:(int(v.get('views24h') or 0),int(v.get('views') or 0)))
            return w['id'],'Most watched in the last 24h'
    w=max(videos,key=lambda v:float(v.get('trendingScore',0)))
    return w['id'],'Trending now · 24h chart warming up'

def main():
    key=os.environ.get('YOUTUBE_API_KEY','').strip()
    if not key: print('ERROR: YOUTUBE_API_KEY is not set.',file=sys.stderr);return 2
    cfg=load_json(CONFIG_PATH); now=datetime.now(timezone.utc)
    if MODE=='archive': age=int(cfg.get('archiveAgeDays',365)); per=int(cfg.get('archiveMaxVideosPerChannel',100)); max_feed=int(cfg.get('maxArchiveVideos',5000))
    else: age=int(cfg.get('recentAgeDays',45)); per=int(cfg.get('recentMaxVideosPerChannel',12)); max_feed=int(cfg.get('maxFeedVideos',800))
    cutoff=now-timedelta(days=age); min_d=int(cfg.get('minDurationSeconds',150))
    channels=[]; resolved=set(); v2c={}; ids=[]
    for cc in cfg.get('channels',[]):
        try:
            ch=resolve_channel(cc,key)
            if ch['id'] in resolved: print(f"SKIP duplicate channel: {ch['name']} ({ch['id']})");continue
            resolved.add(ch['id']); upl=fetch_upload_ids(ch,key,per,cutoff);channels.append(ch)
            for vid in upl:v2c[vid]=ch;ids.append(vid)
            print(f"OK {ch['name']}: {len(upl)} uploads ({MODE})")
        except Exception as exc: print(f'WARN {label(cc)}: {exc}',file=sys.stderr)
        time.sleep(.03)
    seen=set(); ids=[v for v in ids if not(v in seen or seen.add(v))]; videos=[]
    for batch in chunks(ids,50):
        data=api_get('videos',key,part='snippet,contentDetails,statistics,status',id=','.join(batch),maxResults=50)
        for item in data.get('items',[]):
            if item.get('status',{}).get('privacyStatus')!='public':continue
            sn=item.get('snippet',{}); pub=sn.get('publishedAt')
            if not pub:continue
            try: pd=parse_dt(pub)
            except ValueError:continue
            if pd<cutoff:continue
            ds=parse_duration(item.get('contentDetails',{}).get('duration'))
            if ds<min_d:continue
            vid=item['id']; ch=v2c.get(vid)
            if not ch:continue
            st=item.get('statistics',{}); views=int(st.get('viewCount',0) or 0); ageh=max((now-pd).total_seconds()/3600,.25)
            videos.append({'id':vid,'title':sn.get('title','Untitled video'),'description':sn.get('description','')[:240],
                'publishedAt':pub,'duration':fmt_duration(ds),'durationSeconds':ds,'views':views,'likes':int(st.get('likeCount',0) or 0),
                'comments':int(st.get('commentCount',0) or 0),'trendingScore':round(views/math.pow(ageh+2,.68),2),
                'category':categorise(sn.get('title',''),cfg.get('categories',[])),'thumbnail':thumb(sn.get('thumbnails',{}),vid),
                'url':f'https://www.youtube.com/watch?v={vid}','embedUrl':f'https://www.youtube-nocookie.com/embed/{vid}?autoplay=1&rel=0',
                'channelId':ch['id'],'channelName':ch['name'],'channelAvatar':ch['avatar'],'channelUrl':ch['channelUrl'],'featuredCreator':ch['featured']})
    videos.sort(key=lambda v:v['publishedAt'],reverse=True); videos=videos[:max_feed]
    baseline=None
    if MODE=='recent': baseline=apply_daily_views(videos,now)
    cats=[]
    for v in videos:
        if v['category'] not in cats:cats.append(v['category'])
    public=[{k:v for k,v in ch.items() if k!='uploadsPlaylist'} for ch in channels]
    public.sort(key=lambda c:(-(c.get('subscriberCount') or -1),c['name'].lower()))
    fid,flabel=select_featured(videos,baseline)
    payload={'generatedAt':now.isoformat().replace('+00:00','Z'),'mode':MODE,'windowDays':age,'channelCount':len(public),'videoCount':len(videos),
             'categories':cats,'channels':public,'featuredVideoId':fid,'featuredLabel':flabel,'views24hReady':bool(baseline),
             'views24hBaselineAt':baseline.isoformat().replace('+00:00','Z') if baseline else None,'videos':videos}
    write_json(OUTPUT_PATH,payload)
    print(f'Wrote {len(videos)} videos from {len(public)} channels to {OUTPUT_PATH} ({MODE}, {age} days)')
    return 0
if __name__=='__main__': raise SystemExit(main())
