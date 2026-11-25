"""V9 creative cinematic review. Real timed browser clips, no artificial tail padding.
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
import wave
import urllib.request
import hashlib
OUT=Path("creative-preview-v9");OUT.mkdir(exist_ok=True)
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

def isolate(page):
    # Prevent the separate promotional widgets from loading in this review browser.
    for pattern in ["**/advisor-widget.js*","**/smart-advisor.js*"]:
        page.route(pattern,lambda route:route.abort())
    page.add_init_script("""()=>{const css='#darkline-premium-guide,.dl-advisor-widget,.dl-advisor-hint,[id^="darkline-ai-advisor"],[class^="darkline-ai-advisor"]{display:none!important}';const apply=()=>{if(document.head&&!document.getElementById('v9-review-style')){const s=document.createElement('style');s.id='v9-review-style';s.textContent=css;document.head.append(s)}};new MutationObserver(apply).observe(document,{childList:true,subtree:true});apply()}""")

def prepare(page):
    isolate(page);v7.prepare(page);clean(page)
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
        isolate(page)
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
        isolate(desk)
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

def premium_texture(img):
    # Layered simulated brushed-metal frame and subtle bezel-only glass highlights.
    tex=v4.phone_texture(img);d=ImageDraw.Draw(tex)
    w,h=tex.size
    for i in range(4):
        k=38+i*15
        d.rounded_rectangle((i+1,i+1,w-i-2,h-i-2),radius=42-i,outline=(k,k+4,k+19),width=1)
    d.line((45,3,w-45,3),fill="#c8c8dc",width=2)
    d.line((3,90,3,h-90),fill="#8e8ba7",width=2)
    return tex
def premium_phone(im,tex,cx,cy,w,h,yaw,pitch,roll,t):
    v7.phone(im,tex,cx,cy,w,h,yaw,pitch,roll,t)
    q=v4.project(cx,cy,w,h,yaw,pitch,roll,-14);d=ImageDraw.Draw(im)
    a,b=q[0],q[1];u=.45+.35*math.sin(t*2.1);v=min(1,u+.17)
    d.line([(a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u),(a[0]+(b[0]-a[0])*v,a[1]+(b[1]-a[1])*v)],fill="#f3eaff",width=3)

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
        premium_phone(im,a[key],cx,yy,380*scale,710*scale,30*math.cos(z),5,-12*math.cos(z),t)
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
        premium_phone(im,a["dev_slots"],540-120*q,1060,550+60*q,1000,-29+45*q,6,-9+12*q,t)
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
    for k in ["services","slots","admin"]:a["dev_"+k]=premium_texture(a["phone_"+k])
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
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(audio),"-c:v","copy","-c:a","aac","-b:a","160k","-movflags","+faststart","-shortest",str(OUT/"Darkline_auto_V9.mp4")],check=True)
    sheet=Image.new("RGB",(1620,960),"#11111b")
    for i,p in enumerate(sorted(OUT.glob("scene-*.jpg"))):sheet.paste(Image.open(p).resize((270,480),Image.Resampling.LANCZOS),((i//2)*270,(i%2)*480))
    sheet.save(OUT/"storyboard.jpg",quality=95)
    print("V9_AUTO_OK",(OUT/"Darkline_auto_V9.mp4").stat().st_size,flush=True)

def motion_qa():
    p=OUT/"Darkline_auto_V9.mp4"
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




MENU_URL="https://darkline-studio.web.app/demok/vendeglatas-egyben.html?skin=dark"
MENU_DUR=[3.,4.,4.,4.,3.]
GOLD="#f0c981";MINT="#9ce1ce"
def menu_capture():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        page=browser.new_page(viewport={"width":600,"height":1120},device_scale_factor=1.5)
        isolate(page);page.goto(MENU_URL,wait_until="domcontentloaded",timeout=45000)
        frame=page.frame_locator("#dlb-frame")
        frame.locator("#menu-grid").wait_for(timeout=20000)
        clean(page)
        # Use actual customer view, select an actual category; no order submitted.
        frame.locator("#menu-grid").scroll_into_view_if_needed()
        page.locator("#dlb-frame").scroll_into_view_if_needed()
        page.screenshot(path=str(OUT/"menu_phone.png"),animations="disabled")
        frame.locator('[data-cat="foetel"]').click(timeout=12000)
        frame.locator('[data-cat="foetel"].active').wait_for(timeout=10000)
        frame.get_by_role("heading",name="Bélszín Steak",exact=True).wait_for(state="visible",timeout=10000)
        frame.locator("#menu-grid").screenshot(path=str(OUT/"menu_grid.png"),animations="disabled")
        frame.get_by_role("heading",name="Bélszín Steak",exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(OUT/"menu_category.png"),animations="disabled")
        tab=page.locator('[data-tab="napi"]')
        tab.click(timeout=12000)
        page.wait_for_function("document.querySelector('[data-tab=napi]').getAttribute('aria-selected')==='true'")
        page.wait_for_timeout(600)
        page.locator("#dlb-frame").scroll_into_view_if_needed()
        # Verify the iframe navigated to a different real demo; no inferred daily menu.
        inner=page.locator("#dlb-frame").get_attribute("src")
        if not inner or "digitalis-etlap.html" in inner:raise RuntimeError("Daily menu tab did not change iframe")
        page.frame_locator("#dlb-frame").locator("body").wait_for(timeout=20000)
        page.wait_for_timeout(450)
        page.screenshot(path=str(OUT/"menu_daily.png"),animations="disabled")
        # Open the same genuine menu directly; the parent iframe auto-resizes
        # continuously, making the embedded owner button unstable in Playwright.
        owner=browser.new_page(viewport={"width":900,"height":1100},device_scale_factor=1.5)
        isolate(owner)
        owner.goto("https://darkline-studio.web.app/demok/digitalis-etlap.html?skin=dark",wait_until="domcontentloaded",timeout=45000)
        owner.locator("#ds-v23-owner").wait_for(timeout=20000)
        clean(owner)
        owner.locator("#ds-v23-owner").click(timeout=12000)
        owner.locator("#ds-v23-panel").wait_for(state="visible")
        editor=owner.locator("#ds-v23-editor")
        editor.wait_for(state="visible")
        editor.screenshot(path=str(OUT/"menu_admin.png"),animations="disabled",timeout=15000)
        browser.close()
    print("MENU_REAL_STATES_OK category, daily tab, owner view; no order or save",flush=True)
def menu_bg(t,s):
    # Restaurant-specific editorial composition: warm gold light on deep emerald.
    im=Image.new("RGB",(W,H),"#091c1d")
    layer=Image.new("RGB",(270,480));d=ImageDraw.Draw(layer)
    x=int(125+90*math.sin(t*.9+s));y=240
    d.ellipse((x-110,y-100,x+110,y+100),fill=(43,31,10))
    layer=layer.filter(ImageFilter.GaussianBlur(40)).resize((W,H),Image.Resampling.BILINEAR)
    im=ImageChops.screen(im,layer);d=ImageDraw.Draw(im)
    for j in range(5):
        r=170+j*67+int(t*14)
        d.arc((540-r,1040-r,540+r,1040+r),180+int(t*25),330+int(t*25),fill="#3c5247",width=2)
    return im
def menu_brand(im,s,t):
    d=ImageDraw.Draw(im);d.line((72,184,1008,184),fill="#557468",width=2)
    text(im,72,102,"DARKLINE / STUDIO",35,GOLD)
    p=(sum(MENU_DUR[:s])+t)/sum(MENU_DUR)
    d.rounded_rectangle((72,1758,1008,1766),radius=4,fill="#354c45")
    d.rounded_rectangle((72,1758,72+int(936*p),1766),radius=4,fill=GOLD)
def menu_frame(s,t,a):
    im=menu_bg(t,s);q=smooth(t/MENU_DUR[s]);p=ease(t/.75)
    d=ImageDraw.Draw(im)
    if s==0:
        premium_phone(im,a["menu_dev"],540+200*(1-p),1120,525,970,-36+45*p,5,-14+13*p,t)
        text(im,72,215,"VENDÉGLÁTÁS / ÉLŐ DEMÓ",31,GOLD)
        title(im,"Az étlapod",72,305,99,WHITE,t);title(im,"egy érintésre.",72,420,90,GOLD,t,.08)
        text(im,72,555,"Digitális étlap, QR és napi menü.",38,MINT,False)
    elif s==1:
        text(im,72,215,"01 / ÉTELEK",31,GOLD)
        title(im,"Válassz",72,305,110,WHITE,t);title(im,"egyszerűen.",72,425,97,GOLD,t,.08)
        card(im,a["menu_grid"],72,650-int(50*p),936,860,True,.25+.5*q)
        text(im,72,1590,"Valódi ételkategóriák és árak",38,MINT)
    elif s==2:
        text(im,72,215,"02 / NAPI MENÜ",31,GOLD)
        title(im,"Mi van ma",72,305,100,WHITE,t);title(im,"az étlapon?",72,425,99,GOLD,t,.1)
        premium_phone(im,a["daily_dev"],545+45*math.sin(t*1.6),1110,530,980,23-40*q,4,7-12*q,t)
        text(im,72,1635,"Külön napi menü nézet",38,MINT)
    elif s==3:
        text(im,72,215,"03 / SAJÁT ADMIN",31,GOLD)
        title(im,"Te kezeled.",72,305,99,WHITE,t)
        text(im,72,455,"Saját kezelőfelület a demóban.",39,MINT,False)
        card(im,a["menu_admin"],72,595,936,1000,True,.1+.7*q)
        text(im,72,1650,"Tulajdonosi nézet",38,MINT)
    else:
        text(im,72,215,"PRÓBÁLD KI",31,GOLD)
        title(im,"Nézd meg",72,305,110,WHITE,t);title(im,"működés közben.",72,435,79,GOLD,t,.08)
        premium_phone(im,a["menu_dev"],355,1040,380,700,-24+28*q,4,-12+9*q,t)
        premium_phone(im,a["daily_dev"],755,1110,350,650,25-26*q,3,10-7*q,t+.3)
        d.rounded_rectangle((72,1450,1008,1560),radius=28,fill=GOLD)
        text(im,102,1482,"darkline-studio.web.app",48,"#132522",limit=850)
        text(im,72,1620,"Digitális étlap és napi menü demó",35,MINT)
    menu_brand(im,s,t)
    return im
def menu_render():
    a={k:Image.open(OUT/(k+".png")).convert("RGB") for k in ["menu_phone","menu_grid","menu_daily","menu_admin"]}
    a["menu_dev"]=premium_texture(a["menu_phone"]);a["daily_dev"]=premium_texture(a["menu_daily"])
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td);silent=tmp/"silent.mp4";audio=tmp/"sound.wav"
        cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","pipe:0","-c:v","libx264","-preset","fast","-crf","17","-pix_fmt","yuv420p","-threads","3",str(silent)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE);prev=None
        try:
            for s,d in enumerate(MENU_DUR):
                for n in range(round(d*FPS)):
                    im=menu_frame(s,n/FPS,a)
                    if prev is not None and n<8:im=v6.transition(prev,im,n/FPS)
                    if n in [12,round(d*FPS)//2]:im.save(OUT/f"menu-scene-{s+1}-{n:03d}.jpg",quality=94)
                    proc.stdin.write(im.tobytes())
                prev=im
        finally:proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError("Menu encoding failed")
        old=v5.DUR
        try:v5.DUR=MENU_DUR;v5.sound(audio,sum(MENU_DUR))
        finally:v5.DUR=old
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(audio),"-c:v","copy","-c:a","aac","-b:a","160k","-movflags","+faststart","-shortest",str(OUT/"Darkline_menu_V9.mp4")],check=True)
    sheet=Image.new("RGB",(1350,960),"#091c1d")
    for i,p in enumerate(sorted(OUT.glob("menu-scene-*.jpg"))):sheet.paste(Image.open(p).resize((270,480),Image.Resampling.LANCZOS),((i//2)*270,(i%2)*480))
    sheet.save(OUT/"menu_storyboard.jpg",quality=95)
    print("V9_MENU_OK",flush=True)
def narrate():
    # The public Hungarian Anna neural model runs locally in the CI runner.
    from piper import PiperVoice
    voice_dir=Path("voice-model");voice_dir.mkdir(exist_ok=True)
    model=voice_dir/"hu_HU-anna-medium.onnx"
    if not model.exists():
        subprocess.run(["python","-m","piper.download_voices","--download-dir",str(voice_dir),"hu_HU-anna-medium"],check=True)
    voice=PiperVoice.load(str(model))
    # Short original script, timed to the three major sections.
    script="Még mindig telefonon egyezteted az időpontokat? Mutasd meg ügyfeleidnek a szabad időpontokat online. Saját kezelőfelületeddel te irányítod a szolgáltatásaidat. Próbáld ki a Darkline Studio bemutatóját!"
    with tempfile.TemporaryDirectory() as td:
        speech=Path(td)/"speech.wav"
        with wave.open(str(speech),"wb") as w:voice.synthesize_wav(script,w)
        d=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(speech)]).decode().strip())
        speed=max(1,d/19.5)
        if speed>1.5:raise RuntimeError("Narration too long")
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(OUT/"Darkline_auto_V9.mp4"),"-i",str(speech),"-filter_complex",f"[0:a]volume=0.24[bed];[1:a]atempo={speed:.4f},adelay=350:all=1,loudnorm=I=-17:TP=-2:LRA=7[voice];[bed][voice]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[a]","-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart",str(OUT/"Darkline_auto_V9_narrated.mp4")],check=True)
    (OUT/"narration.txt").write_text(script,encoding="utf8")
    print("V9_HU_NEURAL_NARRATION_OK",flush=True)
def check_quality(path,expected,min_open):
    raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(path),"-vf","scale=108:192,format=gray","-f","rawvideo","-"])
    arr=np.frombuffer(raw,dtype=np.uint8).reshape(-1,192,108).astype(np.int16)
    diff=np.abs(np.diff(arr,axis=0)).mean(axis=(1,2));longest=run=0
    for v in diff:
        run=run+1 if v<.05 else 0;longest=max(longest,run)
    info=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)]))
    vs=next(s for s in info["streams"] if s["codec_type"]=="video")
    report={"file":path.name,"frames":len(arr),"first_second":float(diff[:29].mean()),"mean_motion":float(diff.mean()),"longest_near_static":longest/FPS}
    reasons=[]
    if len(arr)!=round(expected*FPS) or (vs["width"],vs["height"])!=(W,H):reasons.append("format")
    if report["first_second"]<min_open:reasons.append("opening_motion")
    if report["mean_motion"]<.45:reasons.append("average_motion")
    if report["longest_near_static"]>.75:reasons.append("static_interval")
    if not any(s["codec_type"]=="audio" for s in info["streams"]):reasons.append("missing_audio")
    report["review_gate"]="PASS" if not reasons else "REJECT";report["reasons"]=reasons
    # Report-only: rejected samples can still be inspected, never published.
    print("V9_QUALITY_GATE",json.dumps(report),flush=True)
    return report
if __name__=="__main__":
    reports=[]
    def failed(name,exc):
        reports.append({"file":name,"review_gate":"REJECT","reasons":["render_failed"],"error":str(exc)[:500]})
        print("V9_VARIANT_FAILED",name,str(exc)[:500],flush=True)
    try:
        capture();render();motion_qa()
        reports.append(check_quality(OUT/"Darkline_auto_V9.mp4",sum(DUR),2.5))
    except Exception as exc:
        failed("Darkline_auto_V9.mp4",exc)
    try:
        if not (OUT/"Darkline_auto_V9.mp4").exists():raise RuntimeError("Auto base video unavailable")
        narrate();reports.append(check_quality(OUT/"Darkline_auto_V9_narrated.mp4",sum(DUR),2.5))
    except Exception as exc:
        failed("Darkline_auto_V9_narrated.mp4",exc)
    try:
        menu_capture();menu_render()
        reports.append(check_quality(OUT/"Darkline_menu_V9.mp4",sum(MENU_DUR),1.0))
    except Exception as exc:
        failed("Darkline_menu_V9.mp4",exc)
    (OUT/"quality_gate.json").write_text(json.dumps(reports,indent=2),encoding="utf8")
    if not any(r["review_gate"]=="PASS" for r in reports):raise RuntimeError("No sample met technical review thresholds")
