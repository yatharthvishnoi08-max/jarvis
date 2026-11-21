import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
const cwd=fileURLToPath(new URL('..',import.meta.url));
const output=mkdtempSync(join(tmpdir(),'jarvis-voice-test-'));
try {
  execFileSync(process.execPath,['node_modules/typescript/bin/tsc','src/voice/VoiceConversation.ts','--target','ES2020','--module','commonjs','--skipLibCheck','--outDir',output],{cwd,stdio:'inherit'});
  execFileSync(process.execPath,['--test','tests/voice-conversation.test.mjs'],{cwd,stdio:'inherit',env:{...process.env,VOICE_TEST_MODULE:join(output,'VoiceConversation.js')}});
} finally { rmSync(output,{recursive:true,force:true}); }
