import type { Run, Entry, Point } from './contracts';
import { route, along } from './routes';
import tokens from './design-tokens.json';

export class Playback {
  time = 14.75;
  playing = false;
  speed: 1 | 2 | 4 = 1;
  loop = false;
  constructor(public run: Run) {}
  seek(time: number) { if (!Number.isFinite(time)) return; this.time = Math.min(24, Math.max(0, time)); }
  restart() { this.time = 0; }
  advance(seconds: number) {
    if (!this.playing || seconds < 0 || !Number.isFinite(seconds)) return;
    const next = this.time + seconds * this.speed / tokens.motion.hourPlaybackSecondsAt1x;
    if (next >= 24 && this.loop) this.time = next % 24;
    else { this.seek(next); if (this.time === 24) this.playing = false; }
  }
  get hour() { return Math.min(23, Math.floor(this.time)); }
  entry(index: number): Entry { return this.run.frames[this.hour].residents[index]; }
  stats(index: number) { return this.time === 24 ? this.entry(index).after : this.entry(index).before; }
  position(index: number): { position: Point; facing: number; moving: boolean } {
    const h = this.hour, entry = this.entry(index);
    const start = h ? this.run.frames[h - 1].residents[index].destination : this.run.initialSnapshot[index].position;
    const points = route(start, entry.destination), distance = (points.length - 1) * 16;
    const stagger = (((this.run.seed + index * 17 + h * 7) % 31 + 31) % 31) / 31 * tokens.motion.departureStaggerFraction;
    const phase = this.time === 24 ? 1 : this.time - h;
    const available = (.95 - stagger) * tokens.motion.hourPlaybackSecondsAt1x;
    const velocity = Math.min(tokens.motion.maxWalkWorldPxPerSecond,
      Math.max(tokens.motion.baseWalkWorldPxPerSecond, distance / available));
    if (distance > available * tokens.motion.maxWalkWorldPxPerSecond)
      throw Error('Route exceeds the presentation speed cap');
    const travelled = Math.min(distance, Math.max(0, phase - stagger) * tokens.motion.hourPlaybackSecondsAt1x * velocity);
    return { ...along(points, travelled), moving: travelled < distance && phase >= stagger };
  }
  counts() {
    const result = { eat: 0, work: 0, sleep: 0, socialize: 0, wander: 0 };
    for (const resident of this.run.frames[this.hour].residents) result[resident.decision.appliedAction]++;
    return result;
  }
}

export function nightAlpha(hour: number) {
  const clock = hour % 24;
  if (clock < 5 || clock >= 23) return .35;
  if (clock < 7) return .35 * (7 - clock) / 2;
  if (clock >= 18) return .35 * (clock - 18) / 5;
  return 0;
}
