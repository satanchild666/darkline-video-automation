"""Private V12.8.2 review: keep the exact approved mixed-device video, add context.
No network, voice generation, hardware redraw or publication. Archive-only proof.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
SOURCE_SHA='8e4ea321cc6875a4fa8386c90efcb4da4803755f61db9fbc0705db41cd30a230'
TIMING_SHA='4994450c07d6f286c38e2cea14c60bc79a454262ff1a81c4bb7b2407067f227d'
DEVICES=('desktop','desktop','desktop','mobile','mobile','mobile','desktop','mobile','desktop','mobile')
CONTEXT=(('Szolgáltatások és portfólió','A látogatói oldal bemutatása'),('Válogatás munkáinkból','Portfólió • Minta projektek'),('Csomag / extra','Induló ár (Ft) • Szerkeszthető minta'),('Válassz alapcsomagot',''),('Válogatás munkáinkból',''),('Csomag / extra • Induló ár',''),('Átlátható árazás','Valóban használható megoldások'),('Ajánlatkérő és árbecslő',''),('Állítsd össze a csomagodat','Alapcsomag és választható extrák'),('Beszéljük át, mire van szükséged',''))
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
REG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ensure(ok,msg):
    if not ok:raise ValueError(msg)
def fit(d,text,size,width,font=FONT):
    while size>=28:
        f=ImageFont.truetype(font,size)
        if d.textlength(text,font=f)<=width:return f
        size-=1
    raise ValueError('text too long')
def patches(s):
    title,detail=CONTEXT[s]
    a=Image.new('RGB',(174,55),'#241b35');d=ImageDraw.Draw(a);d.rounded_rectangle((0,0,173,54),radius=12,fill='#241b35',outline='#695e93',width=2);d.text((87,27),f'{s+1:02d} / 10',anchor='mm',font=ImageFont.truetype(FONT,26),fill='#e8ddff')
    ps=[(866,23,cv2.cvtColor(np.array(a),cv2.COLOR_RGB2BGR))]
    if DEVICES[s]=='desktop':
        a=Image.new('RGB',(900,138),'#1d2138');d=ImageDraw.Draw(a);d.text((20,7),title,font=fit(d,title,42,860),fill='#f1edff');d.text((20,76),detail,font=fit(d,detail,32,860,REG),fill='#b8c2e0');ps.append((90,1241,cv2.cvtColor(np.array(a),cv2.COLOR_RGB2BGR)))
    else:
        # Match the original V1271 studio gradient in the secondary heading region.
        y,x=np.ogrid[165:210,42:1042];r=np.exp(-(((x-530)/750)**2+((y-680)/900)**2));r2=np.exp(-(((x-940)/340)**2+((y-340)/500)**2));bg=np.empty((45,1000,3),np.uint8)
        for i,(base,k,k2) in enumerate(((15,28,49),(15,15,12),(24,37,35))):bg[:,:,i]=np.clip(base+k*r+k2*r2,0,255)
        a=Image.fromarray(bg);d=ImageDraw.Draw(a);label='MOBIL • '+title;d.text((0,1),label,font=fit(d,label,30,990),fill='#e8ddff');ps.append((42,165,cv2.cvtColor(np.array(a),cv2.COLOR_RGB2BGR)))
    return ps
def audio_hash(p):return subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-']).decode().strip()
def main(source,timing,out):
    ensure(sha(source)==SOURCE_SHA and sha(timing)==TIMING_SHA,'unapproved source or narration timing')
    scenes=json.loads(timing.read_text())['scenes'];ensure(len(scenes)==10,'scene count')
    cap=cv2.VideoCapture(str(source));total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));ensure(total==1118 and cap.get(cv2.CAP_PROP_FPS)==30,'source geometry')
    edges=[0]+[round((a['end']+b['start'])*15) for a,b in zip(scenes,scenes[1:])]+[total];ensure(all(b>a for a,b in zip(edges,edges[1:])),'timing order')
    tmp=out.with_name(out.stem+'.partial.mp4');ensure(not out.exists() and not tmp.exists(),'existing output')
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-','-i',str(source),'-map','0:v','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','17','-threads','4','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(tmp)],stdin=subprocess.PIPE)
    count=0;audit=[];lower1=hashlib.sha256();lower2=hashlib.sha256()
    try:
        for s,(start,end) in enumerate(zip(edges,edges[1:])):
            ps=patches(s)
            for x,y,a in ps:ensure(y+a.shape[0]<1429,'overlay intersects original mascot')
            for n in range(start,end):
                ok,im=cap.read();ensure(ok,'missing frame');lower1.update(im[1429:].tobytes())
                for x,y,a in ps:im[y:y+a.shape[0],x:x+a.shape[1]]=a
                lower2.update(im[1429:].tobytes());proc.stdin.write(im.tobytes());count+=1
            audit.append({'scene':s,'device':DEVICES[s],'frames':end-start,'context':CONTEXT[s],'patch_rectangles':[[x,y,a.shape[1],a.shape[0]] for x,y,a in ps]});print('scene',s+1,'frames',end-start,flush=True)
        proc.stdin.close();ensure(proc.wait()==0 and count==total,'encode failed');ensure(lower1.digest()==lower2.digest(),'mascot changed');subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(tmp),'-f','null','-'],check=True);ensure(audio_hash(tmp)==audio_hash(source),'audio altered');tmp.rename(out)
    finally:
        cap.release()
        if proc.poll() is None:proc.kill();proc.wait()
        if tmp.exists():tmp.unlink()
    report={'source_sha256':sha(source),'output_sha256':sha(out),'frames':count,'duration_seconds':count/30,'scenes':audit,'audio_packet_hash':audio_hash(out),'original_lower_strip_preencode_exact':True,'new_tts_calls':0,'publication':False,'fresh_browser':False,'production_ready':False}
    out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('timing',type=Path);p.add_argument('out',type=Path);a=p.parse_args();main(a.source,a.timing,a.out)
