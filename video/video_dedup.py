"""Pre-release video duplicate screening; no network operations."""
import hashlib, json, math, re, subprocess, unicodedata
from pathlib import Path
from difflib import SequenceMatcher

VERSION=1
SAMPLES=12
SIDE=32
MAX_HISTORY=2000

def normalize(text):
    s=unicodedata.normalize("NFKD",str(text).casefold())
    s="".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+",re.sub(r"https?://\S+"," ",s)))

def script_text(plan):
    scenes=plan.get("scenes",[])
    if not isinstance(scenes,list) or not scenes:
        raise ValueError("Missing storyboard")
    result=normalize(" ".join(str(s.get(k,"")) for s in scenes for k in ("heading","detail")))
    if len(result)<30: raise ValueError("Storyboard too short")
    return result

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def run(args):
    return subprocess.run(args,check=True,capture_output=True,timeout=60).stdout

def frame_signatures(path):
    duration=float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)]))
    if not math.isfinite(duration) or not 1<=duration<=180: raise ValueError("Unexpected video duration")
    result=[]
    for i in range(SAMPLES):
        t=duration*(i+.5)/SAMPLES
        raw=run(["ffmpeg","-v","error","-ss",f"{t:.4f}","-i",str(path),"-frames:v","1","-vf",f"scale={SIDE}:{SIDE}:flags=area","-pix_fmt","rgb24","-f","rawvideo","-threads","1","pipe:1"])
        if len(raw)!=SIDE*SIDE*3: raise ValueError("Incomplete frame")
        result.append(raw.hex())
    return result

def fingerprint(path,plan):
    return {"version":VERSION,"sha256":sha256(path),"script":script_text(plan),"frames":frame_signatures(path)}

def validate(record):
    if not isinstance(record,dict) or record.get("version")!=VERSION: raise ValueError("Unknown fingerprint format")
    if not re.fullmatch(r"[0-9a-f]{64}",record.get("sha256","")): raise ValueError("Invalid file hash")
    if not isinstance(record.get("script"),str) or len(record["script"])<30: raise ValueError("Missing storyboard history")
    frames=record.get("frames")
    if not isinstance(frames,list) or len(frames)!=SAMPLES: raise ValueError("Missing frame history")
    if any(not isinstance(f,str) or len(f)!=SIDE*SIDE*6 or not re.fullmatch(r"[0-9a-f]+",f) for f in frames): raise ValueError("Invalid frame history")
    return record

def script_similarity(a,b):
    if a==b:return 1.0
    x,y=set(a.split()),set(b.split())
    return max(len(x&y)/max(1,len(x|y)),SequenceMatcher(None,a,b,autojunk=False).ratio())

def frame_distance(a,b):
    x,y=bytes.fromhex(a),bytes.fromhex(b)
    return sum(abs(u-v) for u,v in zip(x,y))/(len(x)*255)

def compare(a,b):
    validate(a);validate(b)
    if a["sha256"]==b["sha256"]: return "identical file"
    if script_similarity(a["script"],b["script"])>=.80: return "same or near-identical storyboard"
    matrix=[[frame_distance(x,y) for y in b["frames"]] for x in a["frames"]]
    forward=[min(row) for row in matrix]
    backward=[min(row[j] for row in matrix) for j in range(SAMPLES)]
    if sum(d<=.035 for d in forward)>=10 and sum(d<=.035 for d in backward)>=10: return "near-identical visual sequence"
    return None

def check(candidate,history):
    validate(candidate)
    if len(history)>MAX_HISTORY: raise ValueError("History exceeds safe limit")
    for tag,old in history:
        reason=compare(candidate,old)
        if reason: raise ValueError(f"VIDEO_DUPLICATE: {tag}: {reason}")

def save(path,record):
    validate(record)
    Path(path).write_text(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
