"""V12.4 live DOM focus capture and measured typography. No login, submit or clicks.
Readability is a bounded geometric check of a genuine focal text element,
not an assertion that every word of a long webpage is legible on every phone.
"""
import io,json,math,copy,subprocess,zipfile
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image,ImageDraw
import numpy as np
from playwright.sync_api import sync_playwright
from cryptography.hazmat.primitives import serialization
import private_review_v113 as base
import private_review_v111 as seal
import flagship_review_v114 as public
import creative_intelligence_v10 as v
import daily_mascot_v121 as old
import mascot_rig_v121 as rig
import heygen_free_voice_v11 as voice
import daily_catalogue_v124 as cat
W,H=1080,1920
VW,VH=520,900
CW,CH=480,516
UIW,UIH=1040,1118
MIN_TEXT=32
HIDE=".intro-loader,.dlg-avatar,.dlg-thought,.dlg-thought-tour,.dl-advisor-widget,.dl-advisor-hint,.dl-advisor-tab,#darkline-ai-advisor-toggle,#darkline-premium-guide,#dl-stats-consent"
def cleanup(page):
    public.clean_public(page)
    page.add_style_tag(content=HIDE+"{display:none!important;visibility:hidden!important;pointer-events:none!important}")
    if page.locator("#dl-stats-consent").is_visible():raise RuntimeError("Consent overlay visible")
def guard(route):
    req=route.request;u=urlparse(req.url)
    if req.is_navigation_request() and not public.allowed(req.url):return route.abort()
    if req.method not in ("GET","HEAD","OPTIONS"):
        readonly=req.method=="POST" and u.scheme=="https" and u.hostname=="firestore.googleapis.com" and ("/google.firestore.v1.Firestore/Listen/channel" in u.path or u.path.endswith(":runQuery") or u.path.endswith(":batchGet"))
        if not readonly:return route.abort()
    return route.continue_()
def root(page,sel):
    if sel.startswith("heading:"):
        return page.get_by_role("heading",name=sel[8:],exact=False).first
    return page.locator(sel).first
def clamp(x,lo,hi):return max(lo,min(hi,x))
def camera(box,vw=VW,vh=VH):
    # Keep all focal text inside the safe crop, including the rounded pixel coordinates.
    x,y,w,h=box
    if not all(math.isfinite(z) for z in box) or w<=0 or h<=0:raise RuntimeError("Invalid focus geometry")
    if w>CW-18 or h>CH-18:raise RuntimeError("Focal element too large for readable close-up")
    cx=round(clamp(x+w/2-CW/2,0,vw-CW));cy=round(clamp(y+h/2-CH/2,0,vh-CH))
    bx=x-cx;by=y-cy
    if bx<9 or by<9 or bx+w>CW-9 or by+h>CH-9:raise RuntimeError("Focal text clipped")
    minw=max(2*abs(bx+w/2-CW/2)+w+18,CW*.88)
    minh=max(2*abs(by+h/2-CH/2)+h+18,CH*.88)
    zoom=max(minw/CW,minh/CH)
    if zoom>1:raise RuntimeError("Focus cannot remain in frame")
    return (cx,cy,zoom)
def focus(page,loc,ordinal):
    loc.wait_for(state="visible",timeout=20000)
    selector="h1,h2,h3,h4,h5,h6,[role=heading],p,label,button"
    targets=loc.locator(":is("+selector+"):visible")
    if loc.evaluate("(e,s)=>e.matches(s)",selector):targets=loc
    count=targets.count()
    if not count:raise RuntimeError("No visible focal text")
    problems=[]
    for j in range(min(count,30)):
        target=targets.nth((ordinal+j)%count)
        try:
            target.evaluate("e=>e.scrollIntoView({block:'center',inline:'center',behavior:'instant'})")
            page.wait_for_timeout(450);cleanup(page)
            data=target.evaluate("""e=>{
                const s=getComputedStyle(e), text=(e.innerText||'').trim();
                const walker=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);
                const rects=[];let node;
                while(node=walker.nextNode()){
                    if(!node.textContent.trim())continue;
                    const range=document.createRange();range.selectNodeContents(node);
                    rects.push(...Array.from(range.getClientRects()).filter(x=>x.width>2&&x.height>2));
                }
                if(!rects.length)return null;
                const x=Math.min(...rects.map(x=>x.left)),y=Math.min(...rects.map(x=>x.top)),right=Math.max(...rects.map(x=>x.right)),bottom=Math.max(...rects.map(x=>x.bottom));
                const unobstructed=rects.every(r=>{const q=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return q&&(q===e||e.contains(q))});
                return {text,box:[x,y,right-x,bottom-y],font:parseFloat(s.fontSize),unobstructed,visible:s.visibility==='visible'&&s.display!=='none'&&parseFloat(s.opacity)>0.95};
            }""")
            if not data:problems.append("no text rectangles");continue
            if not data["visible"] or not data["unobstructed"]:problems.append("visibility or obstruction");continue
            if not 8<=len(data["text"])<=220:problems.append("text length");continue
            if data["font"]*UIW/CW<MIN_TEXT:problems.append("font below 32px");continue
            x,y,z=camera(data["box"],page.viewport_size["width"],page.viewport_size["height"])
            return data,(x,y,z)
        except (RuntimeError,ValueError) as error:problems.append(str(error))
    raise RuntimeError("No unobstructed readable focal text in section: "+", ".join(sorted(set(problems))))
def capture(topic,out):
    shots=[];aud=[];seen={}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        ctx=browser.new_context(viewport={"width":VW,"height":VH},device_scale_factor=2,service_workers="block")
        ctx.route("**/*",guard)
        pages={}
        for _,k,_,_ in topic.scenes:
            if k in pages:continue
            page=ctx.new_page();page.goto(public.HOST+public.PAGES[k],wait_until="domcontentloaded",timeout=45000)
            page.wait_for_timeout(1800);cleanup(page);pages[k]=page
        for i,(_,k,sel,_) in enumerate(topic.scenes):
            page=pages[k];n=seen.get((k,sel),0);seen[k,sel]=n+1
            errors=[]
            # Try responsive layouts of the SAME source element; never replace it with unrelated content.
            for width in (VW,480,600,760):
                page.set_viewport_size({"width":width,"height":VH})
                page.wait_for_timeout(350);cleanup(page)
                try:
                    data,(x,y,z)=focus(page,root(page,sel),n)
                    break
                except RuntimeError as error:
                    errors.append(str(error))
                    print("V1242_FOCUS_REJECT",i+1,width,str(error),flush=True)
            else:raise RuntimeError("Scene "+str(i+1)+" "+sel+" failed all responsive views: "+"; ".join(errors))
            with Image.open(io.BytesIO(page.screenshot(animations="disabled"))) as ss:
                if ss.size!=(width*2,VH*2):raise RuntimeError("Capture pixel density mismatch")
                im=ss.crop((x*2,y*2,(x+CW)*2,(y+CH)*2)).convert("RGB")
            im.save(out/f"shot-{i:02d}.png");shots.append((im,z))
            # Keep only a short public focal text excerpt, no full-page extraction or private data.
            aud.append({"scene":i+1,"page":page.url,"selector":sel,"text":data["text"],"font_css_px":data["font"],"minimum_projected_px":round(data["font"]*UIW/CW,2),"unobstructed":True,"safe_zoom_ratio":z,"viewport_width":width})
            print("V124_CAPTURE",i+1,"font_px",aud[-1]["minimum_projected_px"],flush=True)
        ctx.close();browser.close()
    (out/"capture_report.json").write_text(json.dumps(aud,ensure_ascii=False,indent=2))
    if len(aud)!=10 or any(a["minimum_projected_px"]<MIN_TEXT or not a["unobstructed"] for a in aud):raise RuntimeError("Readability gate failed")
    return shots,aud
def frame(topic,shots,s,n,edges,caps,en):
    at=n/30;local=(n-edges[s])/30;dur=(edges[s+1]-edges[s])/30
    im=Image.new("RGB",(W,H),"#171122");d=ImageDraw.Draw(im)
    f=rig.font(63,True);lines=rig.wrap(d,topic.scenes[s][0],f,1000)
    if len(lines)>3 or any(d.textlength(l,font=f)>1000 for l in lines):raise RuntimeError("Title overflow")
    for j,l in enumerate(lines):d.text((40,70+j*75),l,font=f,fill="#f4edff")
    src,z=shots[s]
    # Preserve aspect ratio and text visibility throughout; no stretching of narrow fields.
    t=clamp(local/.9,0,1);e=t*t*(3-2*t)
    ratio=1-(1-z)*(.5-.5*math.cos(2*math.pi*local/max(dur,.1)))*e
    sw,sh=src.size;cw=round(sw*ratio);ch=round(sh*ratio);x=(sw-cw)//2;y=(sh-ch)//2
    part=src.crop((x,y,x+cw,y+ch)).resize((UIW,UIH),Image.Resampling.BILINEAR)
    # Small smooth translation within the allocated UI region, no text clipping.
    off=round(12*math.sin(local*1.9));im.paste(part,(20,300+off))
    active=next((c for c in caps if c["start"]<=at<c["end"]),None)
    rig.paste(im,rig.mascot(at,float(en[n]),active is not None,19 if s==9 else s,local,scale=.88),8,1450)
    d=ImageDraw.Draw(im)
    if active:
        cf=rig.font(44,True);lines=rig.wrap(d,active["text"],cf,720)
        if len(lines)>4 or any(d.textlength(l,font=cf)>720 for l in lines):raise RuntimeError("Caption overflow")
        for j,l in enumerate(lines):d.text((325,1480+j*56),l,font=cf,fill="#f4edff")
    d.text((325,1745),"darkline-studio.web.app",font=rig.font(30,True),fill="#c3a3ff")
    return im
def render(topic,out,shots,edges,caps):
    en=old.energy(out/"private_voice.wav",edges[-1]);silent=out/"silent.mp4";movie=out/"daily.mp4"
    proc=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size","1080x1920","-framerate","30","-i","pipe:0","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p","-threads","3",str(silent)],stdin=subprocess.PIPE)
    thumbs=[]
    try:
        for s,(start,end) in enumerate(zip(edges,edges[1:])):
            for n in range(start,end):
                im=frame(topic,shots,s,n,edges,caps,en)
                if n==(start+end)//2:thumbs.append(im.resize((270,480),Image.Resampling.LANCZOS))
                proc.stdin.write(im.tobytes())
            print("V124_SCENE",s+1,flush=True)
    finally:proc.stdin.close()
    if proc.wait():raise RuntimeError("Encoding failed")
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(out/"mix.wav"),"-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart","-shortest",str(movie)],check=True)
    sheet=Image.new("RGB",(1350,960),"#171122")
    for i,im in enumerate(thumbs):sheet.paste(im,((i%5)*270,(i//5)*480))
    sheet.save(out/"storyboard.jpg",quality=94)
    return movie
def generate(topic,out):
    out.mkdir(parents=True,exist_ok=False)
    # Capture and check all focal targets before spending the one allowed speech call.
    shots,audit=capture(topic,out)
    p=copy.deepcopy(v.PLANS["web"]);p["min_open"]=.8
    base.STORIES["web"]=[(r[0],"unused",r[3]) for r in topic.scenes]
    voice.authorize();chosen,settings=voice.profile("web")
    rec,edges,caps,duration=base.speech_and_mix(p,"web",out,settings,chosen)
    movie=render(topic,out,shots,edges,caps)
    report,fp=base.check(v,"web",p,out,movie,rec,edges,caps,duration,{"source":"public_dom","overlay_dom_checks":"passed"})
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(movie),"-f","null","-"],check=True)
    report.update({"topic":topic.key,"width":1080,"height":1920,"fps":30,"mascot":True,"decode":"PASS","overlay_dom_checks":"passed","readability":"PASS","readability_method":"unobstructed focal DOM text, min projected 32px, bounded crop; not full-page OCR","min_projected_text_px":min(a["minimum_projected_px"] for a in audit),"focal_scenes":len(audit),"dedup":"HISTORY_CHECK_REQUIRED","publication":False})
    (out/"quality.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print("V124_RESULT",json.dumps(report,ensure_ascii=False),flush=True)
    return movie,report,fp
def bundle(out):
    sealed=Path("sealed-review-v124");sealed.mkdir(exist_ok=True)
    p=out/"review.zip"
    with zipfile.ZipFile(p,"w",zipfile.ZIP_DEFLATED) as z:
        for name in ("daily.mp4","quality.json","storyboard.jpg","fingerprint.json","captions.srt","narration_timing.json","capture_report.json"):
            z.write(out/name,arcname=name)
    (sealed/"Darkline_V124_daily.dlenc").write_bytes(seal.seal(p.read_bytes(),serialization.load_pem_public_key(base.PUBLIC_KEY)))
def selftest():
    cat.validate_catalogue()
    x,y,z=camera([120,320,240,40]);assert 0<=x<=40 and .88<=z<=1
    for box in ([0,0,10,10],[10,20,510,30],[20,20,60,400]):
        try:camera(box)
        except RuntimeError:pass
        else:raise AssertionError("Unsafe crop accepted")
    t=cat.TOPICS[0];shots=[(Image.new("RGB",(960,1032),"#aaccee"),.88)]*10;edges=[i*120 for i in range(11)]
    im=frame(t,shots,0,5,edges,[{"start":0,"end":2,"text":"Az ajánlatkérés lépései."}],np.zeros(edges[-1]));assert im.size==(W,H)
    print("V124_RENDER_SELFTEST_OK",len(cat.TOPICS),"topics, measured focus geometry",flush=True)
