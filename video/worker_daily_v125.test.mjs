import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {queueVideo} from "./video_publish_gate_v12.mjs";
const day="2026-11-27",now=Date.parse(day+"T12:17:00Z"),due=day+"T15:00:00Z";
const localTime=t=>{const d=new Date(t+3600000).toISOString();return {date:d.slice(0,10),hour:Number(d.slice(11,13)),minute:Number(d.slice(14,16))}};
const kv=new Map();let mutations=0,writes=0,history=[];
const env={AUTO_VIDEO_DAILY_ENABLED:"true",AUTO_VIDEO_PUBLISH_ENABLED:"true",VIDEO_GITHUB_REPO:"satanchild666/darkline-video-automation",POSTS_KV:{
 async get(k,mode){return kv.has(k)?JSON.parse(kv.get(k)):null},
 async put(k,v){writes++;kv.set(k,v)}
}};
const helpers={now:()=>now,localTime,findChannel:async()=>({channelName:"Darkline Studio",service:"facebook",channelId:"test"}),
 listPosts:async()=>history,semanticCheck:async()=>true,
 mutate:async(e,input)=>{mutations++;return {id:"test-post",dueAt:input.dueAt}}};
const ctx=vm.createContext({Date:class extends Date{static now(){return now}},isVideoAuthorized:r=>r.authorized,json:(body,status=200)=>({body,status}),getRequestJson:async r=>r.body,budapestTime:localTime,
 bufferGraphql:null,findDarklineFacebookChannel:null,dsPostCore:null,dsPostNorm:null,dsPostSimilarity:null,dsPostSemanticGuard:null,makeVideoHelpers:()=>helpers,videoEditorialHelpers:h=>h,queueVideo});
vm.runInContext(fs.readFileSync(new URL("./worker_daily_v124.mjs",import.meta.url),"utf8"),ctx);
const caption=vm.runInContext("V124_CAPTIONS.portfolio",ctx),daily=vm.runInContext("dailyVideoV124",ctx);
const req=(route,body,authorized=true)=>daily({method:"POST",authorized,body},env,{pathname:"/video-v124-"+route});
const q={review_gate:"PASS",reasons:[],seconds:50.2,width:1080,height:1920,fps:30,speech_seconds:48.67,audio_peak:.78,overlay_dom_checks:"passed",dedup:"PASS",decode:"PASS",mascot:true,readability:"PASS",focal_scenes:10,min_projected_text_px:32.98};
const body={version:"V12",date:day,dueAt:due,topic:"portfolio",sha256:"a".repeat(64),videoUrl:"https://github.com/satanchild666/darkline-video-automation/releases/download/darkline-v12-"+day+"/darkline-v12-"+day+".mp4",caption,quality:q,dryRun:true};
assert.equal((await req("state",{date:day},false)).status,403);
assert.equal((await req("state",{date:day})).body.dailyEnabled,true);
assert.equal((await req("topic",{topic:"portfolio",caption})).body.status,"V124_TOPIC_AVAILABLE");
assert.equal((await req("topic",{topic:"portfolio",caption:"wrong"})).status,422);
assert.equal((await req("queue",body)).status,422);
env.AUTO_VIDEO_DAILY_ENABLED="false";assert.equal((await req("reserve",{topic:"portfolio",date:day})).status,422);env.AUTO_VIDEO_DAILY_ENABLED="true";
assert.equal(writes,0);assert.equal(mutations,0);
assert.equal((await req("reserve",{topic:"portfolio",date:day})).body.status,"V124_RESERVED");
assert.equal((await req("reserve",{topic:"portfolio",date:day})).status,422);
assert.equal((await req("queue",{...body,quality:{...q,min_projected_text_px:31}})).status,422);
assert.equal((await req("queue",body)).body.status,"DRY_RUN_OK");
assert.equal(mutations,0);
assert.equal((await req("queue",{...body,dryRun:false})).body.status,"SCHEDULED");
assert.equal((await req("queue",{...body,dryRun:false})).status,422);
assert.equal(mutations,1);
assert.equal((await req("state",{date:day})).body.publication,"scheduled");
assert.equal((await req("state",{date:day})).body.generation,"scheduled");
console.log("V125_DAILY_GATE_PASS authenticated state, topic, disabled switch, reservation, quality, dry-run, one mock mutation, no duplicate");
