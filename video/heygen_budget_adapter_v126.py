"""V12.6 review integration for the approved HeyGen renderer.
This module is not installed into production by the review workflow.
The provider's actual price/rounding and account balance must be verified before activation.
"""
import datetime as dt
import os,re
from contextlib import contextmanager
import heygen_budget_v126 as budget

@contextmanager
def install(voice,slot,claim,clock,paid_enabled=False,price_verified=False):
    """Preserve the exact approved renderer, profiles, alignment and HTTP client.
    All speech from the renderer uses the budget reservation; one model, one request.
    Process-local context, no concurrent use of the patched module.
    """
    original=(voice.authorize,voice.speech,voice.MODEL)
    def authorize():
        key=os.getenv("HEYGEN_API_KEY","")
        voice_id=os.getenv("HEYGEN_VOICE_ID","")
        if not key or not re.fullmatch(r"[a-f0-9]{32}",voice_id):
            raise budget.BudgetBlocked("API key or voice ID missing")
        budget.plan("preflight",slot,clock(),paid_enabled,price_verified)
        return key,voice_id
    def speech(text,settings,path):
        authorize()
        if settings not in voice.PROFILES.values():
            raise budget.BudgetBlocked("unapproved voice settings")
        p=budget.plan(text,slot,clock(),paid_enabled,price_verified)
        budget.reserve(claim,p)
        # Recheck date and authorization after reservation; no cross-month dispatch.
        if budget.plan(text,slot,clock(),paid_enabled,price_verified)!=p:
            raise budget.BudgetBlocked("date or model changed after reservation")
        voice.MODEL=p["model"]
        return original[1](text,settings,path)
    try:
        voice.authorize=authorize
        voice.speech=speech
        voice.MODEL=budget.plan("preflight",slot,clock(),paid_enabled,price_verified)["model"]
        yield
    finally:
        voice.authorize,voice.speech,voice.MODEL=original

def selftest():
    from unittest.mock import patch
    from types import SimpleNamespace
    sent=[];ledger={}
    def claim(key,record):
        if key in ledger:return False
        ledger[key]=record;return True
    def send(text,settings,path):
        # Exercise the actual pinned adapter's request payload without networking.
        key,vid=voice.authorize()
        payload=voice.payload(vid,text,settings)
        sent.append(payload)
        return payload
    import heygen_free_voice_v11 as voice
    old=voice.MODEL
    now=dt.datetime(2026,12,1,10,tzinfo=dt.timezone.utc)
    def expect_block(fn):
        try:fn()
        except budget.BudgetBlocked:return
        raise AssertionError("guard bypass")
    with patch.dict(os.environ,{"HEYGEN_API_KEY":"MOCK_ONLY","HEYGEN_VOICE_ID":"a"*32}),patch.object(voice,"speech",send):
        with install(voice,1,claim,lambda:now,True,True):
            assert voice.speech("Magyar próba.",voice.PROFILES["natural"],None)["model"]==budget.MODEL
            expect_block(lambda:voice.speech("Második.",voice.PROFILES["natural"],None))
            expect_block(lambda:voice.speech("x"*1001,voice.PROFILES["natural"],None))
            expect_block(lambda:voice.speech("próba",{"speed":1},None))
        with install(voice,2,claim,lambda:now,True,True):
            assert voice.speech("Második poszt.",voice.PROFILES["premium"],None)["model"]==budget.MODEL
        expect_block(lambda:run_denied(voice,claim,now))
        with install(voice,1,claim,lambda:now-dt.timedelta(days=1)):
            assert voice.speech("Ingyenes.",voice.PROFILES["natural"],None)["model"]==budget.FREE_MODEL
    assert len(sent)==3 and len(ledger)==3 and voice.MODEL==old
    print("V126_ADAPTER_SELFTEST_PASS pinned payload, free/paid switch, duplicate block, approved profiles, restored adapter, no API calls")
def run_denied(voice,claim,now):
    with install(voice,1,claim,lambda:now):pass
if __name__=="__main__":selftest()
