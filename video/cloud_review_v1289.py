"""Manual private cloud entrypoint: read verified archive, review, remove temp assets.
No publishing, TTS, cron registration, ledger changes or credential creation.
"""
import argparse,json,tempfile,datetime as dt
from pathlib import Path
import private_storage_v1289 as storage
import voice_review_v1288 as review

def run(key,folder,out,bundle=None,drive_file_id=None,fresh=None,capture=False):
    storage.private_runtime()
    storage.require((bundle is None)!=(drive_file_id is None),'exactly one private source required')
    storage.require(not out.exists() and not out.with_suffix('.json').exists(),'output exists')
    with tempfile.TemporaryDirectory(prefix='darkline-private-') as tmp:
        tmp=Path(tmp)
        local=storage.download_drive(drive_file_id,tmp/'voice.zip') if drive_file_id else bundle
        receipt=storage.restore(local,tmp/'library')
        review.run(tmp/'library',key,folder,out,fresh=fresh,capture=capture)
        r=json.loads(out.with_suffix('.json').read_text())
        storage.require(r['publication'] is False and r['voice_calls']==0,'unsafe output')
        r.update(private_storage=receipt,storage_provider='google_drive' if drive_file_id else 'verified_bundle',production_ready=False)
        out.with_suffix('.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print('V1289_PRIVATE_ASSEMBLY_PASS',key,flush=True)

def decision(bundle,request):
    storage.private_runtime()
    with tempfile.TemporaryDirectory(prefix='darkline-policy-') as d:
        root=Path(d)/'library';storage.restore(bundle,root)
        return review.daily_decision(root,dt.date.fromisoformat(request['date']),dt.datetime.fromisoformat(request['now']),request['history'],request['occupancy'],request['preflight'],request['complete'])

if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('key');a.add_argument('folder',type=Path);a.add_argument('out',type=Path)
    g=a.add_mutually_exclusive_group(required=True);g.add_argument('--bundle',type=Path);g.add_argument('--drive-file-id')
    a.add_argument('--fresh',type=Path);a.add_argument('--capture',action='store_true');x=a.parse_args()
    run(x.key,x.folder,x.out,x.bundle,x.drive_file_id,x.fresh,x.capture)
