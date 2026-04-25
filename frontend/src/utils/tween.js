export const easing = {
  linear: (t) => t,
  easeInOut: (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
  easeOut: (t) => t * (2 - t),
};

export class Tween {
  constructor(startVal, endVal, durationMs, easingFn = easing.linear) {
    this.startVal = startVal;
    this.endVal = endVal;
    this.durationMs = durationMs;
    this.easingFn = easingFn;
    this.elapsed = 0;
    this.isComplete = false;
  }

  update(deltaMs) {
    if (this.isComplete) return this.endVal;
    this.elapsed += deltaMs;
    const t = Math.min(this.elapsed / this.durationMs, 1);
    const value = this.startVal + (this.endVal - this.startVal) * this.easingFn(t);
    if (t >= 1) this.isComplete = true;
    return value;
  }
}

export class TweenManager {
  constructor() {
    this.tweens = [];
  }

  add(tween) {
    this.tweens.push(tween);
    return tween;
  }

  update(deltaMs) {
    for (const tween of this.tweens) {
      tween.update(deltaMs);
    }
    this.tweens = this.tweens.filter((t) => !t.isComplete);
  }
}
