"""V12.6.8 full-viewport review. No crop, zoom, TTS, save or publication.
A fixed browser viewport is preserved in every frame, including real actions.
Measure multiple readable content elements rather than one enlarged text node.
"""
import io,json,subprocess,tempfile,time
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
from playwright.sync_api import sync_playwright
import demo_renderer_v1266 as demo
import focused_renderer_v124 as r
from action_review_v1267 import CASES,state,screenshot

W,H=1080,1920
AREA=(20,182,1060,1678)
FPS=30
SECONDS=8
def fit_box(size,area=AREA):
    x,y,x2,y2=area;w,h=size
    if w<1 or h<1:raise ValueError("invalid viewport")
    scale=min((x2-x)/w,(y2-y)/h)
    sw,sh=round(w*scale),round(h*scale)
    return (x+((x2-x)-sw)//2,y+((y2-y)-sh)//2,sw,sh)
def paste_viewport(out,im):
    # All source pixels included, independent of image size or scene.
    x,y,w,h=fit_box(im.size)
    out.paste(im.resize((w,h),Image.Resampling.LANCZOS),(x,y))
    return (x,y,w,h)
def view_audit(page):
    # Count distinct non-obscured text-bearing UI elements within the actual viewport.
    # This is contextual visibility, not an OCR claim or a guarantee about every word.
    a=page.evaluate("""()=>{
      const vw=innerWidth,vh=innerHeight;
      const all=[...document.querySelectorAll('h1,h2,h3,h4,p,label,button,a,input,select,strong,span')];
      const found=new Map();
      for(const e of all){
        const s=getComputedStyle(e),b=e.getBoundingClientRect();
        if(s.display==='none'||s.visibility!=='visible'||Number(s.opacity)<.95||b.width<4||b.height<4||b.left<0||b.right>vw||b.top<0||b.bottom>vh)continue;
        const t=(e.innerText||e.getAttribute('placeholder')||e.value||'').trim();
        if(t.length<3||t.length>160)continue;
        const px=b.left+b.width/2,py=b.top+b.height/2,q=document.elementFromPoint(px,py);
        if(!q||!(q===e||e.contains(q)))continue;
        const fs=parseFloat(s.fontSize);
        if(!Number.isFinite(fs))continue;
        const old=found.get(t);
        if(!old||fs>old.font)found.set(t,{font:fs,control:e.matches('button,a,input,select,[role=button]')});
      }
      return {viewport:[vw,vh],items:[...found.values()]};
    }""")
    _,_,w,h=fit_box(tuple(a["viewport"]))
    scale=min(w/a["viewport"][0],h/a["viewport"][1])
    sizes=[v["font"]*scale for v in a["items"]]
    result={"viewport_css":a["viewport"],"display_rect":[w,h],"viewport_coverage":1.0,
      "projected_css_scale":round(scale,3),"visible_text_items":len(sizes),
      "text_items_at_least_22px":sum(v>=22 for v in sizes),
      "visible_controls":sum(v["control"] for v in a["items"]),
      "median_projected_px":round(float(np.median(sizes)),2) if sizes else 0}
    if result["visible_text_items"]<5 or result["text_items_at_least_22px"]<3:
        raise RuntimeError("Insufficient surrounding UI context: "+json.dumps(result))
    return result
def capture_case(browser,case):
    family,key,selector,index,proof,result,title,after=case
    width,height=(760,900) if family=="crm" else (480,800)
    tmp=tempfile.TemporaryDirectory()
    ctx=browser.new_context(viewport={"width":width,"height":height},device_scale_factor=2,service_workers="block",
                            record_video_dir=tmp.name,record_video_size={"width":width*2,"height":height*2})
    page=ctx.new_page()
    blocked=[]
    def route_handler(route):
        if route.request.method not in ("GET","HEAD","OPTIONS"):blocked.append(route.request.method)
        return demo.demo_guard(route,key)
    ctx.route("**/*",route_handler)
    try:
        page.goto("https://"+demo.HOST+"/demok/"+demo.PATHS[key]+"?skin=dark",wait_until="domcontentloaded",timeout=45000)
        page.wait_for_timeout(1200);demo.prepare(page,key)
        action=page.locator(selector).nth(index);action.wait_for(state="visible",timeout=15000)
        action.scroll_into_view_if_needed(timeout=10000)
        action.hover(timeout=10000)
        page.wait_for_timeout(300)
        before_state=state(page,proof);before_result=state(page,result)
        before=screenshot(page);before_audit=view_audit(page)
        if before.size!=(width*2,height*2):raise RuntimeError("unexpected source viewport")
        started=time.monotonic()
        page.wait_for_timeout(450)
        demo.click_sample(page,selector,index)
        page.locator(proof).first.wait_for(state="visible",timeout=15000)
        target=page.locator(result).first
        target.wait_for(state="visible",timeout=15000)
        page.wait_for_timeout(350)
        # Keep the actual page context; if necessary, scroll the real page rather than crop.
        box=target.bounding_box()
        if not box:raise RuntimeError("result geometry missing")
        if box["y"]<0 or box["y"]>height*.55:
            target.evaluate("e=>e.scrollIntoView({block:'start',inline:'nearest',behavior:'smooth'})")
        page.wait_for_timeout(950)
        after_state=state(page,proof);after_result=state(page,result)
        if not after_state["visible"] or not after_result["visible"]:raise RuntimeError("result missing")
        if before_state==after_state and before_result==after_result:raise RuntimeError("no demonstrated state transition")
        final=screenshot(page);after_audit=view_audit(page)
        if final.size!=before.size:raise RuntimeError("viewport changed")
        page.wait_for_timeout(250)
        finished=time.monotonic()
        vid=page.video;closed=time.monotonic();page.close();ctx.close()
        raw=Path(tmp.name)/"action.webm";vid.save_as(str(raw))
        dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(raw)]))
        lo=max(0,dur-(closed-started));hi=min(dur,dur-(closed-finished))
        if hi-lo<1.5:raise RuntimeError("actual browser clip too short")
        frames=Path(tmp.name)/"frames";frames.mkdir()
        subprocess.run(["ffmpeg","-v","error","-ss",str(lo),"-t",str(hi-lo),"-i",str(raw),"-vf","fps=15","-q:v","3",str(frames/"%04d.jpg")],check=True)
        actual=[Image.open(p).convert("RGB") for p in sorted(frames.glob("*.jpg"))]
        if len(actual)<20:raise RuntimeError("actual browser clip incomplete")
        if any(abs(im.width/im.height-width/height)>.003 for im in actual):raise RuntimeError("recording aspect changed")
        arr=np.array([np.asarray(im.resize((96,160)).convert("L"),dtype=np.int16) for im in actual])
        delta=float(np.abs(arr[-1]-arr[0]).mean())
        if delta<.5:raise RuntimeError("recorded interval lacks visible change")
        audit={"family":family,"action":selector,"result":result,"before":before_audit,"after":after_audit,
            "state_changed":True,"network_mutations_blocked":len(blocked),"real_browser_frames":len(actual),
            "recorded_action_seconds":round(hi-lo,3),"recorded_pixel_delta":round(delta,3),
            "viewport_coverage":1.0,"crop":False,"zoom":False,"publication":False,"narration":False}
        return before,actual,final,audit
    finally:
        ctx.close();tmp.cleanup()
def composition(case,im,phase,n):
    family,key,selector,index,proof,result,title,after=case
    bg,accent,secondary,label=demo.PALETTES[family]
    out=Image.new("RGB",(W,H),bg);d=ImageDraw.Draw(out)
    d.rectangle((0,0,W,10),fill=accent)
    d.text((32,22),"DARKLINE STUDIO  /  "+label,font=r.rig.font(25,True),fill=accent)
    text={"before":title,"action":title,"result":after}[phase]
    f=r.rig.font(47,True)
    lines=r.rig.wrap(d,text,f,1010)
    if len(lines)>2:raise RuntimeError("title overflow")
    for j,line in enumerate(lines):d.text((32,64+j*51),line,font=f,fill="#f4edff")
    d.rounded_rectangle((14,176,1066,1684),radius=18,fill="#0b1019",outline=secondary,width=3)
    paste_viewport(out,im)
    d=ImageDraw.Draw(out)
    for i,(tag,p) in enumerate((("1. Választás","before"),("2. Művelet","action"),("3. Eredmény","result"))):
        xx=35+i*345;active=phase==p
        d.rounded_rectangle((xx,1700,xx+320,1757),radius=14,fill=secondary if active else bg,outline=accent if active else secondary,width=2)
        d.text((xx+15,1711),tag,font=r.rig.font(27,True),fill="#f4edff" if active else "#bac3d2")
    d.text((35,1780),"Mintaadatok · nincs mentés vagy beküldés",font=r.rig.font(29),fill="#f4edff")
    d.text((35,1830),"darkline-studio.web.app",font=r.rig.font(34,True),fill=accent)
    d.rectangle((35,1890,1045,1897),fill=secondary)
    d.rectangle((35,1890,35+round(1010*(n+1)/(FPS*SECONDS)),1897),fill=accent)
    return out
def clip(case,assets,out):
    before,actual,final,audit=assets
    path=out/(case[0]+".mp4")
    proc=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size","1080x1920","-framerate","30","-i","pipe:0","-an","-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p","-threads","3","-movflags","+faststart",str(path)],stdin=subprocess.PIPE)
    try:
        for n in range(FPS*SECONDS):
            if n<60:im,phase=before,"before"
            elif n<150:im,phase=actual[min(len(actual)-1,int((n-60)*len(actual)/90))],"action"
            else:im,phase=final,"result"
            proc.stdin.write(composition(case,im,phase,n).tobytes())
    finally:proc.stdin.close()
    if proc.wait():raise RuntimeError("encode failed")
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(path),"-f","null","-"],check=True)
    audit["duration_seconds"]=SECONDS;audit["resolution"]="1080x1920"
    (out/(case[0]+".json")).write_text(json.dumps(audit,ensure_ascii=False,indent=2))
    print("V1268_ACTION_PASS",json.dumps(audit,ensure_ascii=False),flush=True)
def selftest():
    # Pixel-border test: verify all four corners of source survive actual composition,
    # including very wide desktop viewports and tall mobile viewports.
    for size in ((960,1600),(1520,1800),(520,900),(1100,900),(300,1500)):
        src=Image.new("RGB",size,"#222222");d=ImageDraw.Draw(src)
        for x,y,col in ((0,0,"red"),(size[0]-20,0,"green"),(0,size[1]-20,"blue"),(size[0]-20,size[1]-20,"yellow")):
            d.rectangle((x,y,x+19,y+19),fill=col)
        out=Image.new("RGB",(W,H));x,y,w,h=paste_viewport(out,src)
        assert abs(w/h-size[0]/size[1])<.005
        assert (x>=AREA[0] and y>=AREA[1] and x+w<=AREA[2] and y+h<=AREA[3])
        assert out.getpixel((x,y))[0]>150 and out.getpixel((x+w-1,y))[1]>80
        assert out.getpixel((x,y+h-1))[2]>150 and out.getpixel((x+w-1,y+h-1))[0]>150
    print("V1268_NO_CROP_PASS five viewport geometries; all four corners retained")
def main(out):
    selftest();out.mkdir(exist_ok=False)
    results=[];failed=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            for case in CASES:
                try:
                    assets=capture_case(browser,case)
                    clip(case,assets,out);results.append(assets[-1])
                except Exception as e:
                    print("V1268_ACTION_FAIL",case[0],str(e)[:800],flush=True);failed.append(case[0])
        finally:browser.close()
    (out/"report.json").write_text(json.dumps({"passed":results,"failed":failed,"voice_calls":0,"publication":False},ensure_ascii=False,indent=2))
    if failed:raise RuntimeError("Action reviews failed: "+str(failed))
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    main(p.parse_args().out)
