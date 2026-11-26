"""V12.7.0 private perspective device compositing. Full viewport textures; no crop.
Original reviewed video provides its synchronized mascot, caption strip and audio.
No network, voice API or publishing. Device geometry is procedural 2.5D.
"""
import argparse,json,math,subprocess
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
W,H,FPS=1080,1920,30
cv2.setNumThreads(2)
HEADS=['Egy weboldal, két nézet','Referenciák','Saját kezelőfelület','Szolgáltatások mobilon','Munkák bemutatása','Tartalomkezelés mobilon','Átlátható árazás','Előzetes árbecslés','A vállalkozásodra szabva','Induljon a közös munka']
DEVICES=['desktop','desktop','desktop','mobile','mobile','mobile','desktop','mobile','desktop','mobile']
B='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf';F='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def font(n,b=True):return ImageFont.truetype(B if b else F,n)
def readframes(p):
    c=cv2.VideoCapture(str(p));frames=[]
    while True:
        ok,a=c.read()
        if not ok:break
        frames.append(a)
    c.release();return frames
def vec(a):return cv2.resize(a,(96,64),interpolation=cv2.INTER_AREA).astype(np.int16)
def segment(path):
    frames=readframes(path);a=cv2.imread(str(path.with_suffix('.before.png')));b=cv2.imread(str(path.with_suffix('.after.png')))
    if a is None or b is None or len(frames)<20 or any(f.shape!=a.shape for f in frames):raise RuntimeError('missing/mismatched viewport '+path.name)
    v=np.stack([vec(f) for f in frames]);aa,bb=vec(a),vec(b)
    e1=np.abs(v-aa).mean(axis=(1,2,3));e2=np.abs(v-bb).mean(axis=(1,2,3))
    best=min((float(e1[i]+e2[j]),i,j) for j in range(10,len(frames)) for i in range(max(0,j-100),j-9))
    _,i,j=best
    if max(e1[i],e2[j])>5:raise RuntimeError('recording mismatch '+path.name+str((e1[i],e2[j])))
    return frames[i:j+1],{'start':i,'end':j,'before_error':round(float(e1[i]),3),'after_error':round(float(e2[j]),3),'pixel_change':round(float(np.abs(v[i]-v[j]).mean()),3),'viewport':list(a.shape[1::-1])}
def poly(im,pts,col):cv2.fillConvexPoly(im,np.rint(pts).astype(np.int32),col,lineType=cv2.LINE_AA)
def line(im,pts,col,t=1):cv2.polylines(im,[np.rint(pts).astype(np.int32)],False,col,t,cv2.LINE_AA)
def project(coords,center,yaw,pitch):
    a=np.array(coords,np.float64);cy,sy=math.cos(yaw),math.sin(yaw);cp,sp=math.cos(pitch),math.sin(pitch)
    x=a[:,0]*cy+a[:,2]*sy;z=-a[:,0]*sy+a[:,2]*cy;y=a[:,1]*cp-z*sp;z=a[:,1]*sp+z*cp
    scale=2300/(2300+z);return np.c_[center[0]+x*scale,center[1]+y*scale]
def quad(w,h,z=0):return [(-w/2,-h/2,z),(w/2,-h/2,z),(w/2,h/2,z),(-w/2,h/2,z)]
def texture(im,src,q):
    h,w=src.shape[:2];x,y=np.floor(q.min(axis=0)).astype(int);x2,y2=np.ceil(q.max(axis=0)).astype(int)+1
    if x<0 or y<0 or x2>W or y2>1445:raise RuntimeError('screen outside safe bounds')
    m=cv2.getPerspectiveTransform(np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]]),np.float32(q-[x,y]))
    v=cv2.warpPerspective(src,m,(x2-x,y2-y),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    mask=np.zeros(v.shape[:2],np.uint8);cv2.fillConvexPoly(mask,np.rint(q-[x,y]).astype(np.int32),255,lineType=cv2.LINE_AA)
    cv2.copyTo(v,mask,im[y:y2,x:x2])
def device(im,src,kind,t,opening=False):
    w0,h0=src.shape[1],src.shape[0];mobile=kind=='mobile'
    sw=660 if mobile else 956;sh=sw*h0/w0
    center=(540+8*math.sin(t*1.1),805+14*math.cos(t*1.3)) if mobile else (540+5*math.sin(t),685+13*math.cos(t*1.1))
    if opening:
        q=min(1,max(0,t/1.05));ease=q*q*(3-2*q);center=(center[0],center[1]-120*(1-ease))
    yaw=.075*math.sin(t*1.6)+(.04 if mobile else -.035);pitch=.045*math.cos(t*1.4)
    p=lambda pts:project(pts,center,yaw,pitch)
    bw,bh=sw+30,sh+44;outer=p(quad(bw,bh))
    poly(im,outer+[10,20],(18,15,23));poly(im,p(quad(bw+4,bh+4,10)),(72,69,87));poly(im,outer,(24,22,32));line(im,np.vstack([outer,outer[0]]),(137,120,165),2)
    if not mobile:
        y=bh/2;deck=p([(-bw/2,y,0),(bw/2,y,0),(bw*.455,y+94,-205),(-bw*.455,y+94,-205)])
        poly(im,deck+[0,12],(34,30,45));poly(im,deck,(111,105,129));line(im,deck[2:4],(187,179,202),3)
        for row in range(4):
            yy=y+10+row*13;zz=-30-row*28
            for col in range(14):
                xx=-bw*.43+col*bw*.062;kw=bw*.052
                poly(im,p([(xx,yy,zz),(xx+kw,yy,zz),(xx+kw,yy+9,zz-18),(xx,yy+9,zz-18)]),(37,34,49))
        poly(im,p([(-125,y+70,-155),(125,y+70,-155),(125,y+88,-190),(-125,y+88,-190)]),(91,86,109))
    q=p(quad(sw,sh,-1));texture(im,src,q)
    dot=p([(0,-bh/2+9,-1)])[0];cv2.circle(im,tuple(np.rint(dot).astype(int)),3,(155,145,185),-1,cv2.LINE_AA)
    return q
def bg():
    y,x=np.ogrid[:H,:W];r=np.exp(-(((x-530)/750)**2+((y-680)/900)**2));r2=np.exp(-(((x-940)/340)**2+((y-340)/500)**2));a=np.empty((H,W,3),np.uint8)
    for i,(base,k,k2) in enumerate(((24,37,35),(15,15,12),(15,28,49))):a[:,:,i]=np.clip(base+k*r+k2*r2,0,255)
    return a
def header(base,scene):
    a=Image.fromarray(cv2.cvtColor(base,cv2.COLOR_BGR2RGB));d=ImageDraw.Draw(a);d.rectangle((0,0,W,8),fill='#bda3ff')
    d.text((42,33),'DARKLINE STUDIO   /   VALÓDI DEMÓ',font=font(28),fill='#b9a2ff')
    title=HEADS[scene];fs=54
    while d.textlength(title,font=font(fs))>1000:fs-=1
    d.text((42,96),title,font=font(fs),fill='#f4edff');d.text((42,171),'LAPTOP • ASZTALI NÉZET' if DEVICES[scene]=='desktop' else 'TELEFON • MOBILNÉZET',font=font(26),fill='#aeb8d9')
    if DEVICES[scene]=='desktop':
        d.rounded_rectangle((76,1130,1004,1350),radius=28,fill='#1d2138',outline='#695e93',width=2)
        d.text((108,1164),'Teljes asztali felület',font=font(38),fill='#f1edff');d.text((108,1233),'Valódi böngészőnézet • Mintaadatok',font=font(30,False),fill='#b8c2e0')
    else:d.text((W//2,1401),'Mintaadatok · nincs mentés',font=font(24,False),fill='#c1b6d8',anchor='mm')
    return cv2.cvtColor(np.asarray(a),cv2.COLOR_RGB2BGR)
def main(captures,source,timing,out):
    scenes=json.loads(timing.read_text())['scenes'];assert len(scenes)==10
    cap=cv2.VideoCapture(str(source));total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));assert total>=900
    edges=[0]+[round((a['end']+b['start'])*FPS/2) for a,b in zip(scenes,scenes[1:])]+[total]
    b=bg();audit=[]
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-','-i',str(source),'-map','0:v','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','20','-threads','3','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
    try:
        for s,(start,end) in enumerate(zip(edges,edges[1:])):
            clips,info=segment(captures/f'scene-{s:02d}.mp4');base=header(b,s);audit.append(info)
            for n in range(start,end):
                ok,old=cap.read()
                if not ok:raise RuntimeError('original frames exhausted')
                local=(n-start)/FPS;u=(n-start)/max(1,end-start-1);idx=min(len(clips)-1,round(u*(len(clips)-1)))
                im=base.copy();device(im,clips[idx],DEVICES[s],local+s*.5,opening=s==0)
                im[1445:]=old[1445:]
                cv2.rectangle(im,(34,1433),(1046,1438),(65,52,80),-1);cv2.rectangle(im,(34,1433),(34+round(1012*(n+1)/total),1438),(230,158,195),-1)
                proc.stdin.write(im.tobytes())
            print('V1270_RENDER_SCENE',s+1,info,flush=True)
    finally:proc.stdin.close();cap.release()
    if proc.wait():raise RuntimeError('encode failed')
    out.with_suffix('.json').write_text(json.dumps({'scenes':audit,'frames':total,'no_crop':True,'audio_copy':True,'publication':False},indent=2))
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(out),'-f','null','-'],check=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('captures',type=Path);p.add_argument('source',type=Path);p.add_argument('timing',type=Path);p.add_argument('out',type=Path);a=p.parse_args();main(a.captures,a.source,a.timing,a.out)
