"""Voice audition: no publication, no external paid API, built-in voices only."""
import json, subprocess, tempfile, wave
from pathlib import Path
import numpy as np
OUT=Path("voice-review-v102");OUT.mkdir(exist_ok=True)
SR=48000
# Same words for all three candidates, five directed performances.
SCENES=[
    ("Még mindig telefonon egyeztetsz időpontot?",4.5,1.04,"curious question"),
    ("Mutatok egy egyszerűbb megoldást!",4.,1.10,"positive reveal"),
    ("Válassz szolgáltatást, napot, időpontot.",4.,1.06,"clear explanation"),
    ("A többi? A saját kezelőfelületeden.",4.,.99,"contrast, confident"),
    ("Próbáld ki! Darkline Studio.",4.5,.96,"inviting close"),
]
def run(args):
    return subprocess.check_output(args)
def decode(path,tempo=1.0):
    return np.frombuffer(run(["ffmpeg","-v","error","-i",str(path),"-af",f"atempo={tempo:.5f}","-ar",str(SR),"-ac","1","-f","f32le","-"]),dtype="<f4").copy()
def trim(a):
    idx=np.where(np.abs(a)>.004)[0]
    if not len(idx):raise RuntimeError("silent segment")
    return a[max(0,idx[0]-int(.05*SR)):min(len(a),idx[-1]+int(.10*SR))]
def write(path,a):
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR)
        w.writeframes((np.clip(a,-.99,.99)*32767).astype("<i2").tobytes())
def stats(a):
    return {"peak":float(np.max(np.abs(a))),"rms_dbfs":float(20*np.log10(max(1e-9,np.sqrt(np.mean(a*a)))))}
def render(name,generate):
    track=np.zeros(int(sum(s[1] for s in SCENES)*SR),np.float32);timing=[];offset=0
    with tempfile.TemporaryDirectory() as td:
        for i,(words,window,speed,direction) in enumerate(SCENES):
            raw=Path(td)/f"{i}.wav";generate(words,speed,raw)
            a=trim(decode(raw));rate=max(1,len(a)/SR/(window-.50))
            if rate>1.32:raise RuntimeError(f"scene {i+1} too long without excessive acceleration")
            if rate>1.001:
                fitted=Path(td)/f"{i}-trim.wav";write(fitted,a);a=trim(decode(fitted,rate))
            start=int((offset+.20)*SR);end=start+len(a)
            if end>int((offset+window-.12)*SR):raise RuntimeError("scene overflow")
            rms=float(np.sqrt(np.mean(a*a)));a*=min(10**(-18/20)/max(rms,1e-9),.78/max(float(np.max(np.abs(a))),1e-9))
            track[start:end]=a;timing.append({"scene":i+1,"text":words,"direction":direction,"start":start/SR,"end":end/SR,"requested_speed":speed,"fit_tempo":rate,**stats(a)})
            offset+=window
    path=OUT/(name+".wav");write(path,track)
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(path),"-c:a","libmp3lame","-b:a","128k",str(OUT/(name+".mp3"))],check=True)
    report={"voice":name,"status":"READY_FOR_LISTENING","duration":len(track)/SR,"segments":timing,**stats(track),"human_naturalness":"not assessed","publication":False}
    print("VOICE_READY",json.dumps(report,ensure_ascii=False),flush=True)
    return report
def main():
    reports=[]
    def trial(name,fn):
        try:reports.append(fn())
        except Exception as e:
            reports.append({"voice":name,"status":"FAILED","error":str(e)[:500]});print("VOICE_FAILED",name,str(e)[:500],flush=True)
    def baseline():
        from piper import PiperVoice
        folder=Path("voice-model");folder.mkdir(exist_ok=True)
        model=folder/"hu_HU-anna-medium.onnx"
        if not model.exists():subprocess.run(["python","-m","piper.download_voices","--download-dir",str(folder),"hu_HU-anna-medium"],check=True)
        voice=PiperVoice.load(str(model))
        def generate(words,speed,path):
            with wave.open(str(path),"wb") as w:voice.synthesize_wav(words,w)
        return render("A_Piper_Anna_reference",generate)
    trial("A_Piper_Anna_reference",baseline)
    try:
        from supertonic import TTS
        tts=TTS(auto_download=True)
        for name,style_name in [("B_Supertonic_M1","M1"),("C_Supertonic_F1","F1")]:
            def candidate(name=name,style_name=style_name):
                style=tts.get_voice_style(voice_name=style_name)
                def generate(words,speed,path):
                    # Full natural sentences, punctuation, varying speed; no artificial pitch shifts.
                    wav,_=tts.synthesize(text=words,voice_style=style,lang="hu",total_steps=12,speed=speed)
                    tts.save_audio(wav,str(path))
                return render(name,generate)
            trial(name,candidate)
    except Exception as e:
        reports.append({"voice":"Supertonic","status":"FAILED","error":str(e)[:500]});print("VOICE_FAILED Supertonic",str(e)[:500],flush=True)
    (OUT/"voice_report.json").write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding="utf8")
    if len([r for r in reports if r["status"]=="READY_FOR_LISTENING"])<3:raise RuntimeError("Incomplete comparison; inspect available samples")
if __name__=="__main__":main()
