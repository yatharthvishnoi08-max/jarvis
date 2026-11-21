import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const { VoiceConversation } = createRequire(import.meta.url)(process.env.VOICE_TEST_MODULE);
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
function setup(accepted = true) {
  const records = [], sent = [], errors = [], listening = [];
  class Recognition {
    start() { records.push(this); this.onstart?.(); }
    abort() { this.aborted = true; }
  }
  const controller = new VoiceConversation(() => new Recognition(), {
    send: text => { sent.push(text); return accepted; },
    listening: value => listening.push(value), transcript: () => {}, error: text => errors.push(text),
  });
  controller.setBlocked(false); controller.start();
  return {controller, records, sent, errors, listening};
}
function result(text, isFinal=true) { return {resultIndex:0,results:[Object.assign([{transcript:text}],{isFinal})]}; }
test('one click spans multiple turns, waiting for reply/audio and ignoring stale recognition', async () => {
  const f = setup(); await wait(400);
  const first = f.records[0], late = first.onresult;
  first.onresult(result('hello',false)); assert.equal(f.sent.length,0);
  first.onresult(result('hello')); assert.deepEqual(f.sent,['hello']);
  late(result('duplicate')); assert.deepEqual(f.sent,['hello']);
  await wait(400); assert.equal(f.records.length,1,'must wait while thinking or speaking');
  f.controller.setBlocked(false); await wait(400);
  assert.equal(f.records.length,2);
  f.records[1].onresult(result('second turn')); assert.deepEqual(f.sent,['hello','second turn']);
  f.controller.stop();
});
test('silence restarts, stop cancels rearming and ignores late input', async () => {
  const f=setup(); await wait(400); f.records[0].onend(); await wait(650);
  assert.equal(f.records.length,2);
  const late=f.records[1].onresult; f.controller.stop(); late(result('must not send')); await wait(400);
  assert.equal(f.records.length,2); assert.equal(f.sent.length,0);
});
test('playback or approval pauses active microphone and resumes only after unblocking', async () => {
  const f=setup(); await wait(400); const old=f.records[0]; const late=old.onresult;
  f.controller.setBlocked(true); assert.equal(old.aborted,true); late(result('speaker echo'));
  assert.equal(f.sent.length,0); f.controller.setBlocked(false); await wait(400);
  assert.equal(f.records.length,2); f.controller.stop();
});
test('permission failure stops instead of repeatedly prompting', async () => {
  const f=setup(); await wait(400); f.records[0].onerror({error:'not-allowed'}); await wait(650);
  assert.equal(f.controller.enabled,false); assert.equal(f.records.length,1); assert.match(f.errors[0],/Allow microphone/);
});
test('failed send preserves transcript via callback and stops retrying', async () => {
  const f=setup(false); await wait(400); f.records[0].onresult(result('unsent words')); await wait(400);
  assert.deepEqual(f.sent,['unsent words']); assert.equal(f.controller.enabled,false); assert.equal(f.records.length,1);
});

function wakeSetup(idleMs=45000) {
  const records=[],sent=[],awake=[],errors=[],transcripts=[]; let interrupts=0;
  class Recognition {start(){records.push(this);this.onstart?.();} abort(){this.aborted=true;}}
  const controller=new VoiceConversation(()=>new Recognition(),{
    send:text=>{sent.push(text);return true;}, listening:()=>{}, transcript:text=>transcripts.push(text),
    error:message=>errors.push(message), awake:value=>awake.push(value), interrupt:()=>{interrupts++;},
  },idleMs);
  controller.setBlocked(false);controller.start(true);
  return {controller,records,sent,awake,errors,transcripts,get interrupts(){return interrupts;}};
}
test('standby ignores ordinary speech; wake plus command strips wake phrase and dispatches once', async()=>{
  const f=wakeSetup();await wait(200);const rec=f.records[0];const late=rec.onresult;
  rec.onresult(result('the meeting is tomorrow')); assert.equal(f.sent.length,0);assert.deepEqual(f.transcripts,[]);
  rec.onresult(result('Hey Jarvis what is two plus two',false));assert.equal(f.controller.awake,true);assert.equal(f.sent.length,0);
  rec.onresult(result('Hey Jarvis what is two plus two'));assert.deepEqual(f.sent,['what is two plus two']);
  late(result('Hey Jarvis duplicate'));assert.equal(f.sent.length,1);f.controller.stop();
});
test('wake phrase alone waits for next utterance; follow-up does not need another wake', async()=>{
  const f=wakeSetup();await wait(200);f.records[0].onresult(result('Hey Jarvis'));
  assert.equal(f.sent.length,0);f.records[0].onend();await wait(300);
  f.records[1].onresult(result('hello there'));assert.deepEqual(f.sent,['hello there']);
  f.controller.setBlocked(false);await wait(200);f.records[2].onresult(result('and what else'));
  assert.deepEqual(f.sent,['hello there','and what else']);f.controller.stop();
});
test('speaker echo cannot wake or interrupt; new interim speech interrupts before final then sends once', async()=>{
  const f=wakeSetup();await wait(200);const rec=f.records[0];
  f.controller.setPlayback(true,'To start, say Hey Jarvis. Here is the weather forecast for today.');
  rec.onresult(result('Hey Jarvis',false));assert.equal(f.controller.awake,false);assert.equal(f.interrupts,0);
  rec.onresult(result('Hey Jarvis stop',false));assert.equal(f.interrupts,1);assert.equal(f.sent.length,0);
  rec.onresult(result('Hey Jarvis stop'));assert.equal(f.sent.length,0);
  f.controller.setPlayback(true,'Here is the weather forecast for today.');
  rec.onresult(result('weather forecast for today',false));assert.equal(f.interrupts,2,'final stop is local only');
  rec.onend();await wait(300);
  f.records[1].onresult(result('Actually make it shorter',false));assert.equal(f.interrupts,3);
  f.records[1].onresult(result('Actually make it shorter'));assert.deepEqual(f.sent,['Actually make it shorter']);f.controller.stop();
});
test('idle returns to wake standby despite repeated store sync; stop listening never calls model', async()=>{
  const f=wakeSetup(250);await wait(200);f.records[0].onresult(result('hey jarvis'));
  for(let i=0;i<4;i++){f.controller.setPlayback(false,'');await wait(90);}
  assert.equal(f.controller.awake,false);
  f.records[0].onresult(result('this must be ignored'));assert.equal(f.sent.length,0);
  f.records[0].onresult(result('Hey Jarvis stop listening'));assert.equal(f.controller.awake,false);assert.equal(f.sent.length,0);
  f.controller.stop();
});
test('approval block suppresses wake commands and stop disables microphone completely', async()=>{
  const f=wakeSetup();await wait(200);const late=f.records[0].onresult;
  f.controller.setBlocked(true);late(result('Hey Jarvis approve everything'));assert.equal(f.sent.length,0);
  f.controller.setBlocked(false);await wait(200);const last=f.records[1].onresult;
  f.controller.stop();last(result('Hey Jarvis hello'));await wait(300);
  assert.equal(f.sent.length,0);assert.equal(f.records.length,2);
});
test('acoustic interruption stops speech without an ASR result, rejects tail echo, and retains follow-up words',async()=>{
 const f=wakeSetup();await wait(200);f.records[0].onresult(result('Hey Jarvis'));
 f.controller.setPlayback(true,'This is the long story you requested');
 f.controller.interruptFromMicrophone();assert.equal(f.interrupts,1);assert.equal(f.sent.length,0);
 f.controller.interruptFromMicrophone();assert.equal(f.interrupts,1);
 f.records[0].onresult(result('the long story you requested'));assert.equal(f.sent.length,0);
 f.records[0].onresult(result('Make it shorter'));assert.deepEqual(f.sent,['Make it shorter']);f.controller.stop();
});
test('acoustic noise cannot wake standby or bypass a blocked computer task',async()=>{
 const f=wakeSetup();await wait(200);f.controller.setPlayback(true,'reply');f.controller.interruptFromMicrophone();assert.equal(f.interrupts,0);
 f.records[0].onresult(result('Hey Jarvis'));f.controller.setBlocked(true);f.controller.interruptFromMicrophone();assert.equal(f.interrupts,1,'wake phrase interrupted, blocked acoustic event did not');f.controller.stop();
});
