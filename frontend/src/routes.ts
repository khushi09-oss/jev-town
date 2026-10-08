import world from './world.json';
import type { Point } from './contracts';
const ground = new Set(world.walkable.map(([x, y]) => y * 64 + x));
const key = (p: Point) => Math.floor(p.y / 16) * 64 + Math.floor(p.x / 16);
const cache = new Map<string, Point[]>();
export function route(start: Point, end: Point): Point[] {
  const a = key(start), b = key(end), name = `${a}:${b}`;
  const hit = cache.get(name);
  if (hit) return hit;
  if (!ground.has(a) || !ground.has(b)) throw Error('Unwalkable route endpoint');
  const queue = [a], previous = new Map<number, number>([[a, -1]]);
  for (let i = 0; i < queue.length && !previous.has(b); i++) {
    const current = queue[i], x = current % 64, y = Math.floor(current / 64);
    for (const [dx, dy] of [[0, 1], [1, 0], [0, -1], [-1, 0]]) {
      const nx = x + dx, ny = y + dy, n = ny * 64 + nx;
      if (nx >= 0 && nx < 64 && ny >= 0 && ny < 40 && ground.has(n) && !previous.has(n)) {
        previous.set(n, current); queue.push(n);
      }
    }
  }
  if (!previous.has(b)) throw Error('Unreachable destination');
  const tiles = []; let cursor = b;
  while (cursor !== -1) { tiles.push({ x: (cursor % 64) * 16 + 8, y: Math.floor(cursor / 64) * 16 + 8 }); cursor = previous.get(cursor)!; }
  tiles.reverse();
  if (tiles.length === 1) tiles[0] = {x:end.x,y:end.y};
  cache.set(name, tiles);
  return tiles;
}
export function along(points: Point[], distance: number): { position: Point; facing: number } {
  if (points.length === 1) return { position: points[0], facing: 0 };
  const segment = Math.min(points.length - 2, Math.floor(Math.max(0, distance) / 16));
  const a = points[segment], b = points[segment + 1];
  const f = Math.min(1, Math.max(0, (distance - segment * 16) / 16));
  return { position: { x: Math.round(a.x + (b.x - a.x) * f), y: Math.round(a.y + (b.y - a.y) * f) },
    facing: b.x > a.x ? 2 : b.x < a.x ? 1 : b.y < a.y ? 3 : 0 };
}
