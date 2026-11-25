"""V11 private review runner. Never publishes, uploads, or uses a paid voice model."""
import argparse,json,math
from pathlib import Path
import creative_intelligence_v10 as v
import heygen_free_voice_v11 as voice
import video_dedup as dedup
from PIL import ImageDraw
# Preserve earlier working renderer; patch only dashboard layout for this review.
oldframe=v.frame
def frame(key,p,s,t,a,records):
    if key!="crm":return oldframe(key,p,s,t,a,records)
    # More visible foreground movement without changing genuine UI pixels.
    # Camera moves across actual dashboard cards, keeping screenshots readable.
    if s in (1,2):
        base,accent,fg,secondary=p["colors"];im=v.background(p,s,t)
        q=v.v4.smooth(t/v.DUR[s]);e=v.v4.ease(t/.6);d=ImageDraw.Draw(im)
        scene=p["scenes"][s]
        v.v4.text(im,72,100,"DARKLINE / STUDIO",32,fg)
        v.v4.text(im,72,220,p["label"]+"  /  "+f"{s+1:02}",31,accent)
        d.line((72,184,1008,184),fill=secondary,width=2)
        v.v4.text(im,72,305,scene[0],97,fg,limit=936)
        v.v4.text(im,72,422,scene[1],98,accent,limit=936)
        k="feature" if s==1 else "detail"
        v.v4.card(im,a[k],100-int(24*q),590+int(60*(1-e)),880+int(48*q),750+int(80*q),False)
        v.v4.card(im,a["admin_detail"],140+int(70*q),1390-int(30*q),760,120,False)
        at=sum(v.DUR[:s])+t;r=records[s]
        if r["start"]<=at<r["end"]:
            d=ImageDraw.Draw(im);d.rounded_rectangle((72,1570,1008,1710),radius=24,fill="#10121b")
            v.v4.text(im,98,1614,r["text"],42,"#ffffff",limit=884)
        d=ImageDraw.Draw(im);d.rounded_rectangle((72,1758,1008,1766),radius=4,fill=secondary)
        d.rounded_rectangle((72,1758,72+int(936*at/v.TOTAL),1766),radius=4,fill=accent)
        return im
    return oldframe(key,p,s,t,a,records)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--url",required=True);ap.add_argument("--profile",choices=sorted(voice.PROFILES));ap.add_argument("--output",default="private-preview-v11");args=ap.parse_args()
    # Stop before any speech request unless explicitly enabled and in free window.
    voice.authorize()
    key,p=v.select(args.url);chosen,settings=voice.profile(key,args.profile)
    out=Path(args.output)/key
    if out.exists():raise RuntimeError("Use a fresh private output directory; no accidental regeneration")
    out.mkdir(parents=True)
    v.frame=frame
    # Capture first so broken demo doesn't spend voice quota.
    result=v.capture(key,p,out)
    records=voice.prepare(p,out,chosen,settings)
    movie=v.render(key,p,out,records)
    renamed=out/f"Darkline_V11_{key}_{chosen}.mp4";movie.rename(renamed)
    report=v.check(key,p,out,renamed,records,result)
    report["voice_profile"]=chosen;report["voice_model"]=voice.MODEL;report["publication"]=False
    (out/"quality.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    if report["review_gate"]!="PASS":raise RuntimeError("Review rejected; do not publish")
    print("V11_PRIVATE_REVIEW_PASS",key,chosen,"seconds",round(v.TOTAL,3),"publication=false",flush=True)
if __name__=="__main__":main()
