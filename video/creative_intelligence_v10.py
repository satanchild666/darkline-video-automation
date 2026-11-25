"""V10 independent creative review. Public demo views only; no order, save, publication or Buffer call."""
import argparse, json, math, subprocess, tempfile, wave, re
from pathlib import Path
from urllib.parse import urlparse
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from playwright.sync_api import sync_playwright
import creative_cinematic_v9 as v9
import depth_preview_v4 as v4
import cinematic_preview_v5 as v5
import motion_cinematic_v6 as v6
import video_dedup as dedup

ROOT=Path("creative-preview-v10"); ROOT.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30
DUR=[4.5,4.,4.,4.,4.5]; TOTAL=sum(DUR)
BASE="https://darkline-studio.web.app/demok/"
# Independent creative treatments, selected from verified demo path, never arbitrary model output.
PLANS={
"auto":{"path":"autoszerviz.html","style":"Cinematic Tech","label":"AUTÓSZERVIZ","layout":"orbit","colors":["#11101e","#b59aff","#ede7ff","#4b326e"],"bpm":120,"min_open":1.6,
"scenes":[["Még mindig","telefonon?","Időpontok telefonálás nélkül."],["Szolgáltatás","egy érintésre.","Válaszd ki a szolgáltatást."],["Szabad","idősávok.","Nézd meg a szabad időpontokat."],["Saját","kezelőfelület.","Kezeld a szolgáltatásaidat."],["Próbáld ki","a demót.","Fedezd fel a bemutatót."]]},
"menu":{"path":"vendeglatas-egyben.html","style":"Luxury Dining","label":"VENDÉGLÁTÁS","layout":"editorial","colors":["#09201d","#f0c981","#f8efd9","#30594c"],"bpm":92,"min_open":.9,
"scenes":[["Étlapod","egy érintésre.","Digitális étlap a vendégeidnek."],["Ételek","és árak.","Válassz az ételkategóriák közül."],["Mi van ma","az étlapon?","Mutasd meg a napi menüt."],["A kínálat","a kezedben.","Szerkeszd a kínálatodat."],["Nézd meg","működés közben.","Próbáld ki az étlap demót."]]},
"crm":{"path":"ugyfelkezelo.html","style":"Precision Dashboard","label":"ÜGYFÉLKEZELÉS","layout":"dashboard","colors":["#101d2e","#55d5e3","#e7f7fa","#264e68"],"bpm":108,"min_open":.8,
"scenes":[["Ne vesszen el","az érdeklődő.","Lásd egy helyen az érdeklődőket."],["Minden ügyfél","egy táblán.","Kövesd az ügyfelek állapotát."],["A részletek","egy helyen.","Nyisd meg az ügyfél adatait."],["Saját","ügyfélkezelés.","Nézd meg a kezelőfelületet."],["Rendszerezd","az érdeklődést.","Próbáld ki az ügyfélkezelőt."]]},
"web":{"path":"uzleti-weboldal.html","style":"Bright Editorial","label":"ÜZLETI WEBOLDAL","layout":"editorial-light","colors":["#e9e6e1","#2457a5","#192536","#b6cadf"],"bpm":100,"min_open":.8,
"scenes":[["Mutasd meg","a vállalkozásod.","Mutasd be a vállalkozásodat."],["Átlátható","csomagok.","Mutasd meg a szolgáltatásaidat."],["Munkáid","egy helyen.","Adj helyet a referenciáidnak."],["Te kezeled","a tartalmat.","Saját kezelőfelületen dolgozhatsz."],["Ismerd meg","a demót.","Nézd meg az üzleti weboldalt."]]},
"salon":{"path":"szalon.html","style":"Soft Luxury","label":"SZÉPSÉGSZALON","layout":"beauty","colors":["#291c29","#f4aecb","#fff0f4","#74465e"],"bpm":84,"min_open":.8,
"scenes":[["Szalonod","digitálisan.","Mutasd be a szalonod kínálatát."],["Szolgáltatás","kiválasztása.","A vendég szolgáltatást választ."],["Szakember","kiválasztása.","Majd kiválasztja a szakembert."],["A te","kezelőfelületed.","Kezeld saját szolgáltatásaidat."],["Próbáld ki","a szalon demót.","Nézd meg a szalon bemutatóját."]]}
}
def select(url):
    u=urlparse(url)
    if u.scheme!="https" or u.hostname!="darkline-studio.web.app" or u.port not in (None,443) or not u.path.startswith("/demok/"):raise ValueError("Unapproved demo URL")
    matches=[(k,p) for k,p in PLANS.items() if u.path=="/demok/"+p["path"]]
    if len(matches)!=1:raise ValueError("Unknown service: manual review required")
    return matches[0]
def selftest():
    for k,p in PLANS.items():assert select(BASE+p["path"]+"?skin=dark")[0]==k
    for u in ["https://example.com/demok/autoszerviz.html","https://darkline-studio.web.app/demok/unknown.html"]:
        try:select(u)
        except ValueError:continue
        raise AssertionError("Unknown routing accepted")
    assert len(set(p["style"] for p in PLANS.values()))==5
    print("V10_ROUTING_TEST_OK 5 known, 2 rejected, 5 distinct styles",flush=True)
OVERLAYS=['[aria-label="AI tanácsadó segítséget ajánl fel"]','iframe[title="Darkline Studio AI tanácsadó"]','[aria-label="AI üzleti tanácsadás"]','.dl-advisor-widget','.dl-advisor-hint','.dl-advisor-tab','#darkline-premium-guide','.dlg-thought','.dlg-avatar','#darkline-ai-advisor-toggle']
CSS=",".join(OVERLAYS)+"{display:none!important;visibility:hidden!important;pointer-events:none!important}"
old_isolate=v9.isolate;old_clean=v9.clean
def isolate(page):
    old_isolate(page)
    page.add_init_script("(()=>{const css="+json.dumps(CSS)+";const apply=()=>{if(document.head&&!document.getElementById('review-v10-overlay-style')){const s=document.createElement('style');s.id='review-v10-overlay-style';s.textContent=css;document.head.append(s)}};new MutationObserver(apply).observe(document,{subtree:true,childList:true});apply()})()")
def clean(page):
    old_clean(page);page.add_style_tag(content=CSS)
    # Targeted DOM visibility check, not general visual recognition.
    visible=page.evaluate("""sel=>Array.from(document.querySelectorAll(sel)).filter(e=>{const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&e.getClientRects().length>0}).map(e=>e.getAttribute('aria-label')||e.className)""",",".join(OVERLAYS))
    if visible:raise RuntimeError("Known overlay visible: "+str(visible))
v9.isolate=isolate;v9.clean=clean
def snap(page,selector,path):
    clean(page);loc=page.locator(selector).first;loc.wait_for(state="visible",timeout=15000)
    loc.scroll_into_view_if_needed(timeout=15000);page.wait_for_timeout(180);clean(page)
    loc.screenshot(path=str(path),animations="disabled",timeout=20000)
    with Image.open(path) as src:
        # Keep important content large, never distort the captured screenshot.
        if src.height>src.width*1.75:src.crop((0,0,src.width,int(src.width*1.75))).save(path)
def viewport(page,path):
    clean(page);page.screenshot(path=str(path),animations="disabled",timeout=20000)
def open_page(browser,url,width=650,height=1120):
    page=browser.new_page(viewport={"width":width,"height":height},device_scale_factor=1.5)
    isolate(page);page.goto(url,wait_until="domcontentloaded",timeout=45000);page.wait_for_timeout(500);clean(page)
    return page
def admin(page,out):
    owner=page.locator("#ds-v23-owner");owner.wait_for(timeout=20000);clean(page)
    panel=page.locator("#ds-v23-panel")
    if not panel.is_visible():owner.click(timeout=12000)
    panel.wait_for(state="visible",timeout=15000)
    snap(page,"#ds-v23-editor",out/"admin.png")
    # Capture a real visible editable field plus its containing label, without writing.
    editor=page.locator("#ds-v23-editor")
    fields=editor.locator("input:visible,textarea:visible,select:visible")
    if fields.count():
        f=fields.first;f.scroll_into_view_if_needed()
        holder=f.locator("xpath=..")
        holder.screenshot(path=str(out/"admin_detail.png"),animations="disabled",timeout=15000)
    else:raise RuntimeError("No visible editable admin field")
def capture(key,p,out):
    if key=="auto":
        v9.OUT=out;v9.capture()
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
            page=open_page(browser,BASE+p["path"]+"?skin=dark",900,1100);admin(page,out);browser.close()
        return {"source":"live_browser_recordings","overlay_dom_checks":"passed","admin_field":True}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        url=BASE+p["path"]+"?skin=dark"
        if key=="menu":
            page=open_page(browser,BASE+"digitalis-etlap.html?skin=dark")
            page.locator("#menu-grid").wait_for(timeout=20000);viewport(page,out/"hero.png")
            page.locator('[data-cat="foetel"]').click(timeout=12000)
            page.locator('[data-cat="foetel"].active').wait_for()
            page.get_by_role("heading",name="Bélszín Steak",exact=True).wait_for(state="visible")
            snap(page,"#menu-grid",out/"feature.png")
            daily=open_page(browser,BASE+"napi-menu.html?skin=dark")
            snap(daily,"#public-app",out/"detail.png")
            a=open_page(browser,BASE+"digitalis-etlap.html?skin=dark",900,1100);admin(a,out)
        elif key=="crm":
            page=open_page(browser,url,1100,900)
            snap(page,"#crm-stats",out/"hero.png");snap(page,"#crm-board",out/"feature.png")
            card=page.locator('.crm-card[data-crm-id="105"]');card.click(timeout=12000)
            page.locator('.crm-card[data-crm-id="105"][aria-pressed="true"]').wait_for(timeout=12000)
            snap(page,"#crm-detail",out/"detail.png");admin(page,out)
        elif key=="web":
            page=open_page(browser,url,1200,900)
            viewport(page,out/"hero.png");snap(page,"#szolgaltatasok",out/"feature.png");snap(page,"#portfolio",out/"detail.png");admin(page,out)
        elif key=="salon":
            page=open_page(browser,url)
            snap(page,"#service-list",out/"hero.png")
            page.locator("#service-list .service-card").first.click(timeout=12000)
            page.locator("#sec-2").wait_for(state="visible",timeout=15000)
            snap(page,"#staff-list",out/"detail.png")
            # Fresh customer view, no booking finalization.
            second=open_page(browser,url);snap(second,"#service-list",out/"feature.png")
            a=open_page(browser,url,900,1100);admin(a,out)
        browser.close()
    return {"source":"real_demo_screenshots","overlay_dom_checks":"passed","admin_field":True}
def run(args):return subprocess.check_output(args)
def narrations(p,out):
    from piper import PiperVoice
    voice_dir=Path("voice-model");voice_dir.mkdir(exist_ok=True)
    model=voice_dir/"hu_HU-anna-medium.onnx"
    if not model.exists():subprocess.run(["python","-m","piper.download_voices","--download-dir",str(voice_dir),"hu_HU-anna-medium"],check=True)
    voice=PiperVoice.load(str(model));sr=48000;track=np.zeros(round(TOTAL*sr),np.float32);records=[]
    with tempfile.TemporaryDirectory() as tmp:
        for i,(scene,dur) in enumerate(zip(p["scenes"],DUR)):
            speech=Path(tmp)/f"{i}.wav"
            with wave.open(str(speech),"wb") as wf:voice.synthesize_wav(scene[2],wf)
            duration=float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(speech)]))
            speed=max(1,duration/(dur-.55))
            if speed>1.38:raise RuntimeError("Narration exceeds scene window")
            raw=run(["ffmpeg","-v","error","-i",str(speech),"-af",f"atempo={speed:.5f}","-ar",str(sr),"-ac","1","-f","f32le","-"])
            a=np.frombuffer(raw,dtype="<f4").copy()
            if len(a)<sr*.25:raise RuntimeError("Silent or empty narration")
            rms=float(np.sqrt(np.mean(a*a)));peak=float(np.max(np.abs(a)))
            if rms<.0001:raise RuntimeError("Silent speech")
            a*=min(10**(-18/20)/rms,.78/max(peak,1e-6))
            start=round((sum(DUR[:i])+.22)*sr);end=start+len(a)
            if end>round((sum(DUR[:i+1])-.12)*sr):raise RuntimeError("Speech overflow")
            track[start:end]=a
            records.append({"scene":i,"start":start/sr,"end":end/sr,"text":scene[2],"tempo":speed})
    def stamp(sec):
        ms=round(sec*1000);return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"
    (out/"captions.srt").write_text("\n\n".join(f"{i+1}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['text']}" for i,r in enumerate(records))+"\n",encoding="utf8")
    (out/"narration_timing.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf8")
    # Original synthetic soundtrack, tempo and harmony selected by concept.
    t=np.arange(len(track))/sr;bed=np.zeros_like(track);beat=60/p["bpm"]
    hz={"orbit":55,"editorial":110,"dashboard":65.4,"editorial-light":130.8,"beauty":98}[p["layout"]]
    for j,b in enumerate(np.arange(0,TOTAL,beat)):
        u=t-b;m=(u>=0)&(u<min(.35,beat));z=u[m]
        bed[m]+=.12*np.sin(2*np.pi*(78*z-52*z*z))*np.exp(-z*14)
        for k in [1,1.25,1.5]:
            m=(u>=0)&(u<beat);z=u[m]
            bed[m]+=.027*np.sin(2*np.pi*hz*k*[1,1,1.122,1.335][j%4]*z)*np.exp(-z*3)
    duck=np.ones_like(track)*.58
    for r in records:
        a=max(0,round((r["start"]-.08)*sr));b=min(len(track),round((r["end"]+.12)*sr));duck[a:b]=.20
    # Smooth ducking edges and limit peaks.
    window=np.ones(1200,np.float32)/1200
    duck=np.convolve(duck,window,mode="same")
    mix=track+bed*duck
    mix*=min(1,.89/max(float(np.max(np.abs(mix))),1e-6))
    with wave.open(str(out/"mix.wav"),"wb") as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((mix*32767).astype("<i2").tobytes())
    return records
def rgb(h):return tuple(int(h[i:i+2],16) for i in [1,3,5])
def background(p,s,t):
    base,accent,fg,secondary=p["colors"];layout=p["layout"]
    im=Image.new("RGB",(W,H),base);d=ImageDraw.Draw(im);q=t+sum(DUR[:s])
    if layout=="orbit":
        for i in range(11):
            x=int((i*180+105*q)%1700)-350;d.line((x,1550,x+420,235),fill=secondary,width=2)
    elif layout=="editorial":
        for i in range(6):
            r=int(160+90*i+20*t);d.arc((540-r,970-r,540+r,970+r),int(185+q*13),int(335+q*13),fill=secondary,width=3)
    elif layout=="dashboard":
        for x in range(10,1080,90):
            x=int(x+q*19)%1080;d.line((x,210,x,1530),fill=secondary,width=2)
        for y in range(240,1550,90):d.line((72,y,1008,y),fill=secondary,width=2)
    elif layout=="editorial-light":
        d.rectangle((0,230,int(190+35*math.sin(q)),1530),fill=secondary)
        d.line((72,220,1008,220),fill=accent,width=3)
    else:
        for i in range(4):
            x=180+i*245+80*math.sin(q*.6+i);y=850+120*math.cos(q*.8+i)
            d.ellipse((x-240,y-370,x+240,y+370),outline=secondary,width=3)
    if layout!="editorial-light":
        light=Image.new("RGB",(270,480));ld=ImageDraw.Draw(light);x=int(135+100*math.sin(q*.9));y=245
        ld.ellipse((x-95,y-130,x+95,y+130),fill=tuple(int(c*.18) for c in rgb(accent)))
        im=ImageChops.screen(im,light.filter(ImageFilter.GaussianBlur(42)).resize((W,H),Image.Resampling.BILINEAR))
    return im
def load(path):
    with Image.open(path) as im:return im.convert("RGB")
def assets(key,out):
    if key=="auto":
        a={"hero":load(out/"phone_services.png"),"feature":load(out/"service_after.png"),"detail":load(out/"slots_after.png")}
        v9.LIVE={n:sorted((out/n).glob("*.jpg")) for n in ["live_service","live_slots","live_admin"]}
    else:a={k:load(out/(k+".png")) for k in ["hero","feature","detail"]}
    a.update({k:load(out/(k+".png")) for k in ["admin","admin_detail"]})
    for k in ["hero","feature","detail"]:a[k+"_tex"]=v9.premium_texture(a[k])
    return a
def frame(key,p,s,t,a,records):
    base,accent,fg,secondary=p["colors"];layout=p["layout"];im=background(p,s,t);d=ImageDraw.Draw(im)
    q=v4.smooth(t/DUR[s]);e=v4.ease(t/.7);scene=p["scenes"][s]
    v4.text(im,72,100,"DARKLINE / STUDIO",32,fg)
    v4.text(im,72,220,p["label"]+"  /  "+f"{s+1:02}",31,accent)
    d.line((72,184,1008,184),fill=secondary,width=2)
    v4.text(im,72,int(305+35*(1-e)),scene[0],97,fg,limit=936)
    v4.text(im,72,int(422+35*(1-e)),scene[1],98,accent,limit=936)
    if s==0 or s==4:
        if layout=="orbit":
            angle=-1.1+1.9*v4.ease(t/.75)+.6*t
            v5.laptop(im,v5.laptop_texture(a["admin"]),540,980,770,470,22*math.cos(angle),5,-5*math.sin(angle),t)
            for k,z in sorted([("hero_tex",angle),("detail_tex",angle+math.pi)],key=lambda x:math.sin(x[1])):
                dep=math.sin(z);v9.premium_phone(im,a[k],540+340*math.cos(z),1060+70*dep,330+45*dep,640+80*dep,29*math.cos(z),5,-10*math.cos(z),t)
        elif layout=="dashboard":
            v5.laptop(im,v5.laptop_texture(a["feature"]),540,920,920,530,-30+45*q,6,-5+8*q,t)
            v4.card(im,a["detail"],115+int(35*q),1210,850,230)
        elif layout=="editorial-light":
            v5.laptop(im,v5.laptop_texture(a["hero"]),540,970,960,570,-19+34*q,5,-5+7*q,t)
            v4.card(im,a["feature"],110,1255,860,220)
        else:
            v9.premium_phone(im,a["hero_tex"],440+140*e,1020,480+35*q,890,-32+48*q,5,-12+17*q,t)
            v4.card(im,a["detail"],610-int(50*q),1050,365,320)
        if s==4:
            d=ImageDraw.Draw(im);d.rounded_rectangle((90,1440,990,1530),radius=26,fill=accent)
            v4.text(im,115,1459,"darkline-studio.web.app",43,base,limit=850)
    elif s in (1,2):
        k="feature" if s==1 else "detail"
        if key=="auto":
            name="live_service" if s==1 else "live_slots"
            src=v9.read_frame(name,t,DUR[s])
            v4.card(im,src,210-int(45*q),570,660+int(90*q),910)
        elif layout in ("dashboard","editorial-light"):
            v4.card(im,a[k],80-int(8*q),610-int(45*q),920+int(16*q),850+int(60*q),False)
        elif layout=="editorial":
            v4.card(im,a[k],100-int(24*q),600-int(40*q),880+int(48*q),890,False)
        else:v9.premium_phone(im,a[k+"_tex"],540+50*math.sin(t*1.7),1030,530,930,-24+42*q,5,9-15*q,t)
    else:
        v4.card(im,a["admin"],92-int(20*q),575-int(20*q),896+int(40*q),680+int(35*q),False)
        v4.card(im,a["admin_detail"],112-int(30*q),1280-int(18*q),856+int(60*q),220,False)
    # Subtitle is visible exactly during the synthesized phrase, not over UI.
    r=records[s];at=sum(DUR[:s])+t
    if r["start"]<=at<r["end"]:
        d=ImageDraw.Draw(im);d.rounded_rectangle((72,1570,1008,1710),radius=24,fill="#10121b")
        v4.text(im,98,1614,r["text"],42,"#ffffff",limit=884)
    d=ImageDraw.Draw(im);d.rounded_rectangle((72,1758,1008,1766),radius=4,fill=secondary)
    d.rounded_rectangle((72,1758,72+int(936*at/TOTAL),1766),radius=4,fill=accent)
    return im
def render(key,p,out,records):
    a=assets(key,out);silent=out/"silent.mp4";movie=out/f"Darkline_V10_{key}.mp4"
    proc=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","pipe:0","-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p","-threads","3",str(silent)],stdin=subprocess.PIPE)
    try:
        for s,d in enumerate(DUR):
            for n in range(round(d*FPS)):
                im=frame(key,p,s,n/FPS,a,records)
                if n in (12,round(d*FPS)//2):im.save(out/f"scene-{s+1}-{n:03}.jpg",quality=93)
                proc.stdin.write(im.tobytes())
    finally:proc.stdin.close()
    if proc.wait():raise RuntimeError("Encoding failed")
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(out/"mix.wav"),"-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart","-shortest",str(movie)],check=True)
    silent.unlink();(out/"mix.wav").unlink()
    sheet=Image.new("RGB",(1350,960),p["colors"][0])
    for i,f in enumerate(sorted(out.glob("scene-*.jpg"))):sheet.paste(load(f).resize((270,480),Image.Resampling.LANCZOS),((i//2)*270,(i%2)*480))
    sheet.save(out/"storyboard.jpg",quality=94)
    return movie
def check(key,p,out,movie,records,capture_result):
    report=v9.check_quality(movie,TOTAL,p["min_open"])
    info=json.loads(run(["ffprobe","-v","error","-show_streams","-of","json",str(movie)]))
    video=next(s for s in info["streams"] if s["codec_type"]=="video")
    if video["r_frame_rate"]!="30/1":report["reasons"].append("fps")
    audio=np.frombuffer(run(["ffmpeg","-v","error","-i",str(movie),"-map","0:a:0","-ac","1","-ar","48000","-f","f32le","-"]),dtype="<f4")
    peak=float(np.max(np.abs(audio)))
    if peak>=.999:report["reasons"].append("audio_peak")
    if len(records)!=5 or any(r["end"]>sum(DUR[:i+1]) or r["start"]<sum(DUR[:i]) for i,r in enumerate(records)):report["reasons"].append("narration_timing")
    if capture_result["overlay_dom_checks"]!="passed":report["reasons"].append("known_overlay")
    report.update({"style":p["style"],"key":key,"audio_peak":peak,"subtitle_count":len(records),"capture":capture_result,"review_gate":"PASS" if not report["reasons"] else "REJECT","publication":False})
    fp=dedup.fingerprint(movie,{"scenes":[{"heading":x[0]+" "+x[1],"detail":x[2]} for x in p["scenes"]]})
    dedup.save(out/"fingerprint.json",fp)
    print("V10_QUALITY",json.dumps(report,ensure_ascii=False),flush=True)
    return report
def main(url):
    selftest();key,p=select(url);out=ROOT/key;out.mkdir(exist_ok=True)
    (out/"plan.json").write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding="utf8")
    try:
        result=capture(key,p,out);print("V10_CAPTURE_OK",key,result,flush=True)
        records=narrations(p,out);print("V10_NARRATION_OK",key,len(records),flush=True)
        movie=render(key,p,out,records);report=check(key,p,out,movie,records,result)
    except Exception as exc:
        report={"key":key,"review_gate":"REJECT","reasons":["exception"],"error":str(exc)[:600],"publication":False}
        print("V10_FAILURE",json.dumps(report,ensure_ascii=False),flush=True)
        (out/"quality.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
        raise
    (out/"quality.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    if report["review_gate"]!="PASS":raise RuntimeError("Review thresholds not met")
def aggregate(directory):
    reports=[];history=[];pairs=[]
    for key in PLANS:
        paths=list(Path(directory).rglob(f"{key}/quality.json"))+list(Path(directory).glob(f"V10-{key}/quality.json"))
        if len(paths)!=1:reports.append({"key":key,"review_gate":"REJECT","reasons":["missing_report"]});continue
        f=paths[0];r=json.loads(f.read_text(encoding="utf8"));reports.append(r)
        fp=f.parent/"fingerprint.json"
        if fp.exists():
            cand=dedup.validate(json.loads(fp.read_text()))
            for tag,old in history:pairs.append({"a":tag,"b":key,"duplicate":dedup.compare(cand,old)})
            history.append((key,cand))
    result={"reports":reports,"pairwise_comparisons":pairs,"history_scope":"this V10 batch only","publication":False}
    (ROOT/"batch_quality.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print("V10_BATCH",json.dumps(result,ensure_ascii=False),flush=True)
    if len(history)!=5 or len(pairs)!=10 or any(r["review_gate"]!="PASS" for r in reports) or any(x["duplicate"] for x in pairs):raise RuntimeError("V10 batch needs review")
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--url");ap.add_argument("--aggregate");args=ap.parse_args()
    if args.aggregate:aggregate(args.aggregate)
    elif args.url:main(args.url)
    else:selftest()
