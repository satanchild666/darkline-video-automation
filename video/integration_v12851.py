"""V12.8.5 shared catalogue scene capture and compositor. Public sample UI only.
Every topic uses the same scene selection and fallback; no TTS, queue or publishing.
"""
import argparse,hashlib,json,math,subprocess,tempfile
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
import adaptive_context_v1283 as adaptive
import integration_v1283 as engine
import action_review_v1283_desktop as desktop_action
import action_review_v1269 as mobile_action
import action_review_v12691 as repaired_action
from action_review_v1267 import CASES
from action_device_v1281 import fit_viewport
import demo_renderer_v1266 as demo
import focused_renderer_v124 as r
import flagship_review_v114 as public

# Only exact catalogue page/selector combinations may use an action proof.
ACTION_KEYS={'demo_auto_slots':'auto','demo_menu_filter':'menu','demo_salon_staff':'salon','demo_crm_detail':'crm','demo_web_admin':'web'}
ACTION_TARGETS={'auto':'#time-grid','menu':'#menu-grid','salon':'#staff-list','crm':'#crm-detail','web':'#ds-v23-editor'}
VISUAL_ERRORS=('Insufficient surrounding UI context','Actual result is outside visible viewport','Browser recording does not match full viewport screenshots','insufficient readable context','recording mismatch','no meaningful scroll','target outside viewport','Reference views lack visible change','Actual recording shows no meaningful change')
DESKTOP=((1024,640),(720,450),(640,400))
MOBILE=((430,720),(480,800),(384,640))
def require(x,msg):
    if not x:raise RuntimeError(msg)
def action_case(s):
    family=ACTION_KEYS.get(s['key'])
    if family and s['selector']==ACTION_TARGETS[family]:return next(c for c in CASES if c[0]==family)
    return None
def candidates(s):
    first=s['device'];second='mobile' if first=='desktop' else 'desktop'
    return [(kind,size) for kind in (first,second) for size in (DESKTOP if kind=='desktop' else MOBILE)]
NATIVE_ACTIONS={'demo_auto_dates','demo_auto_admin','demo_menu_admin','demo_salon_admin','demo_crm_board'}
REQUIRED_NATIVE=NATIVE_ACTIONS-{'demo_crm_board'}
def plan(key):
    p=adaptive.plan(key)
    for s in p['scenes']:
        s['capture_mode']='verified_action' if action_case(s) else 'native_action' if s['key'] in NATIVE_ACTIONS else 'native_scene'
        s['action_required']=bool(action_case(s) or s['key'] in REQUIRED_NATIVE)
        s['preferred_device']=s['device']
        s['candidates']=[dict(device=k,viewport=list(v)) for k,v in candidates(s)]
    return p
def visible_context(page,kind,size):
    # Conservative final screen width, not the larger review canvas. No CSS zoom.
    vw,vh=size
    if kind=='desktop':scale=760/vw
    else:scale=min(600/vw,(600*720/430)/vh)
    items=page.evaluate("""()=>{const found=new Map();for(const e of document.querySelectorAll('h1,h2,h3,h4,p,label,button,a,input,select,strong,span,li,td,th')){const b=e.getBoundingClientRect(),s=getComputedStyle(e),t=(e.innerText||e.getAttribute('placeholder')||e.value||'').trim();if(t.length<3||t.length>180||b.width<4||b.height<4||b.left<0||b.top<0||b.right>innerWidth||b.bottom>innerHeight||s.visibility!=='visible'||s.display==='none'||Number(s.opacity)<.95)continue;const q=document.elementFromPoint(b.left+b.width/2,b.top+b.height/2);if(!q||!(q===e||e.contains(q)))continue;const f=parseFloat(s.fontSize);if(Number.isFinite(f))found.set(t,Math.max(f,found.get(t)||0));}return [...found.values()]}""")
    projected=[f*scale for f in items]
    data=dict(viewport=list(size),projected_scale=round(scale,4),visible_text_items=len(items),readable_elements=sum(v>=16 for v in projected),threshold_px=16,method='conservative projected CSS geometry, not OCR')
    require(data['visible_text_items']>=5 and data['readable_elements']>=3,'insufficient readable context: '+json.dumps(data));return data
def native_capture(browser,s,kind,size):
    key,selector=s['key'],s['selector'];w,h=size
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td);ctx=browser.new_context(viewport={'width':w,'height':h},device_scale_factor=1,service_workers='block',record_video_dir=td,record_video_size={'width':w,'height':h})
        page=ctx.new_page();actions=[];before=None
        def guard(route):
            from urllib.parse import urlparse
            u=urlparse(route.request.url)
            if route.request.method not in ('GET','HEAD') or u.scheme!='https' or u.hostname!=demo.HOST or u.port not in (None,443) or u.username or u.password or u.path.startswith(('/api/','/auth/','/functions/')):return route.abort()
            if route.request.is_navigation_request():
                if key in demo.PATHS:
                    if not demo.allowed(route.request.url,key):return route.abort()
                elif not public.allowed(route.request.url):return route.abort()
            if u.path.endswith(('advisor-widget.js','smart-advisor.js')):return route.abort()
            return route.continue_()
        ctx.route('**/*',guard)
        original=demo.click_sample
        def recorded_click(p,sel,index=0):
            nonlocal before
            loc=p.locator(sel).nth(index);loc.scroll_into_view_if_needed();p.wait_for_timeout(350)
            if before is None:
                before=Image.open(__import__('io').BytesIO(p.screenshot())).convert('RGB');p.wait_for_timeout(650)
            # The previous demo.prepare controls the allowlist. No form entry or submission.
            permitted={".service-card","#service-list .service-card",".date-btn",'[data-cat="foetel"]',"#ds-v23-owner",'.crm-card[data-crm-id="105"]'}
            require(sel in permitted,'unexpected sample action')
            before_sig=p.evaluate("""()=>[...document.querySelectorAll('.service-card.active,.date-btn.active,[data-cat].active,[aria-pressed=true],#ds-v23-panel,#crm-board,#staff-list,#time-grid')].map(e=>[e.id,e.className,e.getAttribute('aria-pressed'),!!e.getClientRects().length,e.innerText.length])""")
            original(p,sel,index);p.wait_for_timeout(500)
            after_sig=p.evaluate("""()=>[...document.querySelectorAll('.service-card.active,.date-btn.active,[data-cat].active,[aria-pressed=true],#ds-v23-panel,#crm-board,#staff-list,#time-grid')].map(e=>[e.id,e.className,e.getAttribute('aria-pressed'),!!e.getClientRects().length,e.innerText.length])""")
            actions.append(dict(selector=sel,index=index,observable_change=before_sig!=after_sig))
        try:
            if key in demo.PATHS:
                page.goto('https://'+demo.HOST+'/demok/'+demo.PATHS[key]+'?skin=dark',wait_until='domcontentloaded',timeout=45000)
                page.wait_for_timeout(1000)
                demo.click_sample=recorded_click
                try:demo.prepare(page,key)
                finally:demo.click_sample=original
            else:
                page.goto(public.HOST+public.PAGES[key],wait_until='domcontentloaded',timeout=45000);page.wait_for_timeout(1200);r.cleanup(page)
            target=r.root(page,selector);target.wait_for(state='visible',timeout=15000)
            target.evaluate("e=>e.scrollIntoView({block:'start',inline:'nearest',behavior:'instant'})");page.wait_for_timeout(650)
            require(bool((target.inner_text(timeout=3000) or '').strip()),'empty target')
            result=visible_context(page,kind,size)
            if before is None:
                before=Image.open(__import__('io').BytesIO(page.screenshot())).convert('RGB');page.wait_for_timeout(650)
                target.evaluate("""async e=>{let p=e.parentElement;while(p&&!(p.scrollHeight>p.clientHeight+30&&/auto|scroll/.test(getComputedStyle(p).overflowY)))p=p.parentElement;const sc=p||document.scrollingElement;const from=sc.scrollTop;const to=Math.min(sc.scrollHeight-sc.clientHeight,from+Math.round(innerHeight*.23));const start=performance.now();await new Promise(done=>{function tick(now){let q=Math.min(1,(now-start)/1100);sc.scrollTop=from+(to-from)*q*q*(3-2*q);if(q<1)requestAnimationFrame(tick);else done()}requestAnimationFrame(tick)})}""")
                page.wait_for_timeout(350)
            final=Image.open(__import__('io').BytesIO(page.screenshot())).convert('RGB');after_audit=visible_context(page,kind,size);page.wait_for_timeout(900)
            vid=page.video;page.close();ctx.close();raw=tmp/'raw.webm';vid.save_as(str(raw))
            framesdir=tmp/'frames';framesdir.mkdir()
            subprocess.run(['ffmpeg','-v','error','-i',str(raw),'-vf','fps=15','-q:v','3',str(framesdir/'%04d.jpg')],check=True)
            frames=[Image.open(p).convert('RGB') for p in sorted(framesdir.glob('*.jpg'))]
            require(len(frames)>=20 and all(im.size==size for im in frames),'native recording dimensions')
            # Static target may have no scrollable room. Keep genuine recorded frames,
            # never claim a click/scroll unless independent screenshot matching proves it.
            delta=float(np.abs(desktop_action.image_vector(before)-desktop_action.image_vector(final)).mean())
            if s.get('action_required') and not any(a['observable_change'] for a in actions):raise RuntimeError('required sample action not proven')
            if delta>=.5:
                actual,match=desktop_action.locate_action(frames,before,final)
            elif actions:raise RuntimeError('Reference views lack visible change')
            else:
                ref=desktop_action.image_vector(before);err=[float(np.abs(desktop_action.image_vector(f)-ref).mean()) for f in frames]
                i=min(range(len(err)),key=lambda j:err[j]);require(err[i]<=5,'recording mismatch static scene')
                actual=frames[max(0,i-5):min(len(frames),i+10)];match=dict(before_match_error=err[i],after_match_error=err[i],recorded_pixel_delta=delta)
            audit=dict(before=result,after=after_audit,actions=actions,state_changed=bool(any(a['observable_change'] for a in actions) and delta>=.5),scroll_changed=bool(not actions and delta>=.5),crop=False,zoom=False,viewport_coverage=1.0,publication=False,**match)
            return before,actual,final,audit
        finally:
            demo.click_sample=original;ctx.close()
def capture(browser,s):
    case=action_case(s);attempts=[]
    if case:
        preferred=s['device'];family=case[0]
        # Exact already verified action path; preserve its stronger pre-device 22px gate.
        sizes=DESKTOP if preferred=='desktop' else ()
        options=[('desktop',v) for v in sizes]+[('mobile',None)]
        if preferred=='mobile':options += [('desktop',v) for v in DESKTOP]
        for kind,size in options:
            try:
                if kind=='desktop':assets=desktop_action.capture_case(browser,case,viewport=size)
                else:assets=(repaired_action if family in ('auto','salon') else mobile_action).capture_case(browser,case)
                audit=assets[3];require(audit['state_changed'] and not audit['crop'],'action evidence missing')
                actual_size=tuple(audit['before']['viewport_css']);attempts.append(dict(device=kind,viewport=list(actual_size),passed=True));return assets,kind,actual_size,attempts
            except RuntimeError as err:
                if not any(t in str(err) for t in VISUAL_ERRORS):raise
                attempts.append(dict(device=kind,viewport=list(size) if size else None,passed=False,reason=str(err)[:300]))
    else:
        for kind,size in candidates(s):
            try:
                assets=native_capture(browser,s,kind,size);attempts.append(dict(device=kind,viewport=list(size),passed=True));return assets,kind,size,attempts
            except RuntimeError as err:
                if not any(t in str(err) for t in VISUAL_ERRORS):raise
                attempts.append(dict(device=kind,viewport=list(size),passed=False,reason=str(err)[:300]))
    raise RuntimeError('All allowed views failed: '+json.dumps(attempts))
def render_scene(p,s,assets,kind,size,attempts,nframes,out):
    before,actual,after,audit=assets
    require(not audit['crop'] and audit['viewport_coverage']==1 and len(actual)>0,'invalid capture')
    require(not s.get('action_required') or audit.get('state_changed') is True,'required sample action not proven')
    require(30<=nframes<=450,'invalid scene duration')
    st=dict(s,device=kind,viewport=list(size))
    base=adaptive.header(engine.prior.bg(),st);lap=engine.approved.Laptop() if kind=='desktop' else None
    path=out/f"scene-{s['scene']:02d}.mp4";tmp=path.with_suffix('.partial.mp4')
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(tmp)],stdin=subprocess.PIPE)
    count=0;min_width=9999.
    try:
        # Keep a visible starting point and result; real recorded transition between.
        for n in range(nframes):
            qn=n/max(1,nframes-1)
            src=before if qn<.13 else after if qn>.82 else actual[min(len(actual)-1,round((qn-.13)/.69*(len(actual)-1)))]
            a=cv2.cvtColor(np.asarray(src),cv2.COLOR_RGB2BGR);t=n/30+s['scene']*.5
            if kind=='desktop':
                require(size[0]/size[1]==1.6,'desktop aspect mismatch');im,_,q=engine.approved.compose(base,lap,a,t,s['scene']==0)
            else:
                tex,_,_=fit_viewport(a);im=base.copy();q=engine.prior.device(im,tex,'mobile',t,False)
            require(np.isfinite(q).all() and q[:,0].min()>=0 and q[:,0].max()<1080 and q[:,1].min()>=200 and q[:,1].max()<1429,'screen outside safe bounds')
            min_width=min(min_width,float(min(np.linalg.norm(q[1]-q[0]),np.linalg.norm(q[2]-q[3]))))
            proc.stdin.write(im.tobytes());count+=1
            if n in (0,nframes//2,nframes-1):cv2.imwrite(str(out/f"scene-{s['scene']:02d}-{n}.jpg"),cv2.resize(im,(540,960)))
        proc.stdin.close();require(proc.wait()==0 and count==nframes,'encode failed');subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(tmp),'-f','null','-'],check=True);tmp.rename(path)
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        if tmp.exists():tmp.unlink()
    receipt=dict(topic=p['topic'],scene=s['scene'],key=s['key'],selector=s['selector'],text=s['text'],device=kind,preferred_device=s['preferred_device'],capture_mode=s['capture_mode'],action_required=s['action_required'],viewport=list(size),attempts=attempts,frames=count,minimum_screen_width=min_width,video_sha256=engine.sha(path),evidence=audit,fresh_browser=True,voice_calls=0,publication=False,production_ready=False)
    (out/f"scene-{s['scene']:02d}.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print('V1285_SCENE_PASS',s['scene'],kind,size,count,flush=True)
def selftest():
    from collections import Counter
    counts=Counter()
    for t in engine.catalogue.TOPICS:
        p=plan(t.key);old=adaptive.plan(t.key)
        assert len(p['scenes'])==10 and p['voice_bytes']==old['voice_bytes']<=1000 and not p['publication']
        for s,b in zip(p['scenes'],old['scenes']):
            assert all(s[k]==b[k] for k in ('scene','key','selector','text','heading','device','context'))
            assert len(s['candidates'])==6 and s['candidates'][0]['device']==s['preferred_device']
            counts[s['capture_mode']]+=1
    assert sum(counts.values())==510 and counts['native_action']>0
    print('V1285_PLAN_PASS',dict(counts),'51 topics; 510 scenes; all have fallback policy; narration unchanged',flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--selftest',action='store_true');a.add_argument('--topic');a.add_argument('--scenes');a.add_argument('--counts');a.add_argument('--out',type=Path);x=a.parse_args()
    if x.selftest:selftest()
    else:
        p=plan(x.topic);indices=list(map(int,x.scenes.split(',')));counts=list(map(int,x.counts.split(',')));require(len(indices)==len(counts),'count mismatch');x.out.mkdir(exist_ok=False,parents=True)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                for i,n in zip(indices,counts):
                    s=p['scenes'][i];assets,kind,size,attempts=capture(browser,s);render_scene(p,s,assets,kind,size,attempts,n,x.out)
            finally:browser.close()
