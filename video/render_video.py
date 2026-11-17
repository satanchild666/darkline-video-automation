#!/usr/bin/env python3
"""Darkline motion-video renderer. Offline after plan+optional image are supplied.
Renders original animated text + website-grounded content, no stock footage or music.
"""
import argparse
import io
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from urllib.parse import urlparse
from urllib.request import Request, urlopen

COL_BG = (9, 13, 25)
COL_ACCENT = (78, 218, 232)
COL_PURPLE = (129, 98, 219)
COL_WHITE = (242, 247, 255)
COL_MUTED = (183, 200, 217)
FONT_REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def font(size, bold=False):
    path = FONT_BOLD if bold else FONT_REG
    if not os.path.exists(path):
        from PIL import __file__ as pilfile
        path = str(Path(pilfile).parent / 'fonts' / 'DejaVuSans.ttf')
    return ImageFont.truetype(path, size)


def wrap_lines(draw, text, f, max_width, max_lines):
    words = str(text).split()
    lines = []
    line = ''
    for word in words:
        candidate = word if not line else line + ' ' + word
        if draw.textbbox((0,0), candidate, font=f)[2] <= max_width:
            line = candidate
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textbbox((0,0), last + '…', font=f)[2] > max_width: last = last[:-1]
        lines[-1] = last + '…'
    return lines


def load_bg(image_url, size):
    if not image_url: return None
    p = urlparse(image_url)
    if p.scheme != 'https' or p.netloc != 'darkline-ai-growth.marksz0430.workers.dev' or not p.path.startswith('/media/'):
        raise ValueError('Rejecting image from unexpected host')
    with urlopen(Request(image_url, headers={'User-Agent':'DarklineVideo/1'}), timeout=20) as resp:
        b = resp.read(5_000_001)
        if len(b) > 5_000_000: raise ValueError('Source image too large')
    im = Image.open(io.BytesIO(b)).convert('RGB')
    w, h = size
    iw, ih = im.size
    sc = max(w/iw,h/ih)
    im = im.resize((int(iw*sc+1),int(ih*sc+1)),Image.Resampling.LANCZOS)
    return im.crop(((im.width-w)//2,(im.height-h)//2,(im.width+w)//2,(im.height+h)//2))


def background(size, seed, photo):
    w,h = size
    # Original abstract artwork; no external copyrighted footage or music.
    base = Image.new('RGB',size)
    pix=base.load()
    for y in range(h):
        for x in range(w):
            v=y/max(1,h)
            glow=math.exp(-(((x/w-0.70+0.12*seed)/0.45)**2+((v-0.28)/0.35)**2)*3.0)
            pix[x,y]=(int(8+19*v+13*glow),int(14+20*v+10*glow),int(30+23*v+36*glow))
    if photo:
        # Use daily AI artwork only as blurred background texture; preserve readable overlaid text.
        ph=photo.filter(ImageFilter.GaussianBlur(radius=max(12,w//24)))
        base=Image.blend(base, ph, 0.26)
    return base.convert('RGBA')


def render_scene(scene, idx, plan, path, size, photo):
    w,h = size
    im=background(size,idx,photo)
    d=ImageDraw.Draw(im,'RGBA')
    pad=int(w*.082)
    # Visual elements change with each scene.
    for j in range(7):
        y=int(h*(.15 + j*.105))
        d.line([(pad,y), (w-pad,y)], fill=(145,189,235,8), width=1)
    for j in range(4):
        yy=int(h*(.2+j*.17))
        xx=int(w*(.70+0.035*math.sin(j+idx)))
        d.ellipse([xx,yy,xx+int(w*.09),yy+int(w*.09)], outline=(80,214,230,35),width=max(1,w//360))
    d.rounded_rectangle((pad,int(h*.12),w-pad,int(h*.78)),radius=int(w*.04),fill=(8,12,25,178),outline=(120,185,209,72),width=max(1,w//450))
    d.rounded_rectangle((pad+int(w*.038),int(h*.165),pad+int(w*.24),int(h*.174)),radius=4,fill=(*COL_ACCENT,230))
    d.text((pad+int(w*.04),int(h*.205)),f'0{idx+1}  /  04',font=font(int(w*.034), True),fill=(*COL_MUTED,240))
    fy=int(h*.305)
    heading=scene['heading']
    heading_font=font(int(w*.067), True)
    heading_lines=wrap_lines(d,heading,heading_font,w-2*pad-int(w*.10),4)
    for line in heading_lines:
        d.text((pad+int(w*.04),fy),line,font=heading_font,fill=(*COL_WHITE,255),stroke_width=0)
        fy+=int(w*.100)
    fy+=int(h*.035)
    detail_font=font(int(w*.037))
    detail_lines=wrap_lines(d,scene['detail'],detail_font,w-2*pad-int(w*.10),4)
    for line in detail_lines:
        d.text((pad+int(w*.04),fy),line,font=detail_font,fill=(*COL_MUTED,255))
        fy+=int(w*.062)
    # bottom brand stripe and constant site address
    d.rounded_rectangle((pad,int(h*.830),w-pad,int(h*.895)),radius=int(w*.020),fill=(11,29,48,215),outline=(88,170,202,60))
    d.text((pad+int(w*.025),int(h*.843)),'DARKLINE STUDIO',font=font(int(w*.040),True),fill=(*COL_WHITE,255))
    d.text((pad,int(h*.936)),'darkline-studio.web.app',font=font(int(w*.027)),fill=(*COL_MUTED,255))
    d.rectangle((0,h-int(h*.013), int((idx+1)*w/4),h), fill=(*COL_ACCENT,255))
    im.convert('RGB').save(path,quality=93)


def make_audio(path, duration):
    rate=22050
    n=int(duration*rate)
    data=np.zeros(n,dtype=np.float32)
    # Original, quiet synthesised ambient tones (no third-party music).
    tones=[110.0,138.59,164.81,220.0]
    for i, hz in enumerate(tones):
        start=i*duration/4; end=(i+1)*duration/4
        s=int(start*rate); e=min(n,int(end*rate))
        t=np.arange(e-s,dtype=np.float32)/rate
        fade=np.minimum(1,np.minimum(t*1.8,(t.max()-t)*2.0)).clip(0,1)
        data[s:e]+=0.035*fade*(np.sin(2*np.pi*hz*t)+0.25*np.sin(2*np.pi*hz*2*t))
    data=(np.clip(data,-.9,.9)*32767).astype('<i2')
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate);f.writeframes(data.tobytes())


def run(cmd):
    subprocess.run(cmd,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=240)


def render(plan,output,size=(720,1280),seconds=4.5,fps=24):
    if len(plan.get('scenes',[]))!=4: raise ValueError('Four scenes are required')
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    if not __import__('shutil').which('ffmpeg'): raise RuntimeError('ffmpeg binary missing')
    photo=load_bg(plan.get('imageUrl'),size)
    with tempfile.TemporaryDirectory(prefix='darkline-video-') as td:
        tmp=Path(td); segments=[]
        for i,scene in enumerate(plan['scenes']):
            still=tmp/f'card-{i}.png'; mp4=tmp/f'clip-{i}.mp4'
            render_scene(scene,i,plan,still,size,photo)
            # Subtle Ken Burns motion on each independently generated promotional card.
            w,h=size
            frames=round(seconds*fps)
            vf=(f"scale={int(w*1.12)}:{int(h*1.12)},"
                f"zoompan=z='min(zoom+0.0007,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={fps},"
                f"fade=t=in:st=0:d=0.33,fade=t=out:st={max(.1,seconds-.38)}:d=0.38,format=yuv420p")
            run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
                 '-loop','1','-i',str(still),'-vf',vf,'-t',str(seconds),'-an',
                 '-c:v','libx264','-preset','veryfast','-crf','24','-pix_fmt','yuv420p',str(mp4)])
            segments.append(mp4)
        playlist=tmp/'files.txt'
        playlist.write_text(''.join(f"file '{x.as_posix()}'\n" for x in segments))
        joined=tmp/'joined.mp4'
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(playlist),'-c','copy',str(joined)])
        duration=seconds*4
        sound=tmp/'audio.wav';make_audio(sound,duration)
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(joined),'-i',str(sound),
             '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','96k',
             '-movflags','+faststart','-shortest',str(output)])
    return output


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--plan',required=True)
    ap.add_argument('--output',required=True)
    ap.add_argument('--width',type=int,default=720)
    ap.add_argument('--height',type=int,default=1280)
    ap.add_argument('--seconds',type=float,default=4.5)
    a=ap.parse_args()
    result=render(json.loads(Path(a.plan).read_text(encoding='utf8')),a.output,(a.width,a.height),a.seconds)
    print(f'VIDEO_RENDER_OK {result} {result.stat().st_size} bytes')
