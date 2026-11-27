"""Dry-run daily adapter. No secrets, scheduled triggers, voice API or publishing.
All history and preflight evidence must be explicitly supplied; no default allow.
"""
import argparse,datetime as dt,json,tempfile
from pathlib import Path
from zoneinfo import ZoneInfo
import selection_v1266 as sel
import daily_slots_v126 as slots
import heygen_budget_v126 as budget
import review_v1285 as review
import transitions_v1286 as trans
BUDAPEST=ZoneInfo('Europe/Budapest')
def require(ok,msg):
    if not ok:raise ValueError(msg)
def decision(day,now,history,occupancy,preflight,complete,voice_topics):
    require(type(day) is dt.date and now.tzinfo is not None,'invalid time')
    require(complete is True and isinstance(history,list) and isinstance(occupancy,list),'incomplete history')
    require(all(isinstance(x,(list,tuple)) and len(x)==2 and isinstance(x[0],str) and isinstance(x[1],dict) and isinstance(x[1].get('script'),str) and x[1]['script'].strip() for x in history),'malformed history')
    require(isinstance(voice_topics,list) and all(t in sel.FAMILY for t in voice_topics),'invalid voice inventory')
    require(isinstance(preflight,dict),'missing preflight')
    slot=slots.plan(day)[1]
    # Match the existing production schedule, not the earlier 13:00 review draft.
    slot=slots.Slot(slot.number,slot.kind,dt.datetime.combine(day,dt.time(13,17),BUDAPEST),slot.due_at)
    state=slots.decision(slot,now,occupancy,True,True,True)
    result={'date':day.isoformat(),'slot':slot.key,'slot_decision':state,'topic':None,'publication':False,'voice_calls':0,'review_only':True,'production_ready':False}
    require(budget.RESERVE_PER_SLOT*62<=budget.MONTHLY_LIMIT,'budget guard')
    if state!='PREPARE_VIDEO':return result
    def check(t):
        # Even existing voice cannot bypass script/caption duplicate checks.
        if t.key not in preflight:raise RuntimeError('missing read-only caption preflight')
        a=preflight[t.key];require(isinstance(a,dict) and 'status_code' in a and isinstance(a.get('body'),dict),'malformed preflight')
        return a['status_code'],a['body']
    t=sel.choose(history,day,check)
    if t is None:result['slot_decision']='NO_UNIQUE_TOPIC';return result
    result.update(topic=t.key,voice_available=t.key in voice_topics,slot_decision='PREPARE_PRIVATE_REVIEW' if t.key in voice_topics else 'IMAGE_BEFORE_MUTATION',monthly_reservation_ceiling_micro_usd=budget.RESERVE_PER_SLOT*62,monthly_reservation_ceiling_usd=f'{budget.RESERVE_PER_SLOT*62/1000000:.2f}')
    return result
def full_review(topic,folder,out,source=None,timing=None,manifest=None):
    # Explicit manual review only. Never converts an image-fallback decision
    # into a production video. Both outputs are guarded, no publish entrypoint.
    require(not out.exists(),'output exists');out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        raw=Path(tmp)/'assembled.mp4'
        review.run(topic,folder,raw,source,timing,manifest,capture=True)
        trans.render(raw,raw.with_suffix('.json'),out)
def selftest():
    day=dt.date(2026,11,27);now=dt.datetime.combine(day,dt.time(13,17),BUDAPEST)
    avail={k:{'status_code':200,'body':{'status':'V124_TOPIC_AVAILABLE','sideEffects':False}} for k in sel.FAMILY}
    x=decision(day,now,[],[],avail,True,[]);assert x['slot_decision']=='IMAGE_BEFORE_MUTATION' and x['topic'] in sel.FAMILY
    assert x['monthly_reservation_ceiling_micro_usd']==930000 and x['monthly_reservation_ceiling_usd']=='0.93'
    y=decision(day,now,[],[],avail,True,[x['topic']]);assert y['slot_decision']=='PREPARE_PRIVATE_REVIEW'
    t=next(t for t in sel.catalogue.TOPICS if t.key==x['topic'])
    hist=[('prior',{'script':sel.dedup.script_text(sel.original.plan(t))})]
    assert decision(day,now,hist,[],avail,True,[])['topic']!=x['topic']
    du=dt.datetime.combine(day,dt.time(16),BUDAPEST).isoformat()
    assert decision(day,now,[],[{'key':x['slot'],'due_at':du}],avail,True,[])['slot_decision']=='SKIP_OCCUPIED'
    assert decision(day,now-dt.timedelta(minutes=1),[],[],avail,True,[])['slot_decision']=='SKIP_OUTSIDE_WINDOW'
    for f in (lambda:decision(day,now,[],[],avail,False,[]),lambda:decision(day,now,[],[],{},True,[]),lambda:decision(day,now,[],[],{k:{'status_code':503,'body':{}} for k in avail},True,[])):
        try:f()
        except (ValueError,RuntimeError):pass
        else:raise AssertionError('unsafe preflight accepted')
    print('V1286_DAILY_PASS rotation, duplicate history, slot, missing voice fallback, uncertain history/preflight rejection, budget ceiling; no API calls')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--selftest',action='store_true');a.add_argument('--topic');a.add_argument('--folder',type=Path);a.add_argument('--out',type=Path);x=a.parse_args()
    if x.selftest:selftest()
    else:
        require(x.topic and x.folder and x.out,'explicit private review required');full_review(x.topic,x.folder,x.out)
