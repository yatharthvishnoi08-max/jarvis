/** Energy gate on an echo-cancelled microphone. Only interrupts an active reply;
 * it never sends words or activates Jarvis from standby. */
export class SpeechGate {
  private floor = 0.004;
  private began = 0;
  private voicedAt: number | null = null;
  private lastVoiceAt = 0;
  private playing = false;
  private fired = false;
  update(level: number, now: number, speaking: boolean): boolean {
    if (!speaking) {
      this.playing = false; this.fired = false; this.voicedAt = null;
      if (level < 0.025) this.floor = this.floor * 0.96 + level * 0.04;
      return false;
    }
    if (!this.playing) { this.playing = true; this.began = now; }
    if (this.fired || now - this.began < 300) return false;
    const threshold = Math.max(0.008, Math.min(this.floor * 3.5, 0.04));
    if (level < threshold) { if (now - this.lastVoiceAt > 90) this.voicedAt = null; return false; }
    this.lastVoiceAt = now;
    if (this.voicedAt === null) this.voicedAt = now;
    if (now - this.voicedAt < 180) return false;
    this.fired = true;
    return true;
  }
}

export type BargeStatus = 'starting' | 'ready' | 'needs-click' | 'unavailable';
export class MicrophoneInput {
  stream: MediaStream | null = null;
  private context: AudioContext | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private analyser: AnalyserNode | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;
  private closed = false;
  private gate = new SpeechGate();
  constructor(private callbacks: {
    speaking: () => boolean; interrupt: () => void;
    status: (state: BargeStatus) => void; level: (value: number) => void;
  }) {}
  async open() {
    const stream = await navigator.mediaDevices.getUserMedia({audio: {
      echoCancellation: true, noiseSuppression: true, autoGainControl: true,
    }});
    if (this.closed) { stream.getTracks().forEach(t => t.stop()); return; }
    this.stream = stream;
    try {
      this.context = new AudioContext();
      this.source = this.context.createMediaStreamSource(stream);
      this.analyser = this.context.createAnalyser();
      this.analyser.fftSize = 1024;
      this.source.connect(this.analyser); // No connection to speakers: never monitor mic audio.
      this.context.onstatechange = () => this.reportState();
      const samples = new Float32Array(this.analyser.fftSize);
      let lastMeterAt = 0;
      this.timer = setInterval(() => {
        if (!this.analyser || this.context?.state !== 'running') return;
        this.analyser.getFloatTimeDomainData(samples);
        const level = Math.sqrt(samples.reduce((sum, value) => sum + value * value, 0) / samples.length);
        const now = performance.now();
        if (now - lastMeterAt > 100) { lastMeterAt = now; this.callbacks.level(level); }
        if (this.gate.update(level, now, this.callbacks.speaking())) this.callbacks.interrupt();
      }, 25);
      // A browser that requires a gesture is shown an explicit one-time unlock button.
      void this.context.resume().catch(() => this.reportState());
      this.reportState();
    } catch { this.callbacks.status('unavailable'); }
  }
  private reportState() {
    if (!this.closed) this.callbacks.status(this.context?.state === 'running' ? 'ready' : 'needs-click');
  }
  async unlock() { await this.context?.resume(); this.reportState(); }
  startRecognition(recognition: any) {
    const track = this.stream?.getAudioTracks()[0];
    // Modern Chromium accepts a live echo-cancelled input track. Older engines
    // can retain their default microphone path while the acoustic gate still runs.
    try { track ? recognition.start(track) : recognition.start(); }
    catch (error) { if (error instanceof TypeError) recognition.start(); else throw error; }
  }
  close() {
    this.closed = true;
    if (this.timer) clearInterval(this.timer);
    this.source?.disconnect(); this.analyser?.disconnect();
    if (this.context) { this.context.onstatechange = null; void this.context.close().catch(() => {}); }
    this.stream?.getTracks().forEach(track => track.stop());
    this.callbacks.level(0);
  }
}
