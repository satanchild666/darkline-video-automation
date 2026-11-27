"""Private review: non-overlapping dip transitions, unchanged timing and audio."""
import argparse,json,hashlib,subprocess
from pathlib import Path
import cv2,numpy as np
cv2.setNumThreads(1)
TOP=1429
DIP=5

def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bounds(report):
    receipts=report['receipts'];require(len(receipts)==10,'ten receipts required')
    edges=[0]
    for i,r in enumerate(receipts):
        require(r['scene']==i and r['frames']>=2*DIP+2,'invalid scene');edges.append(edges[-1]+r['frames'])
    require(edges[-1]==report['frames'],'frame count mismatch');return edges
def weight(n,edges):
    for b in edges[1:-1]:
        if b-DIP<=n<b:return (b-1-n)/(DIP-1)
        if b<=n<b+DIP:return (n-b)/(DIP-1)
    return 1.
def apply(frame,n,edges):
    a=weight(n,edges)
    if a<1.:
        top=frame[:TOP];neutral=np.empty_like(top);neutral[:]=(34,17,23)
        cv2.addWeighted(top,a,neutral,1-a,0,dst=top)
    return frame
def audio_hash(p):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0?','-c:a','copy','-f','hash','-hash','sha256','-']).decode().strip()
def has_audio(p):
    return bool(subprocess.check_output(['ffprobe','-v','error','-select_streams','a','-show_entries','stream=index','-of','csv=p=0',str(p)]).strip())
def render(source,report_path,out):
    r=json.loads(report_path.read_text());require(r['output_sha256']==sha(source),'source integrity');edges=bounds(r)
    cap=cv2.VideoCapture(str(source));require(tuple(round(cap.get(k)) for k in (cv2.CAP_PROP_FRAME_WIDTH,cv2.CAP_PROP_FRAME_HEIGHT,cv2.CAP_PROP_FPS,cv2.CAP_PROP_FRAME_COUNT))==(1080,1920,30,edges[-1]),'source format')
    tmp=out.with_suffix('.partial.mp4');require(not tmp.exists() and not out.exists(),'output exists')
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-','-i',str(source),'-map','0:v','-map','1:a:0?','-c:v','libx264','-preset','ultrafast','-crf','18','-threads','2','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(tmp)],stdin=subprocess.PIPE)
    lower1=hashlib.sha256();lower2=hashlib.sha256();changed=0
    try:
        for n in range(edges[-1]):
            ok,frame=cap.read();require(ok,'missing frame')
            if weight(n,edges)<1:
                lower1.update(frame[TOP:].tobytes());apply(frame,n,edges);lower2.update(frame[TOP:].tobytes());changed+=1
            proc.stdin.write(frame.tobytes())
        require(not cap.read()[0],'extra frame');proc.stdin.close();require(proc.wait()==0 and lower1.digest()==lower2.digest(),'transition failure')
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(tmp),'-f','null','-'],check=True)
        require(has_audio(tmp)==has_audio(source),'audio stream changed')
        if has_audio(source):require(audio_hash(tmp)==audio_hash(source),'audio packets changed')
        tmp.rename(out)
    finally:
        cap.release()
        if proc.poll() is None:proc.kill();proc.wait()
        if tmp.exists():tmp.unlink()
    r.update(source_sha256=sha(source),output_sha256=sha(out),transition='dip_to_neutral_no_overlap',transition_frames_changed=changed,transition_boundaries=edges[1:-1],lower_strip_preencode_exact=True,narration=has_audio(out),voice_calls=0,publication=False,production_ready=False)
    out.with_suffix('.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print('V1286_TRANSITION_PASS',out.name,edges[-1],changed,flush=True)
def selftest():
    e=list(range(0,1100,100));a=np.full((1920,1080,3),255,np.uint8)
    assert weight(94,e)==1 and weight(99,e)==weight(100,e)==0 and weight(104,e)==1
    b=apply(a.copy(),99,e);assert np.all(b[:TOP]==(34,17,23)) and np.array_equal(a[TOP:],b[TOP:])
    assert np.array_equal(a,apply(a.copy(),50,e))
    assert sum(weight(n,e)<1 for n in range(1000))==72
    print('V1286_TRANSITION_SELFTEST_PASS nine non-overlapping transitions; no lower strip modification')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--selftest',action='store_true');a.add_argument('source',type=Path,nargs='?');a.add_argument('report',type=Path,nargs='?');a.add_argument('out',type=Path,nargs='?');x=a.parse_args()
    if x.selftest:selftest()
    else:render(x.source,x.report,x.out)
