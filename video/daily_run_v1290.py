"""Fixture-only daily decision -> approved private video. Never publish or generate voice.
A claimed request is not retried automatically. A fixture is never production history.
"""
import argparse,json,re,tempfile,datetime as dt
from pathlib import Path

def require(ok,msg):
    if not ok:raise ValueError(msg)

def validate(request):
    require(isinstance(request,dict) and set(request)=={'mode','request_id','date','now','history','occupancy','preflight','complete'},'unexpected request fields')
    require(request['mode']=='SIMULATED_REVIEW','production requests forbidden')
    require(isinstance(request['request_id'],str) and re.fullmatch(r'[A-Za-z0-9_-]{8,80}',request['request_id']) is not None,'invalid request ID')
    require(dt.date.fromisoformat(request['date']).isoformat()==request['date'],'invalid date')
    require(dt.datetime.fromisoformat(request['now']).tzinfo is not None,'timezone required')
    require(request['complete'] is True and isinstance(request['history'],list) and isinstance(request['occupancy'],list) and isinstance(request['preflight'],dict),'incomplete fixture')
    return request

def execute(request,bundle,folder,out,decide,assemble,capture=True):
    validate(request);out=Path(out);folder=Path(folder)
    require(not out.exists() and not out.with_suffix('.json').exists(),'output exists')
    out.parent.mkdir(parents=True,exist_ok=True)
    claim=out.parent/('request-'+request['request_id']+'.json')
    # Exclusive claim guards duplicates inside this workspace; real cross-run
    # dedup still requires the existing authoritative history/slot service.
    with claim.open('x') as f:json.dump({'status':'CLAIMED','mode':request['mode'],'publication':False},f)
    try:
        d=decide(bundle,request)
        require(d.get('publication') is False and d.get('voice_calls')==0 and d.get('review_only') is True,'unsafe decision')
        state=d.get('slot_decision')
        require(state in {'PREPARE_PRIVATE_REVIEW','IMAGE_BEFORE_MUTATION','SKIP_OUTSIDE_WINDOW','SKIP_OCCUPIED','NO_UNIQUE_TOPIC','SKIP_DISABLED','SKIP_NOT_READY'},'unknown decision')
        if state=='PREPARE_PRIVATE_REVIEW':
            topic=d['topic'];require(d.get('voice_available') is True and topic in d.get('verified_voice_topics',[]),'unverified voice')
            assemble(topic,folder,out,bundle=bundle,capture=capture)
            r=json.loads(out.with_suffix('.json').read_text())
            require(out.is_file() and r.get('topic')==topic and r.get('voice_calls')==0 and r.get('publication') is False,'unsafe result')
            require(900<=r['frames']<=3600,'duration outside full ad range')
            result={'status':'REVIEW_READY','decision':d,'frames':r['frames'],'output_sha256':r['output_sha256']}
        else:
            require(not out.exists(),'unexpected output on skip')
            result={'status':'NO_VIDEO','decision':d}
        result.update(mode=request['mode'],request_id=request['request_id'],publication=False,voice_calls=0,production_ready=False)
        claim.write_text(json.dumps(result,ensure_ascii=False,indent=2));return result
    except Exception:
        claim.write_text(json.dumps({'status':'FAILED_NO_RETRY','mode':request['mode'],'publication':False,'voice_calls':0}));raise

def main():
    import private_storage_v1289 as storage
    import cloud_review_v1289 as cloud
    a=argparse.ArgumentParser();a.add_argument('request',type=Path);a.add_argument('folder',type=Path);a.add_argument('out',type=Path);a.add_argument('--drive-file-id',required=True);x=a.parse_args()
    storage.private_runtime();request=validate(json.loads(x.request.read_text()))
    with tempfile.TemporaryDirectory(prefix='darkline-daily-') as tmp:
        bundle=storage.download_drive(x.drive_file_id,Path(tmp)/'voice.zip')
        result=execute(request,bundle,x.folder,x.out,cloud.decision,cloud.run,capture=True)
    print('V1290_DAILY_REVIEW',result['status'],result['decision']['slot_decision'],flush=True)
if __name__=='__main__':main()
