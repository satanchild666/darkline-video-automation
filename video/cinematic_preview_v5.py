"""V5 cinematic creative review. Real mobile and desktop captures. No publication."""
from pathlib import Path
import math, subprocess, tempfile, wave
import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
import motion_preview_v3 as v3
import style_preview_v2 as v2
import depth_preview_v4 as v4
OUT=Path("cinematic-preview");OUT.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30
DUR=[3.,3.5,4.,3.5,4.,4.]
WHITE="#f4f4fa";PURPLE="#c2a9ff";MUTED="#c1bfce"
def capture():
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
        desk.locator("#ds-v23-owner").click(timeout=12000)
        desk.locator("#ds-v23-panel").wait_for(state="visible")
        desk.locator("#ds-v23-editor").scroll_into_view_if_needed()
        desk.wait_for_timeout(250)
        desk.screenshot(path=str(OUT/"desktop_admin.png"),animations="disabled")
        browser.close()
    print("REAL_UI_STATES_OK before/after selections and admin; no booking submitted",flush=True)


ease=v4.ease
smooth=v4.smooth
text=v4.text
label=v4.label
card=v4.card
def brand(im,s,t):
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((72,94,129,151),radius=15,fill="#a888ff")
    text(im,84,105,"DS",25,"#141022");text(im,151,104,"DARKLINE / STUDIO",32)
    d.line((72,184,1008,184),fill="#393347",width=2)
    p=(sum(DUR[:s])+t)/sum(DUR);x=max(1,int(936*p))
    d.rounded_rectangle((72,1758,1008,1766),radius=4,fill="#393347")
    d.rounded_rectangle((72,1758,72+x,1766),radius=4,fill="#a888ff")
def background(t,s):
    im=v2.BG.copy();d=ImageDraw.Draw(im)
    for i in range(9):
        x=int((i*195+40*t+65*s)%1600)-300
        d.line((x,1650,x+420,220),fill="#272137",width=2)
    # Floor grid and a moving reflection below the virtual product.
    for i in range(-4,5):d.line((540+i*28,1250,540+i*240,1710),fill="#29243e",width=2)
    for y in [1330,1420,1545,1690]:d.line((0,y,W,y),fill="#272137",width=2)
    return im
def metal(im,front,back,t):
    d=ImageDraw.Draw(im)
    d.polygon([(x+23,y+31) for x,y in back],fill="#100e19")
    d.polygon(back,fill="#3b354b",outline="#716386",width=2)
    for i in range(4):
        j=(i+1)%4
        d.polygon([back[i],back[j],front[j],front[i]],fill=["#8a829b","#b1a3c7","#302d3c","#6e637f"][i])
    # Simulated specular highlight travels along a metal edge.
    phase=.5+.5*math.sin(t*2.6)
    u=max(0,phase-.16);v=min(1,phase+.16)
    a,b=front[0],front[1]
    d.line([(a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u),(a[0]+(b[0]-a[0])*v,a[1]+(b[1]-a[1])*v)],fill="#e8dcff",width=4)
def device(im,tex,cx,cy,w,h,yaw,pitch,roll,t):
    front=v4.project(cx,cy,w,h,yaw,pitch,roll,-14)
    back=v4.project(cx,cy,w,h,yaw,pitch,roll,19)
    metal(im,front,back,t);v4.warp(im,tex,front)
    d=ImageDraw.Draw(im);d.line([front[0],front[1]],fill="#cfc1e6",width=2)
def laptop_texture(img):
    tex=Image.new("RGB",(1100,680),"#191824")
    d=ImageDraw.Draw(tex);d.rounded_rectangle((1,1,1098,678),radius=25,fill="#242330",outline="#a69bb9",width=3)
    src=img.copy();src.thumbnail((1060,635),Image.Resampling.LANCZOS)
    tex.paste(src,((1100-src.width)//2,(680-src.height)//2))
    d.ellipse((545,9,555,19),fill="#b7a9ce")
    return tex
def laptop(im,tex,cx,cy,w,h,yaw,pitch,roll,t):
    f=v4.project(cx,cy,w,h,yaw,pitch,roll,-12);b=v4.project(cx,cy,w,h,yaw,pitch,roll,15)
    metal(im,f,b,t);v4.warp(im,tex,f,22)
    d=ImageDraw.Draw(im)
    # Hinged base has depth and is aligned to the projected lower screen edge.
    l,r=f[3],f[2];dx=60*math.sin(math.radians(yaw));dy=85+15*math.cos(math.radians(pitch))
    p=[(l[0]-15,l[1]),(r[0]+15,r[1]),(r[0]+55+dx,r[1]+dy),(l[0]-55+dx,l[1]+dy)]
    d.polygon(p,fill="#585568",outline="#b3a6c8",width=3)
    d.line([p[2],p[3]],fill="#ded1f4",width=3)
    def interp(a,b,t):return (a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
    for j in range(1,4):
        q=j/5
        d.line([interp(interp(p[0],p[3],q),interp(p[1],p[2],q),.16),interp(interp(p[0],p[3],q),interp(p[1],p[2],q),.84)],fill="#24232e",width=4)
def floating(im,s,x,y,w,h,t):
    # Actual selected slot text is read from the live demo, rendered legibly.
    d=ImageDraw.Draw(im);y+=int(9*math.sin(t*3))
    d.rounded_rectangle((x+12,y+15,x+w+12,y+h+15),radius=28,fill="#100f1b")
    d.rounded_rectangle((x,y,x+w,y+h),radius=28,fill="#c2a9ff",outline="#e3d8ff",width=3)
    text(im,x+24,y+16,"KIVÁLASZTOTT IDŐSÁV",25,"#33264a",limit=w-48)
    text(im,x+24,y+55,s,65,"#151020",limit=w-48)
def frame(s,t,a):
    im=background(t,s);p=ease(t/.45);q=smooth(t/DUR[s]);phase=math.sin(t*1.6)
    if s==0:
        # Layered hero devices move in opposite directions with restrained metallic highlights.
        laptop(im,a["laptop"],580+110*(1-p),1090,735,465,22-28*q,2,-6+4*q,t)
        device(im,a["dev_services"],360+45*q,1175,435,805,-28+45*q,5,-13+10*q,t)
        device(im,a["dev_slots"],795-55*q,1190,345,640,27-40*q,1,11-7*q,t)
        label(im,"AUTÓSZERVIZ • ÉLŐ DEMÓ")
        text(im,72,292,"Még mindig",99);text(im,72,412,"telefonon?",120,PURPLE)
        text(im,76,555,"Mutasd meg a szabad időpontokat online.",37,b=False)
        card(im,a["service_after"],100,1515,880,150)
    elif s==1:
        label(im,"01 / SZOLGÁLTATÁS");text(im,72,290,"Egyértelmű",91);text(im,72,402,"választás.",110,PURPLE)
        text(im,76,540,"A vendég kiválasztja, mire van szüksége.",38,b=False)
        if t<1.4:
            device(im,a["dev_services"],540,1120,535+55*q,990+70*q,22-38*q,4,8-12*q,t)
        else:
            r=ease((t-1.4)/.40)
            card(im,a["service_before" if t<2.1 else "service_after"],72,735-int(70*r),936,335)
            card(im,a["services"],90,1115,900,420,True,.65)
            v3.tap(im,815,845,t,2.05)
        text(im,78,1630,"Valódi ügyfélnézet",40)
    elif s==2:
        label(im,"02 / IDŐPONT");text(im,72,290,"Nap. Idősáv.",96);text(im,72,407,"Kész.",112,PURPLE)
        card(im,a["dates_before" if t<.75 else "dates_after"],72,645+int(45*(1-p)),936,250)
        v3.tap(im,340,780,t,.71)
        card(im,a["slots_before" if t<1.75 else "slots_after"],72,945,936,420)
        v3.tap(im,245,1080,t,1.71)
        if t>=1.95:floating(im,a["selected"],235,1410,610,155,t)
        text(im,78,1630,"Az elérhető idősávok láthatók.",40)
    elif s==3:
        label(im,"ÜGYFÉLNÉZET • DEMÓ");text(im,72,295,"Az időpont",93);text(im,72,405,"látható.",112,PURPLE)
        device(im,a["dev_slots"],545+40*phase,1090,570,1040,-29+49*q,8-12*q,-10+14*q,t)
        floating(im,a["selected"],180+int(75*q),1460,720,155,t)
        text(im,78,1660,"Kiválasztott idősáv • nincs végleges foglalás",30,b=False)
    elif s==4:
        label(im,"03 / SAJÁT ADMIN");text(im,72,295,"Te irányítod.",99)
        text(im,76,430,"A szolgáltatásaid saját kezelőfelületen.",39,b=False)
        if t<2.0:
            laptop(im,a["laptop"],540,1030,910,560,-22+42*q,5,-4+6*q,t)
            device(im,a["dev_admin"],790-35*q,1345,340,630,18-20*q,-3,8-7*q,t)
        else:
            card(im,a["admin"],72,570,936,950,True,.1+.7*smooth((t-2.)/2.))
        text(im,78,1620,"Tulajdonosi nézet • valódi demó",38)
    else:
        label(im,"PRÓBÁLD KI");text(im,72,290,"Ne csak nézd.",99);text(im,72,410,"Teszteld.",132,PURPLE)
        text(im,76,565,"Autószerviz-időpontfoglaló",45,b=False)
        laptop(im,a["laptop"],510,990,680,420,17-28*q,4,-5,t)
        device(im,a["dev_slots"],755-40*q,1110,320,590,-20+35*q,4,8-8*q,t)
        d=ImageDraw.Draw(im);d.rounded_rectangle((72,1390,1008,1515),radius=35,fill="#c2a9ff")
        text(im,105,1428,"Bemutatóstúdió megnyitása  →",45,"#151020",limit=870)
        text(im,76,1560,"darkline-studio.web.app",43)
        text(im,76,1640,"Valós, kipróbálható funkciók.",34,MUTED,False)
    brand(im,s,t)
    if s and t<.10:
        x=int(-300+1580*ease(t/.10));ImageDraw.Draw(im).polygon([(x,195),(x+54,195),(x-190,1740),(x-244,1740)],fill="#7154a5")
    return im
def sound(path,duration):
    sr=48000;t=np.arange(int(sr*duration))/sr;a=np.zeros_like(t);rng=np.random.default_rng(42)
    for i,beat in enumerate(np.arange(0,duration,.5)):
        z=t-beat;m=(z>=0)&(z<.32);u=z[m]
        a[m]+=.28*np.sin(2*np.pi*(82*u-75*u*u))*np.exp(-u*16)
        z=t-(beat+.25);m=(z>=0)&(z<.075);u=z[m];a[m]+=.04*rng.normal(0,1,len(u))*np.exp(-u*65)
    for i,beat in enumerate(np.arange(0,duration,.25)):
        hz=[55,55,82.41,65.41,55,110,82.41,65.41][i%8];z=t-beat;m=(z>=0)&(z<.23);u=z[m]
        a[m]+=.11*(np.sin(2*np.pi*hz*u)+.35*np.sin(4*np.pi*hz*u)+.12*np.sin(6*np.pi*hz*u))*np.exp(-u*10)
    for beat in np.cumsum([0]+DUR[:-1]):
        z=t-beat;m=(z>=0)&(z<.32);u=z[m];a[m]+=.06*np.sin(2*np.pi*(360*u+700*u*u))*np.exp(-u*12)
    a*=np.minimum(1,t/.035)*np.minimum(1,np.maximum(0,duration-t)/.45)
    with wave.open(str(path),"wb") as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes((np.clip(a,-.9,.9)*32767).astype("<i2").tobytes())
def render():
    a={p.stem:Image.open(p).convert("RGB") for p in OUT.glob("*.png")}
    for k in ["services","slots","admin"]:a["dev_"+k]=v4.phone_texture(a["phone_"+k])
    a["laptop"]=laptop_texture(a["desktop_admin"])
    a["selected"]=(OUT/"selected.txt").read_text(encoding="utf8")
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td);silent=tmp/"silent.mp4";audio=tmp/"sound.wav"
        cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","pipe:0","-c:v","libx264","-preset","fast","-crf","17","-pix_fmt","yuv420p","-threads","3",str(silent)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for s,d in enumerate(DUR):
                for n in range(round(d*FPS)):
                    im=frame(s,n/FPS,a)
                    if n in [12,round(d*FPS)//2]:im.save(OUT/f"scene-{s+1}-{n:03d}.jpg",quality=94)
                    proc.stdin.write(im.tobytes())
        finally:proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError("Encoding failed")
        sound(audio,sum(DUR))
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(audio),"-c:v","copy","-c:a","aac","-b:a","160k","-movflags","+faststart","-shortest",str(OUT/"Darkline_cinematic_V5.mp4")],check=True)
    files=sorted(OUT.glob("scene-*.jpg"));sheet=Image.new("RGB",(1620,960),"#11111b")
    for i,p in enumerate(files):sheet.paste(Image.open(p).resize((270,480),Image.Resampling.LANCZOS),((i//2)*270,(i%2)*480))
    sheet.save(OUT/"storyboard.jpg",quality=95)
    print("V5_CINEMATIC_OK", (OUT/"Darkline_cinematic_V5.mp4").stat().st_size,flush=True)

if __name__=="__main__":capture();render()
