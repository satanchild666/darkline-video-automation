"""Curated public-site advertising angles; no live account or demo form access.
Keep original V124 topics intact. Every new narration is checked against the
1000 UTF-8 byte budget and exact approved renderer's ten-scene contract.
"""
from daily_catalogue_v124 import Topic, TOPICS as ORIGINAL
from content_selection_v123 import caption
from heygen_budget_v126 import MAX_BYTES
import json

# Only public focal targets already present in the approved V114/V124 storyboard.
TARGETS={
 "hero":("home",".hero__copy"),"value":("home",".value-section"),
 "advisor":("home","#okos-ajanlo"),"problem":("home","#megoldaskereso"),
 "work":("home","#sajat-munkak"),"scanner":("home","heading:RadnóTinta Scanner"),
 "custom":("home","#egyedi"),"process":("home","#igy-dolgozunk"),
 "about":("home","#rolam"),"reviews":("home","#velemenyek"),
 "price":("prices","heading:Átlátható árazás"),
 "package":("prices","heading:Egyszerű, egyoldalas weboldal"),
 "admin":("prices","heading:Nem kell engem hívnod"),
 "portal":("home",".portal-spotlight__copy"),"login":("portal","heading:Ügyfélbelépés"),
 "estimate":("home","#ajanlatkeres"),"quote":("quote","heading:Beszéljük át, mire van szükséged"),
 "faq":("home","#gyik"),"contact":("home","#kapcsolat")
}
def topic(key,tag,copy,rows):
    return Topic(key,caption(copy,tag),tuple((title,*TARGETS[target],line) for title,target,line in rows))
NEW=(
topic("first_site","ElsőWeboldal","Most indítod a vállalkozásodat? Mutatjuk, hogyan gondold át az első üzleti weboldalad tartalmát, és milyen nyilvános felületeken tájékozódhatsz a lehetőségekről.",(
 ("Az első weboldalad","hero","Most indítod a vállalkozásodat, és szeretnél egy saját üzleti weboldalt?"),
 ("Kinek szól?","value","Gondold át, kiket szeretnél megszólítani, és milyen információt keresnek."),
 ("Egyoldalas kezdet","package","Az egyoldalas csomag jó kiindulópont lehet egy rövid, áttekinthető bemutatkozáshoz."),
 ("A kínálatod","advisor","Érdemes kiválasztani, milyen szolgáltatásokat szeretnél bemutatni az érdeklődőknek."),
 ("Bizalom","work","Ha már vannak elkészült munkáid, a bemutatásuk segíthet a tájékozódásban."),
 ("Elérhetőség","contact","Gondold át azt is, milyen módon szeretnéd fogadni a megkereséseket."),
 ("Frissítés","admin","A saját kezelőfelület később megkönnyítheti a tartalmak módosítását."),
 ("Kezdő keret","price","Nézd meg a tájékoztató árakat, és tervezz a saját kereted szerint."),
 ("Az indulás lépései","process","Az első beszélgetésen tisztázhatjuk, mi kerüljön a weboldaladra."),
 ("Kezdjük egyszerűen","quote","Írd le, mivel foglalkozol, és milyen célt szolgáljon az első oldalad.")
)),
topic("owner_edit","SajátKezelőfelület","Változik a nyitvatartásod vagy a szolgáltatásod leírása? Egy saját kezelőfelülettel az egyeztetett tartalmak módosítását nem kell minden alkalommal a fejlesztőre bíznod.",(
 ("Változó adatok","admin","Megváltozott egy szolgáltatásod leírása? Egy weboldalnak ezt is követnie kell."),
 ("Saját kezelés","admin","A saját kezelőfelület célja, hogy az egyeztetett tartalmakat te is módosíthasd."),
 ("Mi változik gyakran?","problem","Írd össze, mely adatok változnak nálad rendszeresen, akár hetente."),
 ("Mit tartalmaz?","package","A csomagoknál nézd meg, mely tartalmak kezelésére terjed ki az ajánlat."),
 ("Egyszerű feladatok","value","A mindennapi frissítés ne legyen összetettebb feladat a szükségesnél."),
 ("Egyedi igények","custom","Ha sajátos munkafolyamatod van, az admin felületet is ehhez lehet tervezni."),
 ("Példa a kezelésre","scanner","A bolti készlet és ár kezelése egy különálló digitális feladat példája."),
 ("Átadás","process","Az átadás előtt érdemes átbeszélni, hogyan fogod használni a rendszert."),
 ("Tudnivalók","faq","A gyakori kérdések segítenek tisztázni a további együttműködést."),
 ("Te irányítasz","quote","Mondd el, milyen tartalmakat szeretnél önállóan kezelni a mindennapokban.")
)),
topic("stock_workflow","Készletkezelés","Egy bolti leltárnál a készlet és az árak áttekintése külön feladat. A RadnóTinta Scanner példáján keresztül bemutatjuk, hogyan indulhat egy célzott digitális fejlesztés.",(
 ("Bolti mindennapok","scanner","Egy üzletben a készlet és az árak követése külön figyelmet igényel."),
 ("Megvalósított példa","work","A portfólióban a RadnóTinta Scanner egy konkrét bolti feladatra készült példa."),
 ("Készletadatok","scanner","A fejlesztés a bolti készletek és árak kezeléséhez kapcsolódik."),
 ("Kiindulás a feladatból","problem","Először érdemes megfigyelni, hol kell ugyanazt az adatot többször kezelni."),
 ("Saját igény","custom","Nem minden üzletben azonosak a feladatok, ezért a tervezés egyedi lehet."),
 ("Kezelői nézet","admin","Gondold át, kik kezelnék az adatokat, és mely mezőkre van szükségük."),
 ("Határok","process","A fejlesztés előtt külön tisztázzuk, milyen funkciókat kell megvalósítani."),
 ("Keret","estimate","A terjedelem ismeretében lehet reális költségeket tervezni."),
 ("Kapcsolat","contact","Egy rövid leírás is elég lehet ahhoz, hogy elinduljon az egyeztetés."),
 ("A saját üzleted","quote","Írd meg, melyik bolti feladatot szeretnéd egyszerűbbé tenni.")
)),
topic("service_contact","Szolgáltatók","Ha szolgáltatóként gyakran ugyanazokra a kérdésekre válaszolsz, gondold át, mely információkat érdemes egy saját oldalon, könnyen megtalálható helyen bemutatni.",(
 ("Ismétlődő kérdések","hero","Gyakran ugyanazokat a kérdéseket kapod a szolgáltatásaidról?"),
 ("A látogató célja","value","Egy érdeklődő először azt szeretné megérteni, miben tudsz segíteni neki."),
 ("Világos kínálat","package","A bemutatkozó oldalon a szolgáltatások áttekinthető helyet kaphatnak."),
 ("Tudd, mit keresnek","problem","Gyűjtsd össze a kérdéseket, amelyek új ügyfeleidnél rendszeresen felmerülnek."),
 ("Árak és feltételek","price","Döntsd el, mely árakat és feltételeket tudod előre nyilvánossá tenni."),
 ("Korábbi munka","work","A referenciák segíthetnek megmutatni, milyen feladatokkal foglalkozol."),
 ("Kérdések egy helyen","faq","A gyakori kérdések külön szakasza jó tájékozódási pont lehet."),
 ("Könnyű kapcsolat","contact","Legyen egyértelmű, milyen elérhetőségen kereshetnek meg."),
 ("Változások","admin","A kezelőfelület segíthet a változó információk naprakészen tartásában."),
 ("Tervezzük meg","quote","Meséld el, mire kérdeznek rá leggyakrabban, és tervezzünk ebből.")
)),
topic("restaurant_needs","Vendéglátás","Vendéglátóhelyként gondold át, hogyan találják meg a vendégeid a kínálatot, a nyitvatartást és az elérhetőséget. A videó egy igényfelmérési útmutató, nem kész étlaprendszer bemutatója.",(
 ("Vendéglátóhelyek","problem","Egy vendéglátóhely vendégei gyakran útközben keresnek információt."),
 ("Mit keresnek?","value","A kínálat, a nyitvatartás és a kapcsolatfelvétel fontos tájékozódási pont."),
 ("Gyakori változás","admin","Ha a kínálat gyakran változik, érdemes önálló tartalomkezelésben gondolkodni."),
 ("Egyszerű bemutatkozás","package","Egy rövid weboldal bemutathatja a hely hangulatát és fő információit."),
 ("Saját folyamat","custom","Összetettebb igény esetén külön digitális megoldást is lehet tervezni."),
 ("Kérdések","faq","Gondold át, milyen kérdésekre szeretnéd előre megadni a választ."),
 ("Kapcsolat","contact","A vendégek számára legyen könnyen megtalálható a megfelelő elérhetőség."),
 ("Terjedelem","estimate","Az igények összegyűjtése segít a fejlesztés terjedelmének tervezésében."),
 ("Egyeztetés","process","A megvalósítás előtt tisztázzuk, mi szerepeljen az első változatban."),
 ("A vendégeidért","quote","Írd meg, melyik információt keresik nálad leggyakrabban a vendégek.")
)),
topic("salon_needs","Szépségipar","Szalonod van? Az online bemutatkozásnál a szolgáltatások, a munkáid és az elérhetőség áttekinthetősége fontos. Így fogalmazhatod meg saját weboldalad igényeit.",(
 ("Szalonoknak","problem","Egy szalonnál sok érdeklődő a szolgáltatások és a munkák alapján tájékozódik."),
 ("Mutasd meg a munkád","work","Gondold át, mely referenciáidat szeretnéd bemutatni a saját oldaladon."),
 ("Szolgáltatáslista","package","A bemutatkozásban helyet kaphatnak a szolgáltatásaid rövid leírásai."),
 ("Tájékoztató árak","price","Döntsd el, mely árakat tudod előre egyértelműen megadni az érdeklődőknek."),
 ("Friss információ","admin","Ha a kínálat változik, a saját kezelőfelület lehet fontos szempont."),
 ("Kérdezési lehetőség","contact","Érdemes megtervezni, milyen módon szeretnéd fogadni a megkereséseket."),
 ("Külön funkciók","custom","Ha speciális igényed van, az első egyeztetésen beszéljük át a lehetőségeket."),
 ("Kiválasztás","advisor","Az ajánló segíthet átgondolni, milyen típusú megoldásra van szükséged."),
 ("Tervezés","process","A kialakítást a szalonod tényleges működéséhez érdemes igazítani."),
 ("Induljunk a szalonból","quote","Írd meg, hogyan szeretnéd bemutatni a szalonodat az interneten.")
)),
topic("workshop_needs","Autószerviz","Szervizt vezetsz? Mielőtt digitális rendszert választasz, gondold át, mely ügyfélkérdések és szervezési feladatok terhelik a mindennapjaidat.",(
 ("Műhelymunka","problem","Egy műhelyben munka közben nehéz minden érdeklődő kérdésére azonnal válaszolni."),
 ("Alapinformációk","package","A weboldalon áttekinthetően bemutathatod, milyen munkákat vállalsz."),
 ("Gyakori kérdések","faq","Érdemes összegyűjteni a visszatérő kérdéseket és a fontos feltételeket."),
 ("Megkeresések","contact","Gondold át, hogyan fogadod legszívesebben az új megkereséseket."),
 ("Szervezés","custom","Ha a szervezési feladatokon is könnyítenél, egyedi igényt is megfogalmazhatsz."),
 ("Helyes kiindulás","advisor","Az ajánló segítségével áttekintheted a különböző megoldási irányokat."),
 ("Karbantartás","admin","A változó szolgáltatásleírásokat érdemes könnyen kezelhetővé tenni."),
 ("Költségkeret","estimate","Gondold át, mely feladat a legfontosabb, és milyen keret áll rendelkezésre."),
 ("Egyeztetés","process","A pontos funkciókról a közös tervezés során születhet döntés."),
 ("Műhelyre szabva","quote","Írd le a műhelyed leggyakoribb szervezési nehézségét.")
)),
topic("project_scope","ProjektTervezés","A fejlesztés első lépése nem a programozás, hanem a feladat tisztázása. Nézzük meg, milyen kérdésekkel érdemes behatárolni egy digitális projekt első változatát.",(
 ("A cél tisztázása","process","Egy digitális projekt előtt fontos meghatározni, pontosan mi legyen a cél."),
 ("A valódi probléma","problem","Ne funkciólistával kezdj, hanem azzal, mely feladat okoz nehézséget."),
 ("Felhasználók","value","Gondold át, kik használják majd az elkészült megoldást a gyakorlatban."),
 ("Első változat","custom","Válaszd külön a nélkülözhetetlen funkciókat a későbbi ötletektől."),
 ("Meglévő példák","work","A portfólió segíthet elképzelni, milyen formája lehet egy fejlesztésnek."),
 ("Tartalmi feladat","admin","Tisztázd, mely adatokat kell később önállóan módosítanod."),
 ("Keret","estimate","Az előzetes becslés a terjedelem átgondolásához adhat támpontot."),
 ("Követés","portal","A meghívott ügyfelek a projekt követésére külön portált használhatnak."),
 ("Megállapodás","process","A vállalt feladatokat érdemes egyértelműen rögzíteni a fejlesztés előtt."),
 ("Kezdő kérdések","quote","Az ajánlatkérőben foglald össze, mi legyen az első változat célja.")
)),
topic("budget_priorities","FejlesztésiKeret","Szűkebb költségkerettel is érdemes sorrendbe állítani a digitális igényeket. A tájékoztató csomagok és az előzetes árbecslő a döntés előkészítését segítik.",(
 ("Tervezett kiadás","price","Egy kisebb vállalkozásnál különösen fontos előre átgondolni a fejlesztési kiadást."),
 ("Ami nélkülözhetetlen","problem","Írd össze azokat a problémákat, amelyek megoldása most a legfontosabb."),
 ("Alapcsomag","package","Nézd meg, mely feladatokat fedi le egy egyszerűbb csomag alaptartalma."),
 ("Saját kezelés","admin","A tartalmak későbbi kezelését is érdemes a tervezésbe belevenni."),
 ("Becslés","estimate","Az árbecslővel áttekintheted, hogyan állhat össze egy előzetes elképzelés."),
 ("Későbbi ötletek","custom","A későbbi bővítési igényeket külön is feljegyezheted az első változattól."),
 ("A döntés előtt","faq","A gyakori kérdésekben tájékozódhatsz az együttműködés további részleteiről."),
 ("Pontosítás","process","A végleges terjedelmet és költséget közös egyeztetés alapján határozzuk meg."),
 ("Kérdezz bátran","contact","Ha egy tájékoztató ár nem egyértelmű, kérdezz rá az elérhetőségeinken."),
 ("A te kereted","quote","Mondd el, milyen költségkerettel és elsődleges célokkal számolsz.")
)),
topic("references_trust","ÜzletiReferenciák","Milyen korábbi munkákat érdemes megmutatnod egy üzleti oldalon? A portfólió és a referenciák szerepéről, valamint a tartalmak átgondolásáról szól ez a bemutató.",(
 ("A munka beszél","work","Egy korábbi munka bemutatása segíthet az érdeklődőknek megérteni a tevékenységedet."),
 ("Konkrét példa","scanner","A RadnóTinta Scanner például egy bolti készletkezelési feladathoz kapcsolódik."),
 ("Mit mutass?","work","Válaszd ki azokat a példákat, amelyek jól szemléltetik, mivel foglalkozol."),
 ("Valódi szükséglet","problem","Egy referencia mellett érdemes elmondani, milyen problémára készült."),
 ("Visszajelzések","reviews","Az ügyfélvisszajelzéseknek is külön helyet lehet szánni az oldalon."),
 ("Bemutatkozás","about","A rövid bemutatkozás segít a látogatónak megismerni a vállalkozás szemléletét."),
 ("Új tartalmak","admin","Gondold át, hogyan szeretnéd a későbbi munkákat hozzáadni a bemutatkozásodhoz."),
 ("A látogatói út","package","Az áttekinthető elrendezés segíthet a megfelelő példák megtalálásában."),
 ("Kapcsolódás","contact","A referenciák mellett legyen könnyen elérhető a kapcsolatfelvétel."),
 ("Mutasd meg magad","quote","Írd meg, milyen munkákat szeretnél megmutatni a leendő ügyfeleidnek.")
)),
topic("choose_solution","DigitálisMegoldások","Nem biztos, hogy ugyanaz a digitális megoldás illik egy üzlethez és egy szolgáltatóhoz. Az okos ajánló és az igényfelmérő abban segít, hogy a saját feladatodból indulj ki.",(
 ("Nem egyforma igények","advisor","Egy üzlet és egy szolgáltató egészen eltérő digitális feladatokkal találkozhat."),
 ("A feladat kiválasztása","problem","A megoldáskeresőben a vállalkozás típusából és a problémából indulhatsz ki."),
 ("Bemutatkozó oldal","package","Lehet, hogy első lépésként elegendő egy áttekinthető bemutatkozás."),
 ("Kezelői feladat","admin","Máskor a változó adatok önálló módosítása a fontosabb szempont."),
 ("Saját rendszer","custom","Egyedi munkafolyamatnál érdemes külön rendszertervezésben gondolkodni."),
 ("Konkrét példák","work","A portfólióban különböző feladatokhoz készült megoldásokkal találkozhatsz."),
 ("Az ajánló szerepe","advisor","Az ajánló tájékozódást segít, nem helyettesíti a pontos egyeztetést."),
 ("Költségek","estimate","Az előzetes árbecslés segíthet a választható irányok mérlegelésében."),
 ("Kérdések","faq","Ha bizonytalan vagy, nézd át az együttműködésről szóló tudnivalókat."),
 ("A megfelelő irány","quote","Írd le a saját feladatodat, hogy közösen választhassunk megoldást.")
)),
topic("client_communication","Ügyfélkommunikáció","Egy digitális fejlesztésnél a tiszta kommunikáció legalább olyan fontos, mint a funkciólista. Bemutatjuk a nyilvános kapcsolati lehetőségeket és az ügyfélportál szerepét.",(
 ("Közös nyelv","about","Egy fejlesztés során fontos, hogy mindenki ugyanazt értse az egyeztetett feladat alatt."),
 ("Első kapcsolat","contact","Az első kérdéseket írásban is eljuttathatod hozzánk a nyilvános elérhetőségeken."),
 ("Kérdések összegyűjtése","quote","Az ajánlatkérő segítségével előre összefoglalhatod a legfontosabb igényeket."),
 ("Feladatok","process","A közös munka elején tisztázzuk a célokat és a vállalt terjedelmet."),
 ("Projektkövetés","portal","A meghívott ügyfelek külön portálon követhetik a projektjük állapotát."),
 ("Belépés","login","A nyilvános ügyfélbelépő a meghívott ügyfelek számára biztosít kiindulópontot."),
 ("Saját adatok","portal","Ebben a bemutatóban nem nyitunk meg valódi ügyfélprojektet vagy üzenetet."),
 ("Pontosítás","faq","Az együttműködés kérdéseit érdemes még a fejlesztés előtt tisztázni."),
 ("Visszajelzés","reviews","A visszajelzések segítenek megérteni, mely részleteken érdemes változtatni."),
 ("Beszéljük meg","contact","Ha kérdésed van, keresd meg a Darkline Studio nyilvános elérhetőségeit.")
)),
)
TOPICS=ORIGINAL+NEW
def validate_catalogue():
    assert len(NEW)==12 and len(TOPICS)==16
    assert len({t.key for t in TOPICS})==len(TOPICS)
    from itertools import combinations
    from video_dedup import script_similarity,script_text
    from daily_catalogue_v124 import plan
    for t in TOPICS:
        text=" ".join(r[3] for r in t.scenes)
        assert len(t.scenes)==10 and 500<=len(text)<=1000 and len(text.encode("utf8"))<=MAX_BYTES,(t.key,len(text.encode("utf8")))
        assert "AI-narráció" in t.text and "https://darkline-studio.web.app/" in t.text
        print("V1265_TOPIC",t.key,len(text.encode("utf8")),flush=True)
    for a,b in combinations(TOPICS,2):
        s=script_similarity(script_text(plan(a)),script_text(plan(b)))
        assert s<.80,(a.key,b.key,s)
    print("V1265_CATALOGUE_PASS",len(TOPICS),"topics; 120 new scenes; pairwise script guard",flush=True)
def manifest():
    return {t.key:t.text for t in NEW}
if __name__=="__main__":validate_catalogue()
