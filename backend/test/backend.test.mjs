import {test, before, after} from 'node:test';
import assert from 'node:assert/strict';
import {spawn, execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync,unlinkSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const base='http://127.0.0.1:8787';
const cli='node_modules/wrangler/bin/wrangler.js';
const tokens=['a','b','c','d','e'].map(x=>x.repeat(64));
const hash=s=>createHash('sha256').update(s).digest('hex');
let worker;
const sockets=[];
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function sql(text) { const path=join(tmpdir(),`alfendrof-${process.pid}.sql`);writeFileSync(path,text);try {execFileSync(process.execPath,[cli,'d1','execute','DB','--local','--persist-to','.wrangler/test','--file',path],{stdio:'pipe',env:{...process.env,WRANGLER_SEND_METRICS:'false'}});}finally{unlinkSync(path);} }
async function api(path,who=0,method='GET',data) { return fetch(base+path,{method,headers:{...(who===null?{}:{Authorization:'Bearer '+tokens[who]}),'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)}); }
async function data(path,who=0,method='GET',body,status=200) { const r=await api(path,who,method,body);const b=await r.json();assert.equal(r.status,status,JSON.stringify(b));return b; }
function ws(path,who) {
 return new Promise((resolve,reject)=>{
  const url=base.replace('http','ws')+path;
  // Native clients can supply Authorization on the HTTP upgrade; Node's WebSocket cannot.
  // Use ws for the same authenticated upgrade path used by the desktop client.
  import('ws').then(({default:WebSocket})=>{
   const socket=new WebSocket(url,{headers:{Authorization:'Bearer '+tokens[who]}});const messages=[];
   socket.on('message',raw=>{try{messages.push(JSON.parse(raw.toString()));}catch{}});
   socket.on('error',reject);socket.on('open',()=>{sockets.push(socket);resolve({socket,messages});});
  }).catch(reject);
 });
}
async function until(fn) { for(let i=0;i<100;i++){ const result=fn();if(result)return result;await sleep(30);}throw Error('Timed out'); }
before(async()=>{
 execFileSync(process.execPath,[cli,'d1','migrations','apply','DB','--local','--persist-to','.wrangler/test'],{stdio:'pipe',env:{...process.env,WRANGLER_SEND_METRICS:'false'}});
 let seed=readFileSync('test/seed.sql','utf8');
 for(let i=0;i<5;i++) seed+=`INSERT INTO users(id,discord_id,name,friend_code) VALUES('user${i}','${100+i}','Player ${i}','00000000000${i}');\nINSERT INTO sessions(hash,user_id,expires) VALUES('${hash(tokens[i])}','user${i}',unixepoch()+3600);\n`;
 sql(seed);
 worker=spawn(process.execPath,[cli,'dev','--local','--persist-to','.wrangler/test','--ip','127.0.0.1','--port','8787'],{stdio:['ignore','pipe','pipe'],env:{...process.env,WRANGLER_SEND_METRICS:'false'}});
 let logs='';worker.stdout.on('data',b=>logs+=b);worker.stderr.on('data',b=>logs+=b);
 for(let i=0;i<200;i++){try{if((await fetch(base+'/health')).ok)return;}catch{}if(worker.exitCode!==null)throw Error(logs);await sleep(100);}
 throw Error(logs);
});
after(async()=>{for(const s of sockets)s.close();worker?.kill('SIGTERM');});

test('health and session enforcement',async()=>{
 assert.equal((await api('/v1/me',null)).status,401);
 assert.equal((await data('/v1/me')).id,'user0');
 assert.equal((await api('/auth/device',null,'POST',{})).status,503);
 assert.equal((await api('/auth/discord/callback?state=anything',null)).status,403);
});
test('device claims are pending, then issued exactly once without leaking a browser token',async()=>{
 const secret='f'.repeat(64);sql(`INSERT INTO logins(id,secret_hash,expires) VALUES('login-test','${hash(secret)}',unixepoch()+100);`);
 await data('/auth/device/claim',null,'POST',{device_token:secret},202);
 sql("UPDATE logins SET user_id='user0' WHERE id='login-test';");
 const token=await data('/auth/device/claim',null,'POST',{device_token:secret});assert.match(token.access_token,/^[a-f0-9]{64}$/);
 await data('/auth/device/claim',null,'POST',{device_token:secret},410);
});
test('friend requests require recipient acceptance, support presence and block invitations',async()=>{
 await data('/v1/friends',0,'POST',{friend_code:'000000000001'},201);
 await data('/v1/friends/user1/accept',0,'POST',{},404);
 await data('/v1/friends/user0/accept',1,'POST',{});
 const presence=await ws('/v1/events',1);await until(()=>presence.socket.readyState===1);
 const list=await data('/v1/friends');assert.equal(list.friends[0].state,'accepted');assert.equal(list.friends[0].online,true);
 await data('/v1/friends',0,'POST',{friend_code:'000000000002'},201);await data('/v1/friends/user0/accept',2,'POST',{});
 await data('/v1/blocks',2,'POST',{user_id:'user0'});
 await data('/v1/friends',0,'POST',{friend_code:'000000000002'},404);
});
test('private rooms exchange only UDP candidates and readiness; gameplay relay is absent',async()=>{
 const room=await data('/v1/rooms',0,'POST',{mode:'1v1',build:'test-build'},201);
 await data(`/v1/rooms/${room.id}`,2,'GET',undefined,403);
 await data(`/v1/rooms/${room.id}/join`,1,'POST',{},403);
 await data(`/v1/rooms/${room.id}/invite`,0,'POST',{user_id:'user1'});
 const joined=await data(`/v1/rooms/${room.id}/join`,1,'POST',{},201);assert.equal(joined.slot,1);
 const signal=(character,ready)=>({build:'test-build',character,ready,candidates:['127.0.0.1:7777']});
 await data(`/v1/rooms/${room.id}/signal`,0,'POST',{...signal(0,false),build:'wrong'},409);
 await data(`/v1/rooms/${room.id}/signal`,2,'POST',signal(2,true),403);
 await data(`/v1/rooms/${room.id}/signal`,0,'POST',{...signal(0,false),candidates:['example.com:80']},400);
 await data(`/v1/rooms/${room.id}/signal`,0,'POST',{...signal(0,true),slot:99,user:'spoof'});
 const started=await data(`/v1/rooms/${room.id}/signal`,1,'POST',signal(1,true));assert.equal(started.playing,true);
 const state=await data(`/v1/rooms/${room.id}/state`);assert.deepEqual(state.players.map(p=>p.slot),[0,1]);assert.equal(state.players[0].user,'user0');assert.equal(state.players[0].candidates[0],'127.0.0.1:7777');
 await data(`/v1/rooms/${room.id}/ws?build=test-build`,0,'GET',undefined,404);
 await data(`/v1/rooms/${room.id}`,1,'DELETE',undefined,403);
 await data(`/v1/rooms/${room.id}`,0,'DELETE');
});
test('2v2 room enforces four slots, explicit friendship and room capacity under concurrent joins',async()=>{
 for(const i of [2,3,4]){if(i===2)sql("DELETE FROM blocks;");await data('/v1/friends',0,'POST',{friend_code:`00000000000${i}`},201);await data('/v1/friends/user0/accept',i,'POST',{});}
 const room=await data('/v1/rooms',0,'POST',{mode:'2v2',build:'test-build'},201);
 for(const i of [1,2,3,4])await data(`/v1/rooms/${room.id}/invite`,0,'POST',{user_id:`user${i}`});
 const results=await Promise.all([1,2,3,4].map(i=>api(`/v1/rooms/${room.id}/join`,i,'POST',{})));
 assert.equal(results.filter(r=>r.status===201).length,3);assert.equal(results.filter(r=>r.status===409).length,1);
 const state=await data(`/v1/rooms/${room.id}`);assert.deepEqual(state.members.map(m=>m.slot),[0,1,2,3]);
 await data(`/v1/rooms/${room.id}`,0,'DELETE');
});
test('concurrent matchmaking forms a four-person room without exceeding capacity',async()=>{
 const results=await Promise.all([0,1,2,3].map(i=>data('/v1/matchmaking',i,'POST',{mode:'2v2',build:'queue-test'},201)));
 assert.equal(new Set(results.map(r=>r.id)).size,1);assert.deepEqual(results.map(r=>r.slot).sort(),[0,1,2,3]);
 const other=await data('/v1/matchmaking',4,'POST',{mode:'2v2',build:'different-build'},201);assert.notEqual(other.id,results[0].id);
 for(const [i,r] of results.entries())await data(`/v1/rooms/${r.id}/leave`,i,'POST',{},i===0?200:404);
 await data(`/v1/rooms/${other.id}/leave`,4,'POST',{});
});
test('logout revokes the bearer session and closes presence',async()=>{
 const p=await ws('/v1/events',3);await data('/v1/logout',3,'POST',{});await until(()=>p.socket.readyState>=2);await data('/v1/me',3,'GET',undefined,401);
});
