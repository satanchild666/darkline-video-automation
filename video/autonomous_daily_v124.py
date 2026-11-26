"""V12.4 daily orchestration; one candidate, one free speech call, at most one publish mutation.
Review runs never create a public release. Production is explicitly feature-gated.
"""
import argparse,datetime,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler,urlopen
from urllib.error import HTTPError
from zoneinfo import ZoneInfo
import video_dedup as dedup
import daily_catalogue_v124 as cat
import focused_renderer_v124 as render
import heygen_free_voice_v11 as voice
BASE="https://darkline-ai-growth.marksz0430.workers.dev"
REPO="satanchild666/darkline-video-automation"
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def call(path,body,auth=True):
    if path not in ("/video-v124-state","/video-v124-topic","/video-v124-reserve","/video-v124-queue"):raise RuntimeError("Unknown endpoint")
    token=os.getenv("DARKLINE_TEST_TOKEN","")
    if auth and len(token)<32:raise RuntimeError("Missing token")
    headers={"Content-Type":"application/json","Accept":"application/json","User-Agent":"DarklineStudioVideoAutomation/1.0 (GitHub Actions)"}
    if auth:headers["x-darkline-video-token"]=token
    req=Request(BASE+path,data=json.dumps(body,ensure_ascii=False).encode(),headers=headers,method="POST")
    try:
        with build_opener(NoRedirect()).open(req,timeout=90) as r:
            raw=r.read(16385)
            if len(raw)>16384:raise RuntimeError("Response too large")
            return r.status,json.loads(raw)
    except HTTPError as e:
        try:return e.code,json.loads(e.read(16384))
        except ValueError:return e.code,{}
def gh(*args):return subprocess.check_output(["gh",*args],stderr=subprocess.PIPE,timeout=120)
def history():
    pages=json.loads(gh("api","--paginate","--slurp",f"repos/{REPO}/releases?per_page=100"))
    if not isinstance(pages,list) or any(not isinstance(x,list) for x in pages):raise RuntimeError("History incomplete")
    tags=[r["tag_name"] for page in pages for r in page if re.fullmatch(r"darkline-(?:video|v12)-\d{4}-\d{2}-\d{2}",r.get("tag_name",""))]
    if len(tags)>dedup.MAX_HISTORY or len(tags)!=len(set(tags)):raise RuntimeError("History invalid")
    result=[]
    with tempfile.TemporaryDirectory() as tmp:
        for tag in tags:
            d=Path(tmp)/tag;d.mkdir()
            gh("release","download",tag,"--repo",REPO,"--pattern","fingerprint.json","--dir",str(d))
            result.append((tag,dedup.validate(json.loads((d/"fingerprint.json").read_text()))))
    return result
def choose(hist,day,check):
    # Different starting topic each date. Skip known repeat narration BEFORE voice generation.
    candidates=list(cat.TOPICS);offset=day.toordinal()%len(candidates)
    for topic in candidates[offset:]+candidates[:offset]:
        script=dedup.script_text(cat.plan(topic))
        if any(dedup.script_similarity(script,r["script"])>=.80 for _,r in hist):
            print("V124_SKIP_SCRIPT",topic.key,flush=True);continue
        status,r=check(topic)
        if status==422 and r.get("status")=="V124_TOPIC_DUPLICATE":
            print("V124_SKIP_CAPTION",topic.key,flush=True);continue
        if status!=200 or r.get("status")!="V124_TOPIC_AVAILABLE" or r.get("sideEffects") is not False:
            raise RuntimeError("Topic preflight unavailable; stop, no generation")
        return topic
    return None
def main(review):
    if os.environ.get("GITHUB_REPOSITORY")!=REPO:raise RuntimeError("Wrong repository")
    cat.validate_catalogue()
    now=datetime.datetime.now(ZoneInfo("Europe/Budapest"));date=now.date().isoformat()
    due=now.replace(hour=16,minute=0,second=0,microsecond=0).isoformat()
    status,_=call("/video-v124-state",{},False)
    if status!=403:raise RuntimeError("Unauthenticated endpoint not blocked")
    status,state=call("/video-v124-state",{"date":date})
    if status!=200 or state.get("status")!="V124_STATE_OK":raise RuntimeError("State unavailable")
    print("V124_LIVE_STATE",json.dumps(state),flush=True)
    if not review:
        if not state.get("dailyEnabled"):raise RuntimeError("Daily publishing disabled")
        if state.get("publication") or state.get("generation"):print("V124_SKIP_ALREADY_ATTEMPTED",flush=True);return
        if now.hour>=15:print("V124_SKIP_LATE",flush=True);return
    # No fallback or repeat call after the free authorization expires.
    if datetime.datetime.now(datetime.timezone.utc)>=voice.FREE_UNTIL:
        print("V124_SKIP_FREE_VOICE_EXPIRED",flush=True);return
    voice.authorize()
    hist=history()
    if not review and any(t=="darkline-v12-"+date for t,_ in hist):raise RuntimeError("Existing release; inspect instead of re-upload")
    topic=choose(hist,now.date(),lambda t:call("/video-v124-topic",{"topic":t.key,"caption":t.text}))
    if topic is None:print("V124_SKIP_NO_FRESH_TOPIC",flush=True);return
    print("V124_TOPIC_SELECTED",topic.key,flush=True)
    if not review:
        status,r=call("/video-v124-reserve",{"date":date,"topic":topic.key})
        if status!=200 or r.get("status")!="V124_RESERVED":raise RuntimeError("Daily attempt reservation refused")
    out=Path("private-preview-v124")/topic.key
    movie,q,fp=render.generate(topic,out)
    try:
        dedup.check(fp,hist);q["dedup"]="PASS"
    except ValueError as e:
        q["dedup"]="REJECT";q["reasons"].append("duplicate_video");q["review_gate"]="REJECT"
        print("V124_VIDEO_DUPLICATE",str(e),flush=True)
    (out/"quality.json").write_text(json.dumps(q,ensure_ascii=False,indent=2))
    render.bundle(out)
    if q["review_gate"]!="PASS" or q["reasons"] or q["dedup"]!="PASS":raise RuntimeError("Technical or history gate rejected")
    tag="darkline-v12-"+date;name=tag+".mp4";sha=dedup.sha256(movie)
    body={"version":"V12","date":date,"dueAt":due,"topic":topic.key,"sha256":sha,
          "videoUrl":f"https://github.com/{REPO}/releases/download/{tag}/{name}",
          "caption":topic.text,"quality":{k:q[k] for k in ("review_gate","reasons","seconds","width","height","fps","speech_seconds","audio_peak","overlay_dom_checks","dedup","decode","mascot","readability","min_projected_text_px","focal_scenes")},"dryRun":True}
    if review:
        # Current day may already contain V12.3. The real topic/Buffer check and
        # real video gate are tested without asking to book that occupied slot.
        print("V124_REVIEW_READY",json.dumps({"topic":topic.key,"sha256":sha,"quality":body["quality"]},ensure_ascii=False),flush=True)
        return
    status,r=call("/video-v124-queue",body)
    if status!=200 or r.get("status")!="DRY_RUN_OK" or r.get("sideEffects") is not False:raise RuntimeError("Queue preflight failed; no release")
    with tempfile.TemporaryDirectory() as d:
        target=Path(d)/name;target.write_bytes(movie.read_bytes())
        dedup.save(Path(d)/"fingerprint.json",fp)
        gh("release","create",tag,str(target),str(Path(d)/"fingerprint.json"),"--repo",REPO,"--title","Darkline Studio – automatikus reklámvideó "+date,"--notes","Nyilvános weboldalból, ellenőrzött automatikus reklámvideó.")
        with urlopen(Request(body["videoUrl"],headers={"User-Agent":"DarklineStudioVideoAutomation/1.0"}),timeout=90) as f:raw=f.read(30_000_001)
        if hashlib.sha256(raw).hexdigest()!=sha:raise RuntimeError("Transfer digest mismatch")
    body["dryRun"]=False
    status,r=call("/video-v124-queue",body)
    if status!=200 or r.get("status") not in ("SCHEDULED","ALREADY_SCHEDULED") or not r.get("postId"):
        print("V124_QUEUE_UNCONFIRMED",status,json.dumps(r),flush=True);raise RuntimeError("Do not automatically retry")
    print("V124_BUFFER_SCHEDULED",json.dumps(r),flush=True)
def selftest():
    render.selftest()
    day=datetime.date(2026,11,27)
    calls=[]
    def fake(t):
        calls.append(t.key)
        if len(calls)==1:return 422,{"status":"V124_TOPIC_DUPLICATE"}
        return 200,{"status":"V124_TOPIC_AVAILABLE","sideEffects":False}
    assert choose([],day,fake).key==calls[-1] and len(calls)==2
    assert choose([],day,lambda t:(422,{"status":"V124_TOPIC_DUPLICATE"})) is None
    try:choose([],day,lambda t:(503,{}))
    except RuntimeError:pass
    else:raise AssertionError("Uncertain discovery accepted")
    h=[("mock",{"script":dedup.script_text(cat.plan(t))}) for t in cat.TOPICS]
    assert choose(h,day,lambda t:(_ for _ in ()).throw(AssertionError("Duplicate sent to Buffer"))) is None
    print("V124_DAILY_SELFTEST_OK rotation, narration dedup, topic fallback, failure stop",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--selftest",action="store_true");p.add_argument("--review",action="store_true");a=p.parse_args()
    if a.selftest:selftest()
    else:main(a.review)
