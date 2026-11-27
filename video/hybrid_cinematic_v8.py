"""V8 hybrid cinematic review. Real timed browser clips, no artificial tail padding.
No publication, Buffer calls, bookings or admin saves."""
from pathlib import Path
import math,time,subprocess,tempfile,json
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageChops
from playwright.sync_api import sync_playwright
import style_preview_v2 as v2
import depth_preview_v4 as v4
import cinematic_preview_v5 as v5
import motion_cinematic_v6 as v6
import cinematic_live_v7 as v7
OUT=Path("hybrid-preview-v8");OUT.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30
DUR=[3.,3.,3.5,3.5,4.,4.]
WHITE="#f4f4fa";PURPLE="#c2a9ff";MUTED="#c1bfce"
ease=v4.ease;smooth=v4.smooth;text=v4.text;label=v4.label;card=v4.card;title=v6.title
CSS=v7.CSS+" .dl-advisor-hint,.dl-advisor-widget,.dl-advisor-tab,#darkline-ai-advisor,#darkline-ai-advisor-widget,[aria-label='Digitális megoldásajánló']{display:none!important;pointer-events:none!important}"
def clean(page):
    # Hide only promotional overlays in this isolated capture browser, not on the website.
    page.add_style_tag(content=CSS)
    for loc in [page.get_by_role("button",name="Most nem",exact=True),page.locator(".ds-demo-close"),page.locator('button[aria-label="Ajánló tipp elrejtése"]')]:
        try:
            if loc.first.is_visible():loc.first.click(timeout=1200)
        except Exception:pass
    page.evaluate("""()=>{for(const el of document.querySelectorAll('aside,div,section')){if(el.children.length<4&&el.textContent.trim().startsWith('Kapcsolódó ötlet:')&&el.textContent.length<180){el.style.setProperty('display','none','important')}}}""")
    page.wait_for_timeout(150)
def prepare(page):
    v7.prepare(page);clean(page)
def pan(page,loc):
    loc.evaluate("(el)=>el.scrollIntoView({behavior:'smooth',block:'center'})")
    page.wait_for_timeout(650)
def clip(raw,name,start,end,target):
    duration=end-start
    if duration<1.2:raise RuntimeError("Clip too short: "+name)
    directory=OUT/name;directory.mkdir(exist_ok=True)
    # No tpad or repeated end frame. Fit the recorded interval to the scene.
    # A small trim margin avoids losing a frame due to container rounding.
    ratio=(target+.10)/duration
    subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{start:.4f}","-t",f"{duration:.4f}","-i",str(raw),"-vf",f"setpts={ratio:.8f}*PTS,fps=30","-frames:v",str(round(target*FPS)),"-q:v","3",str(directory/"%04d.jpg")],check=True)
    count=len(list(directory.glob("*.jpg")))
    if count<round(target*FPS)-2:raise RuntimeError(f"Clip incomplete: {name} {count}")
    print("REAL_CLIP_OK",name,"source_seconds",round(duration,3),"frames",count,"no_tail_padding",flush=True)
    return {"clip":name,"source_seconds":round(duration,3),"frames":count,"target_seconds":target,"tail_padding":False}
def record(browser,desktop=False):
    size={"width":1280,"height":800} if desktop else {"width":600,"height":1120}
    ctx=browser.new_context(viewport=size,device_scale_factor=1,record_video_dir=str(OUT/"raw"),record_video_size=size)
    page=ctx.new_page();prepare(page)
    segments=[]
    if not desktop:
        service=page.locator(".service-card").first
        service.scroll_into_view_if_needed();clean(page);page.wait_for_timeout(350)
        start=time.monotonic()
        page.wait_for_timeout(300);service.click(timeout=12000);page.locator(".service-card.active").wait_for()
        page.wait_for_timeout(600)
        day=page.locator(".date-btn").nth(1);pan(page,day)
        page.wait_for_timeout(250)
        boundary=time.monotonic()
        segments.append(("live_service",start,boundary,DUR[1]))
        day.click(timeout=12000);page.locator(".date-btn.active").wait_for()
        page.wait_for_timeout(550)
        slot=page.locator(".time-btn:not([disabled])").first;slot.wait_for(timeout=12000);pan(page,slot)
        page.wait_for_timeout(300);slot.click(timeout=12000);page.locator(".time-btn.active").wait_for()
        page.wait_for_timeout(650);end=time.monotonic()
        segments.append(("live_slots",boundary,end,DUR[2]))
        selected=slot.inner_text().strip()
        if not selected:raise RuntimeError("Actual slot text missing")
        (OUT/"selected.txt").write_text(selected,encoding="utf8")
        clean(page);slot.screenshot(path=str(OUT/"slot_selected.png"),animations="disabled")
        page.locator("#time-grid").screenshot(path=str(OUT/"slots_after.png"),animations="disabled")
        slot.scroll_into_view_if_needed();page.screenshot(path=str(OUT/"phone_slots.png"),animations="disabled")
    else:
        target=page.locator("#ds-v23-owner");target.scroll_into_view_if_needed();clean(page);page.wait_for_timeout(350)
        start=time.monotonic();page.wait_for_timeout(300);target.click(timeout=12000)
        page.locator("#ds-v23-panel").wait_for(state="visible")
        editor=page.locator("#ds-v23-editor");pan(page,editor)
        page.wait_for_timeout(450)
        # Scroll inside the actual editor's scroll container if present.
        editor.evaluate("""el=>{let p=el;while(p&&p.scrollHeight<=p.clientHeight+8)p=p.parentElement;if(p)p.scrollBy({top:220,behavior:'smooth'});else window.scrollBy({top:220,behavior:'smooth'})}""")
        page.wait_for_timeout(850);end=time.monotonic()
        segments.append(("live_admin",start,end,DUR[4]))
    # Compute all timestamps relative to the finalized browser recording end.
    closed_at=time.monotonic();video=page.video;page.close();ctx.close()
    raw=OUT/("admin.webm" if desktop else "mobile.webm");video.save_as(str(raw))
    duration=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(raw)]).decode().strip())
    report=[]
    for name,a,b,target in segments:
        lo=max(0,duration-(closed_at-a));hi=min(duration,duration-(closed_at-b))
        report.append(clip(raw,name,lo,hi,target))
    return report
def capture_stills():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        page=browser.new_page(viewport={"width":480,"height":900},device_scale_factor=2,is_mobile=True,has_touch=True)
        page.goto(v2.URL,wait_until="domcontentloaded",timeout=45000)
        page.locator(".service-card").first.wait_for(timeout=20000)
        for loc in [page.get_by_role("button",name="Most nem",exact=True),page.locator(".ds-demo-close"),page.locator('button[aria-label="Ajánló tipp elrejtése"]')]:
            try:
                if loc.first.is_visible():loc.first.click(timeout=1500)
            except Exception:pass
        page.add_style_tag(content="#darkline-premium-guide,.dlg-avatar,.dlg-thought,.dlg-thought-tour,.dl-advisor-widget,#darkline-ai-advisor-toggle{display:none!important;pointer-events:none!important} .time-btn.active{color:#071017!important;font-weight:800!important} .time-btn.active *{color:#071017!important}")
        clean(page)
        page.wait_for_timeout(350)
        def shot(loc,name):
            loc.scroll_into_view_if_needed(timeout=12000);page.wait_for_timeout(200)
            loc.screenshot(path=str(OUT/(name+".png")),animations="disabled",timeout=15000)
        service=page.locator(".service-card").first
        shot(page.locator("#services-list"),"services");shot(service,"service_before")
        service.scroll_into_view_if_needed();page.screenshot(path=str(OUT/"phone_services.png"),animations="disabled")
        service.click(timeout=12000);page.locator(".service-card.active").wait_for()
        shot(service,"service_after")
        day=page.locator(".date-btn").nth(1)
        shot(page.locator("#date-scroller"),"dates_before")
        day.click(timeout=12000);page.locator(".date-btn.active").wait_for()
        shot(page.locator("#date-scroller"),"dates_after")
        slot=page.locator(".time-btn:not([disabled])").first
        slot.wait_for(timeout=12000);shot(page.locator("#time-grid"),"slots_before")
        slot.click(timeout=12000);page.locator(".time-btn.active").wait_for()
        selected=slot.inner_text().strip()
        if not selected:raise RuntimeError("Selected time label missing")
        (OUT/"selected.txt").write_text(selected,encoding="utf8")
        shot(page.locator("#time-grid"),"slots_after");shot(slot,"slot_selected")
        slot.scroll_into_view_if_needed();page.screenshot(path=str(OUT/"phone_slots.png"),animations="disabled")
        page.locator("#ds-v23-owner").click(timeout=12000);page.locator("#ds-v23-panel").wait_for(state="visible")
        editor=page.locator("#ds-v23-editor");editor.wait_for(state="visible")
        shot(editor,"admin")
        editor.scroll_into_view_if_needed();page.screenshot(path=str(OUT/"phone_admin.png"),animations="disabled")
        # Second actual browser viewport: desktop admin, no form submission.
        desk=browser.new_page(viewport={"width":1366,"height":900},device_scale_factor=1.5)
        desk.goto(v2.URL,wait_until="domcontentloaded",timeout=45000)
        desk.locator("#ds-v23-owner").wait_for(timeout=20000)
        for loc in [desk.get_by_role("button",name="Most nem",exact=True),desk.locator(".ds-demo-close")]:
            try:
                if loc.first.is_visible():loc.first.click(timeout=1500)
            except Exception:pass
        desk.add_style_tag(content="#darkline-premium-guide,.dl-advisor-widget,#darkline-ai-advisor-toggle{display:none!important;pointer-events:none!important}")
        clean(desk)
        desk.locator("#ds-v23-owner").click(timeout=12000)
        desk.locator("#ds-v23-panel").wait_for(state="visible")
        desk.locator("#ds-v23-editor").scroll_into_view_if_needed()
        desk.wait_for_timeout(250)
        desk.screenshot(path=str(OUT/"desktop_admin.png"),animations="disabled")
        browser.close()
    print("REAL_UI_STATES_OK before/after selections and admin; no booking submitted",flush=True)


def capture():
    capture_stills()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        report=record(browser)+record(browser,True)
        browser.close()
    (OUT/"capture_report.json").write_text(json.dumps(report,indent=2),encoding="utf8")
def read_frame(name,t,total):
    files=LIVE[name];idx=min(len(files)-1,max(0,round(t/total*(len(files)-1))))
    with Image.open(files[idx]) as im:return im.convert("RGB")
def brand(im,s,t):
    old=v5.DUR
    try:v5.DUR=DUR;v5.brand(im,s,t)
    finally:v5.DUR=old
def background(t,s):
    old=v7.DUR
    try:im=v7.background(t,s)
    finally:v7.DUR=old
    # A soft moving light pool and separate foreground highlights, no strobe.
    light=Image.new("RGB",(270,480));d=ImageDraw.Draw(light)
    phase=sum(DUR[:s])+t
    x=int(135+95*math.sin(phase*.85));y=260
    d.ellipse((x-70,y-95,x+70,y+95),fill=(27,13,55))
    light=light.filter(ImageFilter.GaussianBlur(32)).resize((W,H),Image.Resampling.BILINEAR)
    return ImageChops.screen(im,light)
def hero(im,a,t,final=False):
    # V6's fast opening orbit with a wider center separation once settled.
    p=ease(t/.72);ang=-1.10+1.85*p+.50*t
    cy=1080 if not final else 1000
    laptopw=760 if not final else 680
    v5.laptop(im,a["laptop"],540+35*math.sin(ang),cy-115,laptopw,laptopw*.61,18*math.cos(ang),5,-4*math.sin(ang),t)
    for key,z in sorted([("dev_services",ang),("dev_slots",ang+math.pi)],key=lambda k:math.sin(k[1])):
        depth=math.sin(z);scale=.80+.14*depth
        cx=540+350*math.cos(z);yy=cy+100+68*depth
        if final:scale*=.83;yy-=35
        v7.phone(im,a[key],cx,yy,380*scale,710*scale,30*math.cos(z),5,-12*math.cos(z),t)
def live_card(im,src,t,duration,y=605,h=1000):
    # Mild continuous reframing: actual video remains the primary content.
    q=smooth(t/duration);w=int(580+100*q);x=(W-w)//2
    d=ImageDraw.Draw(im);d.rounded_rectangle((x-5,y-5,x+w+5,y+h+5),radius=32,outline="#65538e",width=3)
    card(im,src,x,y,w,h)
def frame(s,t,a):
    im=background(t,s);q=smooth(t/DUR[s])
    if s==0:
        hero(im,a,t)
        label(im,"AUTÓSZERVIZ • ÉLŐ DEMÓ")
        title(im,"Még mindig",72,292,99,WHITE,t);title(im,"telefonon?",72,412,120,PURPLE,t,.07)
        text(im,76,555,"Mutasd meg a szabad időpontokat online.",37,b=False)
        card(im,a["service_after"],100,1515,880,150)
    elif s==1:
        label(im,"01 / SZOLGÁLTATÁS")
        title(im,"Egyértelmű",72,290,91,WHITE,t);title(im,"választás.",72,402,110,PURPLE,t,.08)
        text(im,76,540,"A vendég kiválasztja, mire van szüksége.",38,b=False)
        live_card(im,read_frame("live_service",t,DUR[s]),t,DUR[s],610,855)
        # Genuine selected service enlarged independently of the recording.
        if t>1.0:card(im,a["service_after"],90,1475,900,145)
        text(im,78,1660,"Valódi ügyfélnézet",35)
    elif s==2:
        label(im,"02 / IDŐPONT")
        title(im,"Nap. Idősáv.",72,290,96,WHITE,t);title(im,"Kész.",72,407,112,PURPLE,t,.08)
        live_card(im,read_frame("live_slots",t,DUR[s]),t,DUR[s],545,950)
        if t>2.8:v5.floating(im,a["selected"],225,1490,630,155,t)
        text(im,78,1660,"Az elérhető idősávok láthatók.",36)
    elif s==3:
        label(im,"ÜGYFÉLNÉZET • DEMÓ")
        title(im,"Az időpont",72,295,93,WHITE,t);title(im,"látható.",72,405,112,PURPLE,t,.1)
        v7.phone(im,a["dev_slots"],540-120*q,1060,550+60*q,1000,-29+45*q,6,-9+12*q,t)
        if t>1.1:
            r=ease((t-1.1)/.55);card(im,a["slots_after"],int(530-70*r),1030,510,310)
        v5.floating(im,a["selected"],180+int(75*q),1460,720,155,t)
        text(im,78,1660,"Kiválasztott idősáv • nincs végleges foglalás",30,b=False)
    elif s==4:
        label(im,"03 / SAJÁT ADMIN");title(im,"Te irányítod.",72,295,99,WHITE,t)
        text(im,76,430,"A szolgáltatásaid saját kezelőfelületen.",39,b=False)
        actual=read_frame("live_admin",t,DUR[s])
        if t<1.6:
            v5.laptop(im,v5.laptop_texture(actual),540,990,920,560,-24+38*q,4,-5+6*q,t)
        else:
            r=ease((t-1.6)/.45)
            card(im,actual,72,650-int(40*r),936,650)
        card(im,a["admin"],95,1330,890,270,True,.2+.55*q)
        text(im,78,1660,"Tulajdonosi nézet • valódi demó",36)
    else:
        hero(im,a,t,True);label(im,"PRÓBÁLD KI")
        title(im,"Ne csak nézd.",72,290,99,WHITE,t);title(im,"Teszteld.",72,410,132,PURPLE,t,.1)
        text(im,76,565,"Autószerviz-időpontfoglaló",45,b=False)
        d=ImageDraw.Draw(im);d.rounded_rectangle((72,1390,1008,1515),radius=35,fill="#c2a9ff")
        text(im,105,1428,"Bemutatóstúdió megnyitása  →",45,"#151020",limit=870)
        text(im,76,1560,"darkline-studio.web.app",43);text(im,76,1640,"Valós, kipróbálható funkciók.",34,MUTED,False)
    brand(im,s,t);return im
def render():
    global LIVE
    LIVE={n:sorted((OUT/n).glob("*.jpg")) for n in ["live_service","live_slots","live_admin"]}
    a={p.stem:Image.open(p).convert("RGB") for p in OUT.glob("*.png")}
    for k in ["services","slots","admin"]:a["dev_"+k]=v4.phone_texture(a["phone_"+k])
    a["laptop"]=v5.laptop_texture(a["desktop_admin"]);a["selected"]=(OUT/"selected.txt").read_text(encoding="utf8")
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td);silent=tmp/"silent.mp4";audio=tmp/"sound.wav"
        cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","pipe:0","-c:v","libx264","-preset","fast","-crf","17","-pix_fmt","yuv420p","-threads","3",str(silent)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE);prev=None
        try:
            for s,d in enumerate(DUR):
                for n in range(round(d*FPS)):
                    im=frame(s,n/FPS,a)
                    # Preserve the uninterrupted mobile recording across the two scenes.
                    if prev is not None and s!=2 and n<8:im=v6.transition(prev,im,n/FPS)
                    if n in [12,round(d*FPS)//2]:im.save(OUT/f"scene-{s+1}-{n:03d}.jpg",quality=94)
                    proc.stdin.write(im.tobytes())
                prev=im
        finally:proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError("Encoding failed")
        old=v5.DUR
        try:v5.DUR=DUR;v5.sound(audio,sum(DUR))
        finally:v5.DUR=old
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(audio),"-c:v","copy","-c:a","aac","-b:a","160k","-movflags","+faststart","-shortest",str(OUT/"Darkline_hybrid_V8.mp4")],check=True)
    sheet=Image.new("RGB",(1620,960),"#11111b")
    for i,p in enumerate(sorted(OUT.glob("scene-*.jpg"))):sheet.paste(Image.open(p).resize((270,480),Image.Resampling.LANCZOS),((i//2)*270,(i%2)*480))
    sheet.save(OUT/"storyboard.jpg",quality=95)
    print("V8_HYBRID_OK",(OUT/"Darkline_hybrid_V8.mp4").stat().st_size,flush=True)

def motion_qa():
    p=OUT/"Darkline_hybrid_V8.mp4"
    raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(p),"-vf","scale=108:192,format=gray","-f","rawvideo","-"])
    arr=np.frombuffer(raw,dtype=np.uint8).reshape(-1,192,108).astype(np.int16)
    diff=np.abs(np.diff(arr,axis=0)).mean(axis=(1,2))
    longest=run=0
    for v in diff:
        run=run+1 if v<.05 else 0;longest=max(longest,run)
    report={"frames":len(arr),"first_second_mean_abs_gray_change":float(diff[:29].mean()),"mean_abs_gray_change":float(diff.mean()),"longest_near_static_seconds":round(longest/FPS,3),"near_static_threshold":.05}
    if len(arr)!=round(sum(DUR)*FPS):raise RuntimeError("Unexpected encoded frame count")
    (OUT/"motion_report.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    print("MOTION_QA",json.dumps(report),flush=True)

if __name__=="__main__":capture();render();motion_qa()
