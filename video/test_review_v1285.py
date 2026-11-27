"""Offline regression for orchestration, no voice API and no actual personal assets."""
import json,tempfile
from pathlib import Path
import review_v1285 as r
def reject(f):
    try:f()
    except ValueError:return
    raise AssertionError('unsafe input accepted')
def main():
    r.engine.selftest()
    for t in r.engine.engine.catalogue.TOPICS:
        p=r.engine.plan(t.key);assert r.counts_for(p)==[105]*10
    with tempfile.TemporaryDirectory() as d:
        d=Path(d);src=d/'fake.mp4';tim=d/'timing.json';man=d/'manifest.json';src.write_bytes(b'not a voice source')
        p=r.engine.plan('web_services')
        tim.write_text(json.dumps({'scenes':[{'scene':s['scene'],'text':s['text']} for s in p['scenes']]}))
        m={'topic':p['topic'],'source_sha256':r.private.sha(src),'timing_sha256':r.private.sha(tim),'scenes':p['scenes']}
        man.write_text(json.dumps(m));r.voice_plan(p,src,tim,man)
        reject(lambda:r.run('web_services',d,d/'out.mp4',source=src))
        reject(lambda:r.counts_for(p,src,tim,man))
        m['scenes'][0]['text']='unrelated';man.write_text(json.dumps(m));reject(lambda:r.voice_plan(p,src,tim,man))
        assert not (d/'out.mp4').exists()
    print('V1285_ORCHESTRATOR_PASS 51 plans, full silent duration, incomplete voice rejected, invalid video rejected, mismatched script rejected; zero API calls')
if __name__=='__main__':main()
