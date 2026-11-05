import {test} from 'node:test';
import assert from 'node:assert/strict';
import {discordProfile} from '../src/discord.ts';
const config={clientId:'test-app',clientSecret:'local-fixture-only',redirectUri:'https://example.test/auth/discord/callback'};
test('Discord authorization code is exchanged server-side and only the identify profile is requested',async()=>{
 const calls=[];const mock=async(url,options)=>{calls.push({url,options});return calls.length===1?Response.json({access_token:'fixture-access'}):Response.json({id:'123456',username:'player',global_name:'The Player'});};
 assert.deepEqual(await discordProfile('fixture-code',config,mock),{id:'123456',name:'The Player'});
 assert.equal(calls[0].url,'https://discord.com/api/oauth2/token');assert.equal(calls[0].options.body.get('client_secret'),config.clientSecret);assert.equal(calls[0].options.body.get('redirect_uri'),config.redirectUri);
 assert.equal(calls[1].url,'https://discord.com/api/users/@me');assert.equal(calls[1].options.headers.Authorization,'Bearer fixture-access');
});
test('Discord failures and malformed profiles cannot become game accounts',async()=>{
 assert.equal(await discordProfile('code',config,async()=>new Response('',{status:401})),null);
 let n=0;assert.equal(await discordProfile('code',config,async()=>Response.json(++n===1?{access_token:'fixture'}:{id:'not-discord',username:'wrong'})),null);
 assert.equal(await discordProfile('code',config,async()=>Response.json({})),null);
});
