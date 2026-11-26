"""Two-slot Budapest-local planner; review only, no publication calls.
First slot defaults to image, second to approved narrated video.
The existing V124 worker is single-video/day; this module does not bypass it.
"""
import datetime as dt
from zoneinfo import ZoneInfo
from dataclasses import dataclass
BUDAPEST=ZoneInfo("Europe/Budapest")
@dataclass(frozen=True)
class Slot:
    number:int
    kind:str
    generate_at:dt.datetime
    due_at:dt.datetime
    @property
    def key(self):return f"{self.due_at.date().isoformat()}-{self.number}"

def plan(day,mode="image_video"):
    if type(day) is not dt.date or mode not in ("image_video","two_videos"):
        raise ValueError("invalid daily plan")
    def local(h,m=0):return dt.datetime.combine(day,dt.time(h,m),BUDAPEST)
    return (Slot(1,"image" if mode=="image_video" else "video",local(8,0),local(10,0)),
            Slot(2,"video",local(13,0),local(16,0)))

def decision(slot,now,history,history_complete,voice_ready=True,video_slot_ready=True):
    # history is normalized by an eventual live adapter. Uncertainty means stop,
    # never create a second post or a fallback after an ambiguous mutation.
    if now.tzinfo is None or history_complete is not True:return "BLOCK_HISTORY"
    local=now.astimezone(BUDAPEST)
    if not slot.generate_at<=local<slot.due_at-dt.timedelta(minutes=30):return "SKIP_OUTSIDE_WINDOW"
    for r in history:
        if not isinstance(r,dict) or "key" not in r or "due_at" not in r:return "BLOCK_HISTORY"
        try:
            due=dt.datetime.fromisoformat(r["due_at"])
            if due.tzinfo is None:return "BLOCK_HISTORY"
        except (TypeError,ValueError):return "BLOCK_HISTORY"
        if r["key"]==slot.key or abs((due-slot.due_at).total_seconds())<1800:return "SKIP_OCCUPIED"
    if slot.kind=="video" and (voice_ready is not True or video_slot_ready is not True):return "IMAGE_BEFORE_MUTATION"
    return "PREPARE_"+slot.kind.upper()

def selftest():
    from heygen_budget_v126 import RESERVE_PER_SLOT,MONTHLY_LIMIT
    for m in (1,3,10,12):
        start=dt.date(2027,m,1)
        n=0
        while (day:=start+dt.timedelta(days=n)).month==m:
            a,b=plan(day)
            assert a.kind=="image" and b.kind=="video"
            assert a.due_at.hour==10 and b.due_at.hour==16
            assert a.key!=b.key and a.due_at<b.due_at
            assert decision(a,a.generate_at,[],True)=="PREPARE_IMAGE"
            assert decision(b,b.generate_at,[],True)=="PREPARE_VIDEO"
            assert decision(b,b.generate_at,[],True,False)=="IMAGE_BEFORE_MUTATION"
            assert decision(b,b.generate_at,[],True,True,False)=="IMAGE_BEFORE_MUTATION"
            assert decision(b,b.generate_at,[],False)=="BLOCK_HISTORY"
            assert decision(b,b.due_at,[],True)=="SKIP_OUTSIDE_WINDOW"
            assert decision(b,b.generate_at,[{"key":b.key,"due_at":b.due_at.isoformat(),"state":"unknown"}],True)=="SKIP_OCCUPIED"
            assert decision(a,a.generate_at,[{"key":"external","due_at":a.due_at.isoformat()}],True)=="SKIP_OCCUPIED"
            assert decision(b,b.generate_at,[{"key":a.key,"due_at":a.due_at.isoformat()}],True)=="PREPARE_VIDEO"
            assert all(x.kind=="video" for x in plan(day,"two_videos"))
            n+=1
        assert n*2*RESERVE_PER_SLOT<=MONTHLY_LIMIT
    assert plan(dt.date(2027,3,27))[0].due_at.utcoffset()!=plan(dt.date(2027,3,28))[0].due_at.utcoffset()
    assert plan(dt.date(2027,10,30))[1].due_at.utcoffset()!=plan(dt.date(2027,10,31))[1].due_at.utcoffset()
    print("V126_SLOT_SELFTEST_PASS 2 slots/day, Budapest DST, image fallback before mutation, history/occupancy/late guards; no publication")
if __name__=="__main__":selftest()
