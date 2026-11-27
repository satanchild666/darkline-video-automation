"""V12.3: bounded content selection; fail closed on uncertain outcomes.
The topic catalogue is grounded in the existing captured V11.3 demo scripts.
A new caption does not make a duplicate video unique.
"""
from dataclasses import dataclass
@dataclass(frozen=True)
class Candidate:
    topic:str
    angle:str
    text:str
def caption(text,tag):
    return text+"\n\nAnimált kabala, AI-narráció.\nhttps://darkline-studio.web.app/\n#DarklineStudio #"+tag
CATALOGUE=(
 Candidate("web","customer_first",caption("Mit lát egy érdeklődő, amikor először megnyitja a vállalkozásod weboldalát? A bemutatóban a szolgáltatásokat, a referenciákat és a mobilos ügyfélnézetet járjuk körbe. A saját kezelőfelülettel a tartalmak frissítése is egyszerűbb lehet.","Weboldalkészítés")),
 Candidate("web","references",caption("Egy korábbi munkád többet mondhat egy hosszú bemutatkozásnál. A videóban megmutatjuk, hogyan jelenhetnek meg a referenciáid az üzleti weboldalon, és hogyan találhatja meg őket egy telefonról érkező látogató.","Referenciák")),
 Candidate("web","content_editor",caption("Megváltozott egy szolgáltatásod leírása? A bemutatóban az üzleti oldal szerkesztőfelületét is láthatod: itt kezelhetők a megjelenített adatok. A videó a látogatói és a kezelői nézet közötti különbséget is megmutatja.","Tartalomkezelés")),
 Candidate("auto","booking_flow",caption("Szervizelés közben csörög a telefon? Nézzük végig, hogyan választ az ügyfél szolgáltatást, napot és szabad időpontot az autószerviz bemutatófelületén. A videó a foglalási lépéseket mutatja be.","Autószerviz")),
 Candidate("menu","daily_menu",caption("Mit kínálsz ma ebédre? A digitális étlap bemutatójában a vendég a telefonján böngészheti a fogásokat, az árakat és a napi ajánlatot. A kínálat változását külön kezelőfelületen lehet követni.","DigitálisÉtlap")),
)
class StopSafely(RuntimeError):pass
def classify(status,result):
    if not isinstance(result,dict):return "STOP"
    if status==200 and result.get("status")=="DRY_RUN_OK" and result.get("sideEffects") is False:return "PASS"
    if status==422 and result.get("status")=="V122_BLOCKED":
        detail=str(result.get("detail",""))
        if detail.startswith("Semantic duplicate or closely related content; publishing stopped") or detail in ("Duplicate caption","Semantic duplicate check did not pass"):return "DUPLICATE"
    return "STOP"
def select_for_approved(topic,check):
    for c in CATALOGUE:
        if c.topic!=topic:continue
        status,result=check(c)
        outcome=classify(status,result)
        print("V123_ANGLE",c.topic,c.angle,outcome,flush=True)
        if outcome=="PASS":return c,result
        if outcome=="STOP":raise StopSafely("Uncertain or non-duplicate preflight failure; no retry")
    return None,None
def choose_next_topic(excluded,check):
    # Only used BEFORE rendering; no second publish mutation or paid TTS retry.
    for c in CATALOGUE:
        if c.topic in excluded:continue
        status,result=check(c)
        if status==200 and result.get("status")=="V123_TOPIC_AVAILABLE" and result.get("sideEffects") is False:return c
        if status==422 and result.get("status")=="V123_TOPIC_DUPLICATE":continue
        raise StopSafely("Topic discovery unavailable; stop safely")
    return None
