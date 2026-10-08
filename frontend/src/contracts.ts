import { z } from 'zod';
import world from './world.json';

export const actions = ['eat', 'work', 'sleep', 'socialize', 'wander'] as const;
const finite = z.number().finite();
const stat = finite.min(0).max(100);
const stats = z.object({ hunger: stat, energy: stat, mood: stat, money: finite.min(0) }).strict();
const point = z.object({ x: finite.min(0).max(1024), y: finite.min(0).max(640) });
const action = z.enum(actions);
const decision = z.object({ chosenAction: action.nullable(), appliedAction: action,
  confidence: finite.min(0).max(1).nullable(), fellBack: z.boolean(),
  decisionSource: z.enum(['mock', 'jev', 'error-mock']), errorCode: z.string().nullable() });
const resident = z.object({ id: z.string().regex(/^npc\d{2}$/), name: z.string().min(1).max(50),
  trait: z.enum(['lazy', 'social', 'workaholic']), appearanceId: z.string().regex(/^resident-\d{2}$/),
  homeId: z.string().regex(/^home-0[1-6]$/) });
const entry = z.object({ id: z.string(), before: stats, after: stats, decision,
  destination: point.extend({ locationId: z.string(), anchorId: z.string() }) });
const schema = z.object({ schemaVersion: z.literal(1), runId: z.string(), seed: z.number().int(),
  mode: z.enum(['mock', 'jev', 'mixed']), fixtureKind: z.enum(['staged', 'simulation']).optional(),
  hours: z.literal(24), startHour: z.number().int().min(0).max(23), worldId: z.literal('tiny-town-v1'),
  residents: z.array(resident).min(1).max(30),
  initialSnapshot: z.array(z.object({ id: z.string(), stats, position: point })),
  frames: z.array(z.object({ tick: z.number().int(), clockHour: z.number().int(),
    sequence: z.number().int(), residents: z.array(entry) })).length(24) });
export type Run = z.infer<typeof schema>;
export type Identity = Run['residents'][number];
export type Entry = Run['frames'][number]['residents'][number];
export type Point = { x: number; y: number };
export type Action = typeof actions[number];

export function parseRun(input: unknown): Run {
  const run = schema.parse(input);
  const ids = run.residents.map(p => p.id);
  const appearances = new Set(run.residents.map(p => p.appearanceId));
  if (new Set(ids).size !== ids.length || appearances.size !== ids.length)
    throw Error('Duplicate resident identity or appearance');
  if(run.residents.some(p=>Number(p.appearanceId.slice(-2))>=30 || Number(p.id.slice(-2))>=30))
    throw Error('Unknown resident identity or appearance');
  const sameIds = (entries: { id: string }[]) => entries.length === ids.length &&
    entries.every((p, i) => p.id === ids[i]);
  if (!sameIds(run.initialSnapshot)) throw Error('Initial snapshot IDs do not match manifest');
  const walkable = new Set(world.walkable.map(([x, y]) => `${x},${y}`));
  const onGround = (p: Point) => walkable.has(`${Math.floor(p.x / 16)},${Math.floor(p.y / 16)}`);
  if (run.initialSnapshot.some(p => !onGround(p.position))) throw Error('Invalid spawn');
  for (const [h, frame] of run.frames.entries()) {
    if (frame.tick !== h || frame.sequence !== h + 1 || frame.clockHour !== (h + run.startHour) % 24 || !sameIds(frame.residents))
      throw Error('Recording sequence or resident IDs are invalid');
    for (const [i, p] of frame.residents.entries()) {
      const previous = h ? run.frames[h - 1].residents[i].after : run.initialSnapshot[i].stats;
      if (JSON.stringify(p.before) !== JSON.stringify(previous)) {
        // Object key order is irrelevant at the JSON boundary.
        if (Object.keys(previous).some(k => previous[k as keyof typeof previous] !== p.before[k as keyof typeof previous]))
          throw Error('Stats are discontinuous at an hour boundary');
      }
      if (!onGround(p.destination)) throw Error('Destination is not walkable');
      if (p.decision.decisionSource === 'error-mock') {
        if (!p.decision.errorCode || p.decision.chosenAction !== null || p.decision.confidence !== null || p.decision.fellBack)
          throw Error('Error fallback must be separate from a model choice');
      } else if (p.decision.confidence === null || p.decision.chosenAction === null || p.decision.errorCode !== null)
        throw Error('Missing decision result');
      if (p.decision.fellBack && p.decision.appliedAction !== 'wander') throw Error('Invalid low-confidence fallback');
      if(!p.decision.fellBack && p.decision.decisionSource!=='error-mock' && p.decision.chosenAction!==p.decision.appliedAction)
        throw Error('Applied action differs without a fallback');
    }
  }
  return run;
}
