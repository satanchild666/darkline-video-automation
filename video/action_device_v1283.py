"""Fresh action review: test adaptive device selection on real sample operations.
No audio or customer data. This is not a production advertising export.
"""
import argparse,json,subprocess
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
import adaptive_context_v1283 as adaptive
import integration_v1283 as engine
import action_review_v1283_desktop as desktop_capture
import action_review_v12691 as repaired
import action_review_v1269 as standard
from action_review_v1267 import CASES
from action_device_v1281 import TOPICS,fit_viewport

def action_scene(family,phase):
    case=next(c for c in CASES if c[0]==family)
    p=engine.plan(TOPICS[family])
    matches=[s for s in p['scenes'] if s['selector']==case[5]]
    if not matches:raise ValueError('no catalogue match for '+family)
    s=dict(matches[0])
    # Original scene's context is retained; the header describes the actual action.
    s['heading']=case[7] if phase=='after' else case[6]
    return s
def render(family,assets,out):
    before,actual,after,audit=assets
    s=action_scene(family,'before');device=s['device'];desktop=device=='desktop'
    assert audit['state_changed'] and not audit['crop'] and audit['viewport_coverage']==1
    assert (tuple(audit['before']['viewport_css'])==(1024,640))==desktop
    bg=engine.prior.bg()
    bases={}
    for phase in ('before','action','after'):
        st=action_scene(family,phase);base=engine.header(bg,st)
        im=Image.fromarray(cv2.cvtColor(base,cv2.COLOR_BGR2RGB));d=ImageDraw.Draw(im)
        labels={'before':'1 / 3  •  Kiinduló állapot','action':'2 / 3  •  Valódi művelet','after':'3 / 3  •  Látható eredmény'}
        d.text((540,1515),labels[phase],font=engine.prior.font(40),anchor='mm',fill='#eee8ff')
        d.text((540,1585),'Hang nélküli V12.8.3 demópróba',font=engine.prior.font(30,False),anchor='mm',fill='#b9b3d3')
        bases[phase]=cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2BGR)
    lap=engine.approved.Laptop() if desktop else None
    path=out/(family+'.mp4');tmp=out/(family+'.partial.mp4')
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','19','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(tmp)],stdin=subprocess.PIPE)
    count=0;min_scale=100.;min_width=9999.
    try:
        for n in range(240):
            phase='before' if n<60 else 'action' if n<150 else 'after'
            src=before if phase=='before' else after if phase=='after' else actual[min(len(actual)-1,int((n-60)*len(actual)/90))]
            a=cv2.cvtColor(np.asarray(src),cv2.COLOR_RGB2BGR)
            if desktop:
                frame,_,q=engine.approved.compose(bases[phase],lap,a,n/30,False);frac=1.
            else:
                texture,_,rect=fit_viewport(a);frame=bases[phase].copy();q=engine.prior.device(frame,texture,'mobile',n/30,False);frac=rect[2]/860
            assert np.isfinite(q).all() and q[:,0].min()>=0 and q[:,0].max()<1080 and q[:,1].min()>200 and q[:,1].max()<1429
            screen=min(np.linalg.norm(q[1]-q[0]),np.linalg.norm(q[2]-q[3]));min_width=min(min_width,float(screen))
            min_scale=min(min_scale,float(screen*frac/audit['before']['viewport_css'][0]))
            proc.stdin.write(frame.tobytes());count+=1
            if n in (15,60,120,180,239):cv2.imwrite(str(out/(family+f'-{n}.jpg')),cv2.resize(frame,(540,960)))
        proc.stdin.close();assert proc.wait()==0 and count==240
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(tmp),'-f','null','-'],check=True);tmp.rename(path)
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        if tmp.exists():tmp.unlink()
    audit.update(topic=TOPICS[family],fresh_browser=True,device=device,device_reason=s['device_reason'],frames=count,duration_seconds=8,minimum_final_css_scale=min_scale,minimum_screen_width=min_width,voice_calls=0,publication=False,production_ready=False)
    (out/(family+'.json')).write_text(json.dumps(audit,ensure_ascii=False,indent=2));print('V1283_ACTION_PASS',family,device,flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('family',choices=TOPICS);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);case=next(c for c in CASES if c[0]==a.family)
    scene=action_scene(a.family,'before')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
        try:
            cap=desktop_capture if scene['device']=='desktop' else repaired if a.family in ('auto','salon') else standard
            assets=cap.capture_case(browser,case)
        finally:browser.close()
    render(a.family,assets,a.out)
if __name__=='__main__':main()
