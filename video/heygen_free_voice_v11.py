"""Darkline private HeyGen narration adapter. Free preview ONLY; no paid fallback.
No credentials, voice IDs or real audio in the repository.
"""
import os,json,math,re,subprocess,wave
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
from urllib.parse import urlparse
import numpy as np
MODEL="heygen-voice-1-turbo-free"
ENDPOINT="https://api.heygen.com/v3/models/audio/tts"
# Conservative cutoff based on the original advertised November 30 end date.
# Extend only after checking official pricing and explicit owner approval.
FREE_UNTIL=datetime(2026,12,1,tzinfo=timezone.utc)
PROFILES={
 "natural":{"speed":1.0,"pitch_variance":1.0,"expressiveness_boost":.85},
 "dynamic":{"speed":1.06,"pitch_variance":1.35,"expressiveness_boost":1.0},
 "premium":{"speed":.94,"pitch_variance":1.12,"expressiveness_boost":.75}
}
ROUTES={"auto":"dynamic","crm":"natural","web":"natural","menu":"premium","salon":"premium"}
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def profile(key,override=None):
    chosen=override or ROUTES.get(key)
    if chosen not in PROFILES:raise ValueError("Unknown voice profile")
    return chosen,dict(PROFILES[chosen])
def authorize(now=None):
    if (now or datetime.now(timezone.utc))>=FREE_UNTIL:raise RuntimeError("Free preview safety cutoff: verify pricing before extending")
    if os.getenv("DARKLINE_HEYGEN_FREE_ENABLED")!="true":raise RuntimeError("Free HeyGen generation disabled")
    key=os.getenv("HEYGEN_API_KEY","");voice=os.getenv("HEYGEN_VOICE_ID","")
    if not key or not re.fullmatch(r"[a-f0-9]{32}",voice):raise RuntimeError("HeyGen API key or private voice ID missing")
    return key,voice
def payload(voice,text,settings):
    if not 1<=len(text)<=1000:raise ValueError("Narration length outside review budget")
    return {"model":MODEL,"voice_id":voice,"text":text,"language":"hu","with_timestamps":True,**settings}
def speech(text,settings,path):
    key,voice=authorize()
    req=Request(ENDPOINT,data=json.dumps(payload(voice,text,settings),ensure_ascii=False).encode(),headers={"X-Api-Key":key,"Content-Type":"application/json","Accept":"application/json"},method="POST")
    try:
        with build_opener(NoRedirect()).open(req,timeout=90) as res:
            raw=res.read(4000001)
            if len(raw)>4000000:raise RuntimeError("Speech metadata too large")
            result=json.loads(raw)
    except HTTPError as exc:
        raise RuntimeError(f"HeyGen HTTP {exc.code}; no retry or paid fallback") from None
    except URLError:
        raise RuntimeError("HeyGen transport failed; no retry") from None
    if not isinstance(result,dict):raise RuntimeError("Invalid speech result")
    result=result.get("data",result)
    if not isinstance(result,dict):raise RuntimeError("Invalid speech metadata")
    if result.get("model") not in (None,MODEL):raise RuntimeError("Unexpected speech model")
    url=result.get("audio_url")
    if not isinstance(url,str):raise RuntimeError("Missing audio URL")
    u=urlparse(url)
    if u.scheme!="https" or not u.hostname or not (u.hostname=="heygen.ai" or u.hostname.endswith(".heygen.ai")) or u.username or u.password or u.port not in (None,443):raise RuntimeError("Unapproved audio download host")
    try:
        with build_opener(NoRedirect()).open(Request(url),timeout=60) as res:
            audio=res.read(20000001)
    except (HTTPError,URLError):
        raise RuntimeError("Audio retrieval failed; no regeneration") from None
    if not 44<=len(audio)<=20000000 or audio[:4]!=b"RIFF" or audio[8:12]!=b"WAVE":raise RuntimeError("Expected bounded WAV")
    Path(path).write_bytes(audio)
    return result
def timing(phrases,result,duration):
    """Use returned character timestamps only; do not invent alignment."""
    text=" ".join(phrases)
    chars=result.get("original_characters")
    if not isinstance(chars,list) or "".join(str(c.get("text","")) for c in chars)!=text:
        raise RuntimeError("Exact character alignment missing; manual review")
    for c in chars:
        if len(c["text"])!=1:raise RuntimeError("Unexpected character grouping")
        a,b=float(c["start_time"]),float(c["end_time"])
        if not math.isfinite(a+b) or not 0<=a<=b<=duration+.03:raise RuntimeError("Invalid timestamp")
    records=[];pos=0
    for i,phrase in enumerate(phrases):
        subset=chars[pos:pos+len(phrase)]
        start=float(subset[0]["start_time"]);end=min(duration,float(subset[-1]["end_time"]))
        if start>=end or (records and start<records[-1]["end"]-.005):raise RuntimeError("Overlapping phrase timings")
        records.append({"scene":i,"start":start,"end":end,"text":phrase,"tempo":1.0})
        pos+=len(phrase)+1
    return records
def scene_durations(records,duration,fps=30):
    if len(records)!=5:raise RuntimeError("Expected five visual scenes")
    total_frames=max(21*fps,math.ceil((duration+.6)*fps))
    if total_frames>35*fps:raise RuntimeError("Narration too long for review")
    edges=[0]+[round((records[i-1]["end"]+records[i]["start"])*fps/2) for i in range(1,5)]+[total_frames]
    if any(b-a<fps//2 for a,b in zip(edges,edges[1:])):raise RuntimeError("Scene too short")
    return [(b-a)/fps for a,b in zip(edges,edges[1:])]
def stamp(sec):
    ms=round(sec*1000);return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"
def prepare(p,out,chosen,settings):
    import creative_intelligence_v10 as v
    phrases=[s[2] for s in p["scenes"]]
    text=" ".join(phrases);path=out/"private_voice.wav"
    result=speech(text,settings,path)
    raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(path),"-ac","1","-ar","48000","-f","f32le","-"])
    a=np.frombuffer(raw,dtype="<f4").copy();sr=48000
    if not len(a) or not np.isfinite(a).all() or np.max(np.abs(a))<.005:raise RuntimeError("Invalid speech audio")
    duration=len(a)/sr
    records=timing(phrases,result,duration)
    v.DUR=scene_durations(records,duration);v.TOTAL=sum(v.DUR)
    track=np.zeros(round(v.TOTAL*sr),np.float32)
    a*=min(10**(-18/20)/max(float(np.sqrt(np.mean(a*a))),1e-6),.78/max(float(np.max(np.abs(a))),1e-6))
    track[:len(a)]=a
    # Same creative-specific musical bed; duck around real speech intervals.
    t=np.arange(len(track))/sr;bed=np.zeros_like(track);beat=60/p["bpm"]
    hz={"orbit":55,"editorial":110,"dashboard":65.4,"editorial-light":130.8,"beauty":98}[p["layout"]]
    for j,b in enumerate(np.arange(0,v.TOTAL,beat)):
        u=t-b;m=(u>=0)&(u<min(.35,beat));z=u[m]
        bed[m]+=.12*np.sin(2*np.pi*(78*z-52*z*z))*np.exp(-z*14)
        for k in [1,1.25,1.5]:
            m=(u>=0)&(u<beat);z=u[m];bed[m]+=.027*np.sin(2*np.pi*hz*k*[1,1,1.122,1.335][j%4]*z)*np.exp(-z*3)
    duck=np.ones_like(track)*.58
    for r in records:duck[max(0,round((r["start"]-.08)*sr)):min(len(track),round((r["end"]+.12)*sr))]=.20
    duck=np.convolve(duck,np.ones(1200,np.float32)/1200,mode="same")
    mix=track+bed*duck;mix*=min(1,.89/max(float(np.max(np.abs(mix))),1e-6))
    with wave.open(str(out/"mix.wav"),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((mix*32767).astype("<i2").tobytes())
    (out/"captions.srt").write_text("\n\n".join(f"{i+1}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['text']}" for i,r in enumerate(records))+"\n",encoding="utf8")
    (out/"narration_timing.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf8")
    (out/"voice_provenance.json").write_text(json.dumps({"model":MODEL,"profile":chosen,"settings":settings,"duration":duration,"publication":False},indent=2))
    return records
def selftest():
    assert [profile(k)[0] for k in ["auto","menu","crm","web","salon"]]==["dynamic","premium","natural","natural","premium"]
    assert profile("auto","premium")[0]=="premium"
    assert payload("test","Hello",PROFILES["natural"])["model"]==MODEL
    try:authorize(FREE_UNTIL)
    except RuntimeError as e:assert "cutoff" in str(e)
    else:raise AssertionError("Expiration not enforced")
    os.environ.pop("DARKLINE_HEYGEN_FREE_ENABLED",None)
    try:authorize(datetime(2026,11,25,tzinfo=timezone.utc))
    except RuntimeError as e:assert "disabled" in str(e)
    else:raise AssertionError("Disabled mode not enforced")
    phrases=["A.","B.","C.","D.","E."];text=" ".join(phrases)
    chars=[{"text":c,"start_time":i*.4,"end_time":(i+1)*.4} for i,c in enumerate(text)]
    records=timing(phrases,{"original_characters":chars},6)
    dur=scene_durations(records,6)
    assert len(dur)==5 and abs(sum(dur)-21)<.00001
    try:timing(phrases,{},6)
    except RuntimeError:pass
    else:raise AssertionError("Missing alignment accepted")
    print("V11_FREE_VOICE_SELFTEST_OK routes, overrides, fixed free model, expiry, disabled mode, real timestamp contract, missing alignment rejection")
if __name__=="__main__":selftest()
