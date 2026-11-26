"""V12.4 grounded catalogue: each scene is tied to a previously verified public website section.
Topic rotation is bounded. If all candidates repeat previous content, stop instead of recycling."""
from dataclasses import dataclass
from content_selection_v123 import caption
@dataclass(frozen=True)
class Topic:
    key:str
    text:str
    scenes:tuple
# Each scene: title, public page key, previously verified selector, spoken sentence.
TOPICS=(
 Topic("quote",caption("Van egy ötleted, de még nem tudod, milyen adatokkal érdemes ajánlatot kérni? Megmutatjuk a Darkline Studio igényfelmérőjét, az árbecslőt és az egyeztetés menetét. Előzetes tájékozódás, kötelezettség nélkül.","Ajánlatkérés"),(
  ("Mivel kezdjem?","home","#okos-ajanlo","Nem kell kész műszaki tervvel érkezned, ha még csak körvonalazódik az elképzelésed."),
  ("A vállalkozásod igényei","home","#megoldaskereso","Először azt érdemes tisztázni, milyen mindennapi feladatot szeretnél egyszerűbbé tenni."),
  ("Milyen lehetőségek vannak?","home","#okos-ajanlo","Az okos ajánlóban tájékozódhatsz a különböző digitális megoldásokról."),
  ("Előzetes árbecslés","home","#ajanlatkeres","Az árbecslő segíthet átgondolni, milyen szolgáltatásokra lehet szükséged."),
  ("Egyedi elképzelések","home","#egyedi","Ha egyik kész csomag sem illik hozzád, az egyedi fejlesztés lehetőségéről is egyeztethetünk."),
  ("Így kérhetsz ajánlatot","quote","heading:Beszéljük át, mire van szükséged","Az ajánlatkérő oldal néhány kérdéssel segít összefoglalni az igényeidet."),
  ("Az egyeztetés menete","home","#igy-dolgozunk","A fejlesztés előtt közösen tisztázzuk a feladatot és a vállalható terjedelmet."),
  ("További tudnivalók","home","#gyik","A gyakori kérdések között további információkat találsz az együttműködésről."),
  ("Írásban is elérsz","home","#kapcsolat","Ha valamiben bizonytalan vagy, az oldalon található elérhetőségeken is kérdezhetsz."),
  ("Kötetlen első lépés","quote","heading:Beszéljük át, mire van szükséged","A Darkline Studio oldalán ingyenesen, kötelezettség nélkül kérhetsz személyre szabott ajánlatot."),
 )),
 Topic("prices",caption("Mit tartalmaz egy weboldalcsomag? A videóban a tájékoztató árakat, az alaptartalmat és a saját kezelőfelület szerepét járjuk körbe. A pontos ajánlat az igényeid alapján készül.","ÁtláthatóÁrazás"),(
  ("Tervezhető indulás","prices","heading:Átlátható árazás","Egy digitális fejlesztés előtt fontos tudni, milyen lehetőségek közül választhatsz."),
  ("Csomagok és alaptartalom","prices","heading:Egyszerű, egyoldalas weboldal","A szolgáltatások oldalán a csomagok tartalmát és tájékoztató induló árait találod."),
  ("Mi illik hozzád?","home","#okos-ajanlo","Az ajánló segít eligazodni, ha még nem világos, melyik megoldás felel meg az igényeidnek."),
  ("Nem csak a kezdőár","home","#ajanlatkeres","Az árbecslővel további igényeket is átgondolhatsz a tervezés során."),
  ("Saját kezelőfelület","prices","heading:Nem kell engem hívnod","Az alapcsomagok mellé saját kezelőfelület is tartozik a megfelelő tartalmak kezeléséhez."),
  ("Egyedi fejlesztés","home","#egyedi","Ha a csomagokon túlmutató rendszerre van szükséged, arról külön egyeztethetünk."),
  ("Átlátható folyamat","home","#igy-dolgozunk","A pontos feladatot az első egyeztetéstől az átadásig követhető lépésekben beszéljük át."),
  ("Gyakori kérdések","home","#gyik","A további tudnivalókat az együttműködésről a gyakori kérdések között találod."),
  ("Pontos ajánlat","quote","heading:Beszéljük át, mire van szükséged","A végleges ajánlat az igényeid alapján, a vállalt feladatok pontosításával készül."),
  ("Nézd meg a csomagokat","prices","heading:Átlátható árazás","Látogass el a Darkline Studio szolgáltatási oldalára, és nézd meg, mi illik a vállalkozásodhoz."),
 )),
 Topic("portfolio",caption("Mire jó egy egyedi digitális fejlesztés a mindennapokban? A Darkline Studio portfóliója és a RadnóTinta Scanner példája megmutatja, hogyan lehet egy konkrét üzleti feladathoz rendszert tervezni.","EgyediFejlesztés"),(
  ("Valódi üzleti feladatok","home","#sajat-munkak","Egy fejlesztés akkor hasznos, ha a vállalkozásod tényleges feladataihoz kapcsolódik."),
  ("Egy bolti példa","home","heading:RadnóTinta Scanner","A RadnóTinta Scanner a bolti készletek és árak kezeléséhez készült fejlesztés."),
  ("Mi jelent kihívást?","home","#megoldaskereso","Más nehézségekkel találkozik egy üzlet, egy szolgáltató vagy egy másféle vállalkozás."),
  ("A saját igényed","home","#egyedi","Ezért egyedi igények esetén nem feltétlenül egy kész csomagból kell kiindulni."),
  ("Megoldások áttekintése","home","#okos-ajanlo","Az okos ajánló segítségével áttekintheted a szóba jöhető megoldásokat."),
  ("Korábbi munkák","home","#sajat-munkak","A portfólióban további megvalósított fejlesztésekkel is megismerkedhetsz."),
  ("Az első egyeztetés","home","#igy-dolgozunk","A közös munka során először azt tisztázzuk, pontosan mit szeretnél elérni."),
  ("Követhető projekt","home",".portal-spotlight__copy","A meghívott ügyfelek számára a projekt követéséhez külön ügyfélportál áll rendelkezésre."),
  ("Mondd el az ötleted","quote","heading:Beszéljük át, mire van szükséged","Az ajánlatkérő segítségével összefoglalhatod, milyen fejlesztésben gondolkodsz."),
  ("Fedezd fel a példákat","home","#sajat-munkak","Nézd meg a Darkline Studio korábbi munkáit, és gondold át, nálad min lenne érdemes változtatni."),
 )),
 Topic("portal",caption("Hol követhető egy egyeztetett digitális fejlesztés? A bemutató az ügyfélportál nyilvános belépési pontját és a közös munka lépéseit mutatja meg, valódi ügyféladatok megnyitása nélkül.","Ügyfélportál"),(
  ("A projekted egy helyen","home",".portal-spotlight__copy","Egy fejlesztés során fontos, hogy tudd, hol tartanak a közösen egyeztetett feladatok."),
  ("Meghívott ügyfeleknek","portal","heading:Ügyfélbelépés","Az ügyfélportál belépési felülete a meghívott ügyfelek saját projektjeihez vezet."),
  ("Mi előzi meg a projektet?","home","#igy-dolgozunk","A közös munka első lépése a feladatok és az igények tisztázása."),
  ("Ajánlatkérés fiók nélkül","quote","heading:Beszéljük át, mire van szükséged","Az ajánlatkéréshez nem szükséges ügyfélfiók, az első kapcsolatfelvétel külön történik."),
  ("A projekt követése","home",".portal-spotlight__copy","Az ügyfélportálon a meghívott ügyfelek a projekt állapotát, ajánlatát és üzeneteit követhetik."),
  ("Nyilvános belépési pont","portal","heading:Ügyfélbelépés","A videóban csak a nyilvános belépési felületet mutatjuk meg, ügyféladatokat nem nyitunk meg."),
  ("Mit vállalunk?","home","#igy-dolgozunk","A fejlesztés lépéseit előzetesen egyeztetjük, hogy követhető legyen a munkafolyamat."),
  ("Kérdések és válaszok","home","#gyik","Az együttműködéssel kapcsolatos tudnivalókról a gyakori kérdések között tájékozódhatsz."),
  ("Kapcsolatfelvétel","home","#kapcsolat","Ha kérdésed van a folyamattal kapcsolatban, írásban is felveheted velünk a kapcsolatot."),
  ("Ismerd meg az ügyfélportált","home",".portal-spotlight__copy","A Darkline Studio oldalán többet is megtudhatsz arról, hogyan követhetők a közös projektek."),
 )),
)
def validate_catalogue():
    assert len({t.key for t in TOPICS})==len(TOPICS)
    for t in TOPICS:
        assert len(t.scenes)==10
        assert 500<=len(" ".join(r[3] for r in t.scenes))<=1000
        assert all(r[1] in ("home","prices","quote","portal") for r in t.scenes)
        assert "AI-narráció" in t.text and "https://darkline-studio.web.app/" in t.text
def plan(topic):
    return {"scenes":[{"heading":r[0],"detail":r[3]} for r in topic.scenes]}
