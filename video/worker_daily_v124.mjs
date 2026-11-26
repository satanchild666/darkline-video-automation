// V12.4 trusted daily routes. Separate switch; no impact on image or approved one-off posting.
const V124_CAPTIONS={"quote":"Van egy ötleted, de még nem tudod, milyen adatokkal érdemes ajánlatot kérni? Megmutatjuk a Darkline Studio igényfelmérőjét, az árbecslőt és az egyeztetés menetét. Előzetes tájékozódás, kötelezettség nélkül.\n\nAnimált kabala, AI-narráció.\nhttps://darkline-studio.web.app/\n#DarklineStudio #Ajánlatkérés","prices":"Mit tartalmaz egy weboldalcsomag? A videóban a tájékoztató árakat, az alaptartalmat és a saját kezelőfelület szerepét járjuk körbe. A pontos ajánlat az igényeid alapján készül.\n\nAnimált kabala, AI-narráció.\nhttps://darkline-studio.web.app/\n#DarklineStudio #ÁtláthatóÁrazás","portfolio":"Mire jó egy egyedi digitális fejlesztés a mindennapokban? A Darkline Studio portfóliója és a RadnóTinta Scanner példája megmutatja, hogyan lehet egy konkrét üzleti feladathoz rendszert tervezni.\n\nAnimált kabala, AI-narráció.\nhttps://darkline-studio.web.app/\n#DarklineStudio #EgyediFejlesztés","portal":"Hol követhető egy egyeztetett digitális fejlesztés? A bemutató az ügyfélportál nyilvános belépési pontját és a közös munka lépéseit mutatja meg, valódi ügyféladatok megnyitása nélkül.\n\nAnimált kabala, AI-narráció.\nhttps://darkline-studio.web.app/\n#DarklineStudio #Ügyfélportál"};
async function dailyVideoV124(request,env,url){
  if(request.method!=="POST"||!isVideoAuthorized(request,env))return json({error:"Unauthorized"},403);
  try{
    const body=await getRequestJson(request),day=budapestTime(Date.now()).date;
    if(!env.POSTS_KV)throw Error("KV unavailable");
    const enabled=env.AUTO_VIDEO_DAILY_ENABLED==="true"&&env.AUTO_VIDEO_PUBLISH_ENABLED==="true";
    const genKey="video:v124:generation:"+day,pubKey="video:v12:publish:"+day;
    const previous=await env.POSTS_KV.get(pubKey,"json"),generation=await env.POSTS_KV.get(genKey,"json");
    if(url.pathname==="/video-v124-state"){
      if(body.date!==day)throw Error("Invalid date");
      return json({status:"V124_STATE_OK",dailyEnabled:enabled,publication:previous?.state||null,generation:generation?.state||null,sideEffects:false});
    }
    if(!Object.prototype.hasOwnProperty.call(V124_CAPTIONS,body.topic))throw Error("Unknown topic");
    const helpers=videoEditorialHelpers(makeVideoHelpers({bufferGraphql,findDarklineFacebookChannel,budapestTime,dsPostSemanticGuard,dsPostNorm,dsPostCore,dsPostSimilarity}),{dsPostCore,dsPostNorm,dsPostSimilarity,dsPostSemanticGuard});
    if(url.pathname==="/video-v124-topic"){
      if(body.caption!==V124_CAPTIONS[body.topic])throw Error("Unexpected caption");
      const channel=await helpers.findChannel(env);
      if(String(channel.channelName).trim().toLowerCase()!=="darkline studio"||!String(channel.service).toLowerCase().includes("facebook"))throw Error("Wrong destination");
      const history=await helpers.listPosts(env,channel);
      if(await helpers.semanticCheck(env,body.caption,history)!==true)return json({status:"V124_TOPIC_DUPLICATE",sideEffects:false},422);
      return json({status:"V124_TOPIC_AVAILABLE",topic:body.topic,historyCount:history.length,sideEffects:false});
    }
    if(!enabled)throw Error("Daily publishing disabled");
    if(body.date!==day||budapestTime(Date.now()).hour>=15)throw Error("Outside daily generation window");
    if(url.pathname==="/video-v124-reserve"){
      if(previous||generation)throw Error("Daily attempt already exists");
      // The GitHub workflow serializes requests; KV is not a distributed atomic lock.
      await env.POSTS_KV.put(genKey,JSON.stringify({state:"reserved",topic:body.topic,createdAt:new Date().toISOString()}),{expirationTtl:14*86400});
      return json({status:"V124_RESERVED",topic:body.topic});
    }
    if(url.pathname==="/video-v124-queue"){
      if(generation?.state!=="reserved"||generation.topic!==body.topic)throw Error("No matching daily attempt");
      if(body.caption!==V124_CAPTIONS[body.topic]||typeof body.dryRun!=="boolean")throw Error("Unexpected caption or mode");
      const q=body.quality||{};
      if(q.focal_scenes!==10||!Number.isFinite(q.min_projected_text_px)||q.min_projected_text_px<32)throw Error("Focal text check failed");
      const result=await queueVideo(env,body,helpers,{dryRun:body.dryRun});
      if(result.status==="SCHEDULED"||result.status==="ALREADY_SCHEDULED")await env.POSTS_KV.put(genKey,JSON.stringify({...generation,state:"scheduled",postId:result.postId}),{expirationTtl:14*86400});
      return json(result);
    }
    throw Error("Unknown daily route");
  }catch(error){
    const detail=String(error?.message||error).slice(0,180);
    return json({status:detail.startsWith("Semantic duplicate or closely related content; publishing stopped")?"V124_TOPIC_DUPLICATE":"V124_BLOCKED",detail},422);
  }
}
