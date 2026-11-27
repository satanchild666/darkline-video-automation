"""V10.3 full-context narration audition. No publish, no paid API.
Official MOSS-TTS-Nano ONNX built-in voice presets only.
"""
import os, json, subprocess, sys, wave, math
from pathlib import Path
import numpy as np
OUT=Path("voice-review-v103").resolve();OUT.mkdir(exist_ok=True)
ENGINE=Path(os.environ["MOSS_DIR"]).resolve()
SCRIPT="Ismerős? Csörög a telefon, te pedig éppen dolgozol. Pedig az időpontfoglalás lehet egyszerűbb is! Az ügyfeled kiválasztja a szolgáltatást és a szabad időpontot. Te pedig mindent egy helyen látsz. Próbáld ki a Darkline Studio bemutatóját!"
# Full text in one generation, natural punctuation; no fake pitch manipulation.
CANDIDATES=[
    ("D_MOSS_Adam","Adam",42,.85,.80),
    ("E_MOSS_Ava","Ava",42,.85,.80),
    ("F_MOSS_Adam_alternative","Adam",137,1.05,.90)
]
def run(args,**kw):return subprocess.check_output(args,**kw)
def analyze(path):
    a=np.frombuffer(run(["ffmpeg","-v","error","-i",str(path),"-ac","1","-ar","48000","-f","f32le","-"]),dtype="<f4")
    if not len(a) or not np.isfinite(a).all():raise RuntimeError("Invalid audio")
    d=len(a)/48000;peak=float(np.max(np.abs(a)));rms=float(np.sqrt(np.mean(a*a)))
    if not 6<=d<=35 or rms<.001:raise RuntimeError("Duration or signal rejected")
    return {"duration":d,"peak":peak,"rms_dbfs":20*math.log10(rms)}
def main():
    reports=[]
    (OUT/"script.txt").write_text(SCRIPT,encoding="utf8")
    for name,voice,seed,tt,at in CANDIDATES:
        try:
            raw=OUT/(name+"_original.wav");wav=OUT/(name+".wav");mp3=OUT/(name+".mp3")
            subprocess.run([sys.executable,"infer_onnx.py","--voice",voice,"--text",SCRIPT,"--output-audio-path",str(raw),"--cpu-threads","4","--execution-provider","cpu","--seed",str(seed),"--text-temperature",str(tt),"--audio-temperature",str(at),"--max-new-frames","440","--disable-wetext-processing","--disable-normalize-tts-text"],cwd=ENGINE,check=True,timeout=480)
            before=analyze(raw)
            # Loudness-match, no pitch/speed edit. Preserve original for review.
            subprocess.run(["ffmpeg","-v","error","-y","-i",str(raw),"-af","loudnorm=I=-18:TP=-2:LRA=7","-ar","48000","-c:a","pcm_s16le",str(wav)],check=True)
            subprocess.run(["ffmpeg","-v","error","-y","-i",str(wav),"-c:a","libmp3lame","-b:a","160k",str(mp3)],check=True)
            stats=analyze(wav)
            report={"name":name,"preset":voice,"seed":seed,"text_temperature":tt,"audio_temperature":at,"original":before,"normalized":stats,"status":"READY_FOR_LISTENING","human_naturalness":"not assessed","commercial_preset_rights":"verify before publication","publication":False}
        except Exception as exc:
            report={"name":name,"status":"FAILED","error":str(exc)[:500],"publication":False}
        reports.append(report);print("V103_VOICE",json.dumps(report,ensure_ascii=False),flush=True)
        (OUT/"voice_report.json").write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding="utf8")
    if any(r["status"]!="READY_FOR_LISTENING" for r in reports):raise RuntimeError("Voice comparison incomplete")
if __name__=="__main__":main()
