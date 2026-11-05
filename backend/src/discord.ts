export interface DiscordConfig { clientId: string; clientSecret: string; redirectUri: string }
export async function discordProfile(code: string, config: DiscordConfig, http: typeof fetch = fetch): Promise<{id:string;name:string}|null> {
  const response=await http('https://discord.com/api/oauth2/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({client_id:config.clientId,client_secret:config.clientSecret,grant_type:'authorization_code',code,redirect_uri:config.redirectUri})});
  if(!response.ok) return null;
  const token=await response.json<{access_token?:unknown}>();
  if(typeof token.access_token!=='string' || !token.access_token) return null;
  const profile=await http('https://discord.com/api/users/@me',{headers:{Authorization:`Bearer ${token.access_token}`}});
  if(!profile.ok) return null;
  const who=await profile.json<{id?:unknown;username?:unknown;global_name?:unknown}>();
  if(typeof who.id!=='string' || !/^\d+$/.test(who.id) || typeof who.username!=='string') return null;
  return {id:who.id,name:(typeof who.global_name==='string' && who.global_name ? who.global_name : who.username).slice(0,32)};
}
