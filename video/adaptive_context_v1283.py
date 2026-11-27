"""V12.8.3 context-aware private integration. Existing scripts and audio remain unchanged.
This module supplies plans for all 51 topics, and the same approved devices in the renderer.
No publication, TTS or budget mutation.
"""
import cv2,numpy as np
from PIL import Image,ImageDraw
import integration_v1280 as engine
import cinematic_render_v1271 as prior
import demo_topics_v1266 as catalogue

LABELS={(page,selector):label for label,page,selector in catalogue.TARGETS.values()}
DESKTOP_HOME={'#megoldaskereso','#ajanlatkeres','#okos-ajanlo','#sajat-munkak','#igy-dolgozunk'}
def choice(page,selector,index,topic):
    if page.endswith('_admin') or page.startswith('demo_crm'):return 'desktop','management workspace'
    if page=='prices' or (page=='home' and selector in DESKTOP_HOME):return 'desktop','structured comparison'
    if page.startswith(('demo_auto','demo_menu','demo_salon')) or page=='demo_daily' or page=='quote':return 'mobile','visitor journey'
    if page=='demo_web':return ('mobile' if topic.endswith('_mobile') or index%3==1 else 'desktop'),'responsive website'
    return ('desktop' if index%3==0 else 'mobile'),'public information'
def plan(key):
    p=engine.plan(key)
    for s in p['scenes']:
        device,reason=choice(s['key'],s['selector'],s['scene'],key)
        label=LABELS.get((s['key'],s['selector']),s['heading'])
        s.update(device=device,viewport=list(engine.capture_engine.SIZES[device]),device_reason=reason,context=label)
    return p
def font_fit(d,text,width,start=42,minimum=28):
    for size in range(start,minimum-1,-1):
        f=prior.font(size)
        if d.textlength(text,font=f)<=width:return f
    raise ValueError('context text exceeds safe width: '+text)
def header(bg,s):
    a=Image.fromarray(cv2.cvtColor(bg,cv2.COLOR_BGR2RGB));d=ImageDraw.Draw(a)
    d.rectangle((0,0,1080,8),fill='#bda3ff')
    d.text((42,33),'DARKLINE STUDIO   /   VALÓDI DEMÓ',font=prior.font(28),fill='#b9a2ff')
    d.rounded_rectangle((866,23,1040,78),radius=12,fill='#241b35',outline='#695e93',width=2)
    d.text((953,50),f"{s['scene']+1:02d} / 10",anchor='mm',font=prior.font(26),fill='#e8ddff')
    d.text((42,96),s['heading'],font=font_fit(d,s['heading'],996,54,30),fill='#f4edff')
    desktop=s['device']=='desktop'
    if desktop:
        d.text((42,171),'LAPTOP • ASZTALI NÉZET',font=prior.font(26),fill='#aeb8d9')
        d.rounded_rectangle((76,1230,1004,1390),radius=28,fill='#1d2138',outline='#695e93',width=2)
        d.text((108,1248),s['context'],font=font_fit(d,s['context'],860),fill='#f1edff')
        detail='Mintaadatok • nincs mentés' if s['key'].startswith('demo_') else 'Nyilvános weboldal • tájékoztatás'
        d.text((108,1312),detail,font=prior.font(32,False),fill='#b8c2e0')
    else:
        text='MOBIL • '+s['context']
        d.text((42,171),text,font=font_fit(d,text,996,30,26),fill='#e8ddff')
        d.text((540,1401),'Mintaadatok · nincs mentés' if s['key'].startswith('demo_') else 'Nyilvános weboldal',font=prior.font(24,False),fill='#c1b6d8',anchor='mm')
    return cv2.cvtColor(np.asarray(a),cv2.COLOR_RGB2BGR)
def selftest():
    from collections import Counter
    counts=Counter();bg=prior.bg()
    for t in catalogue.TOPICS:
        old=engine.plan(t.key);p=plan(t.key)
        assert p['caption']==old['caption'] and p['voice_bytes']==old['voice_bytes']<=1000 and not p['publication']
        for before,s in zip(old['scenes'],p['scenes']):
            assert all(s[k]==before[k] for k in ('scene','heading','key','selector','text'))
            assert s['viewport']==list(engine.capture_engine.SIZES[s['device']])
            assert not (s['key'].endswith('_admin') or s['key'].startswith('demo_crm')) or s['device']=='desktop'
            assert header(bg,s).shape==(1920,1080,3)
            counts[s['device']]+=1
    assert sum(counts.values())==510 and len(catalogue.TOPICS)==51 and all(counts[k]>0 for k in ('desktop','mobile'))
    print('V1283_PLAN_PASS',dict(counts),'51 topics; 510 context layers; narration unchanged',flush=True)
if __name__=='__main__':selftest()
