"""V3 motion review. Real before/after UI states, no publishing."""
from pathlib import Path
import math, subprocess, tempfile, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
import style_preview_v2 as v2
OUT=Path("motion-preview");OUT.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30
DUR=[1.8,2.7,3.0,2.7,2.3]
WHITE="#f4f4fa"; PURPLE="#c2a9ff"; MUTED="#c1bfce"
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
        page.add_style_tag(content="#darkline-premium-guide,.dlg-avatar,.dlg-thought,.dlg-thought-tour,.dl-advisor-tab,#darkline-ai-advisor-toggle{display:none!important;pointer-events:none!important}")
        page.wait_for_timeout(350)
        def shot(loc,name):
            loc.scroll_into_view_if_needed(timeout=12000);page.wait_for_timeout(200)
            loc.screenshot(path=str(OUT/(name+".png")),animations="disabled",timeout=15000)
        service=page.locator(".service-card").first
        shot(page.locator("#services-list"),"services");shot(service,"service_before")
        service.click(timeout=12000);page.locator(".service-card.active").wait_for()
        shot(service,"service_after")
        day=page.locator(".date-btn").nth(1)
        shot(page.locator("#date-scroller"),"dates_before")
        day.click(timeout=12000);page.locator(".date-btn.active").wait_for()
        shot(page.locator("#date-scroller"),"dates_after")
        slot=page.locator(".time-btn:not([disabled])").first
        slot.wait_for(timeout=12000);shot(page.locator("#time-grid"),"slots_before")
        slot.click(timeout=12000);page.locator(".time-btn.active").wait_for()
        shot(page.locator("#time-grid"),"slots_after");shot(slot,"slot_selected")
        page.locator("#ds-v23-owner").click(timeout=12000);page.locator("#ds-v23-panel").wait_for(state="visible")
        editor=page.locator("#ds-v23-editor");editor.wait_for(state="visible")
        shot(editor,"admin")
        browser.close()
    print("REAL_UI_STATES_OK before/after selections and admin; no booking submitted",flush=True)
def clamp(x):return max(0,min(1,x))
def ease(x):return 1-(1-clamp(x))**3
def smooth(x):x=clamp(x);return x*x*(3-2*x)
def font(n,b=True):return v2.font(n,b)
def txt(im,x,y,text,size,col=WHITE,b=True,limit=930,alpha=255):
    f=font(size,b)
    while f.getlength(text)>limit and size>16:size-=1;f=font(size,b)
    if alpha<255:
        layer=Image.new("RGBA",im.size);ImageDraw.Draw(layer).text((x,y),text,font=f,fill=(*tuple(bytes.fromhex(col[1:])),alpha));im.paste(layer,(0,0),layer)
    else:ImageDraw.Draw(im).text((x,y),text,font=f,fill=col)
def rounded(im,img,x,y,w,h,r=24,cover=False,focus=.5):
    x,y,w,h=map(int,(x,y,w,h));w=max(1,w);h=max(1,h)
    img=img.convert("RGB")
    sc=(max if cover else min)(w/img.width,h/img.height)
    a=img.resize((max(1,round(img.width*sc)),max(1,round(img.height*sc))),Image.Resampling.LANCZOS)
    if cover:
        xx=max(0,(a.width-w)//2);yy=max(0,min(a.height-h,int((a.height-h)*focus)));a=a.crop((xx,yy,xx+w,yy+h))
    tile=Image.new("RGB",(w,h),"#12121e");tile.paste(a,((w-a.width)//2,(h-a.height)//2))
    mask=Image.new("L",(w,h));ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=r,fill=255)
    d=ImageDraw.Draw(im);d.rounded_rectangle((x-5,y-5,x+w+5,y+h+5),radius=r+5,fill="#49385f")
    im.paste(tile,(x,y),mask)
def tap(im,x,y,t,at):
    a=t-at
    if 0<=a<.48:
        r=int(14+88*a/.48)
        d=ImageDraw.Draw(im);d.ellipse((x-r,y-r,x+r,y+r),outline="#c2a9ff",width=max(2,int(10*(1-a/.48))))
        d.ellipse((x-8,y-8,x+8,y+8),fill="#f4f4fa")
def backdrop(t,s):
    im=v2.BG.copy();d=ImageDraw.Draw(im)
    # Moving thin diagonals and restrained accent streak, no flashing.
    for n in range(6):
        x=int((n*250+110*t+90*s)%1450)-200
        d.line((x,1700,x+520,250),fill="#242137",width=3)
    return im
def label(im,text):
    v2.pill(ImageDraw.Draw(im),72,206,text)
def brand(im,t,s):
    d=ImageDraw.Draw(im);d.rounded_rectangle((72,94,129,151),radius=15,fill="#a888ff")
    txt(im,84,105,"DS",25,"#141022");txt(im,151,104,"DARKLINE / STUDIO",32)
    d.line((72,184,1008,184),fill="#393347",width=2)
    x=int(936*(sum(DUR[:s])+t)/sum(DUR))
    d.rounded_rectangle((72,1758,1008,1766),radius=4,fill="#393347")
    if x>0:d.rounded_rectangle((72,1758,72+x,1766),radius=4,fill="#a888ff")
def frame(s,t,a):
    im=backdrop(t,s)
    if s==0:
        # Start instantly with a close product detail, then pull back to reveal the hook.
        p=ease(t/.32);q=smooth(t/1.8)
        rounded(im,a["service_after"],70+int(35*(1-p)),720-int(70*p),940-int(25*q),600,30)
        rounded(im,a["dates_after"],125-int(42*q),1250,850,230,26)
        label(im,"AUTÓSZERVIZ • ÉLŐ DEMÓ")
        txt(im,72,300+int(35*(1-p)),"Még mindig",96)
        txt(im,72,413+int(35*(1-p)),"telefonon?",120,PURPLE)
        txt(im,76,570,"Mutasd meg a szabad időpontokat online.",38,b=False)
        tap(im,780,970,t,.24)
    elif s==1:
        # Full-width list sweeps into a close-up of the actual selected card.
        label(im,"01 / SZOLGÁLTATÁS")
        txt(im,72,297,"Egyértelmű",90);txt(im,72,400,"választás.",110,PURPLE)
        txt(im,76,540,"A vendég kiválasztja, mire van szüksége.",38,b=False)
        p=ease(t/.32);q=ease((t-.85)/.38)
        if t<.85:
            rounded(im,a["services"],72+int(240*(1-p)),650,936,890,30,cover=False)
        else:
            rounded(im,a["service_before" if t<1.22 else "service_after"],72,730-int(65*q),936,370,28)
            rounded(im,a["services"],110,1190+int(35*(1-q)),860,380,24,cover=True,focus=.8)
            tap(im,830,860,t,1.18)
        txt(im,78,1630,"Valódi ügyfélnézet",40)
    elif s==2:
        label(im,"02 / IDŐPONT")
        # Separate sequential real state changes and synchronized punch-in.
        txt(im,72,298,"Nap. Idősáv.",96);txt(im,72,413,"Kész.",112,PURPLE)
        p=ease(t/.28);q=ease((t-1.0)/.32)
        rounded(im,a["dates_before" if t<.52 else "dates_after"],72,650+int(70*(1-p)),936,270,24)
        tap(im,340,780,t,.48)
        rounded(im,a["slots_before" if t<1.48 else "slots_after"],72,970+int(100*(1-q)),936,420,24)
        tap(im,245,1080,t,1.43)
        if t>=1.75:
            p2=ease((t-1.75)/.25)
            rounded(im,a["slot_selected"],225,1430-int(45*p2),630,150,24)
        txt(im,78,1630,"Az elérhető idősávok láthatók.",40)
    elif s==3:
        # Different composition: large real admin close-ups, camera traverses vertically.
        label(im,"03 / SAJÁT ADMIN")
        txt(im,72,298,"Te irányítod.",99)
        txt(im,76,435,"A szolgáltatásaid saját kezelőfelületen.",40,b=False)
        p=ease(t/.30);q=smooth(t/2.7)
        rounded(im,a["admin"],72+int(70*(1-p)),570,936,910,32,cover=True,focus=.15+.7*q)
        txt(im,78,1570,"Tulajdonosi nézet • valódi demó",40)
    else:
        # Final composition breaks away from the UI panels: large typography + direct CTA.
        p=ease(t/.28);label(im,"PRÓBÁLD KI")
        txt(im,72+int(45*(1-p)),365,"Ne csak nézd.",100)
        txt(im,72,493,"Teszteld.",132,PURPLE)
        txt(im,76,680,"Autószerviz-időpontfoglaló",48,b=False)
        d=ImageDraw.Draw(im);d.rounded_rectangle((72,950,1008,1100),radius=38,fill="#c2a9ff")
        txt(im,108,993,"Bemutatóstúdió megnyitása  →",49,"#151020",limit=870)
        txt(im,76,1180,"darkline-studio.web.app",46)
        txt(im,76,1280,"Valós, kipróbálható funkciók.",38,MUTED,False)
        rounded(im,a["service_after"],100,1400,880,220,24)
    brand(im,t,s)
    # A restrained 3-frame accent wipe on cuts; no strobe.
    if s>0 and t<.10:
        d=ImageDraw.Draw(im);x=int(-260+1500*ease(t/.10));d.polygon([(x,195),(x+75,195),(x-190,1740),(x-265,1740)],fill="#7154a5")
    return im
def sound(path,duration):
    sr=48000;t=np.arange(int(sr*duration))/sr;a=np.zeros_like(t)
    rng=np.random.default_rng(42)
    for i,beat in enumerate(np.arange(0,duration,.4)):
        z=t-beat;m=(z>=0)&(z<.24);zz=z[m]
        a[m]+=.22*np.sin(2*np.pi*(78*zz-68*zz**2))*np.exp(-zz*22)
        start=beat+.2;z=t-start;m=(z>=0)&(z<.065);zz=z[m]
        a[m]+=.035*rng.normal(0,1,len(zz))*np.exp(-zz*65)
    for i,beat in enumerate(np.arange(0,duration,.2)):
        hz=[110,110,164.81,130.81,110,220,164.81,130.81][i%8]
        z=t-beat;m=(z>=0)&(z<.19);zz=z[m]
        a[m]+=.055*(np.sin(2*np.pi*hz*zz)+.25*np.sin(2*np.pi*2*hz*zz))*np.exp(-zz*12)
    for beat in [0,1.8,4.5,7.5,10.2]:
        z=t-beat;m=(z>=0)&(z<.26);zz=z[m]
        a[m]+=.045*np.sin(2*np.pi*(390*zz+800*zz**2))*np.exp(-zz*13)
    a*=np.minimum(1,t/.035)*np.minimum(1,np.maximum(0,duration-t)/.3)
    with wave.open(str(path),"wb") as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes((np.clip(a,-.9,.9)*32767).astype("<i2").tobytes())
def render():
    assets={p.stem:Image.open(p).convert("RGB") for p in OUT.glob("*.png")}
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td);silent=tmp/"silent.mp4";audio=tmp/"sound.wav"
        cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","pipe:0","-c:v","libx264","-preset","fast","-crf","17","-pix_fmt","yuv420p","-threads","3",str(silent)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for s,d in enumerate(DUR):
                for n in range(round(d*FPS)):
                    im=frame(s,n/FPS,assets)
                    if n in [8,round(d*FPS)//2]:im.save(OUT/f"scene-{s+1}-{n}.jpg",quality=94)
                    proc.stdin.write(im.tobytes())
        finally:proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError("Encoding failed")
        sound(audio,sum(DUR))
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(audio),"-c:v","copy","-c:a","aac","-b:a","160k","-movflags","+faststart","-shortest",str(OUT/"Darkline_motion_V3.mp4")],check=True)
    files=sorted(OUT.glob("scene-*.jpg"))
    sheet=Image.new("RGB",(1350,960),"#11111b")
    for i,p in enumerate(files):sheet.paste(Image.open(p).resize((270,480),Image.Resampling.LANCZOS),((i//2)*270,(i%2)*480))
    sheet.save(OUT/"storyboard.jpg",quality=95)
    print("V3_MOTION_OK", (OUT/"Darkline_motion_V3.mp4").stat().st_size,flush=True)
if __name__=="__main__":capture();render()
