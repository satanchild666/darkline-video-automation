"""Private CPU-only own-voice audition. No hosted inference, paid API or publication.
Reference must be supplied as an Actions secret; the original recording is never committed.
All output is encrypted for the owner before upload.
"""
import base64,hashlib,io,json,os,subprocess,sys,tempfile,wave,zipfile
from pathlib import Path
import numpy as np
from cryptography.hazmat.primitives import serialization
from private_review_v111 import PUBLIC_KEY,seal
EXPECTED="4e64e78b1df745926868a4a6a5d7b0f689d8fb6458ffd4db9f640e40e2a26966"
SCRIPT="Ismerős? Csörög a telefon, te pedig éppen dolgozol. Pedig az időpontfoglalás lehet egyszerűbb is! Az ügyfeled kiválasztja a szolgáltatást és a szabad időpontot. Te pedig mindent egy helyen látsz. Próbáld ki a Darkline Studio bemutatóját!"
def run(*args,**kwargs):return subprocess.check_output(list(args),**kwargs)
def main():
    os.umask(0o077)
    encoded=os.environ.pop("DARKLINE_MOSS_REFERENCE_B64","").strip()
    if not encoded:raise RuntimeError("V125_REFERENCE_SECRET_MISSING")
    ref=base64.b64decode(encoded,validate=True);del encoded
    if not 10000<len(ref)<48000 or hashlib.sha256(ref).hexdigest()!=EXPECTED:raise RuntimeError("Reference mismatch")
    engine=Path(os.environ["MOSS_DIR"]).resolve()
    out=Path("sealed-voice-v125");out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        d=Path(tmp);(d/"reference.ogg").write_bytes(ref);del ref
        subprocess.run(["ffmpeg","-v","error","-i",str(d/"reference.ogg"),"-ac","1","-ar","48000",str(d/"reference.wav")],check=True)
        (d/"reference.ogg").unlink()
        reports=[]
        for name,seed,tt,at in (("Natural",42,.85,.80),("Expressive",137,1.05,.90)):
            wav=d/(name+".wav");mp3=d/(name+".mp3")
            # No --voice preset, no paid fallback. Official inference runs on this CPU.
            subprocess.run([sys.executable,"infer_onnx.py","--prompt-audio-path",str(d/"reference.wav"),"--text",SCRIPT,"--output-audio-path",str(wav),"--cpu-threads","4","--execution-provider","cpu","--seed",str(seed),"--text-temperature",str(tt),"--audio-temperature",str(at),"--max-new-frames","440","--disable-wetext-processing","--disable-normalize-tts-text"],cwd=engine,check=True,timeout=600,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            a=np.frombuffer(run("ffmpeg","-v","error","-i",str(wav),"-ac","1","-ar","48000","-f","f32le","-"),dtype="<f4")
            seconds=len(a)/48000;peak=float(np.max(np.abs(a)));rms=float(np.sqrt(np.mean(a*a)))
            if not np.isfinite(a).all() or not 6<=seconds<=40 or peak<.005 or rms<.001:raise RuntimeError("Invalid voice audio")
            subprocess.run(["ffmpeg","-v","error","-i",str(wav),"-af","loudnorm=I=-18:TP=-2:LRA=7","-c:a","libmp3lame","-b:a","160k",str(mp3)],check=True)
            reports.append({"name":name,"seconds":seconds,"peak":peak,"rms":rms,"engine":"MOSS-TTS-Nano ONNX CPU","source":"owner reference","quality":"OWNER_LISTENING_REQUIRED","publication":False})
            print("V125_PRIVATE_VOICE_OK",name,round(seconds,2),flush=True)
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
            for r in reports:z.write(d/(r["name"]+".mp3"),arcname=r["name"]+".mp3")
            z.writestr("quality.json",json.dumps(reports,ensure_ascii=False,indent=2))
        (out/"Darkline_V125_own_voice.dlenc").write_bytes(seal(buf.getvalue(),serialization.load_pem_public_key(PUBLIC_KEY)))
    print("V125_ENCRYPTED_VOICE_READY",flush=True)
if __name__=="__main__":main()
