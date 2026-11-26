"""V12.2 first real upload: exact owner-approved V12.1 MP4, no speech calls.
A short-lived, authenticated, per-artifact key is retrieved from the Worker.
No private archive, key, or narration source is published.
"""
import base64,datetime,hashlib,io,json,os,re,struct,subprocess,tempfile,zipfile
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler,urlopen
from urllib.error import HTTPError
from zoneinfo import ZoneInfo
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import video_dedup as dedup
from content_selection_v123 import select_for_approved,choose_next_topic,StopSafely
BASE="https://darkline-ai-growth.marksz0430.workers.dev"
ARTIFACT=15101815043
SHA="85b98f5df6cb08eef1fb66fd0eba3b9e318189bd203728aef3fb8b37946db579"
ARCHIVE_SHA="97ca5342f2285508a3d70601a29547245e1363fc29d02030754236065645dc1f"
CAPTION="Mit lát egy érdeklődő, amikor először megnyitja a vállalkozásod weboldalát? A bemutatóban a szolgáltatásokat, a referenciákat és a mobilos ügyfélnézetet járjuk körbe. A saját kezelőfelülettel a tartalmak frissítése is egyszerűbb lehet. Nézd meg működés közben a Darkline Studio üzleti weboldal demóját: https://darkline-studio.web.app/ \n\nAnimált kabala, AI-narráció. #DarklineStudio #Weboldalkészítés"
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def call(path,body,auth=True):
    if path not in ("/video-v122-approved-source","/video-v122-queue","/video-v123-topic-check"):raise RuntimeError("Unexpected endpoint")
    token=os.getenv("DARKLINE_TEST_TOKEN","")
    if auth and len(token)<32:raise RuntimeError("Missing authentication")
    headers={"Content-Type":"application/json","Accept":"application/json","User-Agent":"DarklineStudioVideoAutomation/1.0 (GitHub Actions)"}
    if auth:headers["x-darkline-video-token"]=token
    try:
        with build_opener(NoRedirect()).open(Request(BASE+path,data=json.dumps(body).encode(),headers=headers,method="POST"),timeout=90) as r:
            raw=r.read(16385)
            if len(raw)>16384:raise RuntimeError("Response too large")
            return r.status,json.loads(raw)
    except HTTPError as e:
        try:r=json.loads(e.read(16384))
        except ValueError:r={}
        return e.code,r
def gh(*args):
    return subprocess.check_output(["gh",*args],stderr=subprocess.PIPE,timeout=120)
def release_history(repo,date):
    pages=json.loads(gh("api","--paginate","--slurp",f"repos/{repo}/releases?per_page=100"))
    if not isinstance(pages,list) or any(not isinstance(x,list) for x in pages):raise RuntimeError("Release history incomplete")
    tags=[r["tag_name"] for page in pages for r in page if re.fullmatch(r"darkline-(?:video|v12)-\d{4}-\d{2}-\d{2}",r.get("tag_name",""))]
    if len(tags)>dedup.MAX_HISTORY or len(tags)!=len(set(tags)):raise RuntimeError("Invalid release inventory")
    if "darkline-v12-"+date in tags:raise RuntimeError("Today already has a V12 release; inspect rather than retry")
    result=[]
    with tempfile.TemporaryDirectory() as tmp:
        for tag in tags:
            d=Path(tmp)/tag;d.mkdir()
            gh("release","download",tag,"--repo",repo,"--pattern","fingerprint.json","--dir",str(d))
            result.append((tag,dedup.validate(json.loads((d/"fingerprint.json").read_text()))))
    return result
def main():
    repo=os.environ["GITHUB_REPOSITORY"]
    assert repo=="satanchild666/darkline-video-automation"
    now=datetime.datetime.now(ZoneInfo("Europe/Budapest"))
    date=now.date().isoformat()
    if date!="2026-11-26" or now.hour>=15:raise RuntimeError("Approved first test window expired")
    due=now.replace(hour=16,minute=0,second=0,microsecond=0).isoformat()
    status,_=call("/video-v122-approved-source",{"artifact":ARTIFACT},False)
    if status!=403:raise RuntimeError("Unauthenticated access not blocked")
    status,permit=call("/video-v122-approved-source",{"artifact":ARTIFACT})
    if status!=200 or permit.get("artifact")!=ARTIFACT or permit.get("sha256")!=SHA or permit.get("artifactSha256")!=ARCHIVE_SHA:raise RuntimeError("Approved source unavailable")
    key=base64.b64decode(permit.pop("key"),validate=True)
    if len(key)!=32:raise RuntimeError("Invalid single-artifact key")
    # Mask the one-artifact key even though no subsequent logs include it.
    print("::add-mask::"+base64.b64encode(key).decode(),flush=True)
    raw=gh("api",f"repos/{repo}/actions/artifacts/{ARTIFACT}/zip")
    if hashlib.sha256(raw).hexdigest()!=ARCHIVE_SHA:raise RuntimeError("Artifact digest mismatch")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:data=z.read("Darkline_V121_web.dlenc")
    if data[:7]!=b"DLV111\x00":raise RuntimeError("Invalid encrypted package")
    n=struct.unpack(">H",data[7:9])[0];end=9+n+12
    plain=AESGCM(key).decrypt(data[9+n:end],data[end:],data[:end]);del key,data,raw
    with zipfile.ZipFile(io.BytesIO(plain)) as z:
        video=z.read("daily.mp4");q=json.loads(z.read("quality.json"));fp=dedup.validate(json.loads(z.read("fingerprint.json")))
    del plain
    if hashlib.sha256(video).hexdigest()!=SHA or fp["sha256"]!=SHA or q.get("review_gate")!="PASS" or q.get("reasons")!=[]:raise RuntimeError("Approved video integrity/quality mismatch")
    hist=release_history(repo,date);dedup.check(fp,hist)
    q["dedup"]="PASS";q["readability"]="PASS" # Exact SHA only, explicit owner rating 5/5.
    print("V123_APPROVED_INTEGRITY_OK",SHA,"history",len(hist),flush=True)
    tag="darkline-v12-"+date;name=tag+".mp4"
    body={"artifact":ARTIFACT,"version":"V12","date":date,"dueAt":due,"sha256":SHA,
          "videoUrl":f"https://github.com/{repo}/releases/download/{tag}/{name}",
          "caption":CAPTION,"quality":{k:q[k] for k in ("review_gate","reasons","seconds","width","height","fps","speech_seconds","audio_peak","overlay_dom_checks","dedup","decode","mascot","readability")},"dryRun":True}
    def check_angle(c):
        return call("/video-v122-queue",{**body,"caption":c.text})
    chosen,r=select_for_approved("web",check_angle)
    if chosen is None:
        fallback=choose_next_topic({"web"},lambda c:call("/video-v123-topic-check",{"topic":c.topic,"caption":c.text}))
        if fallback is None:
            print("V123_NO_FRESH_TOPIC",flush=True)
        else:
            # The alternate requires its OWN movie, never reuse the web MP4 under another label.
            Path("v123-next-topic.json").write_text(json.dumps({"topic":fallback.topic,"angle":fallback.angle,"caption":fallback.text},ensure_ascii=False))
            print("V123_TOPIC_SWITCH",fallback.topic,fallback.angle,"private render required",flush=True)
        return
    body["caption"]=chosen.text
    print("V123_LIVE_DRY_RUN_OK",chosen.angle,json.dumps(r),flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/name;path.write_bytes(video);del video
        subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(path),"-f","null","-"],check=True,timeout=90)
        dedup.save(Path(tmp)/"fingerprint.json",fp)
        # Public transfer is ONLY the specifically approved MP4 and duplicate fingerprint.
        gh("release","create",tag,str(path),str(Path(tmp)/"fingerprint.json"),"--repo",repo,"--title","Darkline Studio – jóváhagyott üzleti weboldal videó","--notes","Jóváhagyott reklámvideó automatikus közzétételhez.")
        request=Request(body["videoUrl"],headers={"User-Agent":"DarklineStudioVideoAutomation/1.0"})
        with urlopen(request,timeout=90) as f:
            downloaded=f.read(20_000_001)
        if hashlib.sha256(downloaded).hexdigest()!=SHA:raise RuntimeError("Public transfer digest mismatch")
    print("V123_PUBLIC_VIDEO_VERIFIED",body["videoUrl"],flush=True)
    body["dryRun"]=False
    status,r=call("/video-v122-queue",body)
    if status!=200 or r.get("status") not in ("SCHEDULED","ALREADY_SCHEDULED") or not r.get("postId"):
        print("V123_QUEUE_BLOCKED",status,json.dumps(r,ensure_ascii=False),flush=True);raise RuntimeError("Buffer outcome not confirmed; do not retry automatically")
    print("V123_BUFFER_SCHEDULED",json.dumps(r),flush=True)
if __name__=="__main__":main()
