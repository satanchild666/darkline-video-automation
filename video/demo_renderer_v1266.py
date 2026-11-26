"""V12.6.6 isolated demo renderer candidate, never active on main.
Reuse V124 geometry, mascot, speech, captions, sound mix and encoding.
Only whitelisted demo navigation and non-submit sample UI actions.
"""
import io,json,math,copy
from pathlib import Path
from urllib.parse import urlparse
from contextlib import contextmanager
from PIL import Image,ImageDraw
import focused_renderer_v124 as r
import flagship_review_v114 as public
import demo_topics_v1266 as cat
from playwright.sync_api import sync_playwright
HOST="darkline-studio.web.app"
PATHS={
 "demo_auto":"autoszerviz.html","demo_auto_dates":"autoszerviz.html","demo_auto_slots":"autoszerviz.html","demo_auto_admin":"autoszerviz.html",
 "demo_menu":"digitalis-etlap.html","demo_menu_filter":"digitalis-etlap.html","demo_daily":"napi-menu.html","demo_menu_admin":"digitalis-etlap.html",
 "demo_salon":"szalon.html","demo_salon_staff":"szalon.html","demo_salon_admin":"szalon.html",
 "demo_crm":"ugyfelkezelo.html","demo_crm_board":"ugyfelkezelo.html","demo_crm_detail":"ugyfelkezelo.html",
 "demo_web":"uzleti-weboldal.html","demo_web_admin":"uzleti-weboldal.html"}
PALETTES={
 "auto":("#171322","#b59aff","#4b326e","TECH / SZERVIZ"),
 "menu":("#10241f","#f0c981","#30594c","ÉTLAP / VENDÉGLÁTÁS"),
 "salon":("#291c29","#f4aecb","#74465e","SZALON / VENDÉGÉLMÉNY"),
 "crm":("#101d2e","#55d5e3","#264e68","CRM / ÜGYFÉLKEZELÉS"),
 "web":("#152135","#a9d0ff","#365879","WEB / ÜZLETI BEMUTATKOZÁS")}
def allowed(url,key):
    u=urlparse(url)
    return u.scheme=="https" and u.hostname==HOST and u.port in (None,443) and not u.username and not u.password and u.path=="/demok/"+PATHS[key]
def demo_guard(route,key):
    req=route.request;u=urlparse(req.url)
    # No POST/PUT/PATCH/DELETE, no authentication, external API, analytics or remote storage.
    if req.method not in ("GET","HEAD","OPTIONS"):return route.abort()
    if req.is_navigation_request() and not allowed(req.url,key):return route.abort()
    if u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443):return route.abort()
    if u.path.startswith(("/api/","/auth/","/functions/")):return route.abort()
    if u.path.endswith(("advisor-widget.js","smart-advisor.js")):return route.abort()
    return route.continue_()
def clean_demo(page,key):
    if not allowed(page.url,key):raise RuntimeError("Demo left its exact allowlist")
    page.add_style_tag(content=r.HIDE+",.ds-demo-close,[aria-label='AI tanácsadó segítséget ajánl fel']{display:none!important;visibility:hidden!important;pointer-events:none!important}")
    if page.locator("#dl-stats-consent").is_visible():raise RuntimeError("Consent overlay visible")
def click_sample(page,selector):
    loc=page.locator(selector).first
    loc.wait_for(state="visible",timeout=15000)
    # Explicit UI state transitions only. No submit, links or form inputs.
    if not loc.evaluate("""e=>!e.closest('a,form') || (e.tagName==='BUTTON' && e.type==='button' && !e.closest('a'))"""):
        raise RuntimeError("Unsafe sample action")
    if loc.evaluate("""e=>e.matches('input,textarea,select,button[type=submit]')||e.getAttribute('type')==='submit'"""):
        raise RuntimeError("Submit or data-entry action forbidden")
    loc.click(timeout=12000)
def prepare(page,key):
    clean_demo(page,key)
    if key in ("demo_auto_dates","demo_auto_slots"):
        click_sample(page,".service-card")
        page.locator(".service-card.active").first.wait_for(state="visible")
        if key=="demo_auto_slots":
            click_sample(page,".date-btn:nth-child(2)")
            page.locator(".date-btn.active").first.wait_for(state="visible")
            page.locator(".time-btn:not([disabled])").first.wait_for(state="visible")
    elif key=="demo_menu_filter":
        click_sample(page,'[data-cat="foetel"]')
        page.locator('[data-cat="foetel"].active').wait_for(state="visible")
    elif key=="demo_salon_staff":
        click_sample(page,"#service-list .service-card")
        page.locator("#staff-list").wait_for(state="visible")
    elif key.endswith("_admin") or key in ("demo_crm_board","demo_crm_detail"):
        if not page.locator("#ds-v23-panel").is_visible():
            click_sample(page,"#ds-v23-owner")
        page.locator("#ds-v23-panel").wait_for(state="visible")
        if key=="demo_crm_detail":
            # Only the public built-in sample card, never external customer data.
            click_sample(page,'.crm-card[data-crm-id="105"]')
            page.locator('.crm-card[data-crm-id="105"][aria-pressed="true"]').wait_for(state="visible")
    clean_demo(page,key)
def capture(topic,out):
    if topic.key not in cat.META:return ORIGINAL_CAPTURE(topic,out)
    shots=[];audit=[];seen={}
    # All contexts have isolated storage. No credentials, real bookings, saving or data entry.
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        pages={};contexts=[]
        try:
            for _,key,_,_ in topic.scenes:
                if key in pages:continue
                ctx=browser.new_context(viewport={"width":r.VW,"height":r.VH},device_scale_factor=2,service_workers="block")
                contexts.append(ctx)
                page=ctx.new_page()
                if key in PATHS:
                    ctx.route("**/*",lambda route,k=key:demo_guard(route,k))
                    page.goto("https://"+HOST+"/demok/"+PATHS[key]+"?skin=dark",wait_until="domcontentloaded",timeout=45000)
                    page.wait_for_timeout(1200);prepare(page,key)
                else:
                    ctx.route("**/*",r.guard)
                    page.goto(public.HOST+public.PAGES[key],wait_until="domcontentloaded",timeout=45000)
                    page.wait_for_timeout(1800);r.cleanup(page)
                pages[key]=page
            for i,(_,key,selector,_) in enumerate(topic.scenes):
                page=pages[key];n=seen.get((key,selector),0);seen[key,selector]=n+1
                errors=[]
                # Preserve exact approved focus/crop geometry, replacing only overlay
                # cleanup for the explicitly allowed demo document.
                old=r.cleanup
                try:
                    if key in PATHS:r.cleanup=lambda p,k=key:clean_demo(p,k)
                    for width in (r.VW,480,600,760):
                        page.set_viewport_size({"width":width,"height":r.VH});page.wait_for_timeout(350);r.cleanup(page)
                        try:
                            data,(x,y,z,cw,ch)=r.focus(page,r.root(page,selector),n)
                            break
                        except Exception as e:errors.append(str(e)[:300])
                    else:raise RuntimeError("Scene "+str(i+1)+" "+key+" "+selector+" failed: "+"; ".join(errors))
                finally:r.cleanup=old
                with Image.open(io.BytesIO(page.screenshot(animations="disabled"))) as ss:
                    if ss.size!=(width*2,r.VH*2):raise RuntimeError("Capture density mismatch")
                    im=ss.crop((x*2,y*2,(x+cw)*2,(y+ch)*2)).convert("RGB")
                im.save(out/f"shot-{i:02d}.png");shots.append((im,z))
                audit.append({"scene":i+1,"page":page.url,"selector":selector,"minimum_projected_px":round(data["projected"],2),"unobstructed":True,"sample_demo":key in PATHS,"safe_zoom_ratio":z})
                print("V1266_CAPTURE",topic.key,i+1,key,audit[-1]["minimum_projected_px"],flush=True)
        finally:
            for ctx in contexts:ctx.close()
            browser.close()
    if len(audit)!=10 or any(a["minimum_projected_px"]<32 for a in audit):raise RuntimeError("Capture gate failed")
    (out/"capture_report.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2))
    return shots,audit

ORIGINAL_CAPTURE=r.capture
ORIGINAL_FRAME=r.frame
def frame(topic,shots,s,n,edges,caps,en):
    if topic.key not in cat.META:return ORIGINAL_FRAME(topic,shots,s,n,edges,caps,en)
    family=cat.META[topic.key]["family"]
    bg,accent,secondary,label=PALETTES[family]
    # Reuse exact original foreground and crop. Recolor only the solid original
    # background above UI and around it, excluding mascot and subtitle regions.
    im=ORIGINAL_FRAME(topic,shots,s,n,edges,caps,en)
    import numpy as np
    a=np.asarray(im).copy()
    old=np.array([23,17,34],dtype=np.uint8)
    rgb=tuple(int(bg[i:i+2],16) for i in (1,3,5))
    # Top and sides; no pixels within actual browser UI or lower caption/mascot.
    for y0,y1,x0,x1 in ((0,285,0,1080),(285,1435,0,19),(285,1435,1061,1080)):
        v=a[y0:y1,x0:x1];mask=np.all(v==old,axis=2);v[mask]=rgb
    im=Image.fromarray(a);d=ImageDraw.Draw(im)
    d.rectangle((0,0,1080,12),fill=accent)
    d.text((40,238),label,font=r.rig.font(25,True),fill=accent)
    # Distinct graphic treatments confined to top/right and a small progress strip.
    if family=="auto":
        for i in range(5):d.line((1005+i*12,32,1035+i*12,63),fill=accent,width=3)
    elif family=="menu":d.arc((950,18,1050,118),0,180,fill=accent,width=4)
    elif family=="salon":d.ellipse((1010,35,1040,65),outline=accent,width=3)
    elif family=="crm":
        for i in range(3):d.rectangle((970+i*30,40,985+i*30,54),fill=accent)
    elif family=="web":d.rounded_rectangle((975,35,1040,70),radius=8,outline=accent,width=3)
    d.rectangle((40,282,1040,287),fill=secondary)
    d.rectangle((40,282,40+round(1000*(n+1)/edges[-1]),287),fill=accent)
    return im

@contextmanager
def install():
    old=(r.capture,r.frame)
    try:r.capture=capture;r.frame=frame;yield
    finally:r.capture,r.frame=old

def selftest():
    assert len(PALETTES)==5 and len(set(v[0] for v in PALETTES.values()))==5
    for key,p in PATHS.items():
        assert allowed("https://"+HOST+"/demok/"+p+"?skin=dark",key)
        assert not allowed("https://evil.example/demok/"+p,key)
        assert not allowed("https://"+HOST+"/ugyfelportal.html",key)
    import numpy as np
    shots=[(Image.new("RGB",(960,1032),"#aaccee"),.88)]*10
    edges=[i*120 for i in range(11)];en=np.zeros(edges[-1])
    for family in PALETTES:
        t=next(t for t in cat.NEW if cat.META[t.key]["family"]==family)
        a=frame(t,shots,0,5,edges,[{"start":0,"end":2,"text":"A bemutató mintaadatai."}],en)
        b=ORIGINAL_FRAME(t,shots,0,5,edges,[{"start":0,"end":2,"text":"A bemutató mintaadatai."}],en)
        assert a.size==(1080,1920)
        # Exact UI region and lower caption/mascot preserved.
        assert a.crop((20,288,1060,1435)).tobytes()==b.crop((20,288,1060,1435)).tobytes()
        assert a.crop((0,1435,1080,1920)).tobytes()==b.crop((0,1435,1080,1920)).tobytes()
    print("V1266_STYLE_PASS five distinct accents; original UI and subtitle pixels preserved; allowlist checks")
if __name__=="__main__":selftest()
