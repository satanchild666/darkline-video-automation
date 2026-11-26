// Small fail-closed patch for the existing monolithic Worker.
// No credentials, source download, deployment or publishing in this module.
export function patchWorker(src) {
  function one(old,replacement){
    if(src.split(old).length!==2)throw Error("Expected exactly one anchor: "+old.slice(0,90));
    src=src.replace(old,replacement);
  }
  one("async function sendDraftToBuffer(env, draft, confirmedRetry = false, queueForPublishing = false, dueAt = null) {",
      "async function sendDraftToBuffer(env, draft, confirmedRetry = false, queueForPublishing = false, dueAt = null, v126Morning = false) {");
  one("  if (queueForPublishing && !(env.AUTO_BUFFER_DRAFTS_ENABLED === 'true' &&\n        env.AUTO_BUFFER_QUEUE_ENABLED === 'true')) {",
      "  const v126Allowed = v126Morning === true && env.AUTO_V126_MORNING_ENABLED === 'true' && env.AUTO_BUFFER_QUEUE_ENABLED === 'false' && !!dueAt && budapestTime(Date.parse(dueAt)).hour === 10 && budapestTime(Date.parse(dueAt)).minute === 0 && !!draft.imageUrl && !draft.videoUrl;\n  if (queueForPublishing && !(env.AUTO_BUFFER_DRAFTS_ENABLED === 'true' &&\n        (env.AUTO_BUFFER_QUEUE_ENABLED === 'true' || v126Allowed))) {");
  one("async function dsScheduledFacebookSlot(env,local,scheduledTime){\n  if(env.AUTO_BUFFER_QUEUE_ENABLED!=='true'||env.AUTO_BUFFER_DRAFTS_ENABLED!=='true'||env.AUTO_IMAGE_DRAFTS_ENABLED!=='true'||!env.POSTS_KV)return;\n  const targetHour=local.hour===8?9:local.hour===15?16:null;",
      "async function dsScheduledFacebookSlot(env,local,scheduledTime,v126Morning=false){\n  const enabled=v126Morning ? env.AUTO_V126_MORNING_ENABLED==='true'&&env.AUTO_BUFFER_QUEUE_ENABLED==='false' : env.AUTO_BUFFER_QUEUE_ENABLED==='true';\n  if(!enabled||env.AUTO_BUFFER_DRAFTS_ENABLED!=='true'||env.AUTO_IMAGE_DRAFTS_ENABLED!=='true'||!env.POSTS_KV)return;\n  const targetHour=v126Morning?(local.hour===9?10:null):(local.hour===8?9:local.hour===15?16:null);");
  one("const result=await sendDraftToBuffer(env,post,false,true,dueAt);","const result=await sendDraftToBuffer(env,post,false,true,dueAt,v126Morning);");
  one("if(targetHour===9){","if(targetHour===9||v126Morning&&targetHour===10){");
  one("    if(['/video-v124-state','/video-v124-topic','/video-v124-reserve','/video-v124-queue'].includes(url.pathname))return dailyVideoV124(request,env,url);",
      "    if(url.pathname==='/posts-v126-morning')return v126MorningRoute(request,env);\n    if(['/video-v124-state','/video-v124-topic','/video-v124-reserve','/video-v124-queue'].includes(url.pathname))return dailyVideoV124(request,env,url);");
  // If the morning route owns today's image slot, the old draft automation must
  // not create a duplicate in the same time window. Lead research stays untouched.
  one("}else if(env.AUTO_IMAGE_DRAFTS_ENABLED==='true'&&env.POSTS_KV&&local.hour>=9&&local.hour<21){",
      "}else if(env.AUTO_V126_MORNING_ENABLED==='true'){\n      if(local.minute===30&&local.hour>=11&&local.hour<=19){try{await dsRefillPostBuffer(env,local);}catch(e){console.warn('Darkline reserve refill:',String(e).slice(0,180));}}\n    }else if(env.AUTO_IMAGE_DRAFTS_ENABLED==='true'&&env.POSTS_KV&&local.hour>=9&&local.hour<21){");
  src += "\n"+morningRoute+"\n";
  return src;
}
const morningRoute = [
"async function v126MorningRoute(request,env){",
"  if(request.method!=='POST'||!isVideoAuthorized(request,env))return json({error:'Unauthorized'},403);",
"  try{",
"    const body=await getRequestJson(request),now=Date.now(),local=budapestTime(now);",
"    if(body.date!==local.date||typeof body.dryRun!=='boolean'||!env.POSTS_KV)throw Error('Invalid date/mode or missing KV');",
"    const helpers=makeVideoHelpers({bufferGraphql,findDarklineFacebookChannel,budapestTime,dsPostSemanticGuard,dsPostNorm,dsPostCore,dsPostSimilarity});",
"    const channel=await helpers.findChannel(env);",
"    if(!channel?.channelId||String(channel.channelName).trim().toLowerCase()!=='darkline studio'||!String(channel.service).toLowerCase().includes('facebook'))throw Error('Wrong destination');",
"    const posts=await helpers.listPosts(env,channel);",
"    if(!Array.isArray(posts)||posts.some(p=>!p.id||!p.status))throw Error('History incomplete');",
"    const enabled=env.AUTO_V126_MORNING_ENABLED==='true'&&env.AUTO_BUFFER_QUEUE_ENABLED==='false'&&env.AUTO_BUFFER_DRAFTS_ENABLED==='true'&&env.AUTO_IMAGE_DRAFTS_ENABLED==='true';",
"    const prior=await env.POSTS_KV.get('posts:v3:slot:'+local.date+':10','json');",
"    if(body.dryRun)return json({status:'V126_MORNING_PREFLIGHT_OK',enabled,historyCount:posts.length,slotState:prior?.status||null,sideEffects:false});",
"    if(!enabled||local.hour!==9||local.minute>=30||prior)throw Error('Morning slot disabled, occupied or outside window');",
"    // Caller is the single serialized GitHub publisher; no fallback or retries after an ambiguous mutation.",
"    const stamp=Math.floor(now/1800000)*1800000;",
"    const result=await dsScheduledFacebookSlot(env,budapestTime(stamp),stamp,true);",
"    if(!result||!['scheduled','existing'].includes(result.status))throw Error('Morning outcome not confirmed');",
"    return json({status:'V126_MORNING_'+result.status.toUpperCase(),dueAt:result.dueAt,postId:result.bufferPostId||null});",
"  }catch(e){return json({status:'V126_MORNING_BLOCKED',detail:String(e?.message||e).slice(0,180)},422);}",
"}"
].join("\n");
