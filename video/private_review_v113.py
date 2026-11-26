"""V11.3 extended owner reviews, not publishing. Reuse the approved V11.1 encryption key
and free-only speech adapter. One speech call per video, never retry automatically."""
import argparse,copy,json,math,os,subprocess,textwrap,wave,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from cryptography.hazmat.primitives import serialization
import private_review_v111 as prior
import heygen_free_voice_v11 as voice
# Owner-only recovery key backed up in Drive; only public half committed.
PUBLIC_KEY=b"""-----BEGIN PUBLIC KEY-----
MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEA1O5tS0UCDEdjXAQltzzk
0GGltEsqbTANXYFURDpbyhUjZgD3ETasl6K+OzLFWvRI+Qsxoyn3jh+c63XnsXcC
sTQAvPIwUQefeMRhXYT17tUwliz+YKGk/eczBMVruWG0RioJI5hyZZWQQoLjsGXd
ZWcddCocT/r+NXB40J/4UXxIxNKx4+EFkgag5fKrY9b2GJ+19zCigecNC2p+XuHm
DwFgFv3qPuqe7grcvD8tX/Na0F7ioIZMj1kPxfhzie4b8Mgk4nE6PQKy+nCU/dDt
vv+/zB6J6xhVWYUtSxH1JpUkB5OkZTNMrMQbGzP0zo0Kmghw1/UXWrTCo3zEM2Tw
o6tAgsTWdnuZKuZsPQcEtcabyQlgpdbZgj7k1uvocrxMAOmCAzAuLsT7GjVJ3dAD
uBpzfnKsY4HxLEX7+f37cJwt3A0jaaWb6keWApBcguvfXDBtQidZ2p2UWzBMoXAu
MdmQ1Tedx6HHwnovVx7V41SfxNKQwAiboJ1mN8MEkXc/AgMBAAE=
-----END PUBLIC KEY-----
"""
ROOT=Path("private-preview-v113")
SEALED=Path("sealed-review-v113")
# title, shot, spoken sentence (one or two short timed captions)
STORIES={
"auto":[
("Még mindig telefonon?","hero","Csörög a telefon, miközben éppen egy autó javításával foglalkozol."),
("Online ügyfélfelület","phone_services","Mutatok egy olyan felületet, ahol az ügyfeled önállóan tájékozódhat."),
("Szolgáltatások","services","Elsőként átnézheti a szerviz szolgáltatásait, és kiválaszthatja, amire szüksége van."),
("Szolgáltatás kiválasztása","live_service","A kiválasztott szolgáltatás jól látható, így egyértelmű, hogy mire foglal időpontot."),
("Nap kiválasztása","dates_after","Ezután a naptárban kiválaszthatja a számára megfelelő napot."),
("Szabad időpontok","live_slots","Az elérhető időpontok közül megnézheti, melyik illik a saját napirendjéhez."),
("Kiválasztott idősáv","slot_selected","A kiválasztott idősáv megjelenik a felületen, mielőtt továbbhaladna."),
("Saját adminfelület","live_admin","Neked pedig külön kezelőfelületed van, ahol áttekintheted a beállításokat."),
("Módosítható kínálat","admin_detail","Ha változik a szolgáltatásod, a kezelőfelületen módosíthatod a tartalmát."),
("Próbáld ki a demót!","cta","Nézd meg az autószervizes bemutatót a Darkline Studio weboldalán, és fedezd fel a lehetőségeket.")],
"web":[
("Mutasd meg a vállalkozásod","hero","Egy vállalkozás weboldala gyakran az első hely, ahol az érdeklődők találkoznak veled."),
("Bemutatkozás mobilon","mobile","A látogatód már telefonról is megismerheti, mivel foglalkozol, és mit kínálsz."),
("Szolgáltatások","feature","A szolgáltatásaidat külön részekben mutathatod be, hogy könnyen áttekinthetők legyenek."),
("Kínálat közelről","feature_detail","Így az érdeklődőnek nem kell az egész weboldalon keresgélnie a számára fontos információkat."),
("Korábbi munkáid","detail","A referenciáidnak is jut hely, ahol megmutathatod a korábbi munkáidat."),
("Referenciák mobilon","portfolio_mobile","A látogató közelebbről is átnézheti a bemutatott példákat, akár telefonról."),
("Saját kezelőfelület","admin","A weboldalhoz kezelőfelület tartozik, hogy a tartalom ne maradjon változatlan."),
("Szerkeszthető adatok","admin_detail","Itt találod azokat a mezőket, amelyekben a bemutatott információkat módosíthatod."),
("Ügyfélnézet","mobile","A cél egy olyan átlátható oldal, amelyet az ügyfeleid egyszerűen használhatnak."),
("Nézd meg működés közben","cta","Ismerd meg a Darkline Studio üzleti weboldalának bemutatóját, és nézd meg, neked hogyan segíthet.")],
"menu":[
("Az első benyomás","hero","Az étlap nem csupán az ételek felsorolása, hanem a vendég első benyomásának fontos része."),
("Digitális étlap","menu_mobile","A vendéged telefonról is kényelmesen megnyithatja és böngészheti a digitális étlapot."),
("Ételkategóriák","feature","Az ételek kategóriákba rendezve jelennek meg, így könnyebb megtalálni a megfelelő fogást."),
("Ételek és árak","dish","A fogások mellett az árakat is láthatja, így egyszerűbb áttekinteni a kínálatot."),
("Napi ajánlat","detail","A napi menüt külön nézetben mutathatod meg, hogy az aktuális ajánlat könnyen megtalálható legyen."),
("Napi menü mobilon","daily_mobile","A vendég a napi ajánlatot is átnézheti a telefonján, akár az étteremben."),
("Saját adminfelület","admin","A kínálatod kezelése a saját adminfelületeden történik, nem az ügyfelek nézetében."),
("Szerkeszthető tartalom","admin_detail","Ha változik egy fogás vagy az ajánlat, a szerkeszthető tartalmat a kezelőfelületen frissítheted."),
("Átlátható étlap","menu_mobile","Az ügyféloldal és a kezelőfelület külön szerepet kap, hogy mindkettő könnyen használható legyen."),
("Fedezd fel a demót!","cta","Próbáld ki a Darkline Studio digitális étlapját és napi menüjét a bemutatóoldalon.")]
}
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def layout(records,duration,fps=30):
    if len(records)!=10 or not 28.5<=duration<=58:raise RuntimeError("Speech outside extended review duration; no forced stretching")
    end=max(30*fps,math.ceil((duration+1.5)*fps))
    edges=[0]
    for left,right in zip(records,records[1:]):
        low=math.ceil(left["end"]*fps-1e-6);high=math.floor(right["start"]*fps+1e-6)
        if low>high:raise RuntimeError("No frame-aligned speech boundary")
        edges.append((low+high)//2)
    edges.append(end)
    if any(b-a<fps for a,b in zip(edges,edges[1:])):raise RuntimeError("Scene shorter than one second")
    return edges
def wrap(draw,text,font,width):
    lines=[];line=""
    for word in text.split():
        nxt=(line+" "+word).strip()
        if line and draw.textlength(nxt,font=font)>width:
            lines.append(line);line=word
        else:line=nxt
    if line:lines.append(line)
    return lines
def caption_chunks(phrases,result,duration,records):
    # Exact character timing supplied by HeyGen; split each sentence on word boundaries.
    chars=result["original_characters"];pos=0;chunks=[]
    for idx,phrase in enumerate(phrases):
        import re
        words=list(re.finditer(r"\S+",phrase))
        groups=[];start=0
        for j in range(1,len(words)):
            if words[j].end()-words[start].start()>58:
                groups.append(words[start:j]);start=j
        groups.append(words[start:])
        for group in groups:
            a=group[0].start();b=group[-1].end()
            chunks.append({"scene":idx,"start":float(chars[pos+a]["start_time"]),"end":min(duration,float(chars[pos+b-1]["end_time"])),"text":phrase[a:b]})
        pos+=len(phrase)+1
    if any(c["end"]<=c["start"] for c in chunks):raise RuntimeError("Invalid caption timing")
    if " ".join(c["text"] for c in chunks)!=" ".join(phrases):raise RuntimeError("Incomplete subtitles")
    return chunks
def speech_and_mix(p,key,out,settings,chosen):
    phrases=[s[2] for s in STORIES[key]]
    audio_path=out/"private_voice.wav"
    result=voice.speech(" ".join(phrases),settings,audio_path)
    raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(audio_path),"-ar","48000","-ac","1","-f","f32le","-"])
    a=np.frombuffer(raw,dtype="<f4").copy();sr=48000;duration=len(a)/sr
    if not len(a) or not np.isfinite(a).all() or float(np.max(np.abs(a)))<.005:raise RuntimeError("Invalid speech")
    rec=voice.timing(phrases,result,duration)
    edges=layout(rec,duration);caps=caption_chunks(phrases,result,duration,rec)
    total=edges[-1]/30
    a*=min(10**(-18/20)/max(float(np.sqrt(np.mean(a*a))),1e-6),.78/max(float(np.max(np.abs(a))),1e-6))
    track=np.zeros(round(total*sr),np.float32);track[:len(a)]=a
    t=np.arange(len(track))/sr;bed=np.zeros_like(track);beat=60/p["bpm"]
    hz={"auto":55,"web":130.8,"menu":110}[key]
    for j,b in enumerate(np.arange(0,total,beat)):
        # Local slices rather than repeatedly scanning the full 40s track.
        start=round(b*sr);end=min(len(track),start+round(beat*sr));z=t[start:end]-b
        bed[start:end]+=(.12*np.sin(2*np.pi*(78*z-52*z*z))*np.exp(-z*14)*(z<.35)).astype(np.float32)
        for k in (1,1.25,1.5):bed[start:end]+=(.027*np.sin(2*np.pi*hz*k*[1,1,1.122,1.335][j%4]*z)*np.exp(-z*3)).astype(np.float32)
    duck=np.ones_like(track)*.58
    for r in rec:duck[max(0,round((r["start"]-.08)*sr)):min(len(track),round((r["end"]+.12)*sr))]=.20
    duck=np.convolve(duck,np.ones(1200,np.float32)/1200,mode="same")
    mix=track+bed*duck
    fade=round(.4*sr);mix[-fade:]*=np.linspace(1,0,fade)
    mix*=min(1,.89/max(float(np.max(np.abs(mix))),1e-6))
    with wave.open(str(out/"mix.wav"),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((mix*32767).astype("<i2").tobytes())
    (out/"captions.srt").write_text("\n\n".join(f"{i+1}\n{voice.stamp(r['start'])} --> {voice.stamp(r['end'])}\n{r['text']}" for i,r in enumerate(caps))+"\n",encoding="utf8")
    (out/"narration_timing.json").write_text(json.dumps({"scenes":rec,"captions":caps,"frame_boundaries":edges},ensure_ascii=False,indent=2),encoding="utf8")
    (out/"voice_provenance.json").write_text(json.dumps({"model":voice.MODEL,"profile":chosen,"settings":settings,"duration":duration,"publication":False},indent=2))
    print("V113_SPEECH_OK",key,round(duration,3),"video",total,"captions",len(caps),flush=True)
    return rec,edges,caps,duration
def capture_extra(v,key,p,out):
    if key=="auto":return
    with v.sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        if key=="web":
            page=v.open_page(browser,v.BASE+p["path"]+"?skin=dark",480,900)
            v.viewport(page,out/"mobile.png")
            v.snap(page,"#portfolio",out/"portfolio_mobile.png")
            v.snap(page,"#szolgaltatasok",out/"feature_detail.png")
        else:
            page=v.open_page(browser,v.BASE+"digitalis-etlap.html?skin=dark",480,900)
            v.viewport(page,out/"menu_mobile.png")
            page.locator('[data-cat="foetel"]').click(timeout=12000)
            loc=page.get_by_role("heading",name="Bélszín Steak",exact=True)
            loc.wait_for(state="visible")
            # Capture actual dish container including price, not invented UI.
            holder=loc.locator("xpath=..")
            holder.scroll_into_view_if_needed();v.clean(page);holder.screenshot(path=str(out/"dish.png"),animations="disabled")
            daily=v.open_page(browser,v.BASE+"napi-menu.html?skin=dark",480,900)
            v.viewport(daily,out/"daily_mobile.png")
        browser.close()
def load_assets(v,key,out):
    a=v.assets(key,out)
    for _,shot,_ in STORIES[key]:
        if shot in a or shot in ("cta","live_service","live_slots","live_admin"):continue
        a[shot]=v.load(out/(shot+".png"))
    return a
def frame(v,key,p,s,n,edges,caps,a):
    at=n/30;t=(n-edges[s])/30;dur=(edges[s+1]-edges[s])/30;q=v.v4.smooth(t/dur)
    base,accent,fg,secondary=p["colors"];im=v.background(p,s,t);d=ImageDraw.Draw(im)
    title,shot,_=STORIES[key][s]
    d.text((72,95),"DARKLINE / STUDIO",font=ImageFont.truetype(BOLD,36),fill=fg)
    d.text((72,165),f"{p['label']}  /  {s+1:02d} · 10",font=ImageFont.truetype(FONT,32),fill=accent)
    d.line((72,230,1008,230),fill=secondary,width=3)
    font=ImageFont.truetype(BOLD,76)
    for i,line in enumerate(wrap(d,title,font,936)):
        d.text((72,270+i*89),line,font=font,fill=fg if i==0 else accent)
    if shot=="cta" or shot=="hero":
        # Opening and closing keep the established cinematic device treatment.
        if key=="auto":
            ang=-1.1+1.9*v.v4.ease(t/.75)+.55*t
            v.v5.laptop(im,v.v5.laptop_texture(a["admin"]),540,920,790,470,22*math.cos(ang),5,-5*math.sin(ang),t)
            for k,z in sorted([("hero_tex",ang),("detail_tex",ang+math.pi)],key=lambda x:math.sin(x[1])):
                dep=math.sin(z);v.v9.premium_phone(im,a[k],540+320*math.cos(z),1000+65*dep,320+40*dep,650+70*dep,25*math.cos(z),5,-8*math.cos(z),t)
        elif key=="web":
            # Rapid initial camera reveal, then deliberate, readable movement.
            e=v.v4.ease(t/1.05);phase=t*1.55
            v.v5.laptop(im,v.v5.laptop_texture(a["hero"]),540-190*(1-e)+30*math.sin(phase),945+65*(1-e),790+170*e,470+100*e,-39+52*e+8*math.sin(phase),5,-7+8*e,t)
            v.v4.card(im,a["mobile"],round(790-155*e+25*math.sin(phase)),round(1090-55*e),300,400)
        else:
            e=v.v4.ease(t/.85);phase=t*1.7
            v.v9.premium_phone(im,a["hero_tex"],240+280*e+45*math.sin(phase),1000+100*(1-e),400+130*e,740+180*e,-50+63*e+12*math.sin(phase),5,-12+14*e,t)
            v.v4.card(im,a["dish"],round(790-190*e+38*math.sin(phase)),round(1160-105*e),345,300)
    else:
        src=v.v9.read_frame(shot,t,dur) if shot.startswith("live_") else a[shot]
        if key=="auto":
            w=round(916+30*q);x=(1080-w)//2;y=round(520+18*(1-v.v4.ease(t/.55))-20*q);h=round(975+30*q)
            v.v4.card(im,src,x,y,w,h,False)
            if shot=="admin_detail":v.v4.card(im,a["admin"],120,1120,840,365,False)
        else:
            # A short camera reveal, followed by steady reframing of the actual UI.
            # Keep the entire screenshot visible; use alternating pans/zoom rather than filler.
            e=v.v4.ease(t/.75);phase=2*math.pi*t/dur
            sway=math.sin(phase*1.45)
            scale=.5+.5*math.sin(phase*1.45-.8)
            w=round(805+115*e+48*scale)
            x=round((1080-w)/2+(-1 if s%2 else 1)*38*sway)
            y=round(555+70*(1-e)-48*math.sin(phase*1.1))
            h=round(855+100*e+35*scale)
            v.v4.card(im,src,x,y,w,h,False)
            if shot=="admin_detail":
                v.v4.card(im,a["admin"],round(94+32*sway),1125,890,360,False)
    d=ImageDraw.Draw(im)
    if shot=="cta":
        d.rounded_rectangle((72,1430,1008,1520),radius=24,fill=accent)
        d.text((96,1451),"darkline-studio.web.app",font=ImageFont.truetype(BOLD,43),fill=base)
    active=next((r for r in caps if r["start"]<=at<r["end"]),None)
    if active:
        cf=ImageFont.truetype(BOLD,46);lines=wrap(d,active["text"],cf,890)
        if len(lines)>3:raise RuntimeError("Caption overflow")
        d.rounded_rectangle((64,1545,1016,1742),radius=24,fill="#11131c")
        for i,line in enumerate(lines):
            d.text(((1080-d.textlength(line,font=cf))/2,1545+(197-len(lines)*55)/2+i*55),line,font=cf,fill="white")
    d.rounded_rectangle((72,1800,1008,1808),radius=4,fill=secondary)
    d.rounded_rectangle((72,1800,72+max(1,int(936*n/edges[-1])),1808),radius=4,fill=accent)
    return im
def render(v,key,p,out,rec,edges,caps):
    a=load_assets(v,key,out);v.DUR=[(b-a)/30 for a,b in zip(edges,edges[1:])];v.TOTAL=edges[-1]/30
    silent=out/"silent.mp4";movie=out/f"Darkline_V113_{key}_{voice.profile(key)[0]}.mp4"
    cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size","1080x1920","-framerate","30","-i","pipe:0","-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p","-threads","3",str(silent)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE);thumbs=[]
    try:
        for s,(start,end) in enumerate(zip(edges,edges[1:])):
            for n in range(start,end):
                im=frame(v,key,p,s,n,edges,caps,a)
                if n==(start+end)//2:thumbs.append(im.resize((270,480),Image.Resampling.LANCZOS))
                proc.stdin.write(im.tobytes())
    finally:proc.stdin.close()
    if proc.wait():raise RuntimeError("Video encoding failed")
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(out/"mix.wav"),"-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart","-shortest",str(movie)],check=True)
    silent.unlink();(out/"mix.wav").unlink()
    sheet=Image.new("RGB",(1350,960),p["colors"][0])
    for i,im in enumerate(thumbs):sheet.paste(im,((i%5)*270,(i//5)*480))
    sheet.save(out/"storyboard.jpg",quality=94)
    return movie
def check(v,key,p,out,movie,rec,edges,caps,duration,capture):
    seconds=edges[-1]/30
    report=v.v9.check_quality(movie,seconds,p["min_open"])
    info=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-of","json",str(movie)]))
    stream=next(s for s in info["streams"] if s["codec_type"]=="video")
    audio=np.frombuffer(subprocess.check_output(["ffmpeg","-v","error","-i",str(movie),"-map","0:a:0","-ac","1","-ar","48000","-f","f32le","-"]),dtype="<f4")
    peak=float(np.max(np.abs(audio)));reasons=report["reasons"]
    if seconds<30:reasons.append("minimum_30_seconds")
    if not 30<=seconds<=60 or duration/seconds<.90:reasons.append("duration_or_speech_coverage")
    if stream["r_frame_rate"]!="30/1" or peak>=.999:reasons.append("fps_or_peak")
    if len(rec)!=10 or len(caps)<10 or any(r["start"]<edges[i]/30-.00001 or r["end"]>edges[i+1]/30+.00001 for i,r in enumerate(rec)):reasons.append("alignment")
    if capture["overlay_dom_checks"]!="passed":reasons.append("overlay")
    report.update({"key":key,"seconds":seconds,"speech_seconds":duration,"audio_peak":peak,"scenes":10,"captions":len(caps),"profile":voice.profile(key)[0],"model":voice.MODEL,"capture":capture,"review_gate":"PASS" if not reasons else "REJECT","human_review":"pending","publication":False})
    fp=v.dedup.fingerprint(movie,{"scenes":[{"heading":x[0],"detail":x[2]} for x in STORIES[key]]})
    v.dedup.save(out/"fingerprint.json",fp)
    (out/"quality.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    return report,fp
def bundle(key,out,movie,public):
    files=[movie]+[out/n for n in ("captions.srt","quality.json","voice_provenance.json","narration_timing.json","storyboard.jpg")]
    path=out/"review.zip"
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        for f in files:z.write(f,arcname=f.name)
    SEALED.mkdir(exist_ok=True);target=SEALED/f"Darkline_V113_{key}.dlenc"
    data=path.read_bytes()
    if not 0<len(data)<100_000_000:raise RuntimeError("Invalid package size")
    target.write_bytes(prior.seal(data,public))
    print("V113_ENCRYPTED_READY",key,target.stat().st_size,flush=True)
def selftest():
    assert all(len(x)==10 and len(" ".join(y[2] for y in x))<=1000 for x in STORIES.values())
    assert all(500<=len(" ".join(y[2] for y in x)) for x in STORIES.values())
    rec=[{"start":i*3.2+.1,"end":i*3.2+3.0} for i in range(10)]
    e=layout(rec,32)
    assert len(e)==11 and e[-1]/30==33.5
    try:layout(rec,20)
    except RuntimeError:pass
    else:raise AssertionError("Too short allowed")
    phrases=[s[2] for s in STORIES["auto"]];txt=" ".join(phrases)
    chars=[{"text":c,"start_time":i*.05,"end_time":(i+1)*.05} for i,c in enumerate(txt)]
    caps=caption_chunks(phrases,{"original_characters":chars},len(txt)*.05,[])
    assert len(caps)>10
    import hashlib
    assert hashlib.sha256(PUBLIC_KEY).hexdigest()=="4072f45fe84425db2ac798137aa7e87a894f821284b8edabcf94a46e93e9f1b3"
    assert serialization.load_pem_public_key(PUBLIC_KEY).key_size==3072
    prior.selftest()
    print("V113_SELFTEST_OK ten scenes, min 30s, split captions, encryption, script limits",flush=True)
def main():
    import creative_intelligence_v10 as v
    voice.authorize()
    public=serialization.load_pem_public_key(PUBLIC_KEY)
    reports=[];history=[]
    for key in ("auto","web","menu"):
        p=copy.deepcopy(v.PLANS[key]);chosen,settings=voice.profile(key);out=ROOT/key;out.mkdir(parents=True,exist_ok=False)
        capture=v.capture(key,p,out);capture_extra(v,key,p,out)
        print("V113_CAPTURE_OK",key,flush=True)
        rec,edges,caps,duration=speech_and_mix(p,key,out,settings,chosen)
        movie=render(v,key,p,out,rec,edges,caps)
        report,fp=check(v,key,p,out,movie,rec,edges,caps,duration,capture)
        for old_key,old in history:
            duplicate=v.dedup.compare(fp,old)
            if duplicate:report["reasons"].append("duplicate_"+old_key);report["review_gate"]="REJECT"
        history.append((key,fp));reports.append(report)
        (out/"quality.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
        bundle(key,out,movie,public)
        print("V113_RESULT",json.dumps(report,ensure_ascii=False),flush=True)
    if any(r["review_gate"]!="PASS" for r in reports):raise RuntimeError("Extended sample needs review")
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--selftest",action="store_true");args=ap.parse_args()
    if args.selftest:selftest()
    else:main()
