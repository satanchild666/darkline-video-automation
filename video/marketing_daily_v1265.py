"""V12.6.5 staged integration. Never called by the existing production workflow.
No fallback if video generation, upload, or publication might already have occurred.
"""
import datetime as dt
import os,json,argparse
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
from zoneinfo import ZoneInfo
import heygen_budget_v126 as budget
import marketing_daily_v1263 as base

def fallback_window(now):
    x=now.astimezone(base.TZ)
    return x.hour==15 and x.minute<30

def fallback_decision(state,release_absent,now):
    if not fallback_window(now):return "SKIP_OUTSIDE_WINDOW"
    if not isinstance(state,dict) or state.get("status")!="V1265_FALLBACK_PREFLIGHT_OK" or state.get("sideEffects") is not False:return "BLOCK_STATE"
    if state.get("enabled") is not True:return "SKIP_DISABLED"
    if state.get("clear") is not True or any(state.get(k) is not None for k in ("video","generation","prior","image")):return "SKIP_POSSIBLE_EXISTING"
    if release_absent is not True:return "BLOCK_RELEASE"
    return "ALLOW_IMAGE"

def fallback_request(body,token):
    req=Request(base.BASE+"/posts-v1265-fallback",data=json.dumps(body).encode(),headers={"Content-Type":"application/json","x-darkline-video-token":token,"User-Agent":"DarklineStudioVideoAutomation/1.0 (GitHub Actions)"},method="POST")
    try:
        with build_opener(base.NoRedirect()).open(req,timeout=150) as r:
            raw=r.read(16385)
            if len(raw)>16384:raise RuntimeError("oversized response")
            return r.status,json.loads(raw)
    except HTTPError as e:return e.code,{}

def release_absent(day,token):
    # A GitHub 404 only after authenticating the expected public repository.
    if not token:return False
    headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","User-Agent":"DarklineBudget/1","X-GitHub-Api-Version":"2022-11-28"}
    def get(path):
        req=Request("https://api.github.com/repos/"+base.REPO+path,headers=headers)
        with build_opener(base.NoRedirect()).open(req,timeout=25) as r:return r.status,json.loads(r.read(250000))
    try:
        status,repo=get("")
        if status!=200 or repo.get("full_name")!=base.REPO or repo.get("private") is not False:return False
        for tag in ("darkline-v12-"+day,"darkline-video-"+day):
            try:
                status,_=get("/releases/tags/"+tag)
                return False
            except HTTPError as e:
                if e.code!=404:return False
        return True
    except (HTTPError,URLError,TimeoutError,OSError,ValueError):return False

def run_fallback(now,env):
    if not base.live_authorized(env):raise RuntimeError("live mode not authorized")
    if not fallback_window(now):return "SKIP_OUTSIDE_WINDOW"
    token=env.get("DARKLINE_TEST_TOKEN","");gh=env.get("GH_TOKEN","")
    if len(token)<32 or not gh:raise RuntimeError("missing auth")
    day=now.astimezone(base.TZ).date().isoformat()
    status,state=fallback_request({"date":day,"dryRun":True},token)
    if status!=200:raise RuntimeError("fallback read unavailable")
    # No release read or reservation until Worker reports a clear slot.
    decision=fallback_decision(state,True,now)
    if decision!="ALLOW_IMAGE":return decision
    if not release_absent(day,gh):return "BLOCK_RELEASE"
    if not budget._github_create(base.REPO,"darkline-voice-budget-ledger",gh,"post-ledger/"+day+"-2.json",{"date":day,"slot":2,"kind":"fallback_image","reserved_micro_usd":0}):raise RuntimeError("fallback claim refused")
    status,r=fallback_request({"date":day,"dryRun":False},token)
    if status!=200 or r.get("status") not in ("V1265_FALLBACK_SCHEDULED","V1265_FALLBACK_EXISTING"):raise RuntimeError("fallback outcome uncertain; inspect Buffer, no retries")
    return r["status"]

def current_kind(now):
    if fallback_window(now):return "fallback"
    slot=base.get_slot(now)
    return {1:"morning",2:"video"}.get(slot.number) if slot else None

def dispatch_allowed(now,kind,day):
    return kind in ("morning","video","fallback") and current_kind(now)==kind and now.astimezone(base.TZ).date().isoformat()==day

def run_extended(now,env):
    if not base.live_authorized(env):raise RuntimeError("live mode not authorized")
    kind=env.get("DARKLINE_V126_EXPECTED_SLOT")
    day=env.get("DARKLINE_V126_EXPECTED_DATE")
    if not dispatch_allowed(now,kind,day):return "SKIP_CHANGED_WINDOW"
    if kind=="fallback":return run_fallback(now,env)
    if kind=="morning":return base.run_live(now,env)
    import catalogue_v1265 as new
    import daily_catalogue_v124 as old
    saved=(old.TOPICS,old.validate_catalogue)
    try:
        old.TOPICS=new.TOPICS
        old.validate_catalogue=new.validate_catalogue
        return base.run_live(now,env)
    finally:old.TOPICS,old.validate_catalogue=saved

def selftest():
    utc=dt.timezone.utc
    d=dt.datetime(2026,12,1,14,7,tzinfo=utc)
    assert fallback_window(d) and fallback_window(dt.datetime(2027,7,1,13,7,tzinfo=utc))
    clean={"status":"V1265_FALLBACK_PREFLIGHT_OK","enabled":True,"clear":True,"video":None,"generation":None,"prior":None,"image":None,"sideEffects":False}
    assert fallback_decision(clean,True,d)=="ALLOW_IMAGE"
    assert fallback_decision(clean,False,d)=="BLOCK_RELEASE"
    assert fallback_decision(clean,None,d)=="BLOCK_RELEASE"
    for k in ("video","generation","prior","image"):
        for v in ("reserved","submitting","uncertain","scheduled"):
            assert fallback_decision({**clean,k:v},True,d)=="SKIP_POSSIBLE_EXISTING"
    assert fallback_decision({**clean,"enabled":False},True,d)=="SKIP_DISABLED"
    assert fallback_decision({**clean,"sideEffects":True},True,d)=="BLOCK_STATE"
    assert fallback_decision(clean,True,d+dt.timedelta(minutes=24))=="SKIP_OUTSIDE_WINDOW"
    try:run_fallback(d,{})
    except RuntimeError:pass
    else:raise AssertionError("unauthorized fallback accepted")
    assert dispatch_allowed(d,"fallback","2026-12-01")
    assert not dispatch_allowed(d,"video","2026-12-01")
    assert not dispatch_allowed(d,"fallback","2026-11-30")
    assert not dispatch_allowed(d,None,"2026-12-01")
    assert current_kind(dt.datetime(2026,12,1,8,17,tzinfo=utc))=="morning"
    assert current_kind(dt.datetime(2026,12,1,12,17,tzinfo=utc))=="video"
    assert run_extended(d,{"GITHUB_REPOSITORY":base.REPO,"GITHUB_REF":"refs/heads/main","DARKLINE_V126_LIVE_ENABLED":"true","DARKLINE_V126_EXPECTED_SLOT":"video","DARKLINE_V126_EXPECTED_DATE":"2026-12-01"})=="SKIP_CHANGED_WINDOW"
    print("V1265_DISPATCH_WINDOW_PASS expected slot and date, delayed video cannot become fallback")
    print("V1265_FALLBACK_POLICY_PASS no speech; no retry; reserved/uncertain/scheduled state and public release block image fallback")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--selftest",action="store_true")
    p.add_argument("--execute",action="store_true")
    a=p.parse_args()
    if a.selftest:selftest()
    elif a.execute:print(run_extended(dt.datetime.now(dt.timezone.utc),os.environ),flush=True)
    else:p.error("explicit mode required")
