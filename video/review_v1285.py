"""One-command private review orchestrator.
Voice assets must be explicitly supplied together and match the exact catalogue script.
Silent reviews never call a voice API. No marketing upload or deployment.
"""
import argparse,json
from pathlib import Path
import integration_v1285 as engine
import assemble_silent_v1285 as silent
import finalize_v1284 as private
def require(ok,msg):
    if not ok:raise ValueError(msg)
def voice_plan(p,source,timing,manifest):
    m=json.loads(manifest.read_text());t=json.loads(timing.read_text());rows=t['scenes']
    require(m['topic']==p['topic'] and m['source_sha256']==private.sha(source) and m['timing_sha256']==private.sha(timing),'voice source identity')
    require(len(rows)==len(m['scenes'])==len(p['scenes'])==10,'voice scene count')
    for s,a,b in zip(p['scenes'],m['scenes'],rows):
        require(all(a[k]==s[k] for k in ('key','selector','text')) and b['scene']==s['scene'] and b['text']==s['text'],'voice script mismatch')
        require(bool(a.get('action_required'))==bool(s['action_required']),'action plan mismatch')
    return m,t
def assemble(topic,folder,out,source=None,timing=None,manifest=None):
    p=engine.plan(topic)
    supplied=[x is not None for x in (source,timing,manifest)]
    require(not any(supplied) or all(supplied),'provide all three private voice assets or none')
    if all(supplied):
        voice_plan(p,source,timing,manifest)
        return private.main(folder,source,timing,manifest,out)
    return silent.silent(topic,folder,out)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('topic');a.add_argument('folder',type=Path);a.add_argument('out',type=Path);a.add_argument('--source',type=Path);a.add_argument('--timing',type=Path);a.add_argument('--manifest',type=Path);x=a.parse_args();assemble(x.topic,x.folder,x.out,x.source,x.timing,x.manifest)
