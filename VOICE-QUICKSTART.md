# Wake word and interruption

On the **Windows laptop**, open `http://localhost:8000/` in Chrome or Edge. Refresh with Ctrl+Shift+R. The header must show **wake-2026.11.21.2** and the Windows hostname. A different label or hostname means you are looking at another build/device. `localhost` on the Mac is not the Windows server. The `?view=basic` fallback has a link back to the voice interface.

Allow microphone permission for this origin once if prompted. If automatic startup is blocked, use **Enable microphone** once. When you see **Say “Hey Jarvis”**, no chat or microphone click is needed for each conversation. Browser sound policies can require **Replay Voice** once to enable audio. Keep one Jarvis tab open; another tab in the same origin cannot take its microphone lock. Keep the computer awake. This is browser wake-word support, not a Windows background service that survives closing the browser.

- Say **Hey Jarvis, what is seven plus eight?** It should answer 15.
- Follow up without the wake phrase while the conversation is active.
- Ask for a long explanation. While it speaks, say **Actually, give me just one sentence**. Playback should stop on microphone speech or recognized interim speech, then the final sentence becomes one new request. Check **Interruption: ready**; if the browser suspends its audio context, click **Enable interruption** once. The microphone level meter should move as you speak.
- **Hey Jarvis, stop** or **stop** during an active conversation stops speech without making a model request.
- **Stop listening** returns to wake-word standby. Ordinary speech is then ignored by Jarvis until the wake phrase.
- After 45 seconds of quiet idle time, it returns to standby automatically.
- **Microphone off** stops recognition entirely. Re-enable using the Hey Jarvis toggle.

Microphone recognition stays available during generated replies. It pauses during computer-task execution and approval waits. Voice interruption stops reply audio; it does not approve or cancel computer actions. Use the existing task Stop / Emergency stop controls for those.

Browser speech recognition may use an online speech service. Standby transcripts are not saved in Jarvis or submitted to its LLM. The microphone now requests browser echo cancellation and shares its live track with speech recognition where supported. An acoustic gate stops an active spoken reply without waiting for a transcript. A second transcript guard rejects recognized fragments of the reply. Echo cancellation quality depends on the device; sustained background noise can also trigger interruption. Headphones reduce speaker feedback. Detection latency and recognition quality depend on the browser, network, microphone and room. Speaker/echo performance must be verified on the physical laptop.

## Validation

- 19 Node tests pass: wake gating, wake-plus-command, follow-up conversation, interim interruption, recognized reply echo, idle timeout, sleep, permission denial, stale recognition, approval blocking, late TTS suppression, stale audio promises, and task state integrity.
- 9 focused Python tests pass: model failure recovery, preserved history, chat/audio delivery, runtime identity and fresh HTML serving.
- Production TypeScript/Vite build passes.
- Full browser fixture passes with explicitly simulated microphone/model/speaker: automatic standby after reload, ignored ordinary speech, wake request, Planner-to-Talk activation, interim interruption before final, single replacement request, return to standby, persisted microphone-off, manual restart, and exclusive microphone handoff between two tabs. This is not proof of physical speech recognition.
- Windows deployment and physical audio evidence belong in WINDOWS-ACCEPTANCE.md. Do not infer hardware success from mocked recognition events.

## Physical feedback and correction

The owner confirmed build .1 and native wake-word/voice reply on Windows. Interruption failed: no live transcript appeared during playback. Build .2 adds shared echo-cancelled capture and acoustic interruption so playback can stop without an ASR event. Four capture/gate tests and two controller acoustic tests pass, including late permission cleanup, noise/startup spike rejection and echo-tail rejection. A full browser fixture verified that a microphone-level signal alone stopped playback with zero additional model requests. This is simulated signal evidence; physical .2 retest remains pending.
