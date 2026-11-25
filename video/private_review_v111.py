"""V11.1 owner-review batch: 3 approved profiles; one free request per demo.
Only encrypted review media may leave the runner.
"""
import argparse, copy, json, math, os, struct, zipfile
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PUBLIC_KEY=b"""-----BEGIN PUBLIC KEY-----
MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEA18V7OR6/GVZ260EEazhX
9xSqcQUYz/4n1LKndLwFY/3oT7rHyaQ2NCfNW7WlIJfqanxzcwR58x/ozhGw57Nq
pSuda34do7vNfp8rxsjixqSPqKCY0SV0Spov+jSXySQ2ziWgsGnUnPJYWbN2jCeJ
EZCqvDr59Qiu+a4KC/YLnGSu3/umWgW2fL5kLy3IcAI5T9yfeiz/t/3zsTVTeKS+
d7fo22cJ01ltA70qxcU8aY+WIb0x+/J0Pb/xGOAWALbmbyxILn382zuyv/M9aLR5
KuXbLw+nxpDbdWGYGo+MvWmhTS8+VdcXp0dJrfVICd4QlIOX/3kn6PJDf2ZHMZ8i
vUKKV5Ea9RZ007EfDpLO5qbAUpL60+SpEheOeiAZkQSSHSRotsOAcrAGzzT1nBGl
MpTpY2Dh9ukl4+ajKueoaLS6d86uEsLLHfoaeQjJnVsh+7jdOuoRI6oWmDD84aD+
mqFgj0JuEBqEc6GDVhKK7HW7/sasGMP7iSEYCehxqKmpAgMBAAE=
-----END PUBLIC KEY-----
"""
MAGIC=b"DLV111\x00"
ROOT=Path("private-preview-v111")
SEALED=Path("sealed-review-v111")
SCRIPTS={
    "web":[
        "Szeretnéd, hogy az ügyfeleid könnyebben megtaláljanak?",
        "Mutasd be a szolgáltatásaidat egy átlátható weboldalon.",
        "A korábbi munkáidnak és referenciáidnak is jut hely.",
        "A saját kezelőfelületeden bármikor frissítheted a tartalmat.",
        "Nézd meg, hogyan működik a Darkline Studio bemutatója!"],
    "auto":[
        "Csörög a telefon, miközben éppen egy autón dolgozol?",
        "Az ügyfeled online kiválaszthatja, milyen szolgáltatást szeretne.",
        "Ezután megnézheti a szabad időpontokat, egyszerűen.",
        "Te pedig a saját felületeden kezelheted a szolgáltatásaidat.",
        "Próbáld ki az autószervizes bemutatót a Darkline Studiónál!"],
    "menu":[
        "Az első benyomás már az étlapnál kezdődik.",
        "Vendégeid könnyen böngészhetnek az ételek és az árak között.",
        "A napi ajánlatodat is megmutathatod ugyanazon a felületen.",
        "Ha változik a kínálat, a kezelőfelületen frissítheted.",
        "Fedezd fel a Darkline Studio digitális étlapját!"]
}
EXPECTED={"web":"natural","auto":"dynamic","menu":"premium"}
def oaep():
    return padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None)
def seal(data,public):
    # Fresh AES-256 key and nonce for each archive; authenticate the header too.
    key=AESGCM.generate_key(bit_length=256);nonce=os.urandom(12)
    wrapped=public.encrypt(key,oaep())
    header=MAGIC+struct.pack(">H",len(wrapped))+wrapped+nonce
    return header+AESGCM(key).encrypt(nonce,data,header)
def durations(records,duration,fps=30):
    # End on a short CTA hold, not twelve seconds of unspoken filler.
    if len(records)!=5:raise RuntimeError("Expected five scenes")
    if not 8<=duration<=30:raise RuntimeError("Speech outside safe preview duration")
    end=math.ceil((duration+1.2)*fps)
    edges=[0]
    for prev,nxt in zip(records,records[1:]):
        low=math.ceil(prev["end"]*fps-1e-6)
        high=math.floor(nxt["start"]*fps+1e-6)
        if low>high:raise RuntimeError("No frame-aligned gap between speech phrases")
        edges.append((low+high)//2)
    edges.append(end)
    if any(b-a<fps//2 for a,b in zip(edges,edges[1:])):raise RuntimeError("Scene too short")
    return [(b-a)/fps for a,b in zip(edges,edges[1:])]
def bundle(key,out,public):
    files=[next(out.glob("Darkline_V111_*.mp4")),out/"captions.srt",out/"quality.json",out/"voice_provenance.json",out/"narration_timing.json",out/"storyboard.jpg"]
    zip_path=out/"review.zip"
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
        for f in files:
            if not f.is_file():raise RuntimeError("Review file missing")
            z.write(f,arcname=f.name)
    SEALED.mkdir(exist_ok=True)
    target=SEALED/f"Darkline_V111_{key}.dlenc"
    data=zip_path.read_bytes()
    if not 0<len(data)<100_000_000:raise RuntimeError("Invalid archive size")
    target.write_bytes(seal(data,public))
    print("V111_ENCRYPTED_REVIEW_READY",key,target.stat().st_size,flush=True)
def selftest():
    public=serialization.load_pem_public_key(PUBLIC_KEY)
    assert public.key_size==3072
    private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    sample=b"review test"
    packed=seal(sample,private.public_key())
    n=struct.unpack(">H",packed[len(MAGIC):len(MAGIC)+2])[0]
    off=len(MAGIC)+2;nonce=packed[off+n:off+n+12];head=packed[:off+n+12]
    key=private.decrypt(packed[off:off+n],oaep())
    assert AESGCM(key).decrypt(nonce,packed[len(head):],head)==sample
    damaged=packed[:-1]+bytes([packed[-1]^1])
    try:AESGCM(key).decrypt(nonce,damaged[len(head):],head)
    except Exception:pass
    else:raise AssertionError("Tampering not rejected")
    rec=[{"start":.2+i*2,"end":1.8+i*2} for i in range(5)]
    assert abs(sum(durations(rec,10))-11.2)<.00001
    assert set(SCRIPTS)==set(EXPECTED)
    print("V111_SELFTEST_OK authenticated encryption, timing, profiles",flush=True)
def main():
    import creative_intelligence_v10 as v
    import heygen_free_voice_v11 as voice
    # Existing V11 free-only and expiry guards are retained.
    voice.authorize()
    public=serialization.load_pem_public_key(PUBLIC_KEY)
    voice.scene_durations=durations
    # Sequential: if any generation fails, stop, never retry or use a paid model.
    for key in ("auto","web","menu"):
        p=copy.deepcopy(v.PLANS[key]);chosen,settings=voice.profile(key)
        if chosen!=EXPECTED[key]:raise RuntimeError("Profile route mismatch")
        for scene,line in zip(p["scenes"],SCRIPTS[key]):scene[2]=line
        out=ROOT/key;out.mkdir(parents=True,exist_ok=False)
        capture=v.capture(key,p,out)
        print("V111_CAPTURE_OK",key,flush=True)
        records=voice.prepare(p,out,chosen,settings)
        print("V111_SPEECH_OK",key,chosen,"seconds",round(records[-1]["end"],3),flush=True)
        movie=v.render(key,p,out,records)
        renamed=out/f"Darkline_V111_{key}_{chosen}.mp4";movie.rename(renamed)
        report=v.check(key,p,out,renamed,records,capture)
        report.update({"voice_profile":chosen,"voice_model":voice.MODEL,"publication":False,"human_review":"pending"})
        (out/"quality.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
        # Even a rejected visual sample is retained encrypted for the owner's review.
        bundle(key,out,public)
        print("V111_RESULT",json.dumps({"key":key,"profile":chosen,"gate":report["review_gate"],"frames":report["frames"],"seconds":round(v.TOTAL,3),"audio_peak":report["audio_peak"],"publication":False}),flush=True)
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--selftest",action="store_true");args=ap.parse_args()
    if args.selftest:selftest()
    else:main()
