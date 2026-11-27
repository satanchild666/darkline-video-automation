"""V7 cinematic design review: continuous real browser footage + perspective motion.
No Buffer, no publication, no booking or admin save. Device lighting is simulated."""
from pathlib import Path
import math, time, subprocess, tempfile, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from playwright.sync_api import sync_playwright
import style_preview_v2 as v2
import depth_preview_v4 as v4
import cinematic_preview_v5 as v5
import motion_cinematic_v6 as v6

OUT=Path("cinematic-live-v7");OUT.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30
DUR=[3.,4.,4.,3.,5.,4.]
WHITE="#f4f4fa";PURPLE="#c2a9ff";MUTED="#c1bfce"
ease=v4.ease;smooth=v4.smooth;text=v4.text;label=v4.label;card=v4.card;title=v6.title
CSS="#darkline-premium-guide,.dlg-avatar,.dlg-thought,.dlg-thought-tour,.dl-advisor-widget,#darkline-ai-advisor-toggle{display:none!important;pointer-events:none!important} .time-btn.active{color:#071017!important;font-weight:800!important} .time-btn.active *{color:#071017!important}"
def prepare(page):
    page.goto(v2.URL,wait_until="domcontentloaded",timeout=45000)
    page.locator(".service-card").first.wait_for(timeout=20000)
    for loc in [page.get_by_role("button",name="Most nem",exact=True),page.locator(".ds-demo-close")]:
        try:
            if loc.first.is_visible():loc.first.click(timeout=1500)
        except Exception:pass
    page.add_style_tag(content=CSS)
    page.wait_for_timeout(300)
def pan(page,loc):
    loc.evaluate("(el)=>el.scrollIntoView({behavior:'smooth',block:'center'})")
    page.wait_for_timeout(700)
def record(browser,name,desktop=False):
    size={"width":1280,"height":800} if desktop else {"width":600,"height":1120}
    ctx=browser.new_context(viewport=size,device_scale_factor=1,record_video_dir=str(OUT/"raw"),record_video_size=size)
    page=ctx.new_page();prepare(page)
    service=page.locator(".service-card").first
    if desktop:
        target=page.locator("#ds-v23-owner");target.scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        begin=time.monotonic()
        page.wait_for_timeout(600);target.click(timeout=12000)
        panel=page.locator("#ds-v23-panel");panel.wait_for(state="visible")
        editor=page.locator("#ds-v23-editor");pan(page,editor)
        page.wait_for_timeout(1100)
        page.evaluate("window.scrollBy({top:240,behavior:'smooth'})")
        page.wait_for_timeout(1300)
    else:
        service.scroll_into_view_if_needed();page.wait_for_timeout(400);begin=time.monotonic()
        page.wait_for_timeout(550);service.click(timeout=12000);page.locator(".service-card.active").wait_for()
        page.wait_for_timeout(700)
        day=page.locator(".date-btn").nth(1);pan(page,day)
        day.click(timeout=12000);page.wait_for_timeout(650)
        slot=page.locator(".time-btn:not([disabled])").first;slot.wait_for(timeout=12000);pan(page,slot)
        slot.click(timeout=12000);page.locator(".time-btn.active").wait_for()
        page.wait_for_timeout(1400)
    elapsed=time.monotonic()-begin
    video=page.video;page.close();ctx.close()
    raw=OUT/(name+".webm");video.save_as(str(raw))
    duration=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(raw)]).decode().strip())
    if elapsed<2 or duration<elapsed-.8:raise RuntimeError("Browser recording incomplete")
    start=max(0,duration-elapsed-.10)
    total=5.0 if desktop else 8.0
    directory=OUT/name;directory.mkdir(exist_ok=True)
    # Constant frame rate, crop away page load, preserve live scrolling/clicks.
    subprocess.run(["ffmpeg","-v","error","-y","-ss",str(start),"-i",str(raw),"-vf",f"fps=30,tpad=stop_mode=clone:stop_duration=4,scale={size['width']}:{size['height']}", "-t",str(total),"-q:v","3",str(directory/"%04d.jpg")],check=True)
    count=len(list(directory.glob("*.jpg")))
    if count<round(total*30)-1:raise RuntimeError("Not enough continuous footage frames")
    print("LIVE_BROWSER_RECORD_OK",name,"actual_seconds",round(elapsed,2),"frames",count,flush=True)
def capture():
    v5.OUT=OUT;v5.capture()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        record(browser,"live_mobile")
        record(browser,"live_admin",True)
        browser.close()
def read_frame(name,t):
    files=LIVE[name];idx=min(len(files)-1,max(0,round(t*30)))
    with Image.open(files[idx]) as img:return img.convert("RGB")
def brand(im,s,t):
    old=v5.DUR
    try:v5.DUR=DUR;v5.brand(im,s,t)
    finally:v5.DUR=old
def background(t,s):
    # Soft studio gradients, shallow-focus bokeh, varied lighting by shot.
    im=v2.BG.copy();layer=Image.new("RGB",(W//4,H//4));d=ImageDraw.Draw(layer)
    phase=sum(DUR[:s])+t
    for i in range(12):
        x=int((i*91+phase*5*(1+i%3))%310)-20
        y=120+int((i*47+phase*2)%320)
        r=5+i%4*4
        d.ellipse((x-r,y-r,x+r,y+r),fill=(38+i%3*9,22,64+i%4*8))
    layer=layer.filter(ImageFilter.GaussianBlur(7)).resize((W,H),Image.Resampling.BILINEAR)
    from PIL import ImageChops
    im=ImageChops.screen(im,layer);d=ImageDraw.Draw(im)
    hue=["#5c3a92","#463a78","#37547f","#744a9e","#4a3b76","#65429a"][s]
    pulse=math.exp(-7*(phase%.5))
    for j in range(3):
        x=int((phase*100+j*390)%1500)-210
        d.line((x,1680,x+420,660),fill=hue,width=1+int(2*pulse))
    return im
def phone(im,texture,cx,cy,w,h,yaw,pitch,roll,t):
    v5.device(im,texture,cx,cy,w,h,yaw,pitch,roll,t)
    # A narrow simulated metallic reflection, kept outside the UI.
    q=v4.project(cx,cy,w,h,yaw,pitch,roll,-14);d=ImageDraw.Draw(im)
    a,b=q[1],q[2];u=.2+.45*(.5+.5*math.sin(t*2.2));v=min(.95,u+.18)
    d.line([(a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u),(a[0]+(b[0]-a[0])*v,a[1]+(b[1]-a[1])*v)],fill="#ddd1ff",width=3)
def device_hero(im,a,t,final=False):
    # Wide framing avoids two phones masking each other's displays.
    q=smooth(t/(4. if final else 3.));cy=1110 if not final else 1000
    v5.laptop(im,a["laptop"],540,cy-105,820 if not final else 760,500 if not final else 465,16-27*q,5,-3+5*q,t)
    phone(im,a["dev_services"],230+45*q,cy+155,295,550,-28+34*q,3,-12+9*q,t)
    phone(im,a["dev_slots"],850-45*q,cy+155,295,550,25-32*q,3,11-8*q,t+.4)
def live_panel(im,src,x,y,w,h):
    # The video is a continuous real browser recording, not interpolated screenshots.
    card(im,src,x,y,w,h)
def frame(s,t,a):
    im=background(t,s);q=smooth(t/DUR[s])
    if s==0:
        # Opening camera push and multi-device reveal.
        device_hero(im,a,t)
        label(im,"AUTÓSZERVIZ • ÉLŐ DEMÓ")
        title(im,"Még mindig",72,292,99,WHITE,t);title(im,"telefonon?",72,412,120,PURPLE,t,.07)
        text(im,76,555,"Mutasd meg a szabad időpontokat online.",37,b=False)
        card(im,a["service_after"],100,1515,880,150)
    elif s==1:
        label(im,"01 / SZOLGÁLTATÁS")
        title(im,"Egyértelmű",72,290,91,WHITE,t);title(im,"választás.",72,402,110,PURPLE,t,.08)
        text(im,76,540,"A vendég kiválasztja, mire van szüksége.",38,b=False)
        live_panel(im,read_frame("live_mobile",t),245,615,590,1000)
        text(im,78,1660,"Valódi, folyamatos képernyőfelvétel",34)
    elif s==2:
        label(im,"02 / IDŐPONT")
        title(im,"Nap. Idősáv.",72,290,96,WHITE,t);title(im,"Kész.",72,407,112,PURPLE,t,.08)
        # The second half continues the same recorded sequence.
        live_panel(im,read_frame("live_mobile",4+t),245,545,590,990)
        if t>2.7:v5.floating(im,a["selected"],225,1490,630,155,t)
        text(im,78,1660,"Az elérhető idősávok láthatók.",36)
    elif s==3:
        label(im,"ÜGYFÉLNÉZET • DEMÓ")
        title(im,"Az időpont",72,295,93,WHITE,t);title(im,"látható.",72,405,112,PURPLE,t,.10)
        phone(im,a["dev_slots"],545+45*math.sin(t*1.8),1090,570,1040,-26+46*q,8-12*q,-10+14*q,t)
        v5.floating(im,a["selected"],180+int(75*q),1460,720,155,t)
        text(im,78,1660,"Kiválasztott idősáv • nincs végleges foglalás",30,b=False)
    elif s==4:
        label(im,"03 / SAJÁT ADMIN");title(im,"Te irányítod.",72,295,99,WHITE,t)
        text(im,76,430,"A szolgáltatásaid saját kezelőfelületen.",39,b=False)
        actual=read_frame("live_admin",t)
        if t<2.0:
            v5.laptop(im,v5.laptop_texture(actual),540,980,940,575,-18+30*q,4,-4+5*q,t)
            phone(im,a["dev_admin"],805,1390,300,550,15-20*q,-3,8-7*q,t)
        else:
            live_panel(im,actual,72,675,936,610)
            card(im,a["admin"],110,1340,860,245,True,.25+.5*q)
        text(im,78,1660,"Tulajdonosi nézet • valódi demó",36)
    else:
        device_hero(im,a,t,True);label(im,"PRÓBÁLD KI")
        title(im,"Ne csak nézd.",72,290,99,WHITE,t);title(im,"Teszteld.",72,410,132,PURPLE,t,.1)
        text(im,76,565,"Autószerviz-időpontfoglaló",45,b=False)
        d=ImageDraw.Draw(im);d.rounded_rectangle((72,1390,1008,1515),radius=35,fill="#c2a9ff")
        text(im,105,1428,"Bemutatóstúdió megnyitása  →",45,"#151020",limit=870)
        text(im,76,1560,"darkline-studio.web.app",43)
        text(im,76,1640,"Valós, kipróbálható funkciók.",34,MUTED,False)
    brand(im,s,t)
    return im
def render():
    global LIVE
    LIVE={n:sorted((OUT/n).glob("*.jpg")) for n in ["live_mobile","live_admin"]}
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
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(audio),"-c:v","copy","-c:a","aac","-b:a","160k","-movflags","+faststart","-shortest",str(OUT/"Darkline_cinematic_V7.mp4")],check=True)
    sheet=Image.new("RGB",(1620,960),"#11111b")
    for i,p in enumerate(sorted(OUT.glob("scene-*.jpg"))):sheet.paste(Image.open(p).resize((270,480),Image.Resampling.LANCZOS),((i//2)*270,(i%2)*480))
    sheet.save(OUT/"storyboard.jpg",quality=95)
    print("V7_CINEMATIC_OK",(OUT/"Darkline_cinematic_V7.mp4").stat().st_size,flush=True)
if __name__=="__main__":capture();render()
