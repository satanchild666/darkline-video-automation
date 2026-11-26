"""V12.7.0 genuine responsive browser footage for the approved web_services script.
No data entry, login, saving, external network writes or publishing.
"""
import json,subprocess,tempfile,time
from pathlib import Path
from playwright.sync_api import sync_playwright
import demo_renderer_v1266 as demo
import focused_renderer_v124 as r
import flagship_review_v114 as public
# Individual scenes follow the original HeyGen web_services narration exactly.
SCENES=[
 ("demo_web","body","desktop"),("demo_web","#portfolio","desktop"),
 ("demo_web_admin","#ds-v23-editor","desktop"),("demo_web","#szolgaltatasok","mobile"),
 ("demo_web","#portfolio","mobile"),("demo_web_admin","#ds-v23-editor","mobile"),
 ("prices","heading:Átlátható árazás","desktop"),("home","#ajanlatkeres","mobile"),
 ("demo_web","#szolgaltatasok","desktop"),("quote","heading:Beszéljük át, mire van szükséged","mobile")
]
SIZES={"desktop":(1024,640),"mobile":(430,720)}
def capture(browser,scene,out):
    key,selector,device=scene
    w,h=SIZES[device]
    with tempfile.TemporaryDirectory() as tmp:
        ctx=browser.new_context(viewport={"width":w,"height":h},device_scale_factor=1,service_workers="block",record_video_dir=tmp,record_video_size={"width":w,"height":h})
        page=ctx.new_page()
        # strict same-origin GET only even for public marketing pages
        def guard(route):
            from urllib.parse import urlparse
            u=urlparse(route.request.url)
            if route.request.method not in ("GET","HEAD","OPTIONS") or u.scheme!="https" or u.hostname!=demo.HOST or u.path.startswith(("/api/","/auth/","/functions/")):return route.abort()
            if route.request.is_navigation_request():
                if key in demo.PATHS:
                    if not demo.allowed(route.request.url,key):return route.abort()
                elif not public.allowed(route.request.url):return route.abort()
            if u.path.endswith(("advisor-widget.js","smart-advisor.js")):return route.abort()
            return route.continue_()
        ctx.route("**/*",guard)
        try:
            if key in demo.PATHS:
                page.goto("https://"+demo.HOST+"/demok/"+demo.PATHS[key]+"?skin=dark",wait_until="domcontentloaded",timeout=45000)
                page.wait_for_timeout(900);demo.clean_demo(page,key)
            else:
                page.goto(public.HOST+public.PAGES[key],wait_until="domcontentloaded",timeout=45000)
                page.wait_for_timeout(1200);r.cleanup(page)
            if key=="demo_web_admin" and not page.locator("#ds-v23-panel").is_visible():
                # Actual owner-button interaction, recorded from the visible guest page.
                btn=page.locator("#ds-v23-owner");btn.scroll_into_view_if_needed();page.wait_for_timeout(400)
                demo.click_sample(page,"#ds-v23-owner")
                page.locator("#ds-v23-panel").wait_for(state="visible",timeout=15000)
            target=r.root(page,selector);target.wait_for(state="visible",timeout=15000)
            target.evaluate("e=>e.scrollIntoView({block:'start',inline:'nearest',behavior:'instant'})")
            page.wait_for_timeout(500)
            # Native scrolling, not an enlarged screenshot. Locate nearest scrolling parent.
            page.screenshot(path=str(out.with_suffix(".before.png")))
            audit=target.evaluate("""e=>{const b=e.getBoundingClientRect();return {text:(e.innerText||'').trim().slice(0,200),width:innerWidth,height:innerHeight,x:b.x,y:b.y,elementHeight:b.height}}""")
            if not audit["text"]:raise RuntimeError("empty target")
            page.wait_for_timeout(600)
            target.evaluate("""async e=>{let p=e.parentElement;while(p&&!(p.scrollHeight>p.clientHeight+30&&/auto|scroll/.test(getComputedStyle(p).overflowY)))p=p.parentElement;const sc=p||document.scrollingElement;const from=sc.scrollTop;const to=Math.min(sc.scrollHeight-sc.clientHeight,from+Math.round(innerHeight*.32));const t=performance.now();await new Promise(resolve=>{function tick(now){let q=Math.min(1,(now-t)/1300);sc.scrollTop=from+(to-from)*q*q*(3-2*q);if(q<1)requestAnimationFrame(tick);else resolve()}requestAnimationFrame(tick)})}""")
            page.wait_for_timeout(1100)
            page.screenshot(path=str(out.with_suffix(".after.png")))
            vid=page.video;page.close();ctx.close()
            raw=Path(tmp)/"raw.webm";vid.save_as(str(raw))
            # Retain exact native viewport, normalize frame rate only.
            subprocess.run(["ffmpeg","-v","error","-y","-i",str(raw),"-vf","fps=15","-an","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p",str(out)],check=True)
            audit.update({"key":key,"selector":selector,"device":device,"viewport":[w,h],"crop":False,"publication":False})
            print("V1270_CAPTURE_PASS",json.dumps(audit,ensure_ascii=False),flush=True)
            return audit
        finally:ctx.close()
def main(out):
    out.mkdir(exist_ok=False)
    report=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            for i,scene in enumerate(SCENES):report.append(capture(browser,scene,out/f"scene-{i:02d}.mp4"))
        finally:browser.close()
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    main(p.parse_args().out)
