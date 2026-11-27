"""Public CI exercises only policy and deliberately invalid inputs, never private media."""
import json,tempfile
from pathlib import Path
import private_storage_v1289 as s
import test_voice_library_v1288 as voice
import daily_review_v1286 as daily
import transitions_v1286 as transitions

def reject(f):
    try:f()
    except ValueError:return
    raise AssertionError('unsafe input accepted')

def main():
    voice.main();daily.selftest();transitions.selftest()
    assert len(s.expected_members())==7 and s.BUNDLE_BYTES<64*1024*1024
    with tempfile.TemporaryDirectory() as d:
        p=Path(d);event=p/'event.json'
        env={'GITHUB_ACTIONS':'true','DARKLINE_PRIVATE_REVIEW':'true','GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_EVENT_PATH':str(event),'GITHUB_REPOSITORY':'owner/repo'}
        reject(lambda:s.private_runtime({'GITHUB_ACTIONS':'true'}))
        event.write_text(json.dumps({'repository':{'private':False,'full_name':'owner/repo'}}));reject(lambda:s.private_runtime(env))
        event.write_text(json.dumps({'repository':{'private':True,'full_name':'other/repo'}}));reject(lambda:s.private_runtime(env))
        event.write_text(json.dumps({'repository':{'private':True,'full_name':'owner/repo'}}));assert s.private_runtime(env)
        reject(lambda:s.private_runtime({**env,'GITHUB_EVENT_NAME':'pull_request'}))
        reject(lambda:s.restore(p/'missing.zip',p/'private'))
        reject(lambda:s.download_drive('https://untrusted.invalid',p/'data.zip'))
        assert not (p/'private').exists() and not (p/'data.zip').exists()
    print('V1289_STORAGE_PASS 7 pinned members, public runner blocked, untrusted event blocked, no credentials or private assets used')
if __name__=='__main__':main()
