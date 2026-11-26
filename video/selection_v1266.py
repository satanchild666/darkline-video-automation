"""History-aware topic ordering, preserving every existing hard duplicate gate."""
import datetime as dt
from collections import Counter
import demo_topics_v1266 as catalogue
import video_dedup as dedup
import daily_catalogue_v124 as original

BASE_FAMILIES={"quote":"planning","prices":"planning","portfolio":"portfolio","portal":"portal",
 "first_site":"web","owner_edit":"web","stock_workflow":"retail","service_contact":"service",
 "restaurant_needs":"menu","salon_needs":"salon","workshop_needs":"auto","project_scope":"planning",
 "budget_priorities":"planning","references_trust":"portfolio","choose_solution":"planning","client_communication":"portal"}
FAMILY={**BASE_FAMILIES,**{k:v["family"] for k,v in catalogue.META.items()}}

def script_index():
    return {dedup.script_text(original.plan(t)):t.key for t in catalogue.TOPICS}

def order(history,day):
    if not isinstance(day,dt.date):raise ValueError("Invalid date")
    idx=script_index()
    # Existing immutable history fingerprints, not guesses about published content.
    # Unknown or unrecognized old scripts do not become fabricated category labels.
    recent=sorted(history,key=lambda item:item[0],reverse=True)[:8]
    known=[FAMILY[idx[r["script"]]] for _,r in recent if r["script"] in idx]
    counts=Counter(known)
    last=known[0] if known else None
    topics=list(catalogue.TOPICS);n=len(topics);offset=day.toordinal()%n
    pos={t.key:(i-offset)%n for i,t in enumerate(topics)}
    def score(t):
        f=FAMILY.get(t.key,"other")
        # Prefer an underserved family, then deterministic date rotation.
        # A seasonal preference is only a tie-breaker, not a bypass of history.
        season=0 if day.month in (11,12) and t.key=="menu_season" else 1
        return (int(f==last),counts[f],season,pos[t.key])
    return sorted(topics,key=score)

def choose(hist,day,check):
    for topic in order(hist,day):
        script=dedup.script_text(original.plan(topic))
        if any(dedup.script_similarity(script,r["script"])>=.80 for _,r in hist):
            print("V1266_SKIP_SCRIPT",topic.key,flush=True);continue
        status,result=check(topic)
        if status==422 and result.get("status")=="V124_TOPIC_DUPLICATE":
            print("V1266_SKIP_CAPTION",topic.key,flush=True);continue
        if status!=200 or result.get("status")!="V124_TOPIC_AVAILABLE" or result.get("sideEffects") is not False:
            raise RuntimeError("Topic preflight unavailable; stop, no generation")
        print("V1266_CHOSEN",topic.key,FAMILY.get(topic.key),flush=True)
        return topic
    return None

def selftest():
    from unittest.mock import patch
    day=dt.date(2026,12,1)
    assert len(order([],day))==len(catalogue.TOPICS)
    auto=next(t for t in catalogue.NEW if t.key=="auto_booking")
    record={"script":dedup.script_text(original.plan(auto))}
    hist=[("darkline-v12-2026-11-30",record)]
    assert FAMILY[order(hist,day)[0].key]!="auto"
    assert [t.key for t in order(hist,day)]==[t.key for t in order(hist,day)]
    calls=[]
    def check(t):
        calls.append(t.key)
        return (422,{"status":"V124_TOPIC_DUPLICATE"}) if len(calls)==1 else (200,{"status":"V124_TOPIC_AVAILABLE","sideEffects":False})
    chosen=choose(hist,day,check)
    assert chosen.key==calls[-1] and len(calls)==2 and auto.key not in calls
    assert choose([],day,lambda t:(422,{"status":"V124_TOPIC_DUPLICATE"})) is None
    try:choose([],day,lambda t:(503,{}))
    except RuntimeError:pass
    else:raise AssertionError("Uncertain preflight accepted")
    print("V1266_SELECTION_PASS family rotation, season tie-break, exact-history dedup, Buffer checks, fail closed")
if __name__=="__main__":selftest()
