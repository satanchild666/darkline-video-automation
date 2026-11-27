"""Offline daily routing regression, no actual credentials or voice assets."""
import json,tempfile,datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo
import daily_run_v1290 as run
import private_storage_v1290 as storage
import daily_review_v1286 as daily
import voice_review_v1288 as voice

def reject(f):
    try:f()
    except (ValueError,FileExistsError,RuntimeError):return
    raise AssertionError('unsafe request accepted')

def main():
    daily.selftest()
    with tempfile.TemporaryDirectory() as d:
        p=Path(d);event=p/'event.json'
        name='satanchild666/Darkline-Studio-AI-marketing-automation'
        ref='refs/heads/dev/v12.9.0-private-runner'
        env={'GITHUB_ACTIONS':'true','DARKLINE_PRIVATE_REVIEW':'true','GITHUB_EVENT_NAME':'push','GITHUB_EVENT_PATH':str(event),'GITHUB_REPOSITORY':name,'GITHUB_REF':ref,'GITHUB_WORKFLOW_REF':name+'/.github/workflows/v1290-private-review.yml@'+ref}
        e={'repository':{'private':True,'full_name':name,'id':1459846231,'owner':{'id':328877800}},'ref':ref}
        event.write_text(json.dumps(e));assert storage.private_runtime(env)
        for key,value in [('GITHUB_REF','refs/heads/main'),('GITHUB_WORKFLOW_REF','other'),('GITHUB_EVENT_NAME','pull_request')]:reject(lambda:storage.private_runtime({**env,key:value}))
        e['repository']['private']=False;event.write_text(json.dumps(e));reject(lambda:storage.private_runtime(env))
        day=dt.date(2026,11,27);now=dt.datetime.combine(day,dt.time(13,17),ZoneInfo('Europe/Budapest'))
        avail={k:{'status_code':200,'body':{'status':'V124_TOPIC_AVAILABLE','sideEffects':False}} for k in daily.sel.FAMILY}
        req={'mode':'SIMULATED_REVIEW','request_id':'test-no-voice','date':day.isoformat(),'now':now.isoformat(),'history':[],'occupancy':[],'preflight':avail,'complete':True}
        def decide(bundle,r):return voice.daily_decision(p/'absent',day,now,r['history'],r['occupancy'],r['preflight'],r['complete'])
        def blocked(*a,**k):raise AssertionError('unexpected render')
        out=p/'video.mp4'
        x=run.execute(req,p/'unused',p/'scenes',out,decide,blocked)
        assert x['status']=='NO_VIDEO' and x['decision']['slot_decision']=='IMAGE_BEFORE_MUTATION'
        reject(lambda:run.execute(req,p/'unused',p/'scenes',out,decide,blocked))
        reject(lambda:run.validate({**req,'mode':'PRODUCTION'}))
        # Positive route uses a mock assembler only. Actual private input is never in public CI.
        def yes(bundle,r):return {'publication':False,'voice_calls':0,'review_only':True,'slot_decision':'PREPARE_PRIVATE_REVIEW','topic':'web_services','voice_available':True,'verified_voice_topics':['web_services']}
        def assemble(topic,folder,out,**k):
            out.write_bytes(b'fixture only');out.with_suffix('.json').write_text(json.dumps({'topic':topic,'frames':1118,'output_sha256':'fixture','publication':False,'voice_calls':0}))
        x=run.execute({**req,'request_id':'test-positive'},p/'unused',p/'scenes',out,yes,assemble)
        assert x['status']=='REVIEW_READY' and x['frames']==1118
    print('V1290_PASS private runner identity, request fixture only, no-voice stop, duplicate local claim, positive mocked routing; no real API calls')
if __name__=='__main__':main()
