"""V12.8.1 public-demo-only action capture and approved device visual smoke test.
No voice, private account data, upload to marketing, deployment, or ledger mutations.
"""
import argparse,json,subprocess
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
import integration_v1280 as engine
import action_review_v1269 as standard
import action_review_v12691 as repaired
from action_review_v1267 import CASES

TOPICS={"auto":"auto_booking","menu":"menu_categories","salon":"salon_services","crm":"crm_board","web":"web_services"}
def fit_viewport(frame):
    # Keep aspect and every viewport edge; approved phone screen is 430:720.
    canvas=np.full((1440,860,3), (18,16,24), np.uint8)
    h,w=frame.shape[:2]; ratio=min(860/w,1440/h)
    nw,nh=round(w*ratio),round(h*ratio)
    x,y=(860-nw)//2,(1440-nh)//2
    canvas[y:y+nh,x:x+nw]=cv2.resize(frame,(nw,nh),interpolation=cv2.INTER_AREA if ratio<1 else cv2.INTER_LINEAR)
    return canvas,ratio,(x,y,nw,nh)

def render(family,assets,out):
    before,actual,after,audit=assets
    case=next(c for c in CASES if c[0]==family)
    p=engine.plan(TOPICS[family])
    assert p["publication"] is False and p["family"]==family
    assert audit["state_changed"] and audit["crop"] is False and audit["viewport_coverage"]==1
    base=engine.header(engine.prior.bg(),{"heading":p["scenes"][0]["heading"],"device":"mobile"})
    im=Image.fromarray(cv2.cvtColor(base,cv2.COLOR_BGR2RGB));d=ImageDraw.Draw(im)
    d.text((540,1570),"V12.8.1 · Hang nélküli vizuális próba",font=engine.prior.font(30),anchor="mm",fill="#eee8ff")
    d.text((540,1640),"Valódi demóművelet · mintaadatok",font=engine.prior.font(26,False),anchor="mm",fill="#b9b3d3")
    base=cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2BGR)
    path=out/(family+".mp4");tmp=out/(family+".partial.mp4")
    proc=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","bgr24","-s","1080x1920","-r","30","-i","-","-an","-c:v","libx264","-preset","veryfast","-crf","20","-threads","2","-pix_fmt","yuv420p","-movflags","+faststart",str(tmp)],stdin=subprocess.PIPE)
    count=0;min_scale=100.;bounds=[]
    try:
        for n in range(240):
            src=before if n<60 else actual[min(len(actual)-1,int((n-60)*len(actual)/90))] if n<150 else after
            a=cv2.cvtColor(np.asarray(src),cv2.COLOR_RGB2BGR)
            texture,ratio,rect=fit_viewport(a);frame=base.copy()
            q=engine.prior.device(frame,texture,"mobile",n/30,False)
            assert np.isfinite(q).all() and q[:,0].min()>=0 and q[:,0].max()<1080 and q[:,1].min()>200 and q[:,1].max()<1429
            # Recalculate contextual scale in the actual final phone projection.
            vw=audit["before"]["viewport_css"][0]
            screen=min(np.linalg.norm(q[1]-q[0]),np.linalg.norm(q[2]-q[3]))
            min_scale=min(min_scale,float(screen*rect[2]/860/vw));bounds.append(q.tolist())
            proc.stdin.write(frame.tobytes());count+=1
            if n in (15,60,120,180,239):cv2.imwrite(str(out/(family+f"-{n}.jpg")),cv2.resize(frame,(540,960)))
        proc.stdin.close();assert proc.wait()==0 and count==240
        subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(tmp),"-f","null","-"],check=True)
        tmp.rename(path)
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        if tmp.exists():tmp.unlink()
    audit.update({"topic":p["topic"],"fresh_browser":True,"device":"approved V12.7.1 mobile","frames":count,"duration_seconds":8,"minimum_final_css_scale":min_scale,"readability_final_visual_review_required":True,"voice_calls":0,"publication":False,"production_ready":False})
    (out/(family+".json")).write_text(json.dumps(audit,ensure_ascii=False,indent=2))
    print("V1281_ACTION_PASS",family,json.dumps(audit,ensure_ascii=False),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("family",choices=TOPICS);parser.add_argument("--out",type=Path,required=True);a=parser.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    case=next(c for c in CASES if c[0]==a.family)
    engine.catalogue.validate_catalogue()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            assets=(repaired if a.family in ("auto","salon") else standard).capture_case(browser,case)
        finally:browser.close()
    render(a.family,assets,a.out)
if __name__=="__main__":main()
