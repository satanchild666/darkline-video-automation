#!/usr/bin/env python3
"""A single scheduled run: Worker AI storyboard -> render -> public release -> Buffer draft.
The token stays in GitHub Actions secrets. No Facebook publishing/queueing.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import re
from video_dedup import fingerprint, check, save, validate, sha256, MAX_HISTORY
from datetime import datetime
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

BASE='https://darkline-ai-growth.marksz0430.workers.dev'
repo=os.environ['GITHUB_REPOSITORY']
token=os.environ.get('DARKLINE_TEST_TOKEN','')
if len(token)<32: raise SystemExit('DARKLINE_TEST_TOKEN missing/too short; add it in GitHub Actions Secrets')

def post(path,obj):
    req=Request(BASE+path,data=json.dumps(obj,ensure_ascii=False).encode(),method='POST',headers={
        'Content-Type':'application/json','x-darkline-test-token':token})
    try:
        with urlopen(req,timeout=60) as r: result=json.loads(r.read(12000))
    except HTTPError as e:
        raise RuntimeError(f'Worker {path}: HTTP {e.code}, {e.read(1000).decode(errors="replace")}') from None
    return result

def gh(*args,check=True):
    return subprocess.run(['gh',*args],capture_output=True,text=True,check=check)

def history_tags():
    pages=json.loads(gh('api','--paginate','--slurp',f'repos/{repo}/releases?per_page=100').stdout)
    if not isinstance(pages,list) or any(not isinstance(p,list) for p in pages):
        raise RuntimeError('Invalid release inventory')
    tags=[]
    for page in pages:
        for release in page:
            tag_name=release.get('tag_name','')
            if tag_name.startswith('darkline-video-'):
                if not re.fullmatch(r'darkline-video-\d{4}-\d{2}-\d{2}',tag_name):
                    raise RuntimeError('Unexpected video release tag')
                tags.append(tag_name)
    if len(tags)>MAX_HISTORY or len(set(tags))!=len(tags):
        raise RuntimeError('Video history incomplete or exceeds safe limit')
    return tags

def load_history(tags,directory,exclude=None):
    records=[]
    for previous in tags:
        if previous==exclude:continue
        target=Path(directory)/previous
        target.mkdir()
        gh('release','download',previous,'--repo',repo,'--pattern','fingerprint.json','--dir',str(target))
        records.append((previous,validate(json.loads((target/'fingerprint.json').read_text(encoding='utf8')))))
    return records

today=datetime.now(ZoneInfo('Europe/Budapest')).date().isoformat()
filename=f'darkline-{today}.mp4'
tag=f'darkline-video-{today}'
url=f'https://github.com/{repo}/releases/download/{tag}/{filename}'
# Screen both new and existing releases before handing them to Buffer.
tags=history_tags()
with tempfile.TemporaryDirectory(prefix='darkline-history-') as temp:
    history=load_history(tags,temp,exclude=tag)
    if tag not in tags:
        plan=post('/video-plan',{})
        if plan.get('status')!='VIDEO_PLAN_OK':raise RuntimeError(f'Unexpected video plan status: {plan.get("status")}')
        if plan.get('date')!=today:raise RuntimeError('Worker timezone/date mismatch')
        Path('video_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
        subprocess.run(['python','video/render_video.py','--plan','video_plan.json','--output',filename],check=True)
        record=fingerprint(filename,plan)
        check(record,history)
        save('fingerprint.json',record)
        gh('release','create',tag,filename,'fingerprint.json','--repo',repo,'--title',f'Darkline Studio automatikus videó – {today}',
           '--notes',f'Weboldalalapú, ellenőrzött AI-forgatókönyvből készült videó – {today}.')
        print(f'VIDEO_RELEASE_CREATED {url}')
    else:
        gh('release','download',tag,'--repo',repo,'--pattern','fingerprint.json','--pattern',filename,'--dir',temp)
        record=validate(json.loads((Path(temp)/'fingerprint.json').read_text(encoding='utf8')))
        if sha256(Path(temp)/filename)!=record['sha256']:
            raise RuntimeError('Existing video integrity check failed')
        check(record,history)
        print(f'EXISTING_VIDEO_RELEASE {url}')
# Buffer receives only the release URL. Worker owns its Buffer API key.
result=post('/video-draft',{'date':today,'videoUrl':url})
if result.get('status') not in ('VIDEO_DRAFT_OK','VIDEO_DRAFT_ALREADY_EXISTS'):
    raise RuntimeError('Buffer video draft creation failed')
print(f'VIDEO_BUFFER_DRAFT_OK savedToBuffer={result.get("savedToBuffer")} publishing={result.get("facebookPublishing")}')
# Keep the public repo active; GitHub may disable cron after 60 days of inactivity.
Path('last-run.json').write_text(json.dumps({'lastSuccessfulVideo':today,'release':url},indent=2)+'\n')
