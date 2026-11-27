"""V12.8.8 private, exact-source narration library.
Approved metadata only; media stays in owner-controlled storage. No TTS or publishing.
"""
import hashlib,json,subprocess
from pathlib import Path
from dataclasses import dataclass

@dataclass(frozen=True)
class Entry:
    key:str
    mode:str
    family:str
    source_sha:str
    timing_sha:str
    audio_sha:str
    frames:int
    manifest_sha:str=''

ENTRIES={
 'legacy_v113_auto':Entry('legacy_v113_auto','legacy','auto','67884f1acadcc3609fb3c1db3284449c7b1dd6f071df533a22c36102b971734f','41f4026e5019f76bd538aee4bc903045ef3df26787f2abc02f451f151495b9a6','bb5b6d6f26d9266587669fe8b298e17ce6bf4eb3710bafd4dfb2ff1e54adc133',1400),
 'legacy_v113_menu':Entry('legacy_v113_menu','legacy','menu','30aaa39c8a0064a2b7e8b7b8a8dffcd7fd58200d0fedb50efcfddf6349b271e0','ef23f2a6c62afd1f9821f92cc0b04b37ba97e21bdcb9ae9be3b2c892839bda9e','01248ab8341d262986442bfd32634e47eb81e532bc876ada0e16af76b1c8aed6',1722),
 'web_services':Entry('web_services','catalogue','web','99a6711de7c12642759331689da79d28d368ed14998e2ffbf39371616e241a62','4994450c07d6f286c38e2cea14c60bc79a454262ff1a81c4bb7b2407067f227d','10b19aae3717cdb2e3f06588ac28b67446f2e75d749988154cccf25a46f9f837',1118,'91f11989fb6b2fe3d7689155a2a98a93cab783108d653643c41ca35942210f92')}
def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def audiohash(p):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-']).decode().strip().removeprefix('SHA256=')
def media(p):
    d=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(p)]));v=[s for s in d['streams'] if s['codec_type']=='video'];a=[s for s in d['streams'] if s['codec_type']=='audio']
    require(len(v)==len(a)==1,'expected one video and one audio stream')
    v=v[0];require((v['width'],v['height'],v['avg_frame_rate'])==(1080,1920,'30/1'),'source geometry')
    return int(v['nb_frames'])
def script(rows):
    require(isinstance(rows,list) and len(rows)==10,'expected ten scenes')
    require(all(r['scene']==i and isinstance(r['text'],str) and r['text'].strip() for i,r in enumerate(rows)),'invalid script rows')
    return tuple(r['text'] for r in rows)
def resolve(root,key,expected):
    require(key in ENTRIES,'no approved narration for exact script')
    e=ENTRIES[key];folder=Path(root)/key
    source=folder/'source.mp4';timing=folder/'timing.json';manifest=folder/'manifest.json'
    require(source.is_file() and timing.is_file(),'private narration files unavailable')
    require(sha(source)==e.source_sha and sha(timing)==e.timing_sha,'approved source or timing hash mismatch')
    t=json.loads(timing.read_text());require(script(t['scenes'])==script(expected),'script mismatch; no substitution')
    require(media(source)==e.frames and audiohash(source)==e.audio_sha,'media or audio packet mismatch')
    if e.mode=='catalogue':
        require(manifest.is_file() and sha(manifest)==e.manifest_sha,'approved manifest unavailable')
        m=json.loads(manifest.read_text())
        require(m['topic']==key and m['source_sha256']==e.source_sha and m['timing_sha256']==e.timing_sha,'manifest identity')
        require(all(all(a[k]==b[k] for k in ('key','selector','text')) and bool(a.get('action_required'))==bool(b.get('action_required')) for a,b in zip(m['scenes'],expected)) and len(m['scenes'])==10,'capture plan mismatch')
    else:
        require(t['topic']==e.family and t['source_sha256']==e.source_sha and t['frames']==e.frames,'legacy identity')
        edges=t['frame_boundaries'];require(len(edges)==11 and edges[0]==0 and edges[-1]==e.frames and all(30<=b-a<=450 for a,b in zip(edges,edges[1:])),'legacy timing')
        manifest=None
    return e,source,timing,manifest
def catalogue_available(root,plans):
    # Legacy scripts never become daily catalogue voice candidates.
    ready=[];blocked={}
    for key,p in plans.items():
        if key not in ENTRIES or ENTRIES[key].mode!='catalogue':continue
        try:resolve(root,key,p['scenes']);ready.append(key)
        except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as err:blocked[key]=str(err)
    return ready,blocked
