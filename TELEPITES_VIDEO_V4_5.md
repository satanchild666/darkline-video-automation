# Darkline Studio AI Growth V4.5.0 – Automatikus videómodul

Ez a csomag a **bizonyítottan működő V4.4.1-re épül**, nem egy új, külön marketingrendszer. A képes napi Cloudflare Cron és a meglévő Buffer-piszkozatok változatlanul megmaradnak.

## Mit csinál?

- Minden nap 13:17-kor (Budapest időzóna) a GitHub Actions magától elindul a felhőben, kikapcsolt laptop mellett is.
- HTTPS-en, a már beállított `AI_TEST_TOKEN` segítségével meghívja a Cloudflare Worker `/video-plan` végpontját.
- A Cloudflare Worker beolvassa a **https://darkline-studio.web.app/** nyilvános fő-, bemutató- és ajánlatoldalait; a meglévő Workers AI négy rövid, magyar jelenetből álló videóforgatókönyvet és egy posztszöveget ír.
- A videó felhasználhatja ugyanazon a napon **már elkészített** AI-képet, **új képgenerálási kvóta nélkül**.
- A GitHub Actions futtatja a FFmpeg-alapú, egyedi animált videókészítőt: 720x1280, 9:16, ~18 másodperc, MP4/H.264 + egyedi, egyszerű, jogtiszta szintetizált háttérhang. Ezek **animált grafikai reklámvideók**, nem filmszerű videógeneráló modellel létrehozott mozgó jelenetek.
- A nyilvános videót az adott napi **GitHub Release** tárolja, ahonnan a Buffer API hozzáférhet.
- A Worker saját, létező `BUFFER_API_KEY` titkával új **Facebook-videópiszkozatot** hoz létre a Darkline Studio csatornán. NEM publikálja, NEM sorolja be a közzétételi sorba.
- Ugyanazon nap ismételt futásnál a Release-t újrahasználja, és nem hoz létre ismétlődő Buffer-piszkozatot.

## Egyszeri telepítés

### 1. Cloudflare Worker V4.5 kódfrissítés

A Cloudflare `darkline-ai-growth` Worker **Edit code** szerkesztőjében a **worker.js** teljes tartalmát használd. A ZIP-ből a `worker.js` a V4.4.1 már kipróbált kódja, a videós bővítéssel. A meglévő kódot előtte mentsd el. A változók és kötések maradjanak változatlanok.

**Settings → Variables and secrets → Add variable**, Text:

- `AUTO_VIDEO_DRAFTS_ENABLED` = `true`
- `VIDEO_GITHUB_REPO` = `<github-felhasznalonev>/darkline-video-automation`

Az összes jelenlegi változó és kötés (`AI`, `IMAGES`, `POSTS_KV`, `BUFFER_API_KEY`, `AI_TEST_TOKEN`, az image/Buffer kapcsolók) marad.

### 2. GitHub nyilvános repo

Hozz létre GitHubon egy **Public** repót **darkline-video-automation** néven. A videók nyilvánosan elérhető MP4-fájlok lesznek; különben a Buffer nem tudja letölteni őket. A kódban nincs API-kulcs.

A GitHub repó gyökerébe kerüljenek a ZIP-ből:

- `.github/workflows/darkline-video.yml`
- `video/render_video.py`
- `video/publish_automation.py`

A `worker.js` nem szükséges a Github repóba; a Cloudflare tartalmazza. Opcionálisan hozzáadhatod a `TELEPITES_VIDEO_V4_5.md` útmutatót.

### 3. Egyetlen titok a GitHubon

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

- Name: `DARKLINE_TEST_TOKEN`
- Secret: ugyanaz a hosszú, titkos token, amelyet a Cloudflare `AI_TEST_TOKEN` változóhoz használunk.

A Buffer kulcsát **nem** kell GitHubba átmásolni. A tokent **ne** írd bele fájlba, commitba, üzenetbe vagy képernyőképbe. Ha a jelenlegi PowerShell-session még megvan, a vágólapra másolhatod: `$global:DarklineAiToken | Set-Clipboard` és közvetlenül beillesztheted a GitHub Secret mezőbe (ezt követően töröld a vágólapról).

### 4. Működés

A workflow a `main` alapértelmezett ágon, Budapest szerint **13:17-kor** automatikusan indul. Az első napi próba az **Actions → Darkline Studio - daily AI promotional video → Run workflow** gombbal végezhető, a titok beállítása és a kód telepítése után. Ez ténylegesen videót és Buffer-piszkozatot hoz létre: **nem csupán olvasóteszt**.

**Ne indítsd el**, amíg a fenti három lépés nem kész. A GitHub órához kötött indítások esetenként késhetnek; ez platformkorlát. Ha az automatizmus nem indul, a GitHub Actions naplóban ellenőrizd. Nyilvános reposioryban 60 nap aktivitás nélkül a GitHub letilthatja az időzítéseket; a workflow sikeres naponta lefutó commitja ezt igyekszik megelőzni.

## Aktuális változók

A Cloudflare status (`GET /`) új mezői:

- `automaticVideoDraftsEnabled` – videópiszkozat készítés bekapcsolva
- `videoGitHubRepoConfigured` – megadott GitHub repo
- `facebookPublishing` – a korábbi képes rendszer változatlan felügyelete alatt marad, alapállapotban `false`

A képes posztok meglévő 10:00/10:30 automatikus futása érintetlen.

## Ingyenes működés és korlátok

- Public GitHub Actions: standard runners jelenleg díjmentesek; egy privát repo és a fizetős API/videómodellek ezt megváltoztathatják.
- A Cloudflare AI ingyenes napi neuronkerete és a napi limit továbbra is vonatkozik a forgatókönyvre és a már beállított képkészítésre. A program nem vásárol automatikusan kreditet.
- A videók eredeti animált tipográfiából, saját szintetikus háttérhangból és opcionálisan a meglévő, naponta generált márkázott képből állnak. **Nem generálnak élőszereplős mozgó videót vagy beszédhangot**; ilyen AI-modellek ingyenes, garantált napi használatát nem tudjuk vállalni.
- A Facebookra kizárólag **piszkozat** kerül. A végleges közzétételt továbbra is te kontrollálod.
- A videó nyilvános GitHub Releases MP4 URL-jét a Buffernek le kell tudnia töltenie. A tényleges Buffer-kompatibilitást az első felhős futás fogja megerősíteni.

## Ellenőrzött helyi tesztek

- `node --check worker.js`
- `node tests/video_worker_test.mjs` – videóterv, cache, Buffer-piszkozat, dupla próbálkozás, URL-védelem, publikálás letiltása
- `python -m py_compile video/*.py`
- `python video/render_video.py --plan video_demo_plan.json --output demo.mp4` – MP4 tényleges renderelése

A korábbi V4.4.1 éles Buffer-piszkozatai megmaradnak, az éles Cloudflare-/GitHub-telepítés a ZIP átadása pillanatában még **NEM történt meg**.
