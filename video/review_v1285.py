"""Unified V12.8.5 private review: capture -> verified receipts -> complete MP4.
No voice synthesis, account secret, marketing queue, upload or deployment.
"""
import argparse,json
from pathlib import Path
import cv2
from playwright.sync_api import sync_playwright
import integration_v12852 as engine
import assemble_silent_v1285 as silent
import finalize_v1284 as private
def require(ok,msg):
    if not ok:raise ValueError(msg)
def voice_plan(p,source,timing,manifest):
    m=json.loads(manifest.read_text());t=json.loads(timing.read_text());rows=t['scenes']
    require(m['topic']==p['topic'] and m['source_sha256']==private.sha(source) and m['timing_sha256']==private.sha(timing),'voice source identity')
    require(len(rows)==len(m['scenes'])==len(p['scenes'])==10,'voice scene count')
    for s,a,b in zip(p['scenes'],m['scenes'],rows):
        require(all(a[k]==s[k] for k in ('key','selector','text')) and b['scene']==s['scene'] and b['text']==s['text'],'voice script mismatch')
        require(bool(a.get('action_required'))==bool(s['action_required']),'action plan mismatch')
    return m,t
def counts_for(p,source=None,timing=None,manifest=None):
    if source is None:return [105]*10
    m,t=voice_plan(p,source,timing,manifest);cap=cv2.VideoCapture(str(source))
    try:w,h,fps,total=private.metadata(cap)
    finally:cap.release()
    require((w,h,fps)==(1080,1920,30) and 900<=total<=3600,'source format')
    rows=t['scenes'];edges=[0]+[round((a['end']+b['start'])*15) for a,b in zip(rows,rows[1:])]+[total]
    recorded=t.get('frame_boundaries',edges)
    require(len(recorded)==11 and all(isinstance(v,int) for v in recorded) and recorded[0]==0 and recorded[-1]==total and all(abs(x-y)<=1 for x,y in zip(recorded,edges)),'recorded boundaries mismatch')
    counts=[b-a for a,b in zip(recorded,recorded[1:])]
    require(all(30<=n<=450 for n in counts),'invalid scene duration');return counts
def validate_alias(p,folder):
    for s in p['scenes']:
        r=json.loads((folder/f"scene-{s['scene']:02d}.json").read_text())
        alias=r.get('evidence',{}).get('resolved_capture')
        if alias is not None:
            require((s['key'],s['selector'])==('demo_crm','#ds-v23-editor') and (alias['key'],alias['selector'])==('demo_crm_board','#crm-board'),'unapproved resolved target')
def run(topic,folder,out,source=None,timing=None,manifest=None,capture=False):
    p=engine.plan(topic);supplied=[x is not None for x in (source,timing,manifest)]
    require(not any(supplied) or all(supplied),'provide all three private voice assets or none')
    counts=counts_for(p,source,timing,manifest)
    require(not out.exists(),'output exists')
    if capture:
        folder.mkdir(exist_ok=False,parents=True)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                for s,n in zip(p['scenes'],counts):
                    assets,kind,size,attempts=engine.capture(browser,s);engine.render_scene(p,s,assets,kind,size,attempts,n,folder)
            finally:browser.close()
    validate_alias(p,folder)
    if all(supplied):return private.main(folder,source,timing,manifest,out)
    return silent.silent(topic,folder,out)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('topic');a.add_argument('folder',type=Path);a.add_argument('out',type=Path);a.add_argument('--source',type=Path);a.add_argument('--timing',type=Path);a.add_argument('--manifest',type=Path);a.add_argument('--capture',action='store_true');x=a.parse_args();run(x.topic,x.folder,x.out,x.source,x.timing,x.manifest,x.capture)
