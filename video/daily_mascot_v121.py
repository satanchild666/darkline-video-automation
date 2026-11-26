"""V12.1 daily service renderer. Review only until integrated publishing is verified."""
import argparse,copy,json,math,os,subprocess,zipfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
from PIL import Image,ImageDraw,ImageOps
from cryptography.hazmat.primitives import serialization
import private_review_v113 as base
import private_review_v111 as encryption
import heygen_free_voice_v11 as voice
import creative_intelligence_v10 as v
import mascot_rig_v121 as rig
ROOT=Path("private-preview-v121")
SEALED=Path("sealed-review-v121")
# The approved catalogue is intentionally bounded. Do not endlessly regenerate identical scripts.
KEYS=("auto","web","menu")
original_clean=v.clean
def clean(page):
    original_clean(page)
    page.add_style_tag(content="#dl-stats-consent{display:none!important;visibility:hidden!important;pointer-events:none!important}")
    if page.locator("#dl-stats-consent").is_visible():raise RuntimeError("Consent overlay visible")
v.clean=clean
v.v9.clean=clean
def energy(path,total):
    a=np.frombuffer(subprocess.check_output(["ffmpeg","-v","error","-i",str(path),"-ac","1","-ar","16000","-f","f32le","-"]),dtype="<f4")
    e=[]
    for n in range(total):
        i=round(n*16000/30);part=a[max(0,i-150):min(len(a),i+550)]
        e.append(float(np.sqrt(np.mean(part*part))) if len(part) else 0)
    return np.clip((np.array(e)-.018)/.12,0,1)
def source(a,key,shot,t,dur):
    if shot.startswith("live_"):return v.v9.read_frame(shot,t,dur)
    if shot in ("hero","cta"):
        return a["phone_services"] if key=="auto" and "phone_services" in a else a["hero"]
    return a[shot]
def frame(p,key,a,s,n,edges,caps,energies):
    t=(n-edges[s])/30;at=n/30;dur=(edges[s+1]-edges[s])/30
    title,shot,_=base.STORIES[key][s]
    im=Image.new("RGB",(1080,1920),"#171122");d=ImageDraw.Draw(im)
    accent=p["colors"][1] if key=="menu" else "#c3a3ff"
    # Unframed title, no scene counter or labels.
    lines=rig.wrap(d,title,rig.font(63,True),1000)
    if len(lines)>3:raise RuntimeError("Title overflow")
    for j,line in enumerate(lines):d.text((40,70+j*75),line,font=rig.font(63,True),fill="#f4edff")
    src=source(a,key,shot,t,dur)
    # A large camera window, with a pan inside the actual captured UI rather than a tiny thumbnail.
    sw,sh=src.size;aspect=1040/1120
    e=v.v4.ease(t/.9)
    cropw=min(sw,sh*aspect);croph=cropw/aspect
    # For wide screens pan across the original pixels; for tall screens pan down.
    z=1.0-.16*(1-e)+.035*math.sin(2*math.pi*t/dur)
    cw=max(1,min(sw,round(cropw*z)));ch=max(1,min(sh,round(croph*z)))
    phase=min(1,max(0,t/dur))
    shift=.1+.8*(.5-.5*math.cos(math.pi*phase))
    x=round((sw-cw)*(shift if s%2==0 else 1-shift));y=round((sh-ch)*shift)
    image=src.crop((x,y,x+cw,y+ch)).resize((1040,1120),Image.Resampling.BILINEAR)
    im.paste(image,(20,300))
    active=next((c for c in caps if c["start"]<=at<c["end"]),None)
    part=rig.mascot(at,float(energies[n]),active is not None,19 if s==9 else s,t,scale=.88)
    rig.paste(im,part,8,1450)
    d=ImageDraw.Draw(im)
    if active:
        lines=rig.wrap(d,active["text"],rig.font(44,True),720)
        if len(lines)>4:raise RuntimeError("Caption overflow")
        for j,line in enumerate(lines):d.text((325,1480+j*56),line,font=rig.font(44,True),fill="#f4edff")
    d.text((325,1745),"darkline-studio.web.app",font=rig.font(30,True),fill=accent)
    return im
def render(p,key,out,edges,caps):
    a=base.load_assets(v,key,out);v.DUR=[(b-a)/30 for a,b in zip(edges,edges[1:])]
    en=energy(out/"private_voice.wav",edges[-1])
    silent=out/"silent.mp4";movie=out/"daily.mp4"
    proc=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size","1080x1920","-framerate","30","-i","pipe:0","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p","-threads","3",str(silent)],stdin=subprocess.PIPE)
    thumbs=[]
    try:
        for s,(start,end) in enumerate(zip(edges,edges[1:])):
            for n in range(start,end):
                im=frame(p,key,a,s,n,edges,caps,en)
                if n==(start+end)//2:thumbs.append(im.resize((270,480),Image.Resampling.LANCZOS))
                proc.stdin.write(im.tobytes())
            print("V121_SCENE",s+1,flush=True)
    finally:proc.stdin.close()
    if proc.wait():raise RuntimeError("Encode failed")
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(out/"mix.wav"),"-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart","-shortest",str(movie)],check=True)
    sheet=Image.new("RGB",(1350,960),"#171122")
    for i,im in enumerate(thumbs):sheet.paste(im,((i%5)*270,(i//5)*480))
    sheet.save(out/"storyboard.jpg",quality=94)
    return movie
def main(key):
    voice.authorize()
    p=copy.deepcopy(v.PLANS[key]);out=ROOT/key;out.mkdir(parents=True,exist_ok=False)
    capture=v.capture(key,p,out);base.capture_extra(v,key,p,out)
    chosen,settings=voice.profile(key)
    rec,edges,caps,duration=base.speech_and_mix(p,key,out,settings,chosen)
    movie=render(p,key,out,edges,caps)
    report,fp=base.check(v,key,p,out,movie,rec,edges,caps,duration,capture)
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(movie),"-f","null","-"],check=True)
    report.update({"width":1080,"height":1920,"fps":30,"mascot":True,"decode":"PASS","overlay_dom_checks":capture["overlay_dom_checks"],"readability":"OWNER_REVIEW_REQUIRED","dedup":"HISTORY_CHECK_REQUIRED","publication":False})
    # Do not assert visual readability or full publication-history clearance from geometry alone.
    # These pending gates deliberately block live scheduling until the daily system can verify them.
    (out/"quality.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    zpath=out/"review.zip"
    with zipfile.ZipFile(zpath,"w",zipfile.ZIP_DEFLATED) as z:
        for f in (movie,out/"quality.json",out/"storyboard.jpg",out/"fingerprint.json",out/"captions.srt",out/"narration_timing.json",out/"voice_provenance.json"):z.write(f,arcname=f.name)
    SEALED.mkdir(exist_ok=True)
    pub=serialization.load_pem_public_key(base.PUBLIC_KEY)
    (SEALED/f"Darkline_V121_{key}.dlenc").write_bytes(encryption.seal(zpath.read_bytes(),pub))
    print("V121_RESULT",json.dumps(report,ensure_ascii=False),flush=True)
    if report["reasons"]:raise RuntimeError("Technical gate failed")
def selftest():
    base.selftest()
    a={"hero":Image.new("RGB",(900,1200),"#aabbcc"),"mobile":Image.new("RGB",(500,900),"#112233")}
    edges=[i*120 for i in range(11)]
    caps=[{"start":0,"end":3,"text":"A vállalkozásod digitális bemutatkozása."}]
    im=frame(v.PLANS["web"],"web",a,0,10,edges,caps,np.zeros(edges[-1]))
    assert im.size==(1080,1920)
    assert rig.mascot(.3,.8).mode=="RGBA"
    print("V121_SELFTEST_OK approved rig, frameless 1040px UI, no paid fallback")
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--selftest",action="store_true");ap.add_argument("--key",choices=KEYS,default="web");a=ap.parse_args()
    if a.selftest:selftest()
    else:main(a.key)
