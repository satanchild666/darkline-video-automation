"""Reusable approved V11.5 two-arm mascot rig; no network or credentials."""
import argparse, bisect, json, math, subprocess, hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
W,H,FPS=1080,1920,30
F='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; B='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(n,b=False):return ImageFont.truetype(B if b else F,n)
INK='#100d19'; VIOLET='#b89cff'; WHITE='#f4edff'; MUTED='#b8a8cc'

def rgb(c):return tuple(int(c[i:i+2],16) for i in (1,3,5))
def rounded_gradient(size,r,top,bottom,outline=None):
    w,h=size; a=np.linspace(rgb(top),rgb(bottom),h).astype(np.uint8); im=Image.fromarray(np.repeat(a[:,None,:],w,axis=1),'RGB').convert('RGBA'); mask=Image.new('L',size);ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=r,fill=255);im.putalpha(mask)
    if outline:ImageDraw.Draw(im).rounded_rectangle((1,1,w-2,h-2),r,outline=outline,width=2)
    return im

def paste(im,part,x,y): im.paste(part,(round(x),round(y)),part if part.mode=='RGBA' else None)
# The rig is deliberately two-armed, with a separate display face and articulated joints.
HEAD=rounded_gradient((182,141),47,'#504763','#181625','#9f83c9')
d=ImageDraw.Draw(HEAD);d.rounded_rectangle((10,8,171,131),40,outline='#77649b',width=2);d.rounded_rectangle((17,18,165,120),32,fill='#0b0c18',outline='#514369',width=2);d.arc((26,22,154,110),195,320,fill='#312a4a',width=2)
BODY=rounded_gradient((126,102),36,'#494057','#181722','#8e72bb');d=ImageDraw.Draw(BODY);d.rounded_rectangle((10,8,115,88),28,outline='#5e4e78',width=2);d.rounded_rectangle((24,24,101,72),18,fill='#151326',outline='#7861a3',width=2);d.text((62,49),'DS',font=font(25,True),fill='#d8c5ff',anchor='mm');d.line((42,83,84,83),fill='#ae8bf3',width=3)
JOINT=rounded_gradient((31,31),15,'#5d4b82','#241d37','#c3a4ff');HAND=rounded_gradient((31,39),13,'#746093','#362b4b','#af91dd')

def mascot(t,energy=0.0,speaking=True,scene=0,local=0.0,scale=1.0):
    im=Image.new('RGBA',(344,320));d=ImageDraw.Draw(im);bob=round(4*math.sin(t*2.35));head_y=24+bob;body_y=168+bob
    # Glow pool and hovering shadow, leaving the transparent boundary intact.
    shadow=Image.new('RGBA',im.size);sd=ImageDraw.Draw(shadow);sd.ellipse((82,276,258,304),fill=(141,83,255,95));shadow=shadow.filter(ImageFilter.GaussianBlur(12));im.alpha_composite(shadow);d=ImageDraw.Draw(im)
    d.ellipse((114,282,230,300),outline='#8f6bc7',width=2);d.ellipse((137,286,207,296),fill='#513474')
    # Arms behind body; right hand points upward during selected phrases, waves on opening/closing.
    for side in (-1,1):
        sx=172+side*60;sy=193+bob;ex=172+side*87;ey=217+bob
        if side==1:
            if scene in (0,19): ey=174+bob;hx=301+8*math.sin(t*5);hy=133+8*math.cos(t*5)
            else: hx=282+8*math.sin(local*2.1);hy=168-35*(.5+.5*math.sin(local*1.7))+bob
        else: hx=68+5*math.sin(t*1.6);hy=248+5*math.cos(t*1.9)+bob
        for a,b in [((sx,sy),(ex,ey)),((ex,ey),(hx,hy))]:
            d.line([a,b],fill='#211b30',width=25);d.line([a,b],fill='#665582',width=17);d.line([(a[0]-2,a[1]-2),(b[0]-2,b[1]-2)],fill='#9582b4',width=3)
        paste(im,JOINT,ex-15,ey-15);paste(im,HAND,hx-15,hy-19)
        d=ImageDraw.Draw(im)
        # Two small finger divisions, no extra arms.
        if side==1 and scene in (0,19):
            d.line((hx-7,hy-10,hx-7,hy+3),fill='#a68cc8',width=2);d.line((hx,hy-11,hx,hy+3),fill='#a68cc8',width=2)
    paste(im,BODY,109,body_y);d=ImageDraw.Draw(im);d.rounded_rectangle((151,154+bob,193,176+bob),10,fill='#4b405e',outline='#9672c9',width=2)
    # antenna and ear modules
    d.line((172,head_y+2,172,head_y-12),fill='#b99df5',width=4);d.ellipse((166,head_y-19,178,head_y-7),fill='#e2ceff')
    for x in (70,257):d.rounded_rectangle((x,head_y+44,x+17,head_y+96),8,fill='#30263e',outline='#9d83c6',width=2);d.line((x+8,head_y+54,x+8,head_y+84),fill='#bba0ff',width=3)
    paste(im,HEAD,81,head_y);d=ImageDraw.Draw(im)
    blink=(t%4.7)>4.53; ey=round(head_y+56+2*math.sin(t*1.6))
    for x in (133,211):
        if blink:d.rounded_rectangle((x-16,ey,x+16,ey+3),2,fill='#c5a6ff')
        else:
            d.rounded_rectangle((x-17,ey-12,x+17,ey+11),9,fill='#493372');d.rounded_rectangle((x-13,ey-9,x+13,ey+8),7,fill='#b692ff');d.rounded_rectangle((x-9,ey-7,x+5,ey-2),3,fill='#f6eaff')
    my=head_y+94; openness=round(3+17*energy) if speaking else 2
    if openness<=4:d.arc((157,my-5,187,my+7),12,168,fill='#ddc6ff',width=3)
    else:
        d.rounded_rectangle((156,my-openness//2,188,my+openness//2),max(2,openness//2),fill='#6e4ca6',outline='#d9bfff',width=2);d.line((162,my-openness//2+3,182,my-openness//2+3),fill='#ecdfff',width=2)
    d.ellipse((116,head_y+82,124,head_y+87),fill='#6d4ca6');d.ellipse((220,head_y+82,228,head_y+87),fill='#6d4ca6')
    if scale!=1:im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
    return im

def wrap(d,s,f,maxw):
    lines=[];line=''
    for word in s.split():
        candidate=(line+' '+word).strip()
        if line and d.textlength(candidate,font=f)>maxw:lines.append(line);line=word
        else:line=candidate
    if line:lines.append(line)
    return lines

