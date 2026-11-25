"""V4 design review only: perspective-projected 3D device, real website UI textures.
No Buffer, no publishing, no customer booking."""
from pathlib import Path
import math, subprocess, tempfile, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from playwright.sync_api import sync_playwright
import motion_preview_v3 as v3
import style_preview_v2 as v2
OUT=Path("depth-preview");OUT.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30
DUR=[2.5,3.0,3.5,3.5,3.0,2.5]
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
        page.add_style_tag(content="#darkline-premium-guide,.dlg-avatar,.dlg-thought,.dlg-thought-tour,.dl-advisor-tab,#darkline-ai-advisor-toggle{display:none!important;pointer-events:none!important}")
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
        shot(page.locator("#time-grid"),"slots_after");shot(slot,"slot_selected")
        slot.scroll_into_view_if_needed();page.screenshot(path=str(OUT/"phone_slots.png"),animations="disabled")
        page.locator("#ds-v23-owner").click(timeout=12000);page.locator("#ds-v23-panel").wait_for(state="visible")
        editor=page.locator("#ds-v23-editor");editor.wait_for(state="visible")
        shot(editor,"admin")
        editor.scroll_into_view_if_needed();page.screenshot(path=str(OUT/"phone_admin.png"),animations="disabled")
        browser.close()
    print("REAL_UI_STATES_OK before/after selections and admin; no booking submitted",flush=True)

def ease(t):return v3.ease(t)
def smooth(t):return v3.smooth(t)
def text(im,x,y,s,n,c=WHITE,b=True,limit=936):v3.txt(im,x,y,s,n,c,b,limit)
def label(im,s):v2.pill(ImageDraw.Draw(im),72,206,s)
def background(t,s):
    im=v2.BG.copy();d=ImageDraw.Draw(im)
    # Parallax architectural lines, no full-screen flashes.
    for i in range(8):
        x=int((i*210+45*t+65*s)%1600)-300
        d.line((x,1650,x+420,220),fill="#272137",width=2)
    return im
def brand(im,s,t):
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((72,94,129,151),radius=15,fill="#a888ff")
    text(im,84,105,"DS",25,"#141022");text(im,151,104,"DARKLINE / STUDIO",32)
    d.line((72,184,1008,184),fill="#393347",width=2)
    p=(sum(DUR[:s])+t)/sum(DUR);x=max(1,int(936*p))
    d.rounded_rectangle((72,1758,1008,1766),radius=4,fill="#393347")
    d.rounded_rectangle((72,1758,72+x,1766),radius=4,fill="#a888ff")
def phone_texture(img):
    # Preserve the genuine viewport; bezel and hardware are promotional illustration.
    tw,th=540,1000
    tex=Image.new("RGB",(tw,th),"#101018");d=ImageDraw.Draw(tex)
    d.rounded_rectangle((1,1,tw-2,th-2),radius=42,fill="#272330",outline="#a39ab8",width=3)
    d.rounded_rectangle((8,8,tw-9,th-9),radius=37,fill="#080a10")
    sw,sh=506,952
    src=img.convert("RGB");ratio=min(sw/src.width,sh/src.height)
    src=src.resize((round(src.width*ratio),round(src.height*ratio)),Image.Resampling.LANCZOS)
    screen=Image.new("RGB",(sw,sh),"#101018")
    screen.paste(src,((sw-src.width)//2,(sh-src.height)//2))
    mask=Image.new("L",(sw,sh));ImageDraw.Draw(mask).rounded_rectangle((0,0,sw-1,sh-1),radius=28,fill=255)
    tex.paste(screen,(17,24),mask)
    d=ImageDraw.Draw(tex);d.rounded_rectangle((230,11,310,18),radius=4,fill="#72717e")
    return tex
def project(cx,cy,w,h,yaw,pitch,roll,depth=0):
    # Genuine 3D perspective projection of a rectangular plane.
    a,b,c=np.radians([yaw,pitch,roll])
    ry=np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])
    rx=np.array([[1,0,0],[0,np.cos(b),-np.sin(b)],[0,np.sin(b),np.cos(b)]])
    rz=np.array([[np.cos(c),-np.sin(c),0],[np.sin(c),np.cos(c),0],[0,0,1]])
    rot=rz@rx@ry; pts=np.array([[-w/2,-h/2,depth],[w/2,-h/2,depth],[w/2,h/2,depth],[-w/2,h/2,depth]])
    q=pts@rot.T;factor=1800/(1800+q[:,2])
    return [(float(cx+x*f),float(cy+y*f)) for (x,y,z),f in zip(q,factor)]
def warp(im,tex,quad,rounded_radius=38):
    # Inverse homography from the projected polygon to texture coordinates.
    x0=max(0,math.floor(min(x for x,y in quad)));y0=max(0,math.floor(min(y for x,y in quad)))
    x1=min(W,math.ceil(max(x for x,y in quad))+1);y1=min(H,math.ceil(max(y for x,y in quad))+1)
    if x1<=x0 or y1<=y0:return
    tw,th=tex.size; src=[(0,0),(tw-1,0),(tw-1,th-1),(0,th-1)]
    mat=[];rhs=[]
    for (x,y),(u,v) in zip(quad,src):
        x-=x0;y-=y0
        mat.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]])
        rhs.extend([u,v])
    coeff=tuple(np.linalg.solve(np.array(mat),np.array(rhs)))
    patch=tex.transform((x1-x0,y1-y0),Image.Transform.PERSPECTIVE,coeff,Image.Resampling.BICUBIC)
    m=Image.new("L",tex.size);ImageDraw.Draw(m).rounded_rectangle((0,0,tw-1,th-1),radius=rounded_radius,fill=255)
    m=m.transform(patch.size,Image.Transform.PERSPECTIVE,coeff,Image.Resampling.BILINEAR)
    im.paste(patch,(x0,y0),m)
def device(im,tex,cx,cy,w,h,yaw,pitch,roll):
    front=project(cx,cy,w,h,yaw,pitch,roll,-14);back=project(cx,cy,w,h,yaw,pitch,roll,19)
    d=ImageDraw.Draw(im)
    d.polygon([(x+22,y+28) for x,y in back],fill="#11101c")
    d.polygon(back,fill="#493b60",outline="#75638c",width=2)
    for i in range(4):
        j=(i+1)%4
        d.polygon([back[i],back[j],front[j],front[i]],fill=["#4d405f","#8c78a3","#292332","#685779"][i])
    warp(im,tex,front)
    d=ImageDraw.Draw(im)
    d.line([front[0],front[1]],fill="#b7a6d2",width=2)
def card(im,a,x,y,w,h,cover=False,focus=.5):
    v3.rounded(im,a,x,y,w,h,26,cover,focus)
def frame(s,t,a):
    im=background(t,s);p=ease(t/.5);q=smooth(t/DUR[s])
    if s==0:
        # Immediate visual hook, angled phone enters and rotates toward viewer.
        device(im,a["dev_services"],572,1155,535+75*p,990+110*p,-29+44*q,10-12*q,-11+8*q)
        label(im,"AUTÓSZERVIZ • ÉLŐ DEMÓ")
        text(im,72,290,"Még mindig",99)
        text(im,72,410,"telefonon?",120,PURPLE)
        text(im,76,555,"Mutasd meg a szabad időpontokat online.",37,b=False)
        card(im,a["service_after"],95+int(35*(1-p)),1480,890,165)
    elif s==1:
        label(im,"01 / SZOLGÁLTATÁS")
        text(im,72,292,"Egyértelmű",91);text(im,72,404,"választás.",110,PURPLE)
        text(im,76,540,"A vendég kiválasztja, mire van szüksége.",38,b=False)
        if t<1.25:
            device(im,a["dev_services"],540,1130,510+40*p,945+70*p,18-23*q,-4,8-10*q)
        else:
            r=ease((t-1.25)/.45)
            card(im,a["service_before" if t<1.8 else "service_after"],72,720-int(60*r),936,400)
            card(im,a["services"],95,1170,890,390,True,.75)
            v3.tap(im,825,850,t,1.75)
        text(im,78,1630,"Valódi ügyfélnézet",40)
    elif s==2:
        label(im,"02 / IDŐPONT")
        text(im,72,290,"Nap. Idősáv.",96);text(im,72,407,"Kész.",112,PURPLE)
        card(im,a["dates_before" if t<.70 else "dates_after"],72,645+int(65*(1-p)),936,280)
        v3.tap(im,340,780,t,.67)
        r=ease((t-.75)/.38)
        card(im,a["slots_before" if t<1.65 else "slots_after"],72,970+int(65*(1-r)),936,430)
        v3.tap(im,245,1095,t,1.60)
        if t>=1.85:
            r=ease((t-1.85)/.35)
            card(im,a["slot_selected"],225,1450-int(40*r),630,155)
        text(im,78,1630,"Az elérhető idősávok láthatók.",40)
    elif s==3:
        # Three-dimensional reveal of the customer view, with a second floating detail.
        label(im,"ÜGYFÉLNÉZET • DEMÓ")
        text(im,72,295,"Az időpont",93);text(im,72,405,"látható.",112,PURPLE)
        device(im,a["dev_slots"],550,1100,550,1020,-23+43*q,8-13*q,-9+15*q)
        card(im,a["slot_selected"],115+int(55*(1-p)),1480,850,170)
        text(im,78,1660,"Kiválasztott idősáv • nincs végleges foglalás",30,b=False)
    elif s==4:
        label(im,"03 / SAJÁT ADMIN")
        text(im,72,295,"Te irányítod.",99)
        text(im,76,430,"A szolgáltatásaid saját kezelőfelületen.",39,b=False)
        if t<1.25:
            device(im,a["dev_admin"],555,1120,535,990,25-28*q,6,-8+10*q)
        else:
            z=smooth((t-1.25)/1.75)
            card(im,a["admin"],72,570,936,950,True,.1+.74*z)
        text(im,78,1600,"Tulajdonosi nézet • valódi demó",38)
    else:
        label(im,"PRÓBÁLD KI")
        text(im,72,292,"Ne csak nézd.",99);text(im,72,412,"Teszteld.",132,PURPLE)
        text(im,76,570,"Autószerviz-időpontfoglaló",45,b=False)
        device(im,a["dev_slots"],545,1010,345,635,15-28*q,-4,6-12*q)
        d=ImageDraw.Draw(im);d.rounded_rectangle((72,1390,1008,1515),radius=35,fill="#c2a9ff")
        text(im,105,1428,"Bemutatóstúdió megnyitása  →",45,"#151020",limit=870)
        text(im,76,1560,"darkline-studio.web.app",43)
        text(im,76,1640,"Valós, kipróbálható funkciók.",34,MUTED,False)
    brand(im,s,t)
    # Single accent sweep, three frames only; avoid strobing.
    if s and t<.10:
        x=int(-300+1580*ease(t/.10));ImageDraw.Draw(im).polygon([(x,195),(x+54,195),(x-190,1740),(x-244,1740)],fill="#7154a5")
    return im
def sound(path,duration):
    sr=48000;t=np.arange(int(sr*duration))/sr;a=np.zeros_like(t);rng=np.random.default_rng(42)
    # Original rhythmic score at 120 BPM with accents synchronized to scene boundaries.
    for i,beat in enumerate(np.arange(0,duration,.5)):
        z=t-beat;m=(z>=0)&(z<.25);u=z[m];a[m]+=.22*np.sin(2*np.pi*(78*u-68*u*u))*np.exp(-u*20)
        z=t-(beat+.25);m=(z>=0)&(z<.075);u=z[m];a[m]+=.035*rng.normal(0,1,len(u))*np.exp(-u*65)
    for i,beat in enumerate(np.arange(0,duration,.25)):
        hz=[110,110,164.81,130.81,110,220,164.81,130.81][i%8];z=t-beat;m=(z>=0)&(z<.23);u=z[m]
        a[m]+=.065*(np.sin(2*np.pi*hz*u)+.25*np.sin(4*np.pi*hz*u))*np.exp(-u*12)
    for beat in np.cumsum([0]+DUR[:-1]):
        z=t-beat;m=(z>=0)&(z<.32);u=z[m];a[m]+=.06*np.sin(2*np.pi*(360*u+700*u*u))*np.exp(-u*12)
    a*=np.minimum(1,t/.035)*np.minimum(1,np.maximum(0,duration-t)/.45)
    with wave.open(str(path),"wb") as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes((np.clip(a,-.9,.9)*32767).astype("<i2").tobytes())
def render():
    a={p.stem:Image.open(p).convert("RGB") for p in OUT.glob("*.png")}
    for k in ["services","slots","admin"]:a["dev_"+k]=phone_texture(a["phone_"+k])
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
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(audio),"-c:v","copy","-c:a","aac","-b:a","160k","-movflags","+faststart","-shortest",str(OUT/"Darkline_depth_V4.mp4")],check=True)
    files=sorted(OUT.glob("scene-*.jpg"));sheet=Image.new("RGB",(1620,960),"#11111b")
    for i,p in enumerate(files):sheet.paste(Image.open(p).resize((270,480),Image.Resampling.LANCZOS),((i//2)*270,(i%2)*480))
    sheet.save(OUT/"storyboard.jpg",quality=95)
    print("V4_DEPTH_OK", (OUT/"Darkline_depth_V4.mp4").stat().st_size,flush=True)
if __name__=="__main__":capture();render()
