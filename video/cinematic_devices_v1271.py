"""Procedural solid device geometry, perspective projection and lit materials.
No external assets, no generated images, no crop of actual browser pixels.
Render-only review module. Metal/glass materials are stylized, not ray traced.
"""
import math
from functools import lru_cache
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W,H=1080,1920
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def rounded(w,h,r,z=0):
    out=[]
    for cx,cy,a in [(w/2-r,-h/2+r,-90),(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180)]:
        for deg in np.linspace(a,a+90,10):
            v=math.radians(deg);out.append((cx+r*math.cos(v),cy+r*math.sin(v),z))
    return np.array(out)

def quad(w,h,z=0):return np.array([[-w/2,-h/2,z],[w/2,-h/2,z],[w/2,h/2,z],[-w/2,h/2,z]],float)

def projection(center,yaw,pitch):
    cy,sy=math.cos(yaw),math.sin(yaw);cp,sp=math.cos(pitch),math.sin(pitch)
    def p(a):
        a=np.array(a,float);x=a[:,0]*cy+a[:,2]*sy;z=-a[:,0]*sy+a[:,2]*cy;y=a[:,1]*cp-z*sp;z=a[:,1]*sp+z*cp
        f=3000/(3000+z)
        return np.c_[center[0]+x*f,center[1]+y*f]
    return p

def poly(im,pts,c):
    cv2.fillConvexPoly(im,np.rint(pts).astype(np.int32),tuple(map(int,c)),lineType=cv2.LINE_AA)

def stroke(im,pts,c,t=1,closed=False):
    cv2.polylines(im,[np.rint(pts).astype(np.int32)],closed,tuple(map(int,c)),t,cv2.LINE_AA)

def warp(im,src,q,alpha=None):
    h,w=src.shape[:2];x,y=np.floor(q.min(axis=0)).astype(int);x2,y2=np.ceil(q.max(axis=0)).astype(int)+1
    if x<0 or y<0 or x2>W or y2>1429:raise RuntimeError('device texture outside safe area '+str((x,y,x2,y2)))
    m=cv2.getPerspectiveTransform(np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]]),np.float32(q-[x,y]))
    v=cv2.warpPerspective(src,m,(x2-x,y2-y),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    if alpha is None:
        mask=np.zeros(v.shape[:2],np.uint8);cv2.fillConvexPoly(mask,np.rint(q-[x,y]).astype(np.int32),255,lineType=cv2.LINE_AA)
    else:mask=cv2.warpPerspective(alpha,m,(x2-x,y2-y),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    roi=im[y:y2,x:x2];cv2.copyTo(v,mask,roi)

def shade_shell(im,p,w,h,r,front,back):
    # Closed, rounded solid: front/back rings and each face of the bevel.
    a=rounded(w,h,r,back);b=rounded(w,h,r,front);pa,pb=p(a),p(b)
    poly(im,pa,(40,37,44));
    for i in range(len(a)):
        j=(i+1)%len(a);d=b[j]-b[i];normal=np.array([d[1],-d[0]],float);normal/=max(np.linalg.norm(normal),1)
        # Environment strips reflected in machined metal, directional edge lighting.
        lit=.5+.5*float(np.dot(normal,[-.65,-.76]));spec=math.exp(-((lit-.82)/.12)**2)
        col=(54+95*lit+45*spec,48+91*lit+43*spec,55+100*lit+48*spec)
        poly(im,[pa[i],pa[j],pb[j],pb[i]],col)
    poly(im,pb,(17,17,22));stroke(im,pb,(123,121,135),1,True)
    return pb

@lru_cache(maxsize=3)
def bezel(w,h,r,phone):
    # Continuous studio-light reflection on glass perimeter; UI is composited on top.
    y,x=np.ogrid[:h,:w];g=10+12*np.exp(-((x/w-.20)/.28)**2)+7*np.exp(-((y/h-.10)/.22)**2)
    rgb=np.broadcast_to(g,(h,w)).astype(np.uint8)
    a=np.stack([rgb+5,rgb+2,rgb],axis=-1)
    img=Image.fromarray(cv2.cvtColor(a,cv2.COLOR_BGR2RGB));d=ImageDraw.Draw(img)
    d.rounded_rectangle((1,1,w-2,h-2),radius=r,outline=(166,169,184),width=2)
    d.rounded_rectangle((5,5,w-6,h-6),radius=max(2,r-5),outline=(57,62,74),width=2)
    d.rounded_rectangle((9,9,w-10,h-10),radius=max(2,r-9),outline=(7,9,13),width=2)
    if phone:
        # Earpiece and lens are above, never over the rectangular viewport.
        d.rounded_rectangle((w//2-43,12,w//2+43,26),radius=7,fill=(4,6,9),outline=(49,53,62),width=1)
        d.ellipse((w//2+24,15,w//2+32,23),fill=(34,50,68));d.ellipse((w//2+26,16,w//2+28,18),fill=(113,155,192))
        d.rounded_rectangle((w//2-36,h-18,w//2+36,h-14),radius=2,fill=(113,114,124))
    else:
        d.ellipse((w//2-5,8,w//2+5,18),fill=(5,8,13),outline=(64,68,83));d.ellipse((w//2-1,10,w//2+2,13),fill=(94,132,165))
    mask=Image.new('L',(w,h),0);ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=r,fill=255)
    return cv2.cvtColor(np.asarray(img),cv2.COLOR_RGB2BGR),np.asarray(mask)

@lru_cache(maxsize=1)
def keyboard_texture():
    w,h=1200,480;y,x=np.ogrid[:h,:w]
    # Long softbox reflections and fine brushed anodized aluminum grain.
    rng=np.random.default_rng(42);grain=rng.normal(0,.8,(h,w))
    g=119+32*np.exp(-((x/w-.19)/.23)**2)+18*np.exp(-((x/w-.83)/.11)**2)-20*(y/h)+grain
    a=np.stack([g+3,g+1,g-3],axis=-1).clip(0,255).astype(np.uint8)
    im=Image.fromarray(a);d=ImageDraw.Draw(im)
    d.rounded_rectangle((3,3,w-4,h-4),radius=27,outline=(194,199,210),width=3)
    d.rounded_rectangle((74,22,w-75,310),radius=16,fill=(77,81,91),outline=(157,161,171),width=2)
    # Speaker perforations on both sides, individual sculpted keycaps, real row sizes.
    for xx in (23,1136):
        for i in range(7):
            for j in range(34):
                x0=xx+i*6;y0=32+j*7;d.ellipse((x0,y0,x0+2,y0+2),fill=(44,47,54))
    labels=[['esc','F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12','⏻'],list('1234567890')+['−','+','⌫'],['tab']+list('QWERTYUIOP')+['[',']'],['caps']+list('ASDFGHJKL')+[';',"'",'enter'],['shift']+list('ZXCVBNM')+[',','.','/','shift'],['fn','ctrl','alt','cmd','space','cmd','alt','←','↑','→']]
    f=ImageFont.truetype(FONT,17);fsmall=ImageFont.truetype(FONT,13)
    for i,row in enumerate(labels):
        yy=32+i*43;kh=35;weights=[4.5 if k=='space' else 1.65 if k in ('shift','enter','caps','tab') else 1 for k in row];total=sum(weights);xx=86
        for k,wt in zip(row,weights):
            kw=(1028-(len(row)-1)*6)*wt/total
            d.rounded_rectangle((xx,yy+3,xx+kw,yy+kh+4),radius=6,fill=(15,17,21))
            d.rounded_rectangle((xx,yy,xx+kw,yy+kh),radius=6,fill=(36,40,47),outline=(83,87,98),width=1)
            d.line((xx+6,yy+1,xx+kw-6,yy+1),fill=(100,104,116),width=1)
            if k!='space':d.text((xx+kw/2,yy+kh/2),k,font=fsmall if len(k)>2 else f,fill=(200,205,216),anchor='mm')
            xx+=kw+6
    d.rounded_rectangle((403,318,797,456),radius=13,fill=(124,128,138),outline=(72,77,88),width=2)
    d.rounded_rectangle((406,321,794,453),radius=11,outline=(173,178,188),width=1)
    mask=Image.new('L',(w,h),0);ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=27,fill=255)
    return cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2BGR),np.asarray(mask)

def device(im,src,kind,t,opening=False):
    mobile=kind=='mobile';h0,w0=src.shape[:2]
    sw=640 if mobile else 908;sh=sw*h0/w0
    bw=sw+(64 if mobile else 42);bh=sh+(76 if mobile else 49)
    center=(540+8*math.sin(t*1.1),807+11*math.cos(t*1.3)) if mobile else (540+5*math.sin(t),667+10*math.cos(t*1.1))
    if opening:
        q=min(1,max(0,t/1.05));ease=q*q*(3-2*q);center=(center[0],center[1]-120*(1-ease))
    yaw=(.13 if mobile else -.12)+.075*math.sin(t*1.6);pitch=.065+.04*math.cos(t*1.4)
    p=projection(center,yaw,pitch)
    rad=52 if mobile else 19
    # Soft local shadow from geometry; no changes to browser contents.
    silhouette=p(rounded(bw,bh,rad,12));shadow=np.zeros((H//4,W//4),np.uint8);cv2.fillConvexPoly(shadow,np.rint((silhouette+[14,28])/4).astype(np.int32),165)
    shadow=cv2.resize(cv2.GaussianBlur(shadow,(0,0),5),(W,H),interpolation=cv2.INTER_LINEAR);roi=im[210:1429];alpha=shadow[210:1429,:,None].astype(np.float32)/255;roi[:]=(roi*(1-.7*alpha)).astype(np.uint8)
    if not mobile:
        # Physical hinge, angled base, solid front lip. Coordinates in 3D, all edges visible.
        y=bh/2-5;rear=bw*.48;front=bw*.475
        deck3=np.array([[-rear,y,5],[rear,y,5],[front,y+145,-185],[-front,y+145,-185]])
        deck=p(deck3);bottom=p(deck3+[0,14,0]);poly(im,bottom+[0,9],(19,18,24));poly(im,[deck[3],deck[2],bottom[2],bottom[3]],(66,69,79));poly(im,[deck[1],deck[2],bottom[2],bottom[1]],(92,94,105));poly(im,deck,(142,142,154))
        k,mask=keyboard_texture();warp(im,k,deck,mask)
        stroke(im,deck[2:4],(207,207,218),2)
        # Recessed lid-opening notch, cast lip, side ports on the near edge.
        mid=(deck[2]+deck[3])/2;v=(deck[2]-deck[3])*.062;stroke(im,[mid-v+[0,4],mid+v+[0,4]],(31,32,39),4)
        stroke(im,[deck[0]+[10,3],deck[1]+[-10,3]],(31,32,40),6)
    shade_shell(im,p,bw,bh,rad,0,15 if mobile else 10)
    b,mask=bezel(round(bw),round(bh),rad,mobile);warp(im,b,p(quad(bw,bh,-.5)),mask)
    # Four-corner mapping retains 100% of actual responsive viewport. Rounded
    # hardware has a genuine black bezel, never a corner mask on the web pixels.
    q=p(quad(sw,sh,-1));warp(im,src,q);stroke(im,q,(4,6,10),1,True)
    if mobile:
        # Side buttons on physical frame, not over the browser.
        for yy,ln in ((-bh*.28,63),(-bh*.11,94),(bh*.15,83)):
            side=-1 if yy<0 else 1
            a=p([(side*bw/2,yy,4),(side*bw/2,yy+ln,4)]);stroke(im,a,(146,148,161),4)
    return q
