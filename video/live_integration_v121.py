"""Live read-only V12.1 integration test; never creates a Buffer post or public release."""
import json,os,sys,subprocess,datetime,tempfile,re
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError
from zoneinfo import ZoneInfo
import video_dedup as dedup
BASE="https://darkline-ai-growth.marksz0430.workers.dev"
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def call(path,body,auth=True):
    if path not in ("/video-v121-preflight","/video-v121-dry-run"):raise ValueError("Invalid endpoint")
    token=os.getenv("DARKLINE_TEST_TOKEN","")
    if auth and len(token)<32:raise RuntimeError("Missing video token")
    h={"Content-Type":"application/json","Accept":"application/json","User-Agent":"DarklineStudioVideoAutomation/1.0 (GitHub Actions)"}
    if auth:h["x-darkline-video-token"]=token
    try:
        with build_opener(NoRedirect()).open(Request(BASE+path,data=json.dumps(body).encode(),headers=h,method="POST"),timeout=60) as response:
            data=response.read(16385)
            if len(data)>16384:raise RuntimeError("Response too large")
            return response.status,json.loads(data)
    except HTTPError as e:
        data=e.read(16384)
        try:obj=json.loads(data)
        except ValueError:obj={}
        return e.code,obj
def preflight():
    status,_=call("/video-v121-preflight",{},False)
    assert status==403,"Unauthenticated request did not fail"
    status,r=call("/video-v121-preflight",{})
    assert status==200 and r.get("status")=="V121_BUFFER_PREFLIGHT_OK" and r.get("channel")=="Darkline Studio" and r.get("sideEffects") is False and r.get("videoAutoPublish") is False,(status,r)
    print("V121_LIVE_PREFLIGHT",json.dumps(r),flush=True)
    status,r=call("/video-v121-dry-run",{})
    assert status==422 and r.get("status")=="V121_BLOCKED" and r.get("sideEffects") is False,(status,r)
    print("V121_LIVE_INVALID_BLOCKED",flush=True)
def history(out):
    repo=os.environ["GITHUB_REPOSITORY"]
    pages=json.loads(subprocess.check_output(["gh","api","--paginate","--slurp",f"repos/{repo}/releases?per_page=100"]))
    if not isinstance(pages,list) or any(not isinstance(p,list) for p in pages):raise RuntimeError("Release history incomplete")
    tags=[r["tag_name"] for page in pages for r in page if re.fullmatch(r"darkline-(?:video|v12)-\d{4}-\d{2}-\d{2}",r.get("tag_name",""))]
    if len(tags)>dedup.MAX_HISTORY or len(tags)!=len(set(tags)):raise RuntimeError("Release inventory invalid")
    records=[]
    with tempfile.TemporaryDirectory() as d:
        for tag in tags:
            dest=Path(d)/tag;dest.mkdir()
            subprocess.run(["gh","release","download",tag,"--repo",repo,"--pattern","fingerprint.json","--dir",str(dest)],check=True,capture_output=True)
            records.append((tag,dedup.validate(json.loads((dest/"fingerprint.json").read_text()))))
        dedup.check(json.loads((out/"fingerprint.json").read_text()),records)
    return len(records)
def candidate(key):
    out=Path("private-preview-v121")/key
    q=json.loads((out/"quality.json").read_text())
    count=history(out)
    print("V121_HISTORY_OK",count,flush=True)
    # The actual candidate is intentionally not published. Readability is still owner-review pending.
    q["dedup"]="PASS";q["historyCount"]=count
    now=datetime.datetime.now(ZoneInfo("Europe/Budapest"));date=now.date().isoformat()
    due=now.replace(hour=16,minute=0,second=0,microsecond=0).isoformat()
    body={"version":"V12","date":date,"dueAt":due,"sha256":dedup.sha256(out/"daily.mp4"),
      "videoUrl":f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/releases/download/darkline-v12-{date}/darkline-v12-{date}.mp4",
      "caption":"Ismerd meg a Darkline Studio üzleti weboldalát! Animált bemutató, AI-narráció. https://darkline-studio.web.app/",
      "quality":{k:q[k] for k in ("review_gate","reasons","seconds","width","height","fps","speech_seconds","audio_peak","overlay_dom_checks","dedup","decode","mascot","readability")}}
    status,r=call("/video-v121-dry-run",body)
    assert status==422 and r.get("status")=="V121_BLOCKED" and "quality" in r.get("detail","").lower(),(status,r)
    print("V121_REAL_CANDIDATE_BLOCKED_PENDING_READABILITY",json.dumps(r),flush=True)
if __name__=="__main__":
    if sys.argv[1]=="preflight":preflight()
    elif sys.argv[1]=="candidate":candidate(sys.argv[2])
    else:raise SystemExit("Invalid mode")
