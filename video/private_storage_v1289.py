"""Pinned private narration bundle restoration and optional authenticated Drive read.
No writes to Drive, no TTS, no publishing. Never use private media in public CI.
"""
import argparse,hashlib,json,os,re,shutil,stat,tempfile,zipfile
from pathlib import Path
import narration_library_v1288 as lib

BUNDLE_SHA='5c689039c71f96c337f8145d08ad751b517fc4ebeaa7f2668569a12da834ed93'
BUNDLE_BYTES=44107525
MAX_MEMBER=32*1024*1024
MAX_TOTAL=64*1024*1024
SCOPE='https://www.googleapis.com/auth/drive.readonly'

def require(ok,msg):
    if not ok:raise ValueError(msg)

def private_runtime(env=None):
    env=os.environ if env is None else env
    if env.get('GITHUB_ACTIONS')=='true':
        require(env.get('DARKLINE_PRIVATE_REVIEW')=='true','private CI not explicitly authorized')
        event_name=env.get('GITHUB_EVENT_NAME')
        require(event_name in ('workflow_dispatch','schedule','push'),'untrusted CI event')
        try: event=json.loads(Path(env['GITHUB_EVENT_PATH']).read_text())
        except (OSError,ValueError,KeyError):raise ValueError('CI privacy not verified') from None
        repo=event.get('repository',{})
        require(repo.get('private') is True and repo.get('full_name')==env.get('GITHUB_REPOSITORY'),'public or unverified CI forbidden')
        if event_name=='push':
            require(str(repo.get('id'))=='1459846231' and str(repo.get('owner',{}).get('id'))=='328877800','unapproved runner repository')
            require(env.get('GITHUB_REF')=='refs/heads/dev/v12.9.0-private-runner' and event.get('ref')==env.get('GITHUB_REF'),'unapproved runner branch')
            require(env.get('GITHUB_WORKFLOW_REF')=='satanchild666/Darkline-Studio-AI-marketing-automation/.github/workflows/v1290-private-review.yml@refs/heads/dev/v12.9.0-private-runner','unapproved runner workflow')
    return True

def expected_members():
    result={}
    for key,e in lib.ENTRIES.items():
        result[key+'/source.mp4']=e.source_sha
        result[key+'/timing.json']=e.timing_sha
        if e.mode=='catalogue':result[key+'/manifest.json']=e.manifest_sha
    return result

def restore(bundle,dest):
    private_runtime();bundle,dest=Path(bundle),Path(dest)
    require(bundle.is_file() and bundle.stat().st_size==BUNDLE_BYTES and lib.sha(bundle)==BUNDLE_SHA,'bundle identity mismatch')
    require(not dest.exists() and not dest.is_symlink(),'destination already exists')
    expected=expected_members();dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.voice-restore-',dir=dest.parent) as tmp:
        staging=Path(tmp)/'library';staging.mkdir(mode=0o700)
        with zipfile.ZipFile(bundle) as z:
            entries=z.infolist();names=[x.filename for x in entries]
            require(len(names)==len(expected) and set(names)==set(expected),'unexpected or duplicate archive members')
            require(sum(i.file_size for i in entries)<=MAX_TOTAL,'archive total too large')
            for i in entries:
                require(not i.is_dir() and not stat.S_ISLNK(i.external_attr>>16) and 0<i.file_size<=MAX_MEMBER,'unsafe archive member')
                dst=staging/i.filename;dst.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
                with z.open(i) as src,dst.open('xb') as out:shutil.copyfileobj(src,out)
                dst.chmod(0o600);require(lib.sha(dst)==expected[i.filename],'member integrity mismatch')
        staging.rename(dest)
    return {'bundle_sha256':BUNDLE_SHA,'bytes':BUNDLE_BYTES,'members':len(expected),'publication':False,'voice_calls':0}

def download_drive(file_id,dest,session=None):
    """Use ADC with read-only scope, or an injected authorized test session.
    Caller must explicitly configure a private runtime identity; no token is persisted.
    """
    private_runtime();require(re.fullmatch(r'[A-Za-z0-9_-]{10,150}',file_id) is not None,'invalid Drive file ID')
    dest=Path(dest);require(not dest.exists() and not dest.is_symlink(),'destination exists');dest.parent.mkdir(parents=True,exist_ok=True)
    if session is None:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        credentials,_=google.auth.default(scopes=[SCOPE]);session=AuthorizedSession(credentials)
    url='https://www.googleapis.com/drive/v3/files/'+file_id
    tmp=dest.with_suffix('.partial');require(not tmp.exists(),'partial already exists')
    try:
        with session.get(url,params={'alt':'media'},stream=True,allow_redirects=False,timeout=(10,90)) as r:
            require(r.status_code==200,'private Drive read failed')
            size=0;h=hashlib.sha256()
            with tmp.open('xb') as f:
                tmp.chmod(0o600)
                for block in r.iter_content(1024*1024):
                    if not block:continue
                    size+=len(block);require(size<=BUNDLE_BYTES,'download exceeds expected size');h.update(block);f.write(block)
            require(size==BUNDLE_BYTES and h.hexdigest()==BUNDLE_SHA,'download integrity mismatch')
        tmp.rename(dest)
    finally:
        if tmp.exists():tmp.unlink()
    return dest

def main():
    p=argparse.ArgumentParser();p.add_argument('dest',type=Path);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--bundle',type=Path);g.add_argument('--drive-file-id');a=p.parse_args()
    if a.bundle:report=restore(a.bundle,a.dest)
    else:
        with tempfile.TemporaryDirectory() as d:report=restore(download_drive(a.drive_file_id,Path(d)/'voice.zip'),a.dest)
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
