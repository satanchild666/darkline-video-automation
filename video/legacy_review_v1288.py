"""Separate legacy V11.3 script review, not part of the 51-topic catalogue.
Only public sample UI; no voice files, TTS, queue, publishing or deployment.
"""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
import integration_v12852 as e
import private_review_v113 as legacy
import action_review_v1283_desktop as action

# A selected time is a local sample selection, never an actual booking.
SLOT_CASE=('auto','demo_auto_slots','.time-btn:not([disabled])',0,'.time-btn.active','#time-grid','Idősáv kiválasztása','Kiválasztott mintaidősáv')
MAP={
 'auto':[('demo_auto','#services-list'),('demo_auto','#services-list'),('demo_auto','#services-list'),('demo_auto_dates','#date-scroller'),('demo_auto_dates','#date-scroller'),('demo_auto_slots','#time-grid'),('demo_auto_slots','#time-grid'),('demo_auto_admin','#ds-v23-editor'),('demo_auto_admin','#ds-v23-editor'),('demo_auto','#services-list')],
 'menu':[('demo_menu','#menu-grid'),('demo_menu','#menu-grid'),('demo_menu_filter','#menu-grid'),('demo_menu','#menu-grid'),('demo_daily','#public-app'),('demo_daily','#public-app'),('demo_menu_admin','#ds-v23-editor'),('demo_menu_admin','#ds-v23-editor'),('demo_menu','#menu-grid'),('demo_menu','#menu-grid')]}
EDGES={'auto':[0,124,253,410,564,672,811,928,1056,1187,1400],'menu':[0,180,338,507,665,831,975,1154,1335,1510,1722]}
def plan(family):
    p={'topic':'legacy_v113_'+family,'scenes':[]}
    for i,((heading,shot,text),(key,selector)) in enumerate(zip(legacy.STORIES[family],MAP[family])):
        device='desktop' if key.endswith('_admin') else 'mobile'
        # Alternate native device for distinct narrative angles, unchanged screen models.
        if (family,i) in {('auto',0),('menu',0),('menu',8)}:device='desktop'
        if (family,i) in {('auto',8)}:device='mobile'
        s=dict(scene=i,heading=heading,key=key,selector=selector,text=text,device=device,preferred_device=device,device_reason='legacy script',context=heading,capture_mode='native_action' if key in e.NATIVE_ACTIONS else 'verified_action' if key in e.ACTION_KEYS else 'native_scene',action_required=bool(key in e.REQUIRED_NATIVE or key in e.ACTION_KEYS))
        p['scenes'].append(s)
    return p
def capture(browser,family,s):
    if family=='auto' and s['scene']==6:
        attempts=[]
        for kind,size in e.candidates(s):
            try:
                assets=action.capture_case(browser,SLOT_CASE,viewport=size)
                assert assets[3]['state_changed'] is True
                attempts.append(dict(device=kind,viewport=list(size),passed=True))
                return assets,kind,size,attempts
            except RuntimeError as err:
                if not any(t in str(err) for t in e.VISUAL_ERRORS):raise
                attempts.append(dict(device=kind,viewport=list(size),passed=False,reason=str(err)[:300]))
        raise RuntimeError('selected time failed all visual gates')
    return e.capture(browser,s)
def main(family,indices,out):
    p=plan(family);out.mkdir(parents=True,exist_ok=False)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
        try:
            for i in indices:
                s=p['scenes'][i];assets,kind,size,attempts=capture(browser,family,s)
                e.render_scene(p,s,assets,kind,size,attempts,EDGES[family][i+1]-EDGES[family][i],out)
        finally:browser.close()
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('family',choices=MAP);a.add_argument('--scenes',required=True);a.add_argument('--out',type=Path,required=True);x=a.parse_args();main(x.family,list(map(int,x.scenes.split(','))),x.out)
