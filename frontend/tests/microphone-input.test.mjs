import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const {SpeechGate,MicrophoneInput}=createRequire(import.meta.url)(process.env.MIC_TEST_MODULE);
test('acoustic gate ignores idle voices, initial playback transient, short clicks and steady low noise',()=>{
 const gate=new SpeechGate();
 for(let t=0;t<1000;t+=25)assert.equal(gate.update(.1,t,false),false);
 for(let t=1000;t<1300;t+=25)assert.equal(gate.update(.2,t,true),false);
 assert.equal(gate.update(.04,1400,true),false);
 for(let t=1425;t<2000;t+=25)assert.equal(gate.update(.003,t,true),false);
});
test('sustained microphone speech interrupts once without any recognition transcript and rearms next reply',()=>{
 const gate=new SpeechGate();gate.update(.001,0,true);
 let triggers=0;for(let t=325;t<900;t+=25)if(gate.update(t===400?.002:.06,t,true))triggers++;
 assert.equal(triggers,1);
 gate.update(.001,1000,false);gate.update(.001,1100,true);
 for(let t=1425;t<1900;t+=25)if(gate.update(.06,t,true))triggers++;
 assert.equal(triggers,2);
});
test('capture requests echo cancellation, shares the same live track, and stops tracks on cleanup',async()=>{
 let stopped=0,received, constraints;const track={stop(){stopped++;}};
 Object.defineProperty(globalThis,'navigator',{configurable:true,value:{mediaDevices:{getUserMedia:async c=>{constraints=c;return {getTracks:()=>[track],getAudioTracks:()=>[track]};}}}});
 global.AudioContext=class {state='running';createMediaStreamSource(){return{connect(){},disconnect(){}};}createAnalyser(){return{fftSize:1024,getFloatTimeDomainData(a){a.fill(0);},disconnect(){}};}resume(){return Promise.resolve();}close(){return Promise.resolve();}};
 const states=[];const input=new MicrophoneInput({speaking:()=>false,interrupt:()=>assert.fail('idle must not interrupt'),status:s=>states.push(s),level:()=>{}});
 await input.open();input.startRecognition({start:t=>{received=t;}});
 assert.equal(constraints.audio.echoCancellation,true);assert.equal(received,track);assert.equal(states.at(-1),'ready');input.close();assert.equal(stopped,1);
});
test('permission finishing after cleanup stops the stream instead of starting capture',async()=>{
 let resolve,stopped=0;Object.defineProperty(globalThis,'navigator',{configurable:true,value:{mediaDevices:{getUserMedia:()=>new Promise(r=>{resolve=r;})}}});
 const input=new MicrophoneInput({speaking:()=>false,interrupt:()=>{},status:()=>assert.fail('disposed capture must not start'),level:()=>{}});
 const opening=input.open();input.close();resolve({getTracks:()=>[{stop(){stopped++;}}]});await opening;assert.equal(stopped,1);
});
