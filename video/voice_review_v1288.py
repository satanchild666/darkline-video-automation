"""Unified approved voice review. Separate legacy and catalogue paths.
No secrets, live ledger claims, generation or publishing. Private media required.
"""
import argparse,json,tempfile
from pathlib import Path
import narration_library_v1288 as lib
import integration_v12852 as engine
import legacy_review_v1287 as legacy
import assemble_legacy_v1287 as archive
import review_v1285 as review
import transitions_v1286 as trans
import daily_review_v1286 as daily
def expected(key):
    e=lib.ENTRIES.get(key)
    if e and e.mode=='legacy':return legacy.plan(e.family)
    return engine.plan(key)
def daily_decision(root,day,now,history,occupancy,preflight,complete):
    plans={t.key:engine.plan(t.key) for t in engine.engine.catalogue.TOPICS}
    ready,blocked=lib.catalogue_available(root,plans)
    result=daily.decision(day,now,history,occupancy,preflight,complete,ready)
    result.update(verified_voice_topics=ready,blocked_voice_assets=blocked)
    return result
def run(root,key,folder,out,fresh=None,capture=False):
    p=expected(key);e,src,timing,manifest=lib.resolve(root,key,p['scenes'])
    lib.require(not out.exists(),'output exists')
    out.parent.mkdir(parents=True,exist_ok=True)
    if e.mode=='legacy':
        lib.require(not capture and fresh is not None,'legacy review requires explicitly verified scene folder')
        archive.render(e.family,src,timing,folder,fresh,out)
    else:
        lib.require(fresh is None,'unexpected legacy scene folder')
        with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
            raw=Path(tmp)/'assembled.mp4'
            review.run(key,folder,raw,src,timing,manifest,capture=capture)
            trans.render(raw,raw.with_suffix('.json'),out)
    lib.require(lib.audiohash(out)==e.audio_sha and lib.media(out)==e.frames,'final media mismatch')
    r=json.loads(out.with_suffix('.json').read_text())
    lib.require(r['publication'] is False and r['voice_calls']==0,'unsafe output')
    r.update(narration_library_key=key,approved_source_sha256=e.source_sha,approved_timing_sha256=e.timing_sha,mode=e.mode,production_ready=False)
    out.with_suffix('.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print('V1288_VOICE_REVIEW_PASS',key,e.frames,flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser()
    for name in ('root','key','folder','out'):a.add_argument(name,type=str if name=='key' else Path)
    a.add_argument('--fresh',type=Path);a.add_argument('--capture',action='store_true');x=a.parse_args();run(x.root,x.key,x.folder,x.out,x.fresh,x.capture)
