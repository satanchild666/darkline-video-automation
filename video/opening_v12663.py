"""Animated real-demo header; isolated from UI, mascot and synchronized captions."""
from PIL import Image,ImageDraw,ImageFont
from functools import lru_cache

@lru_cache(maxsize=32)
def font(size):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',size)

def opening_header(title,bg,accent,frame):
    im=Image.new('RGB',(1080,215),bg);d=ImageDraw.Draw(im)
    f=font(63);lines=[];line=''
    for word in title.split():
        nxt=(line+' '+word).strip()
        if line and d.textlength(nxt,font=f)>1000:lines.append(line);line=word
        else:line=nxt
    if line:lines.append(line)
    if not lines or len(lines)>2 or any(d.textlength(x,font=f)>1000 for x in lines):raise RuntimeError('Opening title overflow')
    t=max(0,min(1,frame/30));ease=t*t*(3-2*t)
    y=5+round((1-ease)*(100 if len(lines)==1 else 28))
    title_bottom=0
    for i,line in enumerate(lines):
        at=(40,y+i*75)
        box=d.textbbox(at,line,font=f)
        if box[0]<0 or box[2]>1080 or box[3]>215:raise RuntimeError('Opening text outside safe header')
        title_bottom=max(title_bottom,box[3])
        d.text(at,line,font=f,fill='#f4edff')
    delay=9 if len(lines)==1 else 14
    t2=max(0,min(1,(frame-delay)/(30-delay)));e2=t2*t2*(3-2*t2)
    if t2>0:
        text='VALÓDI DEMÓ  /  MINTAADATOK';sf=font(30)
        x=40+round((1-e2)*385);at=(x,169 if len(lines)==1 else 178)
        box=d.textbbox(at,text,font=sf)
        if box[2]>1080 or box[3]>215 or box[1]<title_bottom+3:raise RuntimeError('Opening subtitle overlap')
        d.text(at,text,font=sf,fill=accent)
    return im

def selftest(topics,meta,palettes):
    import numpy as np
    from PIL import Image
    checked=0
    for topic in topics:
        bg,accent,_,_=palettes[meta[topic.key]['family']]
        frames=[opening_header(topic.scenes[0][0],bg,accent,n) for n in range(31)]
        assert all(im.size==(1080,215) for im in frames)
        assert frames[0].tobytes()!=frames[30].tobytes()
        assert opening_header(topic.scenes[0][0],bg,accent,90).tobytes()==frames[30].tobytes()
        checked+=1
    print('V12663_OPENING_LAYOUT_PASS',checked,'topics; safe text geometry; actual title entrance')
