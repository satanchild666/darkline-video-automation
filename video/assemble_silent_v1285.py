"""Full-length silent review with original approved two-arm mascot and catalogue captions.
Existing matching private audio uses finalize_v1284 separately. No audio synthesis.
"""
import argparse,json,subprocess,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
import integration_v1285 as engine
import mascot_rig_v121 as rig
def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def silent(topic,folder,out):
    p=engine.plan(topic);receipts=[];frames=0
    for i,s in enumerate(p['scenes']):
        path=folder/f'scene-{i:02d}.mp4';a=json.loads(path.with_suffix('.json').read_text())
        require(a['topic']==topic and a['scene']==i and all(a[k]==s[k] for k in ('key','selector','text')),'scene mismatch')
        require(a['video_sha256']==engine.engine.sha(path) and a['fresh_browser'] is True and a['publication'] is False and a['voice_calls']==0,'unsafe scene')
        require(not a['evidence']['crop'] and a['evidence']['viewport_coverage']==1 and a['attempts'][-1]['passed'],'capture gate')
        require(not s['action_required'] or a['evidence']['state_changed'] is True,'action gate')
        receipts.append(a);frames+=a['frames']
    require(900<=frames<=3600,'duration outside full ad range')
    tmp=out.with_name(out.stem+'.partial.mp4');require(not tmp.exists() and not out.exists(),'existing file')
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','18','-threads','3','-pix_fmt','yuv420p','-movflags','+faststart',str(tmp)],stdin=subprocess.PIPE)
    count=0
    try:
        for i,(s,a) in enumerate(zip(p['scenes'],receipts)):
            cap=cv2.VideoCapture(str(folder/f'scene-{i:02d}.mp4'))
            try:
                require(tuple(round(cap.get(k)) for k in (cv2.CAP_PROP_FRAME_WIDTH,cv2.CAP_PROP_FRAME_HEIGHT,cv2.CAP_PROP_FPS,cv2.CAP_PROP_FRAME_COUNT))==(1080,1920,30,a['frames']),'video geometry')
                # Same approved mascot rig, quiet mouth when no matching existing narration.
                lower=Image.new('RGB',(1080,491),'#171122');d=ImageDraw.Draw(lower)
                d.text((325,16),'HANG NÉLKÜLI PRÓBA',font=rig.font(25,True),fill='#c3a3ff')
                for fs in range(42,27,-1):
                    f=rig.font(fs,True);lines=rig.wrap(d,s['text'],f,720)
                    if len(lines)<=4 and all(d.textlength(l,font=f)<=720 for l in lines):break
                else:raise RuntimeError('caption overflow')
                for j,l in enumerate(lines):d.text((325,65+j*(fs+10)),l,font=f,fill='#f4edff')
                d.text((325,316),'darkline-studio.web.app',font=rig.font(30,True),fill='#c3a3ff')
                for n in range(a['frames']):
                    ok,frame=cap.read();require(ok,'missing frame')
                    im=lower.copy();rig.paste(im,rig.mascot(count/30,0.,False,19 if i==9 else i,n/30,scale=.88),8,21)
                    frame[1429:]=cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2BGR)
                    proc.stdin.write(frame.tobytes());count+=1
                require(not cap.read()[0],'extra frame')
            finally:cap.release()
        proc.stdin.close();require(proc.wait()==0 and count==frames,'encode failed')
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(tmp),'-f','null','-'],check=True);tmp.rename(out)
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        if tmp.exists():tmp.unlink()
    report=dict(topic=topic,frames=count,duration_seconds=count/30,fresh_scenes=10,action_scenes=sum(bool(a['evidence'].get('state_changed')) for a in receipts),voice_calls=0,narration=False,publication=False,production_ready=False,output_sha256=engine.engine.sha(out),receipts=receipts)
    out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('V1285_FULL_PASS',topic,count,report['action_scenes'],flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('topic');a.add_argument('folder',type=Path);a.add_argument('out',type=Path);x=a.parse_args();silent(x.topic,x.folder,x.out)
