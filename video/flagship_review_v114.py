"""V11.4 flagship website walkthrough. No demo pages, login, submissions, or posting.
Two bounded free-only narration calls; encrypted owner review only."""
import argparse,copy,json,math,subprocess,wave,zipfile
from pathlib import Path
from urllib.parse import urlparse
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from cryptography.hazmat.primitives import serialization
import private_review_v113 as base
import private_review_v111 as seal
import heygen_free_voice_v11 as voice
ROOT=Path("private-preview-v114")
SEALED=Path("sealed-review-v114")
HOST="https://darkline-studio.web.app/"
PAGES={"home":"","prices":"megoldasok.html","quote":"ajanlat.html","portal":"ugyfelportal.html"}
# Each row: heading, public page, selector or visible heading, narration.
STORY=[
("Kevesebb adminisztráció","home",".hero__copy","Üdvözöllek a Darkline Studio oldalán! A célom, hogy több időd maradjon a vállalkozásodra."),
("Kisvállalkozásoknak","home",".value-section","Weboldalakat és egyedi digitális rendszereket készítek, a mindennapi igényeidből kiindulva."),
("Okos ajánló","home","#okos-ajanlo","Az okos ajánló segít eligazodni, ha még nem tudod, milyen megoldásra van szükséged."),
("Vállalkozásod kihívásai","home","#megoldaskereso","Válaszd ki a vállalkozásod típusát és a problémát, amelyen szeretnél könnyíteni."),
("Megvalósított munkák","home","#sajat-munkak","A portfólióban valódi, korábban megvalósított fejlesztéseimet ismerheted meg."),
("Egyedi fejlesztések","home","heading:RadnóTinta Scanner","A RadnóTinta leltárkezelője például a bolti készletek és árak kezelését támogatja."),
("Saját ötleted","home","#egyedi","Ha egy kész csomag nem illik az elképzelésedhez, egyedi megoldásról is egyeztethetünk."),
("Hogyan dolgozunk?","home","#igy-dolgozunk","A munkafolyamatot négy lépésben mutatom be, az első egyeztetéstől az átadásig."),
("Emberi léptékben","home","#rolam","Fontos számomra, hogy a fejlesztés érthető legyen, és a valódi problémákra adjon választ."),
("Visszajelzések","home","#velemenyek","A véleményeknek külön helyük van az oldalon, mert az ügyfelek visszajelzése is számít."),
("Szolgáltatások és árak","prices","heading:Átlátható árazás","A szolgáltatások oldalán átlátható csomagokat és tájékoztató induló árakat találsz."),
("Mit tartalmaz a csomag?","prices","heading:Egyszerű, egyoldalas weboldal","Minden csomagnál megismerheted az alaptartalmat. A pontos terjedelmet írásban egyeztetjük."),
("Saját kezelőfelület","prices","heading:Nem kell engem hívnod","Az alapcsomagokhoz saját kezelőfelület jár, így a megfelelő tartalmakat önállóan módosíthatod."),
("Ügyfélportál","home","#ugyfelbelepes","A meghívott ügyfelek az ügyfélportálon követhetik a projektjük állapotát, ajánlatát és üzeneteit."),
("Biztonságos belépés","portal","heading:Ügyfélbelépés","Ez a saját projektek belépési pontja. Az ajánlatkéréshez azonban nem szükséges ügyfélfiók."),
("Árbecslő","home","#ajanlatkeres","Az árbecslő segít megtervezni az igényeidet és áttekinteni a választható megoldásokat."),
("Személyes ajánlat","quote","heading:Beszéljük át, mire van szükséged","Az ajánlatkérő néhány kérdéssel segít összefoglalni, mit szeretnél megvalósítani."),
("Gyakori kérdések","home","#gyik","A gyakori kérdések között további információkat találsz az együttműködésről."),
("Kapcsolatfelvétel","home","#kapcsolat","Ha kérdésed van, az elérhetőségeken keresztül írásban is felveheted velem a kapcsolatot."),
("Ismerd meg a Darkline Studiót","home",".hero__copy","Nézz körül a Darkline Studio weboldalán, és kérj személyre szabott, kötelezettség nélküli ajánlatot!")
]
def allowed(url):
    u=urlparse(url)
    return u.scheme=="https" and u.hostname=="darkline-studio.web.app" and u.port in (None,443) and u.path in ("/","/index.html","/megoldasok.html","/ajanlat.html","/ugyfelportal.html")
def capture(v,out):
    # Only public, allowlisted documents. Block navigation to demo paths and all form submissions.
    shots=[];audit=[]
    with v.sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        ctx=browser.new_context(viewport={"width":1050,"height":1050},device_scale_factor=1.5)
        def guard(route):
            req=route.request
            if req.method not in ("GET","HEAD","OPTIONS"):return route.abort()
            if req.is_navigation_request() and not allowed(req.url):return route.abort()
            return route.continue_()
        ctx.route("**/*",guard)
        pages={}
        for key,path in PAGES.items():
            page=ctx.new_page();v.isolate(page)
            page.goto(HOST+path,wait_until="domcontentloaded",timeout=45000)
            page.wait_for_timeout(2200)
            if not allowed(page.url):raise RuntimeError("Unexpected public page navigation")
            # Hide intrusive prompts; no account login or real data entry.
            page.add_style_tag(content=".intro-loader,.dlg-avatar,.dlg-thought,.dlg-thought-tour,.dl-advisor-widget,.dl-advisor-hint,#darkline-ai-advisor-toggle{display:none!important;visibility:hidden!important}")
            v.clean(page)
            pages[key]=page
        for i,(title,key,sel,_) in enumerate(STORY):
            page=pages[key]
            if sel.startswith("heading:"):
                loc=page.get_by_role("heading",name=sel[8:],exact=False).first
                loc.wait_for(state="visible",timeout=20000)
                loc=loc.locator("xpath=ancestor::*[self::article or self::section][1]")
                if not loc.count():raise RuntimeError("Heading container absent")
            else:loc=page.locator(sel).first
            loc.wait_for(state="visible",timeout=20000)
            loc.scroll_into_view_if_needed(timeout=15000);page.wait_for_timeout(500);v.clean(page)
            # Crop to the actual section, keeping text legible; avoid giant screenshots.
            box=loc.bounding_box()
            if not box or box["width"]<50 or box["height"]<30:raise RuntimeError("Empty section")
            if box["height"]>1250:
                loc.evaluate("el=>el.scrollIntoView({block:'start',behavior:'instant'})")
                page.wait_for_timeout(250);v.clean(page)
                box=loc.bounding_box()
                # Viewport clip restricted to the requested section.
                x=max(0,box["x"]);y=max(0,box["y"])
                width=min(1050-x,box["width"]);height=min(1050-y,box["height"])
                if width<50 or height<50:raise RuntimeError("Invalid viewport clip")
                page.screenshot(path=str(out/f"shot-{i:02d}.png"),clip={"x":x,"y":y,"width":width,"height":height},animations="disabled")
            else:
                loc.screenshot(path=str(out/f"shot-{i:02d}.png"),animations="disabled",timeout=20000)
            shots.append(v.load(out/f"shot-{i:02d}.png"))
            audit.append({"scene":i+1,"page":page.url,"section":sel})
            print("V114_CAPTURE",i+1,key,flush=True)
        ctx.close();browser.close()
    (out/"capture_report.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf8")
    return shots
def narrate(p,out):
    # Reuse the verified ten-scene speech/timing/mixing module in two bounded chapters.
    # No extra voice generation on an error. Both chapters use the same approved profile.
    chosen="natural";settings=voice.profile("web",chosen)[1]
    edges=[0];caps=[];records=[];durations=[];tracks=[]
    for chapter in range(2):
        sub=out/f"chapter-{chapter}";sub.mkdir()
        rows=STORY[chapter*10:(chapter+1)*10]
        base.STORIES["web"]=[(r[0],"unused",r[3]) for r in rows]
        rec,e,cc,duration=base.speech_and_mix(p,"web",sub,settings,chosen)
        offset=edges[-1]/30
        for r in rec:
            records.append({**r,"scene":r["scene"]+chapter*10,"start":r["start"]+offset,"end":r["end"]+offset})
        for r in cc:
            caps.append({**r,"scene":r["scene"]+chapter*10,"start":r["start"]+offset,"end":r["end"]+offset})
        edges.extend([edges[-1]+x for x in e[1:]])
        durations.append(duration)
        with wave.open(str(sub/"mix.wav"),"rb") as w:
            assert w.getnchannels()==1 and w.getsampwidth()==2 and w.getframerate()==48000
            tracks.append(w.readframes(w.getnframes()))
    total=edges[-1]/30
    if not 65<=total<=120:raise RuntimeError("Flagship duration outside target")
    with wave.open(str(out/"mix.wav"),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(b"".join(tracks))
    (out/"captions.srt").write_text("\n\n".join(f"{i+1}\n{voice.stamp(r['start'])} --> {voice.stamp(r['end'])}\n{r['text']}" for i,r in enumerate(caps))+"\n",encoding="utf8")
    (out/"narration_timing.json").write_text(json.dumps({"scenes":records,"captions":caps,"frame_boundaries":edges},ensure_ascii=False,indent=2),encoding="utf8")
    (out/"voice_provenance.json").write_text(json.dumps({"model":voice.MODEL,"profile":chosen,"duration":sum(durations),"chapters":durations,"publication":False},indent=2))
    return records,edges,caps,sum(durations)
def frame(v,p,shots,s,n,edges,caps,fonts):
    at=n/30;t=(n-edges[s])/30;dur=(edges[s+1]-edges[s])/30
    e=v.v4.ease(t/.8);phase=2*math.pi*t/dur
    im=v.background(p,s,t);d=ImageDraw.Draw(im)
    fg="#f2eaff";accent="#c3a3ff"
    d.text((72,95),"DARKLINE / STUDIO",font=fonts[0],fill=fg)
    d.text((72,165),f"WEBOLDALBEMUTATÓ  /  {s+1:02d} · {len(STORY)}",font=fonts[1],fill=accent)
    d.line((72,230,1008,230),fill="#65528d",width=3)
    for i,line in enumerate(base.wrap(d,STORY[s][0],fonts[2],936)):
        d.text((72,260+i*80),line,font=fonts[2],fill=fg if i==0 else accent)
    # Camera reveal and gentle movement of real captures; no invented UI.
    w=round(780+160*e+45*math.sin(phase));h=round(820+140*e+35*math.sin(phase+1))
    x=round((1080-w)/2+(-1 if s%2 else 1)*(95*(1-e)+32*math.sin(phase*1.25)))
    y=round(510+100*(1-e)-26*math.sin(phase))
    v.v4.card(im,shots[s],x,y,w,h,False)
    d=ImageDraw.Draw(im)
    if s==len(STORY)-1:
        d.rounded_rectangle((72,1430,1008,1520),radius=24,fill=accent)
        d.text((96,1450),"darkline-studio.web.app",font=fonts[3],fill="#171121")
    active=next((r for r in caps if r["start"]<=at<r["end"]),None)
    if active:
        lines=base.wrap(d,active["text"],fonts[4],890)
        if len(lines)>3:raise RuntimeError("Caption overflow")
        d.rounded_rectangle((64,1545,1016,1742),radius=24,fill="#11131c")
        for i,line in enumerate(lines):
            d.text(((1080-d.textlength(line,font=fonts[4]))/2,1545+(197-len(lines)*55)/2+i*55),line,font=fonts[4],fill="white")
    d.rounded_rectangle((72,1800,1008,1808),radius=4,fill="#65528d")
    d.rounded_rectangle((72,1800,72+max(1,int(936*n/edges[-1])),1808),radius=4,fill=accent)
    return im
def render(v,p,out,shots,edges,caps):
    v.DUR=[(b-a)/30 for a,b in zip(edges,edges[1:])];v.TOTAL=edges[-1]/30
    fonts=[ImageFont.truetype(base.BOLD,36),ImageFont.truetype(base.FONT,32),ImageFont.truetype(base.BOLD,68),ImageFont.truetype(base.BOLD,43),ImageFont.truetype(base.BOLD,46)]
    silent=out/"silent.mp4";movie=out/"Darkline_V114_flagship.mp4"
    cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size","1080x1920","-framerate","30","-i","pipe:0","-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p","-threads","3",str(silent)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE);thumbs=[]
    try:
        for s,(start,end) in enumerate(zip(edges,edges[1:])):
            for n in range(start,end):
                im=frame(v,p,shots,s,n,edges,caps,fonts)
                if n==(start+end)//2:thumbs.append(im.resize((270,480),Image.Resampling.LANCZOS))
                proc.stdin.write(im.tobytes())
            print("V114_SCENE_RENDERED",s+1,flush=True)
    finally:proc.stdin.close()
    if proc.wait():raise RuntimeError("Video encoding failed")
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(out/"mix.wav"),"-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart","-shortest",str(movie)],check=True)
    sheet=Image.new("RGB",(1350,1920),"#171121")
    for i,im in enumerate(thumbs):sheet.paste(im,((i%5)*270,(i//5)*480))
    sheet.save(out/"storyboard.jpg",quality=94)
    return movie
def selftest():
    assert len(STORY)==20 and set(r[1] for r in STORY)==set(PAGES)
    assert all(500<=len(" ".join(r[3] for r in STORY[i:i+10]))<=1000 for i in (0,10))
    assert not allowed(HOST+"demok/autoszerviz.html") and not allowed(HOST+"bemutatok.html")
    assert all(allowed(HOST+x) for x in PAGES.values())
    base.selftest()
    print("V114_SELFTEST_OK 20 scenes, two bounded scripts, no demo navigation, owner encryption",flush=True)
def main():
    import creative_intelligence_v10 as v
    voice.authorize()
    public=serialization.load_pem_public_key(base.PUBLIC_KEY)
    out=ROOT/"flagship";out.mkdir(parents=True,exist_ok=False)
    p=copy.deepcopy(v.PLANS["web"]);p.update({"colors":["#171121","#c3a3ff","#f2eaff","#65528d"],"layout":"editorial-light","bpm":100})
    shots=capture(v,out)
    records,edges,caps,duration=narrate(p,out)
    movie=render(v,p,out,shots,edges,caps)
    total=edges[-1]/30
    report=v.v9.check_quality(movie,total,.8)
    info=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-of","json",str(movie)]))
    stream=next(s for s in info["streams"] if s["codec_type"]=="video")
    audio=np.frombuffer(subprocess.check_output(["ffmpeg","-v","error","-i",str(movie),"-map","0:a:0","-ac","1","-ar","48000","-f","f32le","-"]),dtype="<f4")
    peak=float(np.max(np.abs(audio)));reasons=report["reasons"]
    if not 65<=total<=120 or duration/total<.90:reasons.append("duration")
    if stream["r_frame_rate"]!="30/1" or peak>=.999:reasons.append("fps_or_peak")
    if len(records)!=20 or any(r["start"]<edges[i]/30-.00001 or r["end"]>edges[i+1]/30+.00001 for i,r in enumerate(records)):reasons.append("alignment")
    report.update({"seconds":total,"speech_seconds":duration,"scenes":20,"captions":len(caps),"audio_peak":peak,"profile":"natural","model":voice.MODEL,"demo_pages_opened":0,"review_gate":"PASS" if not reasons else "REJECT","human_review":"pending","publication":False})
    (out/"quality.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    path=out/"review.zip"
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        for f in [movie]+[out/n for n in ("captions.srt","quality.json","voice_provenance.json","narration_timing.json","storyboard.jpg","capture_report.json")]:z.write(f,arcname=f.name)
    SEALED.mkdir(exist_ok=True);data=path.read_bytes()
    if not 0<len(data)<100_000_000:raise RuntimeError("Invalid package size")
    (SEALED/"Darkline_V114_flagship.dlenc").write_bytes(seal.seal(data,public))
    print("V114_RESULT",json.dumps(report,ensure_ascii=False),flush=True)
    if reasons:raise RuntimeError("Flagship needs human review")
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--selftest",action="store_true");args=ap.parse_args()
    if args.selftest:selftest()
    else:main()
