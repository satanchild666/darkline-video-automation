// V12.4.1 compare only meaningful editorial content, not required repeated disclosures,
// the identical website URL, hashtags or brand name. Keep the existing semantic threshold.
export function videoEditorialCore(value,core){
  return String(core(String(value||"")))
    .replace(/https?:\/\/[^\s]+/giu," ")
    .replace(/#[\p{L}\p{N}_]+/gu," ")
    .replace(/\bDarkline\s+Studi[oó](?:[^\s,.!?;:]*)?/giu," ")
    .replace(/(?:A videó )?animált kabalával és AI-narrációval készült\.?/giu," ")
    .replace(/Animált kabala,\s*AI-narráció\.?/giu," ")
    .replace(/(?:AI-narrációval készült|AI-narráció)\.?/giu," ")
    .replace(/\s+/g," ").trim();
}
export function videoEditorialHelpers(helpers,{dsPostCore,dsPostNorm,dsPostSimilarity,dsPostSemanticGuard}){
  return {...helpers,async semanticCheck(env,caption,posts){
    const candidate=videoEditorialCore(caption,dsPostCore),norm=dsPostNorm(candidate);
    if(norm.length<60)throw Error("Insufficient distinct editorial content");
    const history=posts.map(p=>({...p,text:videoEditorialCore(p.text,dsPostCore)})).filter(p=>dsPostNorm(p.text).length>=25);
    if(history.some(p=>dsPostNorm(p.text)===norm||dsPostSimilarity(p.text,candidate)>.72))return false;
    await dsPostSemanticGuard(env,candidate,history);
    return true;
  }};
}
