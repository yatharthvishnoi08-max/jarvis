/** One recognition utterance per reply, with explicit pause/resume and stale-event guards. */
export class VoiceConversation {
  enabled = false;
  private blocked = true;
  private recognition: any = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  constructor(private factory: () => any, private callbacks: {
    send: (text: string) => boolean;
    listening: (value: boolean) => void;
    transcript: (text: string) => void;
    error: (message: string) => void;
  }) {}
  start() { if (this.enabled) return; this.enabled = true; this.resume(); }
  stop() { this.enabled = false; this.pause(); }
  setBlocked(value: boolean) {
    if (this.blocked === value) return;
    this.blocked = value;
    if (value) this.pause(); else this.resume();
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
  private resume(delay = 350) {
    if (!this.enabled || this.blocked || this.recognition || this.timer) return;
    this.timer = setTimeout(() => {
      this.timer = null;
      if (!this.enabled || this.blocked) return;
      let recognition: any;
      try { recognition = this.factory(); }
      catch { this.fail('Speech recognition is unavailable in this browser. You can still type your message.'); return; }
      this.recognition = recognition;
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
        this.callbacks.transcript((final || interim).trim());
        if (!final.trim()) return;
        // Pause synchronously before dispatch so late results cannot send twice.
        this.blocked = true;
        this.pause();
        if (!this.callbacks.send(final.trim())) this.fail('Your words are in the message box. Send them when Jarvis is ready.');
      };
      recognition.onerror = (event: any) => {
        if (this.recognition !== recognition) return;
        if (event.error === 'no-speech' || event.error === 'aborted') return;
        this.fail(event.error === 'not-allowed' || event.error === 'service-not-allowed'
          ? 'Allow microphone access for this page, then start voice again.'
          : event.error === 'network'
          ? 'Speech recognition lost its connection. Start voice again, or type your message.'
          : 'The microphone is unavailable. Check your input device, then start voice again.');
      };
      recognition.onend = () => {
        if (this.recognition !== recognition) return;
        this.recognition = null;
        this.callbacks.listening(false);
        this.resume(600);
      };
      try { recognition.start(); }
      catch { this.fail('Could not start the microphone. Start voice again, or type your message.'); }
    }, delay);
  }
  private fail(message: string) { this.stop(); this.callbacks.error(message); }
}
