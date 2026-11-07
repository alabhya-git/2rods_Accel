// Microphone frames for the call: every 20 ms, 16 kHz mono PCM and its loudness, posted to the page.
// It runs on the audio thread, so hearing the owner never waits on the page being busy.
class MicFrames extends AudioWorkletProcessor {
  constructor() {
    super()
    this.ratio = sampleRate / 16000 // 3 at 48 kHz: average each group of input samples into one (a box low-pass)
    this.acc = 0
    this.sum = 0
    this.n = 0
    this.out = new Float32Array(320)
    this.len = 0
  }

  process(inputs) {
    const ch = inputs[0] && inputs[0][0]
    if (!ch) return true
    for (let i = 0; i < ch.length; i++) {
      this.sum += ch[i]
      this.n++
      this.acc += 1
      if (this.acc >= this.ratio) {
        this.acc -= this.ratio
        this.out[this.len++] = this.sum / this.n
        this.sum = 0
        this.n = 0
        if (this.len === 320) {
          let e = 0
          for (let j = 0; j < 320; j++) e += this.out[j] * this.out[j]
          this.port.postMessage({ rms: Math.sqrt(e / 320), pcm: this.out }, [this.out.buffer])
          this.out = new Float32Array(320)
          this.len = 0
        }
      }
    }
    return true
  }
}

registerProcessor('mic-frames', MicFrames)
