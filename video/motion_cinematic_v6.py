"""V6: cinematic review-only motion system. Real UI assets, no Buffer or social writes."""
from pathlib import Path
import math, subprocess, tempfile, wave
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import cinematic_preview_v5 as v5
import depth_preview_v4 as v4
import motion_preview_v3 as v3
import style_preview_v2 as v2
OUT=Path("motion-cinematic-v6");OUT.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30
DUR=[3.,3.5,4.,3.5,4.,4.]
WHITE="#f4f4fa";PURPLE="#c2a9ff";MUTED="#c1bfce"
ease=v4.ease;smooth=v4.smooth;text=v4.text;label=v4.label;card=v4.card
def capture():
    v5.OUT=OUT;v5.capture()
def beat(t):
    return math.exp(-9*(t%0.5))
@lru_cache(maxsize=96)
def title_texture(s,n,color):
    font=v3.font(n,True)
    while font.getlength(s)>880 and n>18:n-=1;font=v3.font(n,True)
    bb=font.getbbox(s);w=int(font.getlength(s))+24;h=bb[3]-bb[1]+32
    im=Image.new("RGBA",(w,h));d=ImageDraw.Draw(im)
    for k in range(9,0,-1):
        d.text((12+k*.65,8-bb[1]+k*.65),s,font=font,fill="#51416e")
    d.text((12,8-bb[1]),s,font=font,fill=color)
    return im
def title(im,s,x,y,n,c,t,delay=0):
    a=ease((t-delay)/.42);tex=title_texture(s,n,c)
    w,h=tex.size;cx=x+w/2+45*(1-a);cy=y+h/2+32*(1-a)
    # Perspective of the extruded lettering settles front-on; face stays legible.
    quad=v4.project(cx,cy,w,h,-18*(1-a),-9*(1-a),-4*(1-a),0)
    # Transform alpha as well as RGB (no opaque rectangular background).
    x0=max(0,math.floor(min(x for x,y in quad)));y0=max(0,math.floor(min(y for x,y in quad)))
    x1=min(W,math.ceil(max(x for x,y in quad))+1);y1=min(H,math.ceil(max(y for x,y in quad))+1)
    if x1<=x0 or y1<=y0:return
    mat=[];rhs=[]
    for (xx,yy),(u,v) in zip(quad,[(0,0),(w-1,0),(w-1,h-1),(0,h-1)]):
        xx-=x0;yy-=y0;mat.extend([[xx,yy,1,0,0,0,-u*xx,-u*yy],[0,0,0,xx,yy,1,-v*xx,-v*yy]]);rhs.extend([u,v])
    cf=tuple(np.linalg.solve(np.array(mat),np.array(rhs)))
    patch=tex.transform((x1-x0,y1-y0),Image.Transform.PERSPECTIVE,cf,Image.Resampling.BICUBIC)
    im.paste(patch,(x0,y0),patch)
def bg(t,s):
    im=v5.background(t,s);d=ImageDraw.Draw(im);pulse=beat(sum(DUR[:s])+t)
    # Deliberately restrained light trails, never full-frame flashing.
    for i in range(28):
        x=(i*197+int(36*t*(1+i%3)))%1080;y=650+(i*113+int(25*t))%1010
        r=1+i%3;v=int(32+18*pulse+7*(i%4))
        d.ellipse((x-r,y-r,x+r,y+r),fill=(v,v-7,min(255,v+30)))
    for k in range(3):
        x=int((t*170+k*370+80*s)%1450)-180
        d.line((x,1670,x+380,680),fill=(47+int(13*pulse),38,71+int(18*pulse)),width=2)
    return im
def orbit(im,a,t,final=False):
    # Continuous depth-sorted orbit of virtual devices, not an image spin.
    p=ease(t/.75);ang=-1.05+1.6*p+.44*t
    positions=[("dev_services",ang),("dev_slots",ang+math.pi)]
    lapw=740 if not final else 700; cy=1100 if not final else 1030
    v5.laptop(im,a["laptop"],540,cy-90,lapw,lapw*.61,18*math.cos(ang),5,-3*math.sin(ang),t)
    for key,z in sorted(positions,key=lambda k:math.sin(k[1])):
        depth=math.sin(z);scale=.83+.17*depth
        cx=540+310*math.cos(z);yy=cy+90+65*depth
        if final:scale*=.85;yy-=35
        v5.device(im,a[key],cx,yy,390*scale,735*scale,32*math.cos(z),5,-12*math.cos(z),t)
def zoom(im,t,at,x,y):
    # Camera punch around a tap, with a short, eased release.
    age=t-at
    if 0<=age<.36:
        k=1+.045*math.sin(math.pi*age/.36)
        w,h=round(W/k),round(H/k);x0=max(0,min(W-w,round(x*(1-1/k))));y0=max(0,min(H-h,round(y*(1-1/k))))
        return im.crop((x0,y0,x0+w,y0+h)).resize((W,H),Image.Resampling.BICUBIC)
    return im
def frame(s,t,a):
    im=bg(t,s);p=ease(t/.45);q=smooth(t/DUR[s])
    if s==0:
        orbit(im,a,t)
        label(im,"AUTÓSZERVIZ • ÉLŐ DEMÓ")
        title(im,"Még mindig",72,292,99,WHITE,t)
        title(im,"telefonon?",72,412,120,PURPLE,t,.08)
        text(im,76,555,"Mutasd meg a szabad időpontokat online.",37,b=False)
        card(im,a["service_after"],100,1515,880,150)
    elif s==1:
        label(im,"01 / SZOLGÁLTATÁS")
        title(im,"Egyértelmű",72,290,91,WHITE,t);title(im,"választás.",72,402,110,PURPLE,t,.08)
        text(im,76,540,"A vendég kiválasztja, mire van szüksége.",38,b=False)
        if t<1.4:
            v5.device(im,a["dev_services"],540,1120,535+55*q,990+70*q,22-38*q,4,8-12*q,t)
        else:
            r=ease((t-1.4)/.40);card(im,a["service_before" if t<2.1 else "service_after"],72,735-int(70*r),936,335)
            card(im,a["services"],90,1115,900,420,True,.65)
            v3.tap(im,815,845,t,2.05);im=zoom(im,t,2.05,815,845)
        text(im,78,1630,"Valódi ügyfélnézet",40)
    elif s==2:
        label(im,"02 / IDŐPONT");title(im,"Nap. Idősáv.",72,290,96,WHITE,t);title(im,"Kész.",72,407,112,PURPLE,t,.10)
        card(im,a["dates_before" if t<.75 else "dates_after"],72,645+int(45*(1-p)),936,250)
        v3.tap(im,340,780,t,.71)
        card(im,a["slots_before" if t<1.75 else "slots_after"],72,945,936,420)
        v3.tap(im,245,1080,t,1.71)
        if t>=1.95:v5.floating(im,a["selected"],235,1410,610,155,t)
        im=zoom(im,t,1.71,245,1080);text(im,78,1630,"Az elérhető idősávok láthatók.",40)
    elif s==3:
        label(im,"ÜGYFÉLNÉZET • DEMÓ");title(im,"Az időpont",72,295,93,WHITE,t);title(im,"látható.",72,405,112,PURPLE,t,.10)
        v5.device(im,a["dev_slots"],545+65*math.sin(t*1.8),1090,570,1040,-29+49*q,8-12*q,-10+14*q,t)
        v5.floating(im,a["selected"],180+int(75*q),1460,720,155,t)
        text(im,78,1660,"Kiválasztott idősáv • nincs végleges foglalás",30,b=False)
    elif s==4:
        label(im,"03 / SAJÁT ADMIN");title(im,"Te irányítod.",72,295,99,WHITE,t)
        text(im,76,430,"A szolgáltatásaid saját kezelőfelületen.",39,b=False)
        if t<2.0:
            v5.laptop(im,a["laptop"],540,1030,910,560,-22+42*q,5,-4+6*q,t)
            v5.device(im,a["dev_admin"],790-35*q,1345,340,630,18-20*q,-3,8-7*q,t)
        else:card(im,a["admin"],72,570,936,950,True,.1+.7*smooth((t-2.)/2.))
        text(im,78,1620,"Tulajdonosi nézet • valódi demó",38)
    else:
        orbit(im,a,t,True);label(im,"PRÓBÁLD KI")
        title(im,"Ne csak nézd.",72,290,99,WHITE,t);title(im,"Teszteld.",72,410,132,PURPLE,t,.10)
        text(im,76,565,"Autószerviz-időpontfoglaló",45,b=False)
        d=ImageDraw.Draw(im);d.rounded_rectangle((72,1390,1008,1515),radius=35,fill="#c2a9ff")
        text(im,105,1428,"Bemutatóstúdió megnyitása  →",45,"#151020",limit=870)
        text(im,76,1560,"darkline-studio.web.app",43);text(im,76,1640,"Valós, kipróbálható funkciók.",34,MUTED,False)
    v5.brand(im,s,t)
    return im
def transition(prev,cur,t):
    # Eight-frame spatial wipe between compositions, with a luminous seam.
    p=smooth(t/.27);edge=int(-200+1480*p)
    mask=Image.new("L",(W,H));d=ImageDraw.Draw(mask)
    d.polygon([(0,0),(edge+170,0),(edge-120,H),(0,H)],fill=255)
    result=Image.composite(cur,prev,mask)
    if 0<p<1:ImageDraw.Draw(result).line((edge+170,0,edge-120,H),fill="#a888ff",width=5)
    return result
def render():
    a={p.stem:Image.open(p).convert("RGB") for p in OUT.glob("*.png")}
    for k in ["services","slots","admin"]:a["dev_"+k]=v4.phone_texture(a["phone_"+k])
    a["laptop"]=v5.laptop_texture(a["desktop_admin"]);a["selected"]=(OUT/"selected.txt").read_text(encoding="utf8")
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td);silent=tmp/"silent.mp4";audio=tmp/"sound.wav"
        cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","pipe:0","-c:v","libx264","-preset","fast","-crf","17","-pix_fmt","yuv420p","-threads","3",str(silent)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE);prev=None
        try:
            for s,d in enumerate(DUR):
                for n in range(round(d*FPS)):
                    im=frame(s,n/FPS,a)
                    if prev is not None and n<8:im=transition(prev,im,n/FPS)
                    if n in [12,round(d*FPS)//2]:im.save(OUT/f"scene-{s+1}-{n:03d}.jpg",quality=94)
                    proc.stdin.write(im.tobytes())
                prev=im
        finally:proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError("Encoding failed")
        # Same original 120 BPM track as V5; motion pulses use its exact half-second beat.
        v5.sound(audio,sum(DUR))
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(silent),"-i",str(audio),"-c:v","copy","-c:a","aac","-b:a","160k","-movflags","+faststart","-shortest",str(OUT/"Darkline_motion_V6.mp4")],check=True)
    sheet=Image.new("RGB",(1620,960),"#11111b")
    for i,p in enumerate(sorted(OUT.glob("scene-*.jpg"))):sheet.paste(Image.open(p).resize((270,480),Image.Resampling.LANCZOS),((i//2)*270,(i%2)*480))
    sheet.save(OUT/"storyboard.jpg",quality=95)
    print("V6_CINEMATIC_OK",(OUT/"Darkline_motion_V6.mp4").stat().st_size,flush=True)
if __name__=="__main__":capture();render()
