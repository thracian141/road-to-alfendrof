import { DurableObject } from 'cloudflare:workers';
import { discordProfile } from './discord';
interface Env extends Cloudflare.Env { DISCORD_CLIENT_SECRET: string }
type User = { id: string; name: string; friend_code: string };
type Config = { id: string; owner: string; mode: '1v1' | '2v2'; build: string; expires: number };
const now = () => Math.floor(Date.now()/1000);
const random = () => [...crypto.getRandomValues(new Uint8Array(32))].map(x=>x.toString(16).padStart(2,'0')).join('');
async function digest(s: string) { return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)))].map(x=>x.toString(16).padStart(2,'0')).join(''); }
class Failure extends Error { constructor(public status: number, message: string) { super(message); } }
function check(condition: unknown, status: number, message: string): asserts condition { if (!condition) throw new Failure(status,message); }
const json = (data: unknown, status=200) => Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
async function body(request: Request): Promise<Record<string, unknown>> {
  check(request.headers.get('Content-Type')?.startsWith('application/json'),415,'Expected JSON');
  check(Number(request.headers.get('Content-Length')||0)<=8192,413,'Body too large');
  const reader=request.body?.getReader(); check(reader,400,'Expected JSON body');
  const chunks: Uint8Array[]=[]; let size=0;
  while(true) { const {done,value}=await reader.read(); if(done) break; size+=value.byteLength; if(size>8192) { await reader.cancel(); throw new Failure(413,'Body too large'); } chunks.push(value); }
  const bytes=new Uint8Array(size); let offset=0; for(const chunk of chunks) { bytes.set(chunk,offset); offset+=chunk.byteLength; }
  const text=new TextDecoder().decode(bytes);
  let value; try { value=JSON.parse(text); } catch { throw new Failure(400,'Invalid JSON'); }
  check(value && typeof value==='object' && !Array.isArray(value),400,'Expected object'); return value;
}
function field(value: unknown, max=128): string { check(typeof value==='string' && value.length>0 && value.length<=max,400,'Invalid field'); return value; }
function origin(env: Env) { const url=new URL(env.PUBLIC_ORIGIN); check(url.protocol==='https:' || ['localhost','127.0.0.1'].includes(url.hostname),503,'Invalid public origin'); return url.origin; }
const pair=(a: string,b: string)=>[a,b].sort();
async function rate(env: Env, request: Request, group: string, limit=120) {
  const ip=request.headers.get('CF-Connecting-IP') || 'local';
  const row=await env.DB.prepare('INSERT INTO throttle(key,window,hits) VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET hits=CASE WHEN window=excluded.window THEN hits+1 ELSE 1 END,window=excluded.window RETURNING hits').bind(`${group}:${ip}`,Math.floor(now()/60)).first<{hits:number}>();
  check(row && row.hits<=limit,429,'Too many requests');
}
async function user(env: Env, request: Request): Promise<User> {
  const token=request.headers.get('Authorization')?.match(/^Bearer ([a-f0-9]{64})$/)?.[1];
  check(token,401,'Sign in required');
  const u=await env.DB.prepare('SELECT u.id,u.name,u.friend_code FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.hash=? AND s.expires>?').bind(await digest(token),now()).first<User>();
  check(u,401,'Session expired'); return u;
}
async function blocked(env: Env, a: string,b: string) { return !!await env.DB.prepare('SELECT 1 FROM blocks WHERE (blocker=? AND blocked=?) OR (blocker=? AND blocked=?)').bind(a,b,b,a).first(); }
async function notify(env: Env, id: string,event: unknown) { await env.PRESENCE.getByName(id).notify(event); }
function page(text: string) { return new Response(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Road to Alfendrof</title><h1>Road to Alfendrof</h1><p>${text}</p>`,{headers:{'Content-Type':'text/html;charset=utf-8','Cache-Control':'no-store','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'",'Referrer-Policy':'no-referrer'}}); }

async function handle(request: Request,env: Env): Promise<Response> {
  const url=new URL(request.url), p=url.pathname, method=request.method;
  if (p==='/health' && method==='GET') return json({ok:true,service:'alfendrof-multiplayer',protocol:2});
  if (p==='/auth/device' && method==='POST') {
    await rate(env,request,'login',5);
    check(env.DISCORD_CLIENT_ID && env.DISCORD_CLIENT_SECRET,503,'Discord login is not configured');
    const id=crypto.randomUUID(), secret=random();
    await env.DB.prepare('INSERT INTO logins(id,secret_hash,expires) VALUES(?,?,?)').bind(id,await digest(secret),now()+600).run();
    return json({id,device_token:secret,expires_in:600,interval:3,verification_uri:`${origin(env)}/auth/discord?request=${id}`},201);
  }
  if (p==='/auth/device/claim' && method==='POST') {
    await rate(env,request,'poll',60); const b=await body(request);
    const row=await env.DB.prepare('SELECT id,user_id FROM logins WHERE secret_hash=? AND expires>?').bind(await digest(field(b.device_token,64)),now()).first<{id:string;user_id:string|null}>();
    check(row,410,'Login expired'); if (!row.user_id) return json({status:'pending'},202);
    const claimed=await env.DB.prepare('DELETE FROM logins WHERE id=? AND user_id IS NOT NULL RETURNING user_id').bind(row.id).first<{user_id:string}>();
    check(claimed,410,'Login already claimed'); const token=random();
    await env.DB.prepare('INSERT INTO sessions(hash,user_id,expires) VALUES(?,?,?)').bind(await digest(token),claimed.user_id,now()+30*86400).run();
    return json({access_token:token,token_type:'Bearer',expires_in:30*86400});
  }
  if (p==='/auth/discord' && method==='GET') {
    await rate(env,request,'oauth',10); check(env.DISCORD_CLIENT_ID && env.DISCORD_CLIENT_SECRET,503,'Discord login is not configured');
    const id=field(url.searchParams.get('request'));
    check(await env.DB.prepare('SELECT 1 FROM logins WHERE id=? AND expires>? AND user_id IS NULL').bind(id,now()).first(),410,'Login expired');
    const state=random(); await env.DB.prepare('INSERT INTO oauth_states(hash,login_id,expires) VALUES(?,?,?)').bind(await digest(state),id,now()+600).run();
    const authorize=new URL('https://discord.com/oauth2/authorize');
    authorize.search=new URLSearchParams({client_id:env.DISCORD_CLIENT_ID,redirect_uri:`${origin(env)}/auth/discord/callback`,response_type:'code',scope:'identify',state,prompt:'consent'}).toString();
    return new Response(null,{status:302,headers:{Location:authorize.toString(),'Cache-Control':'no-store','Set-Cookie':`oauth_state=${state}; HttpOnly; SameSite=Lax; Path=/auth/discord; Max-Age=600${url.protocol==='https:'?'; Secure':''}`}});
  }
  if (p==='/auth/discord/callback' && method==='GET') {
    await rate(env,request,'oauth',10); const state=field(url.searchParams.get('state'),64);
    check(request.headers.get('Cookie')?.split(';').some(x=>x.trim()===`oauth_state=${state}`),403,'Login browser mismatch');
    const login=await env.DB.prepare('DELETE FROM oauth_states WHERE hash=? AND expires>? RETURNING login_id').bind(await digest(state),now()).first<{login_id:string}>();
    check(login,403,'Invalid or reused login state');
    const code=field(url.searchParams.get('code'),512);
    const who=await discordProfile(code,{clientId:env.DISCORD_CLIENT_ID,clientSecret:env.DISCORD_CLIENT_SECRET,redirectUri:`${origin(env)}/auth/discord/callback`});
    check(who,502,'Discord login failed'); const name=who.name;
    const u=await env.DB.prepare('INSERT INTO users(id,discord_id,name,friend_code) VALUES(?,?,?,?) ON CONFLICT(discord_id) DO UPDATE SET name=excluded.name RETURNING id').bind(crypto.randomUUID(),who.id,name,random().slice(0,12).toUpperCase()).first<{id:string}>();
    check(u,500,'Could not create player');
    const changed=await env.DB.prepare('UPDATE logins SET user_id=? WHERE id=? AND expires>? AND user_id IS NULL').bind(u.id,login.login_id,now()).run(); check(changed.meta.changes,410,'Login expired');
    return page('Signed in. Return to the game. Only approve sign-in requests you started yourself.');
  }
  const me=await user(env,request); await rate(env,request,'api');
  if (p==='/v1/me' && method==='GET') return json(me);
  if (p==='/v1/logout' && method==='POST') {
    await env.DB.prepare('DELETE FROM sessions WHERE hash=?').bind(await digest(request.headers.get('Authorization')!.slice(7))).run();
    await env.PRESENCE.getByName(me.id).disconnect();
    const memberships=await env.DB.prepare('SELECT room_id FROM members WHERE user_id=?').bind(me.id).all<{room_id:string}>();
    await Promise.all(memberships.results.map(m=>env.ROOMS.getByName(m.room_id).disconnect(me.id)));
    return json({ok:true});
  }
  if (p==='/v1/presence' && method==='POST') { await env.PRESENCE.getByName(me.id).heartbeat(); return json({ok:true}); }
  if (p==='/v1/events' && method==='GET') return env.PRESENCE.getByName(me.id).fetch(new Request('https://presence/ws',{headers:{Upgrade:request.headers.get('Upgrade')||''}}));
  if (p==='/v1/friends' && method==='GET') {
    const rows=await env.DB.prepare('SELECT u.id,u.name,u.friend_code,f.state,f.requester FROM friendships f JOIN users u ON u.id=CASE WHEN f.a=? THEN f.b ELSE f.a END WHERE f.a=? OR f.b=?').bind(me.id,me.id,me.id).all<User & {state:string;requester:string}>();
    const friends=await Promise.all(rows.results.map(async f=>({...f,online:f.state==='accepted' && await env.PRESENCE.getByName(f.id).online()})));
    return json({friends});
  }
  if (p==='/v1/friends' && method==='POST') {
    const b=await body(request); const friend=await env.DB.prepare('SELECT id FROM users WHERE friend_code=?').bind(field(b.friend_code,12).toUpperCase()).first<{id:string}>();
    check(friend && friend.id!==me.id && !await blocked(env,me.id,friend.id),404,'Player unavailable');
    const counts=await env.DB.prepare('SELECT count(*) AS n FROM friendships WHERE a=? OR b=?').bind(me.id,me.id).first<{n:number}>(); check(counts!.n<32,409,'Friend limit reached');
    const [a,c]=pair(me.id,friend.id);
    await env.DB.prepare("INSERT OR IGNORE INTO friendships(a,b,requester,state) VALUES(?,?,?,'pending')").bind(a,c,me.id).run();
    await notify(env,friend.id,{type:'friend_request',from:me.id}); return json({ok:true},201);
  }
  const friendRoute=p.match(/^\/v1\/friends\/([^/]+)(\/accept)?$/);
  if (friendRoute) {
    const other=friendRoute[1], [a,b]=pair(me.id,other);
    if (method==='POST' && friendRoute[2]) {
      check(!await blocked(env,me.id,other),404,'Player unavailable');
      const result=await env.DB.prepare("UPDATE friendships SET state='accepted' WHERE a=? AND b=? AND state='pending' AND requester<>?").bind(a,b,me.id).run(); check(result.meta.changes,404,'No incoming request');
      await notify(env,other,{type:'friend_accepted',user:me.id}); return json({ok:true});
    }
    if (method==='DELETE' && !friendRoute[2]) { await env.DB.prepare('DELETE FROM friendships WHERE a=? AND b=?').bind(a,b).run(); return json({ok:true}); }
  }
  if (p==='/v1/blocks' && method==='POST') {
    const b=await body(request), other=field(b.user_id); check(other!==me.id,400,'Cannot block yourself'); const [a,c]=pair(me.id,other);
    await env.DB.batch([env.DB.prepare('INSERT OR IGNORE INTO blocks(blocker,blocked) VALUES(?,?)').bind(me.id,other),env.DB.prepare('DELETE FROM friendships WHERE a=? AND b=?').bind(a,c)]); return json({ok:true});
  }
  if (p==='/v1/invites' && method==='GET') {
    return json({invites:(await env.DB.prepare('SELECT i.id,i.room_id,r.mode,r.build,r.owner FROM invites i JOIN rooms r ON r.id=i.room_id WHERE i.user_id=? AND i.expires>? AND r.expires>?').bind(me.id,now(),now()).all()).results});
  }
  if (p==='/v1/rooms' && method==='POST') {
    const b=await body(request); check(b.mode==='1v1'||b.mode==='2v2',400,'Invalid mode'); const build=field(b.build,128); const id=crypto.randomUUID();
    const count=await env.DB.prepare('SELECT count(*) AS n FROM rooms WHERE owner=? AND expires>?').bind(me.id,now()).first<{n:number}>(); check(count!.n<3,409,'Close an existing room first');
    await env.DB.batch([env.DB.prepare('INSERT INTO rooms(id,owner,mode,build,expires) VALUES(?,?,?,?,?)').bind(id,me.id,b.mode,build,now()+3*3600),env.DB.prepare('INSERT INTO members(room_id,user_id,slot) VALUES(?,?,0)').bind(id,me.id)]); return json({id,slot:0,mode:b.mode,build},201);
  }
  if (p==='/v1/matchmaking' && method==='POST') {
    const b=await body(request); check(b.mode==='1v1'||b.mode==='2v2',400,'Invalid mode'); const build=field(b.build,128), cap=b.mode==='2v2'?4:2;
    const existing=await env.DB.prepare('SELECT r.id,m.slot FROM rooms r JOIN members m ON m.room_id=r.id WHERE m.user_id=? AND r.public=1 AND r.started=0 AND r.mode=? AND r.build=? AND r.expires>?').bind(me.id,b.mode,build,now()).first();
    if(existing) return json(existing);
    const available=`r.public=1 AND r.started=0 AND r.mode=? AND r.build=? AND r.expires>? AND (SELECT count(*) FROM members WHERE room_id=r.id)<? AND NOT EXISTS(SELECT 1 FROM members m JOIN blocks b ON (b.blocker=m.user_id AND b.blocked=?) OR (b.blocked=m.user_id AND b.blocker=?) WHERE m.room_id=r.id)`;
    const id=crypto.randomUUID();
    const result=await env.DB.batch([
      env.DB.prepare(`INSERT INTO rooms(id,owner,mode,build,expires,public) SELECT ?,?,?,?,?,1 WHERE NOT EXISTS(SELECT 1 FROM rooms r WHERE ${available})`).bind(id,me.id,b.mode,build,now()+3600,b.mode,build,now(),cap,me.id,me.id),
      env.DB.prepare(`INSERT INTO members(room_id,user_id,slot) SELECT r.id,?,s FROM rooms r CROSS JOIN (SELECT 0 AS s UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3) WHERE ${available} AND s<? AND NOT EXISTS(SELECT 1 FROM members WHERE room_id=r.id AND slot=s) ORDER BY r.expires,r.id,s LIMIT 1 RETURNING room_id AS id,slot`).bind(me.id,b.mode,build,now(),cap,me.id,me.id,cap)
    ]);
    check(result[1].results.length,409,'Try finding a match again'); return json(result[1].results[0],201);
  }
  const roomRoute=p.match(/^\/v1\/rooms\/([^/]+)(?:\/(invite|join|signal|state|leave))?$/);
  if (roomRoute) {
    const id=roomRoute[1], action=roomRoute[2];
    const room=await env.DB.prepare('SELECT * FROM rooms WHERE id=? AND expires>?').bind(id,now()).first<Config>(); check(room,404,'Room unavailable');
    const member=await env.DB.prepare('SELECT slot FROM members WHERE room_id=? AND user_id=?').bind(id,me.id).first<{slot:number}>();
    if (action==='invite' && method==='POST') {
      check(room.owner===me.id,403,'Only the host can invite'); const b=await body(request), other=field(b.user_id); const [a,c]=pair(me.id,other);
      check(await env.DB.prepare("SELECT 1 FROM friendships WHERE a=? AND b=? AND state='accepted'").bind(a,c).first() && !await blocked(env,me.id,other),403,'Invite accepted friends only');
      await env.DB.prepare('INSERT INTO invites(id,room_id,user_id,expires) VALUES(?,?,?,?) ON CONFLICT(room_id,user_id) DO UPDATE SET expires=excluded.expires').bind(crypto.randomUUID(),id,other,now()+600).run();
      await notify(env,other,{type:'room_invite',room:id,from:me.id}); return json({ok:true});
    }
    if (action==='join' && method==='POST') {
      if (member) return json({id,slot:member.slot});
      check(await env.DB.prepare('SELECT 1 FROM invites WHERE room_id=? AND user_id=? AND expires>?').bind(id,me.id,now()).first() && !await blocked(env,me.id,room.owner),403,'Invitation required');
      const cap=room.mode==='2v2'?4:2;
      for (let retry=0;retry<4;retry++) {
        const added=await env.DB.prepare('INSERT OR IGNORE INTO members(room_id,user_id,slot) SELECT ?,?,s FROM (SELECT 0 AS s UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3) WHERE s<? AND NOT EXISTS(SELECT 1 FROM members WHERE room_id=? AND slot=s) LIMIT 1 RETURNING slot').bind(id,me.id,cap,id).first<{slot:number}>();
        if (added) return json({id,slot:added.slot},201);
        const own=await env.DB.prepare('SELECT slot FROM members WHERE room_id=? AND user_id=?').bind(id,me.id).first<{slot:number}>(); if(own) return json({id,slot:own.slot});
      }
      throw new Failure(409,'Room full');
    }
    check(member,403,'Room membership required');
    if (!action && method==='GET') return json({...room,members:(await env.DB.prepare('SELECT m.slot,u.id,u.name FROM members m JOIN users u ON u.id=m.user_id WHERE m.room_id=? ORDER BY m.slot').bind(id).all()).results});
    if (!action && method==='DELETE') { check(room.owner===me.id,403,'Only the host can close'); await env.ROOMS.getByName(id).shutdown(); await env.DB.prepare('DELETE FROM rooms WHERE id=?').bind(id).run(); return json({ok:true}); }
    const stub=env.ROOMS.getByName(id); await stub.configure(room);
    if(action==='state' && method==='GET') return json({...await stub.state(),members:(await env.DB.prepare('SELECT m.slot,u.name FROM members m JOIN users u ON u.id=m.user_id WHERE m.room_id=? ORDER BY m.slot').bind(id).all()).results});
    if(action==='signal' && method==='POST') {
      const b=await body(request); check(b.build===room.build,409,'Game build mismatch');
      check(Number.isInteger(b.character) && Number(b.character)>=0 && Number(b.character)<256 && typeof b.ready==='boolean',400,'Invalid fighter or readiness');
      check(Array.isArray(b.candidates) && b.candidates.length>0 && b.candidates.length<=3,400,'UDP addresses required');
      const candidates=b.candidates.map(x=>field(x,64));
      check(candidates.every(x=>{ const m=x.match(/^(\d{1,3}\.){3}\d{1,3}:(\d{1,5})$/); if(!m) return false; const [ip,port]=x.split(':'); return ip.split('.').every(n=>+n<=255) && +port>0 && +port<=65535 && ip!=='0.0.0.0'; }),400,'Invalid UDP address');
      const state=await stub.signal(me.id,member.slot,Number(b.character),b.ready,candidates);
      if(state.playing) await env.DB.prepare('UPDATE rooms SET started=1 WHERE id=?').bind(id).run();
      return json(state);
    }
    if(action==='leave' && method==='POST') {
      await stub.disconnect(me.id);
      if(room.owner===me.id) { await stub.shutdown(); await env.DB.prepare('DELETE FROM rooms WHERE id=?').bind(id).run(); }
      else await env.DB.prepare('DELETE FROM members WHERE room_id=? AND user_id=?').bind(id,me.id).run();
      return json({ok:true});
    }
  }
  throw new Failure(404,'Not found');
}
export default {
  async fetch(request: Request,env: Env) { try { return await handle(request,env); } catch(e) { if(e instanceof Error && e.message.includes('social_limit')) return json({error:'Player limit reached'},409); if(e instanceof Failure) return json({error:e.message},e.status); console.error(JSON.stringify({event:'request_failed',kind:e instanceof Error?e.name:'unknown'})); return json({error:'Internal error'},500); } },
  async scheduled(_event: ScheduledController,env: Env) { const t=now(); await env.DB.batch(['sessions','oauth_states','logins','invites','rooms'].map(table=>env.DB.prepare(`DELETE FROM ${table} WHERE expires<?`).bind(t))); await env.DB.prepare('DELETE FROM throttle WHERE window<?').bind(Math.floor(t/60)-10).run(); }
};

export class Presence extends DurableObject<Env> {
  constructor(ctx: DurableObjectState,env: Env) { super(ctx,env); ctx.setWebSocketAutoResponse(new WebSocketRequestResponsePair('ping','pong')); }
  async fetch(request: Request) { if(request.headers.get('Upgrade')?.toLowerCase()!=='websocket') return new Response('WebSocket required',{status:426}); for(const old of this.ctx.getWebSockets()) old.close(4000,'Signed in elsewhere'); const pair=new WebSocketPair(); this.ctx.acceptWebSocket(pair[1]); return new Response(null,{status:101,webSocket:pair[0]}); }
  async disconnect() { this.ctx.storage.kv.delete('heartbeat'); for(const ws of this.ctx.getWebSockets()) ws.close(4003,'Signed out'); }
  async online() { return this.ctx.getWebSockets().some(ws=>ws.readyState===1) || (this.ctx.storage.kv.get<number>('heartbeat')||0)>now(); }
  heartbeat() { this.ctx.storage.kv.put('heartbeat',now()+60); }
  async notify(event: unknown) { const data=JSON.stringify(event); for(const ws of this.ctx.getWebSockets()) { try { ws.send(data); } catch { ws.close(1011,'Reconnect'); } } }
  webSocketMessage(ws: WebSocket) { ws.close(1008,'Only ping is accepted'); }
  webSocketClose(ws: WebSocket,code:number) { ws.close(code,'Closed'); }
  webSocketError(ws: WebSocket) { ws.close(1011,'Reconnect'); }
}

type Peer={user:string;slot:number;character:number;ready:boolean;candidates:string[]};
export class Room extends DurableObject<Env> {
  async configure(config: Config) { if(!this.ctx.storage.kv.get('config')) { this.ctx.storage.kv.put('config',config); await this.ctx.storage.setAlarm(config.expires*1000); } }
  state() { const config=this.ctx.storage.kv.get<Config>('config'); check(config && config.expires>now(),410,'Room expired'); return {players:[...this.ctx.storage.kv.list<Peer>({prefix:'peer:'})].map(([,peer])=>peer).sort((a,b)=>a.slot-b.slot),playing:this.ctx.storage.kv.get<boolean>('playing')||false}; }
  signal(user:string,slot:number,character:number,ready:boolean,candidates:string[]) {
    const config=this.ctx.storage.kv.get<Config>('config'); check(config && config.expires>now(),410,'Room expired');
    this.ctx.storage.transactionSync(()=>{
      check(!this.ctx.storage.kv.get('playing'),409,'Match already started');
      this.ctx.storage.kv.put(`peer:${slot}`,{user,slot,character,ready,candidates});
      const peers=[...this.ctx.storage.kv.list<Peer>({prefix:'peer:'})].map(([,peer])=>peer);
      if(peers.length===(config.mode==='2v2'?4:2) && peers.every(p=>p.ready)) this.ctx.storage.kv.put('playing',true);
    }); return this.state();
  }
  disconnect(user:string) { for(const [key,peer] of this.ctx.storage.kv.list<Peer>({prefix:'peer:'})) if(peer.user===user) this.ctx.storage.kv.delete(key); }
  async shutdown() { await this.ctx.storage.deleteAll(); }
  async alarm() { await this.shutdown(); }
}
