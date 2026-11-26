"""V12.6 conservative monthly voice budget, review-only until explicit activation.
No paid network calls here. Reserve each UTC date/slot once BEFORE any TTS call.
Use a dedicated persistent GitHub ledger branch; create-only PUT is the atomic claim.
Only the caller winning HTTP 201 may submit exactly one request. Never retry ambiguity.
"""
import datetime as dt
import json, hashlib, re
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

MODEL = "heygen-voice-1-turbo"
FREE_MODEL = "heygen-voice-1-turbo-free"
FREE_UNTIL = dt.datetime(2026,12,1,tzinfo=dt.timezone.utc)
MAX_BYTES = 1000
# Reserve at $15/M chars even though the current Turbo published rate is $4/M.
# Integer microdollars, conservative UTF-8 byte upper bound for text characters.
RESERVE_PER_SLOT = 15000
MONTHLY_LIMIT = 1000000
MAX_SLOTS_PER_DAY = 2
assert 31 * MAX_SLOTS_PER_DAY * RESERVE_PER_SLOT <= MONTHLY_LIMIT

class BudgetBlocked(RuntimeError): pass
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def plan(text,slot,now,paid_enabled=False,price_verified=False):
    if now.tzinfo is None: raise BudgetBlocked("timezone required")
    utc=now.astimezone(dt.timezone.utc)
    if type(slot) is not int or slot not in (1,2): raise BudgetBlocked("invalid slot")
    if not isinstance(text,str) or not text.strip(): raise BudgetBlocked("empty text")
    n=len(text.encode("utf-8"))
    if n>MAX_BYTES: raise BudgetBlocked("text exceeds byte ceiling")
    free=utc<FREE_UNTIL
    if not free and not (paid_enabled is True and price_verified is True):
        raise BudgetBlocked("paid mode not explicitly enabled or price not verified")
    return {"date":utc.date().isoformat(),"month":utc.strftime("%Y-%m"),"slot":slot,
            "model":FREE_MODEL if free else MODEL,"bytes":n,
            "reserved_micro_usd":RESERVE_PER_SLOT,
            "text_sha256":hashlib.sha256(text.encode("utf-8")).hexdigest()}
def reserve(claim,plan_data):
    # Revalidate structural fields rather than trusting a mutable caller payload.
    d=dt.date.fromisoformat(plan_data["date"])
    s=plan_data["slot"]
    if type(s) is not int or s not in (1,2) or plan_data["month"]!=d.strftime("%Y-%m"):
        raise BudgetBlocked("invalid claim")
    if plan_data["reserved_micro_usd"]!=RESERVE_PER_SLOT or not 1<=plan_data["bytes"]<=MAX_BYTES:
        raise BudgetBlocked("invalid reservation")
    key=f"voice-ledger/{d.isoformat()}-{s}.json"
    if claim(key,plan_data) is not True: raise BudgetBlocked("duplicate or uncertain reservation")
    return key

def _github_create(repo,branch,token,key,record):
    # The Contents API PUT without a SHA is create-only. Never retry a conflict
    # or an ambiguous network result. Only HTTP 201 authorizes the caller.
    import base64
    from urllib.parse import quote
    if repo!="satanchild666/darkline-video-automation" or not token:
        raise BudgetBlocked("ledger configuration invalid")
    body={"message":"Reserve bounded narration slot "+key.rsplit("/",1)[-1],
          "branch":branch,"content":base64.b64encode(json.dumps(record,sort_keys=True).encode()).decode()}
    req=Request(f"https://api.github.com/repos/{repo}/contents/{quote(key,safe='/')}",data=json.dumps(body).encode(),
        headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","Content-Type":"application/json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"DarklineBudget/1"},method="PUT")
    try:
        with build_opener(NoRedirect()).open(req,timeout=25) as r:return r.status==201
    except (HTTPError,URLError,TimeoutError,OSError):return False

def github_claim(repo,branch,token,key,record):
    # Production branch must never be reset or delete ledger files.
    if branch!="darkline-voice-budget-ledger" or not re.fullmatch(r"voice-ledger/\d{4}-\d{2}-\d{2}-[12]\.json",key):
        raise BudgetBlocked("production ledger configuration invalid")
    return _github_create(repo,branch,token,key,record)

def github_test_claim(repo,token,run,attempt):
    # Fixed test branch, isolated namespace and no real voice metadata.
    if not re.fullmatch(r"\d{1,20}",run) or not re.fullmatch(r"\d{1,5}",attempt):
        raise BudgetBlocked("invalid test run")
    return _github_create(repo,"darkline-voice-budget-ledger-test",token,
        f"test-ledger/{run}-{attempt}.json",{"test_only":True,"run":run,"attempt":attempt,"reserved_micro_usd":0})

def guarded_speech(text,slot,now,claim,send,paid_enabled=False,price_verified=False):
    """send is an injected, non-retrying fixed-model TTS adapter; no other model allowed."""
    p=plan(text,slot,now,paid_enabled,price_verified)
    reserve(claim,p)
    # No refund on failure, no retry, never resend on timeout.
    return send(text,p["model"])

def selftest():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Lock
    ledger={};lock=Lock();sent=[]
    def claim(key,record):
        with lock:
            if key in ledger:return False
            ledger[key]=record;return True
    def send(text,model):
        sent.append((text,model));return "mock speech"
    def blocked(fn):
        try:fn()
        except BudgetBlocked:return
        raise AssertionError("budget was not blocked")
    t=dt.datetime(2026,12,1,tzinfo=dt.timezone.utc)
    blocked(lambda:guarded_speech("teszt",1,t,claim,send))
    blocked(lambda:guarded_speech("teszt",1,t,claim,send,True,False))
    blocked(lambda:guarded_speech("á"*501,1,t,claim,send,True,True))
    blocked(lambda:guarded_speech("teszt",3,t,claim,send,True,True))
    blocked(lambda:guarded_speech("teszt",True,t,claim,send,True,True))
    assert plan("teszt",1,t-dt.timedelta(seconds=1))["model"]==FREE_MODEL
    assert plan("teszt",1,t,True,True)["model"]==MODEL
    assert not sent
    for day in range(31):
        now=t+dt.timedelta(days=day)
        for slot in (1,2):
            assert guarded_speech("x"*1000,slot,now,claim,send,True,True)=="mock speech"
            blocked(lambda:guarded_speech("changed",slot,now,claim,send,True,True))
    assert len(sent)==len(ledger)==62
    assert sum(x["reserved_micro_usd"] for x in ledger.values())==930000
    # Across two simultaneous jobs only one request can win.
    next_month=t+dt.timedelta(days=31)
    def race(_):
        try:return guarded_speech("teszt",1,next_month,claim,send,True,True)
        except BudgetBlocked:return "blocked"
    with ThreadPoolExecutor(max_workers=8) as pool:r=list(pool.map(race,range(8)))
    assert r.count("mock speech")==1 and r.count("blocked")==7
    # A transport failure must consume the reservation, no automatic retry.
    def fail(*args):raise TimeoutError("mock failure")
    try:guarded_speech("teszt",2,next_month,claim,fail,True,True)
    except TimeoutError:pass
    else:raise AssertionError("failure missing")
    blocked(lambda:guarded_speech("teszt",2,next_month,claim,send,True,True))
    blocked(lambda:guarded_speech("teszt",1,next_month+dt.timedelta(days=1),lambda *_:None,send,True,True))
    print("V126_BUDGET_SELFTEST_PASS 62 slots, 0.93 USD reserved maximum, duplicate/race/timeout/price/UTF8/expiry guards; zero real API calls")
if __name__=="__main__":selftest()
