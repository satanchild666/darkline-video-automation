"""V12.8.4 private final assembly. Receipts bind fresh frames to the authorized timed script.
No network, voice generation or publishing. Existing source lower strip and audio only.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
import cv2,numpy as np
cv2.setNumThreads(2)
def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def audio_hash(p):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-']).decode().strip()
def metadata(cap):
    return tuple(int(round(cap.get(k))) for k in (cv2.CAP_PROP_FRAME_WIDTH,cv2.CAP_PROP_FRAME_HEIGHT,cv2.CAP_PROP_FPS,cv2.CAP_PROP_FRAME_COUNT))
def main(folder,source,timing,manifest,out):
    m=json.loads(manifest.read_text());t=json.loads(timing.read_text());scenes=t['scenes']
    require(m['source_sha256']==sha(source) and m['timing_sha256']==sha(timing),'source/timing integrity')
    require(len(scenes)==len(m['scenes'])==10,'scene count')
    original=cv2.VideoCapture(str(source));w,h,fps,total=metadata(original)
    require((w,h,fps)==(1080,1920,30) and 900<=total<=3600,'source format')
    edges=[0]+[round((a['end']+b['start'])*15) for a,b in zip(scenes,scenes[1:])]+[total]
    recorded=t.get('frame_boundaries',edges)
    require(len(recorded)==11 and all(isinstance(v,int) for v in recorded) and recorded[0]==0 and recorded[-1]==total and all(abs(x-y)<=1 for x,y in zip(recorded,edges)),'recorded boundaries mismatch')
    edges=recorded
    require(all(b>a for a,b in zip(edges,edges[1:])),'timing order')
    receipts=[]
    for i,(start,end) in enumerate(zip(edges,edges[1:])):
        path=folder/f'scene-{i:02d}.mp4';receipt=json.loads(path.with_suffix('.json').read_text())
        require(scenes[i]['scene']==i and scenes[i]['text']==m['scenes'][i]['text'],'manifest script mismatch')
        require(receipt['topic']==m['topic'] and receipt['scene']==i and all(receipt[k]==m['scenes'][i][k] for k in ('key','selector','text')),'scene identity mismatch')
        require(receipt['frames']==end-start and receipt['video_sha256']==sha(path),'scene integrity')
        require(receipt['fresh_browser'] is True and receipt['voice_calls']==0 and receipt['publication'] is False,'unsafe receipt')
        evidence=receipt['evidence'];require(evidence['crop'] is False and evidence['viewport_coverage']==1.0,'viewport altered')
        require(receipt['attempts'][-1]['passed'] is True and receipt['attempts'][-1]['device']==receipt['device'] and receipt['attempts'][-1]['viewport']==receipt['viewport'],'invalid resolved view')
        if m['scenes'][i].get('action_required'):require(evidence.get('state_changed') is True,'missing action proof')
        receipts.append(receipt)
    tmp=out.with_name(out.stem+'.partial.mp4');require(not out.exists() and not tmp.exists(),'existing output')
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-','-i',str(source),'-map','0:v','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','17','-threads','3','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(tmp)],stdin=subprocess.PIPE)
    a=hashlib.sha256();b=hashlib.sha256();count=0
    try:
        for i,(start,end) in enumerate(zip(edges,edges[1:])):
            cap=cv2.VideoCapture(str(folder/f'scene-{i:02d}.mp4'))
            try:
                require(metadata(cap)==(1080,1920,30,end-start),'scene video geometry')
                for _ in range(end-start):
                    ok,frame=cap.read();ok2,old=original.read();require(ok and ok2,'missing video frame')
                    a.update(old[1429:].tobytes());frame[1429:]=old[1429:];b.update(frame[1429:].tobytes())
                    proc.stdin.write(frame.tobytes());count+=1
                require(not cap.read()[0],'unexpected extra scene frame')
            finally:cap.release()
        proc.stdin.close();require(proc.wait()==0 and count==total and a.digest()==b.digest(),'assembly failed')
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(tmp),'-f','null','-'],check=True)
        require(audio_hash(tmp)==audio_hash(source),'audio mismatch');tmp.rename(out)
    finally:
        original.release()
        if proc.poll() is None:proc.kill();proc.wait()
        if tmp.exists():tmp.unlink()
    report=dict(topic=m['topic'],frames=count,duration_seconds=count/30,audio_packet_hash=audio_hash(out),source_sha256=sha(source),output_sha256=sha(out),lower_strip_preencode_exact=True,fresh_scenes=len(receipts),receipts=receipts,voice_calls=0,publication=False,production_ready=False)
    out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));return report
if __name__=='__main__':
    a=argparse.ArgumentParser()
    for arg in ('folder','source','timing','manifest','out'):a.add_argument(arg,type=Path)
    p=a.parse_args();main(p.folder,p.source,p.timing,p.manifest,p.out)
