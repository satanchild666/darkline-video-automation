"""V12.6.3 integration candidate. Not active on main.
The morning image uses the new scoped Worker route; the afternoon video reuses
the exact approved V124 renderer and existing Buffer publication gate.
Do not enable until the live Worker patch, rate/model billing and tests are verified.
"""
import datetime as dt
import os,json,argparse
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
from zoneinfo import ZoneInfo
import heygen_budget_v126 as budget
from heygen_budget_adapter_v126 import install
from daily_slots_v126 import plan

REPO="satanchild666/darkline-video-automation"
BASE="https://darkline-ai-growth.marksz0430.workers.dev"
TZ=ZoneInfo("Europe/Budapest")
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*a,**kw):return None
def worker(path,body,token):
    if path not in ("/video-v124-state","/posts-v126-morning"):raise RuntimeError("unapproved Worker route")
    req=Request(BASE+path,data=json.dumps(body).encode(),headers={"Content-Type":"application/json","x-darkline-video-token":token,"User-Agent":"DarklineStudioVideoAutomation/1.0 (GitHub Actions)"},method="POST")
    try:
        with build_opener(NoRedirect()).open(req,timeout=100) as r:
            raw=r.read(16385)
            if len(raw)>16384:raise RuntimeError("oversized response")
            return r.status,json.loads(raw)
    except HTTPError as e:return e.code,{}
def price_authorized(now,env):
    # A finite validity period deliberately fails closed if pricing becomes stale.
    try:
        checked=dt.date.fromisoformat(env["DARKLINE_HEYGEN_PRICE_CHECKED_UTC"])
        today=now.astimezone(dt.timezone.utc).date()
        return env.get("DARKLINE_HEYGEN_RATE_CEILING")=="15" and 0<=(today-checked).days<=31
    except (KeyError,ValueError):return False
def live_authorized(env):
    return env.get("GITHUB_REPOSITORY")==REPO and env.get("GITHUB_REF")=="refs/heads/main" and env.get("DARKLINE_V126_LIVE_ENABLED")=="true"
def get_slot(now):
    a,b=plan(now.astimezone(TZ).date())
    local=now.astimezone(TZ)
    # The current Worker morning route accepts 09:00–09:29. Afternoon renderer has a 15:00 deadline.
    if local.hour==9 and local.minute<30:return a
    if b.generate_at<=local<b.due_at-dt.timedelta(hours=1):return b
    return None

def preflight(now,token,call=worker):
    day=now.astimezone(TZ).date().isoformat()
    status,r=call("/video-v124-state",{"date":day},token)
    if status!=200 or r.get("status")!="V124_STATE_OK" or r.get("sideEffects") is not False:raise RuntimeError("live video state unavailable")
    return {"date":day,"dailyEnabled":r.get("dailyEnabled"),"generation":r.get("generation"),"publication":r.get("publication"),"sideEffects":False}

def run_live(now,env):
    if not live_authorized(env):raise RuntimeError("live mode not authorized")
    slot=get_slot(now)
    if slot is None:return "SKIP_OUTSIDE_WINDOW"
    token=env.get("DARKLINE_TEST_TOKEN","")
    gh=env.get("GH_TOKEN","")
    if len(token)<32 or not gh:raise RuntimeError("missing auth")
    if slot.number==1:
        status,r=worker("/posts-v126-morning",{"date":slot.due_at.date().isoformat(),"dryRun":True},token)
        if status!=200 or r.get("status")!="V126_MORNING_PREFLIGHT_OK" or r.get("sideEffects") is not False or r.get("enabled") is not True:raise RuntimeError("morning route unavailable")
        if r.get("slotState"):return "SKIP_MORNING_OCCUPIED"
        # Separate immutable post claim, no voice cost. No resend on uncertain result.
        key="post-ledger/"+slot.key+".json"
        if not budget._github_create(REPO,"darkline-voice-budget-ledger",gh,key,{"date":slot.due_at.date().isoformat(),"slot":1,"kind":"image","reserved_micro_usd":0}):raise RuntimeError("post claim refused")
        status,r=worker("/posts-v126-morning",{"date":slot.due_at.date().isoformat(),"dryRun":False},token)
        if status!=200 or r.get("status") not in ("V126_MORNING_SCHEDULED","V126_MORNING_EXISTING"):raise RuntimeError("morning outcome uncertain; inspect Buffer, no retries")
        return r["status"]
    state=preflight(now,token)
    if state["publication"] or state["generation"]:return "SKIP_VIDEO_OCCUPIED"
    if state["dailyEnabled"] is not True:raise RuntimeError("video gate disabled")
    paid=env.get("DARKLINE_HEYGEN_PAID_ENABLED")=="true"
    verified=price_authorized(now,env)
    budget.plan("preflight",2,now,paid,verified)
    import autonomous_daily_v124 as daily
    import heygen_free_voice_v11 as voice
    def claim(key,record):return budget.github_claim(REPO,"darkline-voice-budget-ledger",gh,key,record)
    # The existing daily orchestration has a free-only cutoff. The guarded
    # adapter is now the sole authority. Restore in finally, never globally.
    cutoff=voice.FREE_UNTIL
    try:
        with install(voice,2,claim,lambda:dt.datetime.now(dt.timezone.utc),paid,verified):
            voice.FREE_UNTIL=dt.datetime.max.replace(tzinfo=dt.timezone.utc)
            daily.main(False)
    finally:voice.FREE_UNTIL=cutoff
    return "VIDEO_FLOW_RETURNED_CHECK_STATE"

def selftest():
    utc=dt.timezone.utc
    d=dt.datetime(2026,12,1,8,17,tzinfo=utc)
    assert get_slot(d).number==1
    assert get_slot(d+dt.timedelta(minutes=20)) is None
    assert get_slot(dt.datetime(2026,7,1,11,17,tzinfo=utc)).number==2
    assert get_slot(dt.datetime(2026,7,1,13,17,tzinfo=utc)) is None
    e={"DARKLINE_HEYGEN_PRICE_CHECKED_UTC":"2026-11-26","DARKLINE_HEYGEN_RATE_CEILING":"15"}
    assert price_authorized(d,e) and not price_authorized(d+dt.timedelta(days=40),e)
    assert not price_authorized(d,{**e,"DARKLINE_HEYGEN_RATE_CEILING":"16"})
    assert not live_authorized({"GITHUB_REPOSITORY":REPO,"GITHUB_REF":"refs/heads/main"})
    calls=[]
    def mock(path,body,token):
        calls.append((path,body));return 200,{"status":"V124_STATE_OK","sideEffects":False,"dailyEnabled":True,"publication":"scheduled","generation":None}
    assert preflight(d,"mock",mock)["publication"]=="scheduled"
    assert calls==[("/video-v124-state",{"date":"2026-12-01"})]
    print("V1263_INTEGRATION_POLICY_PASS window, DST, rate expiry, live switch, read-only state")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--selftest",action="store_true")
    p.add_argument("--preflight",action="store_true")
    p.add_argument("--execute",action="store_true")
    a=p.parse_args()
    now=dt.datetime.now(dt.timezone.utc)
    if a.selftest:selftest()
    elif a.preflight:
        token=os.getenv("DARKLINE_TEST_TOKEN","")
        if len(token)<32:raise RuntimeError("missing auth")
        print("V1263_LIVE_VIDEO_STATE",json.dumps(preflight(now,token)),flush=True)
    elif a.execute:print(run_live(now,os.environ),flush=True)
    else:p.error("choose explicit mode")
