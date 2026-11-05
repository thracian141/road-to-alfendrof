// Run from the backend directory inside the repository Nix shell.
// Only local .wrangler/native state is mutated; no real accounts or credentials.
import {spawn,execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync,unlinkSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
const cli='node_modules/wrangler/bin/wrangler.js';
const env={...process.env,WRANGLER_SEND_METRICS:'false'};
const args=['--local','--persist-to','.wrangler/native'];
execFileSync(process.execPath,[cli,'d1','migrations','apply','DB',...args],{stdio:'pipe',env});
let sql=readFileSync('test/seed.sql','utf8');
for(let i=1;i<=4;i++)sql+=`INSERT INTO users(id,discord_id,name,friend_code) VALUES('native${i}','${900+i}','Native ${i}','10000000000${i}');\nINSERT INTO sessions(hash,user_id,expires) VALUES('${createHash('sha256').update(String(i).repeat(64)).digest('hex')}','native${i}',unixepoch()+3600);\n`;
const path=join(tmpdir(),`alfendrof-native-${process.pid}.sql`);writeFileSync(path,sql);
try{execFileSync(process.execPath,[cli,'d1','execute','DB',...args,'--file',path],{stdio:'pipe',env});}finally{unlinkSync(path);}
const worker=spawn(process.execPath,[cli,'dev',...args,'--ip','127.0.0.1','--port','8790'],{env,stdio:['ignore','pipe','pipe']});
let logs='';worker.stdout.on('data',b=>logs+=b);worker.stderr.on('data',b=>logs+=b);
try{
 let ready=false;for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:8790/health')).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}
 if(!ready)throw Error(logs);
 const result=spawn('cargo',['test','--lib','native_discovery_then_direct_four_player_combat','--','--ignored','--test-threads=1'],{cwd:'..',env:{...env,ALFENDROF_NATIVE_TEST_URL:'http://127.0.0.1:8790'},stdio:'inherit'});
 process.exitCode=await new Promise(resolve=>{result.once('error',()=>resolve(1));result.once('exit',code=>resolve(code??1));});
}finally{worker.kill('SIGTERM');}
