#!/usr/bin/env python3
"""A single scheduled run: Worker AI storyboard -> render -> public release -> Buffer draft.
The token stays in GitHub Actions secrets. No Facebook publishing/queueing.
"""
import json
import os
from pathlib import Path
import subprocess
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

today=datetime.now(ZoneInfo('Europe/Budapest')).date().isoformat()
filename=f'darkline-{today}.mp4'
tag=f'darkline-video-{today}'
url=f'https://github.com/{repo}/releases/download/{tag}/{filename}'
# Re-runs are idempotent, and already released videos are not regenerated.
existing=gh('release','view',tag,'--repo',repo,check=False)
if existing.returncode!=0:
    plan=post('/video-plan',{})
    if plan.get('status')!='VIDEO_PLAN_OK': raise RuntimeError(f'Unexpected video plan status: {plan.get("status")}')
    if plan.get('date')!=today: raise RuntimeError('Worker timezone/date mismatch')
    Path('video_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
    subprocess.run(['python','video/render_video.py','--plan','video_plan.json','--output',filename],check=True)
    gh('release','create',tag,filename,'--repo',repo,'--title',f'Darkline Studio automatikus videó – {today}',
       '--notes',f'Weboldalalapú, AI-forgatókönyvből készült animált marketingvideó – {today}.')
    print(f'VIDEO_RELEASE_CREATED {url}')
else:
    print(f'EXISTING_VIDEO_RELEASE {url}')
# Buffer receives only the release URL. Worker owns its Buffer API key.
result=post('/video-draft',{'date':today,'videoUrl':url})
if result.get('status') not in ('VIDEO_DRAFT_OK','VIDEO_DRAFT_ALREADY_EXISTS'):
    raise RuntimeError('Buffer video draft creation failed')
print(f'VIDEO_BUFFER_DRAFT_OK savedToBuffer={result.get("savedToBuffer")} publishing={result.get("facebookPublishing")}')
# Keep the public repo active; GitHub may disable cron after 60 days of inactivity.
Path('last-run.json').write_text(json.dumps({'lastSuccessfulVideo':today,'release':url},indent=2)+'\n')
