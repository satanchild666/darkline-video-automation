"""Laptop-only V12.7.3. Uses exact V1271 frame for all mobile scenes and lower strip.
True PBR mesh render (VTK/EGL). Original voice audio packets are copied unchanged.
"""
import argparse,json,math,subprocess,hashlib,time
from pathlib import Path
import cv2,numpy as np
import cinematic_render_v1271 as prior
from laptop_v1273 import Laptop
W,H,FPS=1080,1920,30
cv2.setNumThreads(2)

def geometry(lap,t,opening=False):
    a,q=lap.render(t);a=cv2.resize(a,(1080,1000),interpolation=cv2.INTER_AREA);q=q*np.array([1080/lap.width,1000/lap.height],np.float32)
    # Device position changes smoothly without scaling/cropping the full viewport.
    ease=min(1,max(0,t/1.05));ease=ease*ease*(3-2*ease)
    y=255+round(10*math.cos(t*1.1)-(105*(1-ease) if opening else 0))
    q[:,1]+=y
    mask=a[:,:,3];ys,xs=np.where(mask>12)
    bounds=[int(xs.min()),int(ys.min()+y),int(xs.max()),int(ys.max()+y)]
    if bounds[0]<14 or bounds[2]>=1066 or bounds[1]<220 or bounds[3]>=1220:raise RuntimeError('device outside safe region '+str(bounds))
    if min(np.linalg.norm(q[1]-q[0]),np.linalg.norm(q[2]-q[3]))<760:raise RuntimeError('screen width below 760 px')
    return a,q,y,bounds

def compose(base,lap,src,t,opening=False):
    a,q,y,bounds=geometry(lap,t,opening)
    # Real studio shadow follows projected shell, soft grounding shadow beneath deck.
    im=base.copy();small=np.zeros((H//4,W//4),np.uint8);m=cv2.resize(a[:,:,3],(270,250),interpolation=cv2.INTER_AREA);yy=y//4+5
    small[yy:yy+250]=m;small=cv2.GaussianBlur(small,(0,0),5);shadow=cv2.resize(small,(W,H),interpolation=cv2.INTER_LINEAR)
    zone=im[210:1220];z=shadow[210:1220,:,None].astype(np.float32)/255.;zone[:]=(zone*(1-.46*z)).astype(np.uint8)
    # Off-screen renderer returns RGB(A), preserve hardware alpha, not screen mask.
    rgb=cv2.cvtColor(a[:,:,:3],cv2.COLOR_RGB2BGR);alpha=a[:,:,3,None].astype(np.float32)/255.;roi=im[y:y+1000]
    roi[:]=np.rint(rgb*alpha+roi*(1-alpha)).astype(np.uint8)
    prior.texture(im,src,q)
    return im,bounds,q

def main(captures,source,timing,out,preview=False):
    data=json.loads(timing.read_text());scenes=data['scenes'];assert len(scenes)==10
    cap=cv2.VideoCapture(str(source));total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));assert total>=900
    edges=[0]+[round((a['end']+b['start'])*FPS/2) for a,b in zip(scenes,scenes[1:])]+[total]
    lap=Laptop();b=prior.bg();audit=[];mobile_hash=hashlib.sha256();mobile_out=hashlib.sha256();lower_in=hashlib.sha256();lower_out=hashlib.sha256();count=0
    if preview:
        for s in (0,1,2,6,8):
            clips,info=prior.segment(captures/f'scene-{s:02d}.mp4');base=prior.header(b,s)
            im,bounds,q=compose(base,lap,clips[len(clips)//2],.6+s*.5,s==0);print(s,bounds,q.tolist(),flush=True)
            cv2.imwrite(str(out.parent/f'preview{s}.jpg'),cv2.resize(im,(540,960)))
        cap.release();return
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-','-i',str(source),'-map','0:v','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','17','-threads','3','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
    try:
        for s,(start,end) in enumerate(zip(edges,edges[1:])):
            desktop=prior.DEVICES[s]=='desktop';bounds_all=[];widths=[]
            if desktop:clips,info=prior.segment(captures/f'scene-{s:02d}.mp4');base=prior.header(b,s)
            else:info={'phone':'unchanged decoded V1271 frame'}
            for n in range(start,end):
                ok,old=cap.read()
                if not ok:raise RuntimeError('original frames exhausted')
                if desktop:
                    local=(n-start)/FPS;u=(n-start)/max(1,end-start-1);idx=min(len(clips)-1,round(u*(len(clips)-1)))
                    im,bounds,q=compose(base,lap,clips[idx],local+s*.5,s==0);bounds_all.append(bounds);widths.append(float(min(np.linalg.norm(q[1]-q[0]),np.linalg.norm(q[2]-q[3]))));im[1429:]=old[1429:]
                else:
                    im=old;mobile_hash.update(old.tobytes());mobile_out.update(im.tobytes())
                lower_in.update(old[1429:].tobytes());lower_out.update(im[1429:].tobytes());proc.stdin.write(im.tobytes());count+=1
            if desktop:info.update({'hardware_bounds':[min(x[0] for x in bounds_all),min(x[1] for x in bounds_all),max(x[2] for x in bounds_all),max(x[3] for x in bounds_all)],'minimum_screen_width':round(min(widths),2)})
            info.update({'scene':s,'frames':end-start,'desktop':desktop});audit.append(info);print('V1273_RENDER_SCENE',s+1,json.dumps(info),flush=True)
    finally:proc.stdin.close();cap.release()
    if proc.wait():raise RuntimeError('encode failed')
    assert count==total and mobile_hash.digest()==mobile_out.digest() and lower_in.digest()==lower_out.digest()
    out.with_suffix('.json').write_text(json.dumps({'scenes':audit,'frames':count,'no_crop':True,'audio_copy':True,'phone_and_lower_panel_preencode_exact':True,'publication':False,'renderer':'VTK OpenGL PBR mesh, studio IBL, physical model'},indent=2))
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(out),'-f','null','-'],check=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('captures',type=Path);p.add_argument('source',type=Path);p.add_argument('timing',type=Path);p.add_argument('out',type=Path);p.add_argument('--preview',action='store_true');a=p.parse_args();main(a.captures,a.source,a.timing,a.out,a.preview)
