"""V12.8.3 adaptive private catalogue -> full viewport -> approved V1273 device compositor.
No API credentials, TTS, queue, upload or deployment entrypoints.
"""
import argparse, datetime as dt, hashlib, json, math, subprocess
from pathlib import Path
import demo_topics_v1266 as catalogue
import selection_v1266 as selection
import flagship_review_v114 as public
import demo_renderer_v1266 as demo
import cinematic_capture_v1280 as capture_engine
import cinematic_render_v1273 as approved
import cinematic_render_v1271 as prior
import mascot_rig_v121 as rig
import cv2,numpy as np
from PIL import Image,ImageDraw

DEVICES=tuple(prior.DEVICES)
def require(ok,msg):
    if not ok: raise ValueError(msg)
def topic(key):
    return next(t for t in catalogue.TOPICS if t.key==key)
from adaptive_context_v1283 import plan,header
def verify_capture(p,folder):
    report=json.loads((folder/'report.json').read_text());require(len(report)==10,'capture count')
    for s,r in zip(p['scenes'],report):
        for k in ('key','selector','device','viewport'):require(s[k]==r[k],f"scene {s['scene']} mismatch: {k}")
        require(r.get('crop') is False and r.get('publication') is False,'unsafe capture')
        require(r.get('readability',{}).get('pass') is True,'readability evidence missing')
        for suffix in ('.mp4','.before.png','.after.png'):require((folder/f"scene-{s['scene']:02d}{suffix}").is_file(),'missing capture')
    return report

def timing_edges(p,timing,total):
    scenes=timing['scenes'];require(len(scenes)==10,'timing count')
    end=0
    for i,(s,r) in enumerate(zip(p['scenes'],scenes)):
        require(r['text']==s['text'] and r['scene']==i,'voice/script mismatch')
        require(end<=r['start']<r['end']<=total/30+.01,'invalid timing');end=r['end']
    edges=[0]+[round((a['end']+b['start'])*15) for a,b in zip(scenes,scenes[1:])]+[total]
    require(all(b>a for a,b in zip(edges,edges[1:])),'invalid edges');return edges

def render(p,folder,timing_path,source,out):
    # source is a trusted existing private video with matching timed robot/caption strip.
    # Requires an explicit provenance manifest binding all source bytes to this exact plan.
    verify_capture(p,folder);timing=json.loads(timing_path.read_text()); manifest=json.loads(source.with_suffix('.provenance.json').read_text())
    require(manifest=={'topic':p['topic'],'plan_sha256':digest_json(p),'video_sha256':sha(source),'timing_sha256':sha(timing_path)},'source provenance mismatch')
    cap=cv2.VideoCapture(str(source));total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));require(900<=total<=3600 and cap.get(cv2.CAP_PROP_FPS)==30 and cap.get(cv2.CAP_PROP_FRAME_WIDTH)==1080 and cap.get(cv2.CAP_PROP_FRAME_HEIGHT)==1920,'source format')
    edges=timing_edges(p,timing,total);lap=approved.Laptop();bg=prior.bg(); count=0; audit=[]
    tmp=out.with_name(out.stem+'.partial.mp4');require(not out.exists() and not tmp.exists(),'output exists')
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-','-i',str(source),'-map','0:v','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','17','-threads','3','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(tmp)],stdin=subprocess.PIPE)
    try:
        for s,(start,end) in zip(p['scenes'],zip(edges,edges[1:])):
            clips,info=prior.segment(folder/f"scene-{s['scene']:02d}.mp4");base=header(bg,s); require(info['viewport']==s['viewport'],'viewport mismatch')
            for n in range(start,end):
                ok,old=cap.read();require(ok,'source exhausted');local=(n-start)/30;idx=round((n-start)/max(1,end-start-1)*(len(clips)-1));t=local+s['scene']*.5
                if s['device']=='desktop':im,_,q=approved.compose(base,lap,clips[idx],t,s['scene']==0)
                else:im=base.copy();q=prior.device(im,clips[idx],'mobile',t,s['scene']==0)
                require(np.isfinite(q).all() and q[:,0].min()>=0 and q[:,0].max()<1080 and q[:,1].min()>=0 and q[:,1].max()<1429,'screen out of bounds')
                im[1429:]=old[1429:];proc.stdin.write(im.tobytes());count+=1
            audit.append(info)
        proc.stdin.close();require(proc.wait()==0 and count==total,'encoding failure');subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(tmp),'-f','null','-'],check=True);require(audio_hash(tmp)==audio_hash(source),'audio changed');tmp.rename(out)
    finally:
        cap.release()
        if proc.poll() is None:proc.kill();proc.wait()
        if tmp.exists():tmp.unlink()
    return {'topic':p['topic'],'frames':count,'capture':audit,'publication':False,'production_ready':False}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest_json(p):return hashlib.sha256(json.dumps(p,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def audio_hash(p):return subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-']).decode().strip()
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('topic');a.add_argument('--capture',type=Path);a.add_argument('--timing',type=Path);a.add_argument('--source',type=Path);a.add_argument('--out',type=Path);x=a.parse_args();p=plan(x.topic)
    if x.source:
        require(x.capture and x.timing and x.out,'missing render arguments');print(json.dumps(render(p,x.capture,x.timing,x.source,x.out),ensure_ascii=False))
    elif x.capture:capture_engine.main(x.capture,[(s['key'],s['selector'],s['device']) for s in p['scenes']])
    else:print(json.dumps(p,ensure_ascii=False,indent=2))
