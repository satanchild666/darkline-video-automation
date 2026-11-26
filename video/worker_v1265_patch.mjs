// Candidate patch for V117; never deploy automatically.
export function patchWorker(src,captions){
  function one(old,replacement){
    if(src.split(old).length!==2)throw Error("Expected one anchor: "+old.slice(0,100));
    src=src.replace(old,replacement);
  }
  if(Object.keys(captions).length!==12||Object.entries(captions).some(([k,v])=>!/^[a-z_]{3,30}$/.test(k)||typeof v!=="string"||!v.includes("AI-narráció")||!v.includes("https://darkline-studio.web.app/")))throw Error("Invalid manifest");
  const matches=src.match(/^const V124_CAPTIONS=(\{[^\n]+\});$/m);
  if(!matches)throw Error("Missing V124 caption allowlist");
  const original=JSON.parse(matches[1]);
  if(Object.keys(original).length!==4||Object.keys(captions).some(k=>k in original))throw Error("Unexpected original catalogue");
  one(matches[0],"const V124_CAPTIONS="+JSON.stringify({...original,...captions})+";");
  one("const v126Allowed = v126Morning === true && env.AUTO_V126_MORNING_ENABLED === 'true' && env.AUTO_BUFFER_QUEUE_ENABLED === 'false' && !!dueAt && budapestTime(Date.parse(dueAt)).hour === 10 && budapestTime(Date.parse(dueAt)).minute === 0 && !!draft.imageUrl && !draft.videoUrl;",
      "const v126Allowed = ((v126Morning === true && env.AUTO_V126_MORNING_ENABLED === 'true' && !!dueAt && budapestTime(Date.parse(dueAt)).hour === 10) || (v126Morning === 'fallback' && env.AUTO_V126_FALLBACK_ENABLED === 'true' && !!dueAt && budapestTime(Date.parse(dueAt)).hour === 16)) && env.AUTO_BUFFER_QUEUE_ENABLED === 'false' && budapestTime(Date.parse(dueAt)).minute === 0 && !!draft.imageUrl && !draft.videoUrl;");
  one("const enabled=v126Morning ? env.AUTO_V126_MORNING_ENABLED==='true'&&env.AUTO_BUFFER_QUEUE_ENABLED==='false' : env.AUTO_BUFFER_QUEUE_ENABLED==='true';",
      "const enabled=v126Morning==='fallback' ? env.AUTO_V126_FALLBACK_ENABLED==='true'&&env.AUTO_BUFFER_QUEUE_ENABLED==='false' : v126Morning===true ? env.AUTO_V126_MORNING_ENABLED==='true'&&env.AUTO_BUFFER_QUEUE_ENABLED==='false' : env.AUTO_BUFFER_QUEUE_ENABLED==='true';");
  one("const targetHour=v126Morning?(local.hour===9?10:null):(local.hour===8?9:local.hour===15?16:null);",
      "const targetHour=v126Morning==='fallback'?(local.hour===15?16:null):v126Morning===true?(local.hour===9?10:null):(local.hour===8?9:local.hour===15?16:null);");
  one("if(url.pathname==='/posts-v126-morning')return v126MorningRoute(request,env);",
      "if(url.pathname==='/posts-v126-morning')return v126MorningRoute(request,env);\n    if(url.pathname==='/posts-v1265-fallback')return v1265FallbackRoute(request,env);");
  one("if(url.pathname===\"/video-v124-reserve\"){\n      if(previous||generation)throw Error(\"Daily attempt already exists\");",
      "if(url.pathname===\"/video-v124-reserve\"){\n      if(await env.POSTS_KV.get('posts:v1265:fallback:'+day,'json'))throw Error('Afternoon image already reserved');\n      if(previous||generation)throw Error(\"Daily attempt already exists\");");
  one("if(url.pathname===\"/video-v124-queue\"){\n      if(generation?.state!==\"reserved\"||generation.topic!==body.topic)throw Error(\"No matching daily attempt\");",
      "if(url.pathname===\"/video-v124-queue\"){\n      if(await env.POSTS_KV.get('posts:v1265:fallback:'+day,'json'))throw Error('Afternoon image already reserved');\n      if(generation?.state!==\"reserved\"||generation.topic!==body.topic)throw Error(\"No matching daily attempt\");");
  return src+"\n"+fallbackSource+"\n";
}
export const fallbackSource = [
"async function v1265FallbackRoute(request,env){",
"  if(request.method!=='POST'||!isVideoAuthorized(request,env))return json({error:'Unauthorized'},403);",
"  try{",
"    const body=await getRequestJson(request),now=Date.now(),local=budapestTime(now);",
"    if(body.date!==local.date||typeof body.dryRun!=='boolean'||!env.POSTS_KV)throw Error('Invalid date/mode or missing KV');",
"    const key='posts:v1265:fallback:'+local.date;",
"    const video=await env.POSTS_KV.get('video:v12:publish:'+local.date,'json');",
"    const gen=await env.POSTS_KV.get('video:v124:generation:'+local.date,'json');",
"    const prior=await env.POSTS_KV.get(key,'json');",
"    const image=await env.POSTS_KV.get('posts:v3:slot:'+local.date+':16','json');",
"    const enabled=env.AUTO_V126_FALLBACK_ENABLED==='true'&&env.AUTO_BUFFER_QUEUE_ENABLED==='false'&&env.AUTO_BUFFER_DRAFTS_ENABLED==='true'&&env.AUTO_IMAGE_DRAFTS_ENABLED==='true';",
"    const clear=!video&&!gen&&!prior&&!image;",
"    if(body.dryRun)return json({status:'V1265_FALLBACK_PREFLIGHT_OK',enabled,clear,video:video?.state||null,generation:gen?.state||null,prior:prior?.status||null,image:image?.status||null,sideEffects:false});",
"    if(!enabled||!clear||local.hour!==15||local.minute>=30)throw Error('Fallback not safe, disabled or outside window');",
"    // Caller has an independent create-only GitHub post claim and proved no public release.",
"    // Block further video attempts before any image generation or Buffer mutation.",
"    await env.POSTS_KV.put(key,JSON.stringify({status:'reserved',date:local.date}),{expirationTtl:14*86400});",
"    const stamp=Math.floor(now/1800000)*1800000;",
"    const r=await dsScheduledFacebookSlot(env,budapestTime(stamp),stamp,'fallback');",
"    if(!r||!['scheduled','existing'].includes(r.status))throw Error('Fallback result uncertain; no retry');",
"    await env.POSTS_KV.put(key,JSON.stringify({status:r.status,date:local.date,postId:r.bufferPostId||null}),{expirationTtl:14*86400});",
"    return json({status:'V1265_FALLBACK_'+r.status.toUpperCase(),dueAt:r.dueAt,postId:r.bufferPostId||null});",
"  }catch(e){return json({status:'V1265_FALLBACK_BLOCKED',detail:String(e?.message||e).slice(0,180)},422);}",
"}"
].join("\n");
