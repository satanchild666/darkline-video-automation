// V12.1 adapter uses the live Worker's existing read helpers.
// Tests never send a Buffer createPost mutation.
export function makeVideoHelpers({bufferGraphql,findDarklineFacebookChannel,budapestTime,dsPostSemanticGuard,dsPostNorm,dsPostCore,dsPostSimilarity}){
  return {
    now:()=>Date.now(),localTime:budapestTime,findChannel:findDarklineFacebookChannel,
    async listPosts(env,channel){
      let after=null;const all=[];
      for(let page=0;page<20;page++){
        const r=await bufferGraphql(env,'query V121History($input: PostsInput!, $after: String) { posts(first:100,after:$after,input:$input){edges{node{id text status dueAt sentAt createdAt}} pageInfo{hasNextPage endCursor}} }',{input:{organizationId:channel.organizationId,filter:{channelIds:[channel.channelId],status:['draft','scheduled','sending','sent','needs_approval','error']}},after});
        if(!Array.isArray(r.posts?.edges)||!r.posts?.pageInfo)throw Error("Buffer history incomplete");
        all.push(...r.posts.edges.map(x=>x.node).filter(Boolean));
        if(!r.posts.pageInfo.hasNextPage)return all;
        if(!r.posts.pageInfo.endCursor||r.posts.pageInfo.endCursor===after)throw Error("Invalid history cursor");
        after=r.posts.pageInfo.endCursor;
      }
      throw Error("Buffer history exceeds safe limit");
    },
    async semanticCheck(env,caption,posts){
      const norm=dsPostNorm(dsPostCore(caption));
      if(norm.length<25||posts.some(p=>typeof p.text==="string"&&(dsPostNorm(dsPostCore(p.text))===norm||dsPostSimilarity(dsPostCore(p.text),dsPostCore(caption))>.72)))return false;
      await dsPostSemanticGuard(env,caption,posts);
      return true;
    },
    async mutate(env,input){
      if(env.AUTO_VIDEO_PUBLISH_ENABLED!=="true")throw Error("Independent video switch disabled");
      if(input.saveToDraft!==false||input.schedulingType!=="automatic"||input.mode!=="customScheduled"||!input.assets?.[0]?.video?.url||input.assets.length!==1)throw Error("Invalid video mutation");
      const result=await bufferGraphql(env,'mutation V121Video($input: CreatePostInput!) { createPost(input:$input){... on PostActionSuccess{post{id dueAt}} ... on MutationError{message}} }',{input});
      return result.createPost?.post;
    }
  };
}
export async function videoPreflight(env,helpers){
  const ch=await helpers.findChannel(env);
  if(!ch?.channelId||String(ch.channelName).trim().toLowerCase()!=="darkline studio"||!String(ch.service).toLowerCase().includes("facebook"))throw Error("Wrong destination");
  const posts=await helpers.listPosts(env,ch);
  return {status:"V121_BUFFER_PREFLIGHT_OK",channel:ch.channelName,historyCount:posts.length,videoAutoPublish:env.AUTO_VIDEO_PUBLISH_ENABLED==="true",sideEffects:false};
}
