/** Browser voice lifecycle. Idle audio is never sent to the Jarvis model.
 * Recognition itself may use the browser vendor's online speech service.
 */
export const normalizeSpeech = (text: string) => text.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, ' ').replace(/\s+/g, ' ').trim();
const wake = /^(?:hey|hi|hello|okay|ok)\s+jarvis\b[\s,.!?:;-]*/i;
const stop = /^(?:stop|stop speaking|stop talking|be quiet|wait|pause)[.!?]*$/i;
export class VoiceConversation {
  enabled = false;
  awake = false;
  private blocked = true;
  private recognition: any = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private idleTimer: ReturnType<typeof setTimeout> | null = null;
  private playing = false;
  private echoText = '';
  private echoUntil = 0;
  private interrupted = false;
  constructor(private factory: () => any, private callbacks: {
    send: (text: string) => boolean;
    listening: (value: boolean) => void;
    transcript: (text: string) => void;
    error: (message: string) => void;
    interrupt?: () => void;
    awake?: (value: boolean) => void;
    sleep?: () => void;
  }, private idleMs = 45000) {}
  start(wakeOnly = false) {
    if (!this.enabled) { this.enabled = true; this.setAwake(!wakeOnly); this.resume(); }
    else if (!wakeOnly && !this.awake) this.setAwake(true);
  }
  stop() { this.enabled = false; this.pause(); this.setAwake(false); }
  standby() { this.setAwake(false); this.callbacks.transcript(''); }
  setBlocked(value: boolean) {
    if (this.blocked === value) return;
    this.blocked = value;
    if (value) { this.pause(); this.clearIdle(); } else { this.resume(); this.armIdle(); }
  }
  setPlayback(value: boolean, text = '') {
    if (text) this.echoText = normalizeSpeech(text);
    if (this.playing && !value) this.echoUntil = Date.now() + 1800;
    const changed = this.playing !== value;
    this.playing = value;
    if (changed) { if (value) this.clearIdle(); else this.armIdle(); }
  }
  private clearIdle() { if (this.idleTimer) clearTimeout(this.idleTimer); this.idleTimer = null; }
  private armIdle() {
    this.clearIdle();
    if (this.enabled && this.awake && !this.blocked && !this.playing)
      this.idleTimer = setTimeout(() => this.standby(), this.idleMs);
  }
  private setAwake(value: boolean) {
    if (this.awake !== value) { this.awake = value; this.callbacks.awake?.(value); }
    this.armIdle();
  }
  private isEcho(text: string) {
    if (!this.playing && Date.now() > this.echoUntil) return false;
    const heard = normalizeSpeech(text);
    return !!heard && !!this.echoText && (' ' + this.echoText + ' ').includes(' ' + heard + ' ');
  }
  private pause() {
    if (this.timer) { clearTimeout(this.timer); this.timer = null; }
    const previous = this.recognition;
    this.recognition = null;
    if (previous) {
      previous.onstart = previous.onresult = previous.onerror = previous.onend = null;
      try { previous.abort(); } catch { /* Already ended. */ }
      this.callbacks.listening(false);
    }
  }
  private resume(delay = 150) {
    if (!this.enabled || this.blocked || this.recognition || this.timer) return;
    this.timer = setTimeout(() => {
      this.timer = null;
      if (!this.enabled || this.blocked) return;
      let recognition: any;
      try { recognition = this.factory(); }
      catch { this.fail('Speech recognition is unavailable in this browser. Open Jarvis in Chrome or Edge.'); return; }
      this.recognition = recognition;
      this.interrupted = false;
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-IN';
      recognition.onstart = () => {
        if (this.recognition === recognition) this.callbacks.listening(true);
      };
      recognition.onresult = (event: any) => {
        if (this.recognition !== recognition || !this.enabled || this.blocked) return;
        let final = '', interim = '';
        for (let i = event.resultIndex || 0; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) final += result[0].transcript + ' ';
          else interim += result[0].transcript;
        }
        const heard = (final || interim).trim();
        if (!heard || this.isEcho(heard)) return;
        const hasWake = wake.test(heard);
        if (!this.awake && !hasWake) return;
        if (hasWake) this.setAwake(true);
        const words = heard.replace(wake, '').trim();
        // Interrupt on recognition of new speech, before waiting for its final result.
        // Echo filtering is a text guard, not acoustic echo cancellation.
        if (this.playing && !this.interrupted && (hasWake || stop.test(words) || words.split(/\s+/).length >= 2)) {
          this.interrupted = true; this.playing = false;
          this.callbacks.interrupt?.();
        }
        this.armIdle();
        this.callbacks.transcript(words);
        if (!final.trim()) return;
        if (/^(?:stop listening|go to sleep|goodbye jarvis)[.!?]*$/i.test(words)) {
          this.callbacks.interrupt?.(); this.standby(); this.callbacks.sleep?.(); return;
        }
        if (!words || stop.test(words)) {
          if (stop.test(words)) this.callbacks.interrupt?.();
          return;
        }
        this.blocked = true;
        this.clearIdle(); this.pause();
        if (!this.callbacks.send(words)) this.fail('Your words are in the message box. Send them when Jarvis is ready.');
      };
      recognition.onerror = (event: any) => {
        if (this.recognition !== recognition) return;
        if (event.error === 'no-speech' || event.error === 'aborted') return;
        this.fail(event.error === 'not-allowed' || event.error === 'service-not-allowed'
          ? 'Allow microphone access for this page, then click Enable microphone once. Wake word will work after that.'
          : event.error === 'network'
          ? 'Browser speech recognition lost its connection. Click Enable microphone to retry, or type your message.'
          : 'The microphone is unavailable. Check your input device, then click Enable microphone.');
      };
      recognition.onend = () => {
        if (this.recognition !== recognition) return;
        this.recognition = null;
        this.callbacks.listening(false);
        this.resume(250);
      };
      try { recognition.start(); }
      catch { this.fail('Could not start the microphone automatically. Click Enable microphone once.'); }
    }, delay);
  }
  private fail(message: string) { this.callbacks.error(message); this.stop(); }
}
