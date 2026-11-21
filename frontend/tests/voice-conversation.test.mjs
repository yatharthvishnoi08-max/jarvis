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
