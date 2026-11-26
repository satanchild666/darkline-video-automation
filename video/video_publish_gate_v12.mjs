// V12: independent video publishing gate. Do not enable the global image queue.
// Integrate with the existing Worker by injecting its authenticated Buffer and time helpers.
export function validateVideoRelease(body,repo,localDate){
  if(!body||body.version!=="V12"||body.date!==localDate)throw Error("Invalid video version/date");
  if(!/^[\w.-]+\/[\w.-]+$/.test(repo||""))throw Error("Invalid repository");
  const expected="https://github.com/"+repo+"/releases/download/darkline-v12-"+localDate+"/darkline-v12-"+localDate+".mp4";
  if(body.videoUrl!==expected)throw Error("Unexpected public release URL");
  if(!/^[a-f0-9]{64}$/.test(body.sha256||""))throw Error("Missing video SHA256");
  const q=body.quality||{};
  if(q.review_gate!=="PASS"||!Array.isArray(q.reasons)||q.reasons.length||!Number.isFinite(q.seconds)||q.seconds<30||q.seconds>120||q.width!==1080||q.height!==1920||q.fps!==30||!Number.isFinite(q.speech_seconds)||q.speech_seconds/q.seconds<.9||!Number.isFinite(q.audio_peak)||q.audio_peak<=0||q.audio_peak>=.999||q.overlay_dom_checks!=="passed"||q.dedup!=="PASS"||q.decode!=="PASS"||q.mascot!==true||q.readability!=="PASS")throw Error("Video quality gate rejected");
  if(typeof body.caption!=="string"||body.caption.length<60||body.caption.length>2000||!body.caption.includes("https://darkline-studio.web.app/")||!body.caption.includes("AI-narráció"))throw Error("Invalid caption");
  if(!Number.isFinite(Date.parse(body.dueAt)))throw Error("Invalid scheduled time");
  return {videoUrl:expected,sha256:body.sha256,caption:body.caption.trim(),dueAt:new Date(body.dueAt).toISOString()};
}
const normalize=s=>String(s||"").toLocaleLowerCase("hu").normalize("NFKC").replace(/\s+/g," ").trim();
export async function queueVideo(env,body,helpers,{dryRun=true}={}){
  const {now,localTime,findChannel,listPosts,semanticCheck,mutate}=helpers;
  if(!env.POSTS_KV)throw Error("KV missing");
  const t=now(),day=localTime(t).date;
  const v=validateVideoRelease(body,env.VIDEO_GITHUB_REPO,day);
  const due=Date.parse(v.dueAt),local=localTime(due);
  if(local.date!==day||local.hour!==16||local.minute!==0||due-t<300000)throw Error("Outside reserved video slot");
  if(!dryRun&&env.AUTO_VIDEO_PUBLISH_ENABLED!=="true")throw Error("Video publishing disabled");
  const key="video:v12:publish:"+day;
  const previous=await env.POSTS_KV.get(key,"json");
  if(previous){
    if(previous.sha256!==v.sha256)throw Error("Different video already registered");
    if(previous.state==="scheduled")return {status:"ALREADY_SCHEDULED",postId:previous.postId,dueAt:previous.dueAt};
    throw Error("Previous attempt unresolved; never retry automatically");
  }
  const channel=await findChannel(env);
  if(!channel?.channelId||String(channel.channelName).trim().toLowerCase()!=="darkline studio"||!String(channel.service).toLowerCase().includes("facebook"))throw Error("Wrong destination");
  const posts=await listPosts(env,channel);
  if(!Array.isArray(posts)||posts.some(p=>!p.id||!p.status))throw Error("History incomplete");
  const active=posts.filter(p=>p.status!=="draft"&&p.status!=="error");
  const sameDay=active.filter(p=>{const d=Date.parse(p.dueAt||p.sentAt);return Number.isFinite(d)&&localTime(d).date===day});
  if(sameDay.length>=2||sameDay.some(p=>Math.abs(Date.parse(p.dueAt||p.sentAt)-due)<30*60000))throw Error("Daily limit or slot occupied");
  if(posts.some(p=>normalize(p.text)===normalize(v.caption)))throw Error("Duplicate caption");
  if(await semanticCheck(env,v.caption,posts)!==true)throw Error("Semantic duplicate check did not pass");
  if(dryRun)return {status:"DRY_RUN_OK",channel:channel.channelName,dueAt:v.dueAt,sideEffects:false};
  // The caller must be the single serialized GitHub publisher. KV is not an atomic lock.
  // Persist before mutation; a network error leaves an uncertain record, never retry.
  await env.POSTS_KV.put(key,JSON.stringify({state:"submitting",sha256:v.sha256,dueAt:v.dueAt}));
  try{
    const result=await mutate(env,{text:v.caption,channelId:channel.channelId,schedulingType:"automatic",mode:"customScheduled",dueAt:v.dueAt,saveToDraft:false,aiAssisted:true,assets:[{video:{url:v.videoUrl}}],metadata:{facebook:{type:"post"}}});
    if(!result?.id||!result.dueAt||Math.abs(Date.parse(result.dueAt)-due)>1000)throw Error("Buffer result unconfirmed");
    await env.POSTS_KV.put(key,JSON.stringify({state:"scheduled",sha256:v.sha256,postId:result.id,dueAt:result.dueAt}));
    return {status:"SCHEDULED",postId:result.id,dueAt:result.dueAt,facebookPublished:false};
  }catch(e){
    await env.POSTS_KV.put(key,JSON.stringify({state:"uncertain",sha256:v.sha256,dueAt:v.dueAt}));
    throw Error("Buffer outcome uncertain; inspect before retry");
  }
}
