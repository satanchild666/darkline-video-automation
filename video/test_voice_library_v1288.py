"""Offline regression: no private voice files or paid API usage."""
import datetime as dt,tempfile
from pathlib import Path
from zoneinfo import ZoneInfo
import narration_library_v1288 as lib
import voice_review_v1288 as review
def reject(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('unsafe voice accepted')
def main():
    review.engine.selftest()
    assert len(review.engine.engine.catalogue.TOPICS)==51
    assert {k for k,e in lib.ENTRIES.items() if e.mode=='catalogue'}=={'web_services'}
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)
        for key in lib.ENTRIES:
            reject(lambda:lib.resolve(root,key,review.expected(key)['scenes']))
        for key in ('auto_booking','menu_categories','salon_services','crm_board'):
            reject(lambda:lib.resolve(root,key,review.expected(key)['scenes']))
        p=root/'web_services';p.mkdir();(p/'source.mp4').write_bytes(b'wrong voice');(p/'timing.json').write_text('{}')
        reject(lambda:lib.resolve(root,'web_services',review.expected('web_services')['scenes']))
        day=dt.date(2026,11,27);now=dt.datetime.combine(day,dt.time(13,17),ZoneInfo('Europe/Budapest'))
        avail={k:{'status_code':200,'body':{'status':'V124_TOPIC_AVAILABLE','sideEffects':False}} for k in review.daily.sel.FAMILY}
        result=review.daily_decision(root,day,now,[],[],avail,True)
        assert not result['verified_voice_topics'] and result['slot_decision']=='IMAGE_BEFORE_MUTATION' and not result['publication']
    print('V1288_LIBRARY_PASS 3 pinned sources, exact-script only, missing/tampered file blocked, legacy excluded from daily, no calls')
if __name__=='__main__':main()
