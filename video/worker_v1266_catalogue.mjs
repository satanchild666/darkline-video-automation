// Narrow V119 patch: caption allowlist only. Never change live flags or deploy here.
export function patchWorker(src,captions){
 const entries=Object.entries(captions);
 if(entries.length!==35||entries.some(([k,v])=>!/^[a-z_]{3,30}$/.test(k)||typeof v!=="string"||!v.includes("AI-narráció")||!v.includes("https://darkline-studio.web.app/")))throw Error("Invalid new manifest");
 const m=src.match(/^const V124_CAPTIONS=(\{[^\n]+\});$/m);
 if(!m||src.split(m[0]).length!==2)throw Error("Expected one exact allowlist");
 const old=JSON.parse(m[1]);
 if(Object.keys(old).length!==16||entries.some(([k])=>k in old))throw Error("Unexpected current catalogue");
 const result=src.replace(m[0],"const V124_CAPTIONS="+JSON.stringify({...old,...captions})+";");
 if(!result.includes("async function v1265FallbackRoute(")||!result.includes("async function v126MorningRoute("))throw Error("Expected original routes");
 return result;
}
