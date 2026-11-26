import assert from "node:assert/strict";
import vm from "node:vm";
import {fallbackSource} from "./worker_v1265_patch.mjs";
const local={date:"2026-12-01",hour:15,minute:7};
const memory=new Map();
let writes=0,submissions=0,ambiguous=false;
const env={AUTO_V126_FALLBACK_ENABLED:"true",AUTO_BUFFER_QUEUE_ENABLED:"false",AUTO_BUFFER_DRAFTS_ENABLED:"true",AUTO_IMAGE_DRAFTS_ENABLED:"true",POSTS_KV:{
  get:async k=>memory.get(k)||null,put:async(k,v)=>{writes++;memory.set(k,JSON.parse(v))}
}};
const ctx=vm.createContext({Date:{now:()=>Date.parse("2026-12-01T14:07:00Z")},Math,JSON,
 isVideoAuthorized:r=>r.auth===true,json:(body,status=200)=>({body,status}),getRequestJson:async r=>r.body,
 budapestTime:()=>({...local}),dsScheduledFacebookSlot:async(e,l,t,mode)=>{
   assert.equal(mode,"fallback");assert.equal(memory.get("posts:v1265:fallback:"+local.date)?.status,"reserved");
   submissions++;if(ambiguous)throw Error("transport uncertain");
   return {status:"scheduled",dueAt:"2026-12-01T15:00:00Z",bufferPostId:"mock"};
 }});
vm.runInContext(fallbackSource,ctx);
const request=(dryRun=true,auth=true)=>ctx.v1265FallbackRoute({method:"POST",auth,body:{date:local.date,dryRun}},env);
assert.equal((await request(true,false)).status,403);
assert.equal((await request()).body.clear,true);
assert.equal(writes,0);assert.equal(submissions,0);
for(const k of ["video:v12:publish:","video:v124:generation:","posts:v1265:fallback:"]){
 for(const status of ["reserved","submitting","uncertain","scheduled"]){
   memory.set(k+local.date,{state:status,status});
   assert.equal((await request()).body.clear,false);
   assert.equal((await request(false)).status,422);memory.clear();
 }
}
memory.set("posts:v3:slot:"+local.date+":16",{status:"uncertain"});
assert.equal((await request(false)).status,422);memory.clear();
env.AUTO_V126_FALLBACK_ENABLED="false";assert.equal((await request(false)).status,422);env.AUTO_V126_FALLBACK_ENABLED="true";
local.hour=14;assert.equal((await request(false)).status,422);local.hour=15;
assert.equal(writes,0);assert.equal(submissions,0);
assert.equal((await request(false)).body.status,"V1265_FALLBACK_SCHEDULED");
assert.equal((await request(false)).status,422);assert.equal(submissions,1);
memory.clear();ambiguous=true;
assert.equal((await request(false)).status,422);assert.equal(memory.get("posts:v1265:fallback:"+local.date).status,"reserved");
assert.equal((await request(false)).status,422);assert.equal(submissions,2);
console.log("V1265_WORKER_FALLBACK_PASS auth, dry-run, no existing video, window, separate switch, reserve-before-mutation, ambiguous blocks retry");
