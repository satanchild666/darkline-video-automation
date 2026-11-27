"""Private V11.3 archive-script reassembly. Original audio and burned-in timed captions.
No network, voice synthesis, new catalogue entries or publication. Uses reviewed scene receipts.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
import mascot_rig_v121 as rig
import cinematic_render_v1271 as prior
import transitions_v1286 as trans
cv2.setNumThreads(1)
MAP={
 'auto':[('demo_auto','#services-list',0),('demo_auto','#services-list',4),('demo_auto','#services-list',0),('demo_auto_dates','#date-scroller',1),('demo_auto_dates','#date-scroller',1),('demo_auto_slots','#time-grid',2),('demo_auto_slots','#time-grid',None),('demo_auto_admin','#ds-v23-editor',6),('demo_auto_admin','#ds-v23-editor',6),('demo_auto','#services-list',4)],
 'menu':[('demo_menu','#menu-grid',0),('demo_menu','#menu-grid',5),('demo_menu_filter','#menu-grid',1),('demo_menu','#menu-grid',2),('demo_daily','#public-app',3),('demo_daily','#public-app',3),('demo_menu_admin','#ds-v23-editor',4),('demo_menu_admin','#ds-v23-editor',4),('demo_menu','#menu-grid',5),('demo_menu','#menu-grid',0)]}
OLD_TOPICS={'auto':'auto_booking','menu':'menu_categories'}
TOP=1429

def require(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audiohash(p):return subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-']).decode().strip()
def header(bg,title,i,kind,context):
 a=Image.fromarray(cv2.cvtColor(bg[:200],cv2.COLOR_BGR2RGB));d=ImageDraw.Draw(a);d.rectangle((0,0,1080,8),fill='#bda3ff');d.text((42,33),'DARKLINE STUDIO   /   VALÓDI DEMÓ',font=rig.font(28,True),fill='#b9a2ff');d.rounded_rectangle((866,23,1040,78),radius=12,fill='#241b35',outline='#695e93',width=2);d.text((953,50),f'{i+1:02d} / 10',anchor='mm',font=rig.font(26,True),fill='#e8ddff')
 for size in range(54,29,-1):
  f=rig.font(size,True)
  if d.textlength(title,font=f)<=996:break
 else:raise ValueError('title overflow')
 d.text((42,96),title,font=f,fill='#f4edff');d.text((42,165),'LAPTOP • ASZTALI NÉZET' if kind=='desktop' else 'MOBIL • '+context,font=rig.font(26,True),fill='#e8ddff')
 return cv2.cvtColor(np.array(a),cv2.COLOR_RGB2BGR)
def render(family,source,timing,archive,fresh,out):
 t=json.loads(timing.read_text());require(t['topic']==family and t['source_sha256']==sha(source),'source mismatch');edges=t['frame_boundaries'];require(len(edges)==11 and all(b>a for a,b in zip(edges,edges[1:])),'timing order');total=edges[-1];rows=[]
 for i,(key,sel,j) in enumerate(MAP[family]):
  path=fresh/f'scene-{i:02d}.mp4';isfresh=path.exists()
  if not isfresh:
   require(j is not None,'missing exact selected time action');path=archive/f'scene-{j:02d}.mp4'
  r=json.loads(path.with_suffix('.json').read_text());require(r['video_sha256']==sha(path) and r['key']==key and r['selector']==sel and not r['publication'] and r['voice_calls']==0 and r['evidence']['crop'] is False,'scene receipt invalid')
  if isfresh:require(r['topic']=='legacy_v113_'+family and r['scene']==i and r['text']==t['scenes'][i]['text'],'fresh script mismatch')
  else:require(r['topic']==OLD_TOPICS[family] and r['scene']==j,'archive receipt mismatch')
  if family=='auto' and i==6:require(r['evidence'].get('state_changed') and r['evidence'].get('action')=='.time-btn:not([disabled])','selected slot not proven')
  rows.append((path,r,isfresh))
 old=cv2.VideoCapture(str(source));require(round(old.get(cv2.CAP_PROP_FRAME_COUNT))==total,'source frame count')
 audio=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(source),'-ac','1','-ar','16000','-f','f32le','-']),dtype='<f4');en=[]
 for n in range(total):
  k=round(n*16000/30);x=audio[max(0,k-150):min(len(audio),k+550)];en.append(float(np.clip((np.sqrt(np.mean(x*x))-.018)/.12,0,1)) if len(x) else 0.)
 tmp=out.with_suffix('.partial.mp4');require(not tmp.exists() and not out.exists(),'existing output')
 proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-','-i',str(source),'-map','0:v','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','19','-threads','2','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(tmp)],stdin=subprocess.PIPE)
 bg=prior.bg();bottom=Image.new('RGB',(1080,491),'#171122');d=ImageDraw.Draw(bottom);d.text((325,305),'darkline-studio.web.app',font=rig.font(30,True),fill='#c3a3ff');count=0;caption_count=0;audit=[]
 try:
  for i,(path,r,isfresh) in enumerate(rows):
   start,end=edges[i:i+2];length=end-start;cap=cv2.VideoCapture(str(path));srcframes=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));require(srcframes==r['frames'],'scene length mismatch');last=None;lastidx=-1;title=t['scenes'][i]['title'];head=header(bg,title,i,r['device'],title)
   # Use one complete captured interaction interval, preserve its chronology, and hold the final state.
   try:
    for n in range(length):
     target=round(n*(srcframes-1)/max(1,length-1))
     while lastidx<target:
      ok,last=cap.read();require(ok,'scene frames missing');lastidx+=1
     ok,original=old.read();require(ok,'original timing missing');frame=last.copy();frame[:200]=head
     # Existing caption is cropped ONLY from the original caption strip, never from the website viewport.
     crop=original[1545:1742,64:1016];speaking=bool(np.count_nonzero(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)>190)>180)
     lower=bottom.copy();rig.paste(lower,rig.mascot(count/30,en[count],speaking,19 if i==9 else i,n/30,scale=.88),8,21)
     if speaking:
      # Original exact word timing as burned-in captions, resized to fit the approved right region.
      patch=cv2.resize(crop,(730,151),interpolation=cv2.INTER_AREA);lower.paste(Image.fromarray(cv2.cvtColor(patch,cv2.COLOR_BGR2RGB)),(320,48));caption_count+=1
     frame[TOP:]=cv2.cvtColor(np.asarray(lower),cv2.COLOR_RGB2BGR);trans.apply(frame,count,edges);proc.stdin.write(frame.tobytes());count+=1
     if n==length//2:cv2.imwrite(str(out.parent/f'{out.stem}-{i:02d}.jpg'),cv2.resize(frame,(360,640)))
   finally:cap.release()
   audit.append(dict(scene=i,key=r['key'],selector=r['selector'],source_scene=r['scene'],source_topic=r['topic'],new_capture=isfresh,source_sha256=r['video_sha256'],frames=length,device=r['device'],action=r['evidence'].get('state_changed',False)));print(family,i,count,flush=True)
  require(not old.read()[0],'extra original frame');proc.stdin.close();require(proc.wait()==0 and count==total,'encoding failure');subprocess.run(['ffmpeg','-v','error','-xerror','-threads','2','-i',str(tmp),'-f','null','-'],check=True);require(audiohash(tmp)==audiohash(source),'audio packets changed');tmp.rename(out)
 finally:
  old.release()
  if proc.poll() is None:proc.kill();proc.wait()
  if tmp.exists():tmp.unlink()
 report=dict(topic='legacy_v113_'+family,frames=count,duration_seconds=count/30,source_sha256=sha(source),output_sha256=sha(out),audio_packet_hash=audiohash(out),original_audio_bit_exact=True,caption_frames=caption_count,caption_method='original burned-in timed subtitle strip, resized only',scene_boundaries=edges,transition='V1286 dip',receipts=audit,voice_calls=0,publication=False,production_ready=False)
 out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('V1287_LEGACY_PASS',family,count,caption_count,flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('family',choices=MAP);a.add_argument('source',type=Path);a.add_argument('timing',type=Path);a.add_argument('archive',type=Path);a.add_argument('fresh',type=Path);a.add_argument('out',type=Path);x=a.parse_args();render(x.family,x.source,x.timing,x.archive,x.fresh,x.out)
