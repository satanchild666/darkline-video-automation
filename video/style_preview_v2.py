"""Design review only: real public demo captures, original motion graphics, no posting."""
import math, subprocess, tempfile, wave, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from playwright.sync_api import sync_playwright

OUT=Path("visual-preview")
OUT.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
URL="https://darkline-studio.web.app/demok/autoszerviz.html?skin=dark"
def font(n,b=False):return ImageFont.truetype(BOLD if b else FONT,n)
def capture():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        page=browser.new_page(viewport={"width":480,"height":900},device_scale_factor=2,is_mobile=True,has_touch=True)
        # No analytics opt-in or external writes. Real demo interaction only.
        page.goto(URL,wait_until="domcontentloaded",timeout=45000)
        page.locator(".service-card").first.wait_for(timeout=20000)
        for loc in [page.get_by_role("button",name="Most nem",exact=True),page.locator(".ds-demo-close"),page.locator('button[aria-label="Ajánló tipp elrejtése"]')]:
            try:
                if loc.first.is_visible():loc.first.click(timeout=1500)
            except Exception:pass
        page.add_style_tag(content="#darkline-premium-guide,.dlg-avatar,.dlg-thought,.dlg-thought-tour,.dl-advisor-tab,#darkline-ai-advisor-toggle{display:none!important;pointer-events:none!important}")
        page.wait_for_timeout(350)
        def shot(locator,name):
            locator.scroll_into_view_if_needed(timeout=12000)
            page.wait_for_timeout(280)
            locator.screenshot(path=str(OUT/name),animations="disabled",timeout=15000)
        first=page.locator(".service-card").first
        shot(page.locator("#services-list"),"services.png")
        first.click(timeout=12000)
        page.locator(".service-card.active").wait_for()
        day=page.locator(".date-btn").nth(1)
        day.click(timeout=12000)
        slot=page.locator(".time-btn:not([disabled])").first
        slot.wait_for(timeout=12000);slot.click(timeout=12000)
        page.locator(".time-btn.active").wait_for()
        shot(page.locator("#date-scroller"),"dates.png")
        shot(page.locator("#time-grid"),"slots.png")
        page.locator("#ds-v23-owner").click(timeout=12000)
        page.locator("#ds-v23-panel").wait_for(state="visible")
        editor=page.locator("#ds-v23-editor")
        editor.wait_for(state="visible")
        shot(editor,"admin.png")
        browser.close()
    print("REAL_DEMO_CAPTURE_OK selected service, day, time; opened owner view; no booking submitted")

def fit(im,w,h):
    im=im.convert("RGB")
    scale=min(w/im.width,h/im.height)
    return im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
def ease(t):
    t=max(0,min(1,t));return 1-(1-t)**3
def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
def bg():
    y,x=np.mgrid[0:H,0:W].astype(np.float32)
    glow=np.exp(-((x-900)**2/500**2+(y-680)**2/650**2))
    blue=np.exp(-((x-100)**2/440**2+(y-1460)**2/540**2))
    a=np.stack([11+35*glow+5*blue,12+6*glow+17*blue,20+38*glow+36*blue],axis=-1)
    return Image.fromarray(np.uint8(a))
BG=bg()
def line(d,xy,txt,size=54,col="#f4f4fa",b=True):
    d.text(xy,txt,font=font(size,b),fill=col)
def pill(d,x,y,txt):
    f=font(26,True);w=d.textlength(txt,font=f)+48
    d.rounded_rectangle((x,y,x+w,y+56),radius=28,fill="#25243c",outline="#5c4b82",width=2)
    d.text((x+24,y+11),txt,font=f,fill="#dfd1ff")
def panel(im,img,x,y,w,h):
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((x-12,y-12,x+w+12,y+h+12),radius=30,fill="#12121e",outline="#55436b",width=3)
    a=fit(img,w,h)
    im.paste(a,(x+(w-a.width)//2,y+(h-a.height)//2))
def frame(s,t,assets):
    im=BG.copy();d=ImageDraw.Draw(im)
    # Editorial safe area; all text and critical controls remain away from Reels overlays.
    d.rounded_rectangle((72,95,129,152),radius=15,fill="#a888ff")
    line(d,(84,106),"DS",25,"#141022")
    line(d,(151,104),"DARKLINE / STUDIO",32)
    d.line((72,186,1008,186),fill="#393347",width=2)
    e=ease(t/.42)
    y=int(226+34*(1-e))
    d.rectangle((72,210,72+int(170*e),218),fill="#a888ff")
    if s==0:
        pill(d,72,y+36,"AUTÓSZERVIZ • ÉLŐ DEMÓ")
        line(d,(72,y+122),"Még mindig",92)
        line(d,(72,y+232),"telefonon?",116,"#c2a9ff")
        line(d,(75,y+386),"Mutasd meg a szabad időpontokat online.",37,b=False)
        panel(im,assets["services"],104,int(820-90*e),872,750)
        line(d,(82,1620),"01   /   IDŐPONTFOGLALÓ",34,"#c2a9ff")
    elif s==1:
        pill(d,72,y+36,"01 / SZOLGÁLTATÁS")
        line(d,(72,y+124),"Egyértelmű",85)
        line(d,(72,y+220),"választás.",105,"#c2a9ff")
        line(d,(75,y+365),"A vendég kiválasztja, mire van szüksége.",37,b=False)
        panel(im,assets["services"],83,int(730+32*(1-e)),914,790)
        line(d,(82,1620),"Valódi ügyfélnézet",38)
    elif s==2:
        pill(d,72,y+36,"02 / IDŐPONT")
        line(d,(72,y+124),"Nap. Idősáv.",88)
        line(d,(72,y+224),"Kész.",112,"#c2a9ff")
        panel(im,assets["dates"],100,int(690+30*(1-e)),880,300)
        panel(im,assets["slots"],100,int(1030+40*(1-e)),880,465)
        line(d,(82,1620),"Az elérhető idősávok láthatók.",37)
    elif s==3:
        pill(d,72,y+36,"03 / SAJÁT ADMIN")
        line(d,(72,y+124),"Te irányítod.",90)
        line(d,(75,y+255),"A szolgáltatásaid saját kezelőfelületen.",39,b=False)
        panel(im,assets["admin"],82,int(690+32*(1-e)),916,850)
        line(d,(82,1620),"Tulajdonosi nézet • valódi demó",35)
    else:
        pill(d,72,y+36,"PRÓBÁLD KI")
        line(d,(72,y+180),"Ne csak nézd.",90)
        line(d,(72,y+300),"Teszteld.",126,"#c2a9ff")
        line(d,(76,y+490),"Autószerviz-időpontfoglaló",42,b=False)
        d.rounded_rectangle((72,1100,1008,1240),radius=36,fill="#c2a9ff")
        line(d,(111,1140),"Bemutatóstúdió megnyitása  →",47,"#151020")
        line(d,(76,1310),"darkline-studio.web.app",42)
        line(d,(76,1415),"Valós, kipróbálható funkciók.",35,"#c1bfce",False)
    # Continuous moving progress cue, not a repeated full-screen text card.
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((72,1760,1008,1770),radius=5,fill="#393347")
    progress=(s+min(1,t/[2.2,3.0,3.3,3.3,2.7][s]))/5
    d.rounded_rectangle((72,1760,72+int(936*progress),1770),radius=5,fill="#a888ff")
    line(d,(72,1790),"DARKLINE STUDIO  /  DESIGN PREVIEW",25,"#b0a8bf",False)
    return im
def sound(path,duration):
    sr=48000;t=np.arange(int(sr*duration))/sr
    a=np.zeros_like(t)
    # Original minimal synth bed and soft percussive scene cues; no third-party music.
    for beat in np.arange(0,duration,.5):
        z=t-beat;m=(z>=0)&(z<.35);zz=z[m]
        a[m]+=.11*np.sin(2*np.pi*(72*zz-42*zz**2))*np.exp(-zz*17)
    for k,hz in enumerate([110,164.81,220,277.18]):
        a+=.017*np.sin(2*np.pi*hz*t+.4*np.sin(2*np.pi*.35*t+k))*(.65+.35*np.sin(2*np.pi*.23*t+k))
    for v in [0,2.2,5.2,8.5,11.8]:
        z=t-v;m=(z>=0)&(z<.23);zz=z[m];a[m]+=.035*np.sin(2*np.pi*(440*zz+600*zz**2))*np.exp(-zz*14)
    a*=np.minimum(1,t/.12)*np.minimum(1,np.maximum(0,duration-t)/.55)
    with wave.open(str(path),"wb") as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes((np.clip(a,-1,1)*32767).astype("<i2").tobytes())
def render():
    assets={k:Image.open(OUT/(k+".png")).convert("RGB") for k in ["services","dates","slots","admin"]}
    durations=[2.2,3.0,3.3,3.3,2.7]
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td);silent=temp/"silent.mp4";audio=temp/"sound.wav"
        cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","pipe:0","-c:v","libx264","-preset","fast","-crf","17","-pix_fmt","yuv420p","-threads","3",str(silent)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for s,duration in enumerate(durations):
                frame(s,.7,assets).save(OUT/f"scene-{s+1}.jpg",quality=94)
                for n in range(round(duration*FPS)):
                    proc.stdin.write(frame(s,n/FPS,assets).tobytes())
        finally:proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError("Video encoding failed")
        sound(audio,sum(durations))
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(audio),"-c:v","copy","-c:a","aac","-b:a","160k","-movflags","+faststart","-shortest",str(OUT/"Darkline_style_V2_preview.mp4")],check=True)
    sheet=Image.new("RGB",(1350,480),"#11111b")
    for s in range(5):
        img=Image.open(OUT/f"scene-{s+1}.jpg").resize((270,480),Image.Resampling.LANCZOS)
        sheet.paste(img,(s*270,0))
    sheet.save(OUT/"storyboard.jpg",quality=95)
    print("STYLE_VIDEO_OK", (OUT/"Darkline_style_V2_preview.mp4").stat().st_size)
if __name__=="__main__":
    capture()
    render()
