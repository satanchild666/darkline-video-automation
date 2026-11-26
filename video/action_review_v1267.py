"""V12.6.7 action-first demo review. No speech, credentials, saving, or publication.
Each clip records real browser pixels before, during and after a safe sample action.
Static focal text remains measured; no simulated UI, cursor or fake click effects.
"""
import io,json,math,subprocess,tempfile,time
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
import demo_renderer_v1266 as demo
import focused_renderer_v124 as r

# family, exact page state, action selector, index, proof selector, resulting focal section
CASES=(
 ("auto","demo_auto_dates",".date-btn",1,".date-btn.active","#time-grid","Nap kiválasztása","Elérhető mintaidősávok"),
 ("menu","demo_menu",'[data-cat="foetel"]',0,'[data-cat="foetel"].active',"#menu-grid","Főételek szűrése","Szűrt étlap"),
 ("salon","demo_salon","#service-list .service-card",0,"#staff-list","#staff-list","Szolgáltatás kiválasztása","Szakemberek megjelenítése"),
 ("crm","demo_crm_board",'.crm-card[data-crm-id="105"]',0,'.crm-card[data-crm-id="105"][aria-pressed="true"]',"#crm-detail","Mintaügyfél megnyitása","Ügyfél részletei"),
 ("web","demo_web","#ds-v23-owner",0,"#ds-v23-panel","#ds-v23-editor","Kezelőfelület megnyitása","Szerkesztő megjelenítése"),
)
def visible(loc):
    return loc.count()>0 and loc.first.is_visible()
def state(page,selector):
    loc=page.locator(selector).first
    return {"visible":visible(loc),"text":loc.inner_text(timeout=3000).strip()[:4000] if visible(loc) else ""}
def screenshot(page):
    return Image.open(io.BytesIO(page.screenshot(animations="disabled"))).convert("RGB")
def measured(page,loc,key):
    data,(x,y,z,cw,ch)=demo.demo_focus(page,loc,0,key)
    if data["projected"]<32 or not data["unobstructed"]:raise RuntimeError("unreadable result")
    return data,(x,y,cw,ch)
def crop(im,box):
    x,y,w,h=box
    return im.crop((2*x,2*y,2*(x+w),2*(y+h))).resize((r.UIW,r.UIH),Image.Resampling.LANCZOS)
def fit(im,w,h):
    scale=min(w/im.width,h/im.height)
    return im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
def capture_case(browser,case):
    family,key,selector,index,proof,result,title,after=case
    width=1100 if family=="crm" else r.VW
    tmp=tempfile.TemporaryDirectory()
    ctx=browser.new_context(viewport={"width":width,"height":r.VH},device_scale_factor=2,service_workers="block",record_video_dir=tmp.name,record_video_size={"width":width,"height":r.VH})
    page=ctx.new_page()
    blocked=[]
    def route_handler(route):
        if route.request.method not in ("GET","HEAD","OPTIONS"):
            blocked.append(route.request.method)
        return demo.demo_guard(route,key)
    ctx.route("**/*",route_handler)
    try:
        page.goto("https://"+demo.HOST+"/demok/"+demo.PATHS[key]+"?skin=dark",wait_until="domcontentloaded",timeout=45000)
        page.wait_for_timeout(1200)
        demo.prepare(page,key)
        action=page.locator(selector).nth(index)
        action.wait_for(state="visible",timeout=15000)
        # Capture a readable close-up of the actual control before acting.
        data,box=measured(page,action,key)
        before_state=state(page,proof)
        before_result=state(page,result)
        before=crop(screenshot(page),box)
        overview=screenshot(page)
        # Actual browser interaction. Mouse input is performed only on allowlisted non-submit controls.
        action.hover(timeout=10000)
        started=time.monotonic()
        page.wait_for_timeout(250)
        demo.click_sample(page,selector,index)
        page.locator(proof).first.wait_for(state="visible",timeout=15000)
        page.wait_for_timeout(850)
        finished=time.monotonic()
        after_state=state(page,proof)
        after_result=state(page,result)
        if not after_state["visible"] or not after_result["visible"]:raise RuntimeError("result missing")
        if before_state==after_state and before_result==after_result:raise RuntimeError("no demonstrated state transition")
        data2,box2=measured(page,page.locator(result).first,key)
        final=crop(screenshot(page),box2)
        # Finalize the real Playwright recording, then extract the click interval.
        vid=page.video;closed=time.monotonic();page.close();ctx.close()
        raw=Path(tmp.name)/"action.webm";vid.save_as(str(raw))
        dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(raw)]))
        lo=max(0,dur-(closed-started));hi=min(dur,dur-(closed-finished))
        if hi-lo<.8:raise RuntimeError("actual browser clip too short")
        frames=Path(tmp.name)/"frames";frames.mkdir()
        subprocess.run(["ffmpeg","-v","error","-ss",str(lo),"-t",str(hi-lo),"-i",str(raw),"-vf","fps=15","-q:v","3",str(frames/"%04d.jpg")],check=True)
        actual=[Image.open(p).convert("RGB") for p in sorted(frames.glob("*.jpg"))]
        if len(actual)<10:raise RuntimeError("actual browser clip incomplete")
        audit={"family":family,"action":selector,"result":result,"before_px":round(data["projected"],2),"after_px":round(data2["projected"],2),
               "state_changed":True,"network_mutations_blocked":len(blocked),"real_browser_frames":len(actual),"recorded_action_seconds":round(hi-lo,3),"publication":False,"narration":False}
        return before,overview,actual,final,audit
    finally:
        ctx.close();tmp.cleanup()

def composition(case,im,phase,n):
    family,key,selector,index,proof,result,title,after=case
    bg,accent,secondary,label=demo.PALETTES[family]
    out=Image.new("RGB",(1080,1920),bg);d=ImageDraw.Draw(out)
    d.rectangle((0,0,1080,12),fill=accent)
    d.text((40,32),"DARKLINE STUDIO   /   VALÓDI DEMÓ",font=r.rig.font(29,True),fill=accent)
    text={"before":title,"action":"Művelet a demóban","result":after}[phase]
    lines=r.rig.wrap(d,text,r.rig.font(58,True),1000)
    if len(lines)>2:raise RuntimeError("title overflow")
    for j,line in enumerate(lines):d.text((40,100+j*70),line,font=r.rig.font(58,True),fill="#f4edff")
    # Two compositions: readable close-up at both ends, full visible viewport
    # during the real operation. No claim that every overview text is 32px.
    part=fit(im,1040,1118);x=(1080-part.width)//2;y=300+(1118-part.height)//2
    d.rounded_rectangle((14,294,1066,1424),radius=22,fill="#0b1019",outline=secondary,width=3)
    out.paste(part,(x,y))
    d=ImageDraw.Draw(out)
    for i,(tag,p) in enumerate((("1. Választás","before"),("2. Művelet","action"),("3. Eredmény","result"))):
        xx=35+i*345;active=phase==p
        d.rounded_rectangle((xx,1462,xx+320,1534),radius=18,fill=secondary if active else bg,outline=accent if active else secondary,width=3)
        d.text((xx+15,1480),tag,font=r.rig.font(29,True),fill="#f4edff" if active else "#bac3d2")
    d.text((40,1620),"Mintaadatok – nincs mentés vagy beküldés",font=r.rig.font(33),fill="#f4edff")
    d.text((40,1710),"darkline-studio.web.app",font=r.rig.font(40,True),fill=accent)
    d.rectangle((40,1845,1040,1853),fill=secondary)
    d.rectangle((40,1845,40+round(1000*(n+1)/180),1853),fill=accent)
    return out

def clip(case,assets,out):
    before,overview,actual,final,audit=assets
    path=out/(case[0]+".mp4")
    proc=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size","1080x1920","-framerate","30","-i","pipe:0","-an","-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p","-threads","3","-movflags","+faststart",str(path)],stdin=subprocess.PIPE)
    try:
        for n in range(180):
            if n<45:im,phase=before,"before"
            elif n<60:im,phase=overview,"action"
            elif n<108:im,phase=actual[min(len(actual)-1,int((n-60)*len(actual)/48))],"action"
            else:im,phase=final,"result"
            proc.stdin.write(composition(case,im,phase,n).tobytes())
    finally:proc.stdin.close()
    if proc.wait():raise RuntimeError("encode failed")
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(path),"-f","null","-"],check=True)
    audit["duration_seconds"]=6;audit["resolution"]="1080x1920"
    (out/(case[0]+".json")).write_text(json.dumps(audit,ensure_ascii=False,indent=2))
    print("V1267_ACTION_PASS",json.dumps(audit,ensure_ascii=False),flush=True)

def main(out):
    out.mkdir(exist_ok=False)
    results=[];failed=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            for case in CASES:
                try:
                    assets=capture_case(browser,case)
                    clip(case,assets,out);results.append(assets[-1])
                except Exception as e:
                    print("V1267_ACTION_FAIL",case[0],str(e)[:800],flush=True);failed.append(case[0])
        finally:browser.close()
    (out/"report.json").write_text(json.dumps({"passed":results,"failed":failed,"voice_calls":0,"publication":False},ensure_ascii=False,indent=2))
    if failed:raise RuntimeError("Action reviews failed: "+str(failed))
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    main(p.parse_args().out)
