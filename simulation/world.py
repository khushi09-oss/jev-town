"""Authored walkable ground and action anchors. Python assigns all destinations."""
import json
from collections import deque
from pathlib import Path

LAYOUT = json.loads(Path(__file__).with_name('world-layout.json').read_text())
WIDTH, HEIGHT, TILE = 64, 40, 16


def rect_tiles(rect):
    x, y, w, h = rect
    return {(a, b) for a in range(x, x + w) for b in range(y, y + h)}


def ground():
    walk = set()
    for road in LAYOUT['roads']:
        width = road['widthTiles']
        for (x1, y1), (x2, y2) in zip(road['pointsTiles'], road['pointsTiles'][1:]):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    for dx in range(-(width // 2), width - width // 2):
                        for dy in range(-(width // 2), width - width // 2):
                            walk.add((x + dx, y + dy))
    for region in LAYOUT['regions']:
        if region['id'] in ('square', 'park', 'east-bank'):
            walk |= rect_tiles(region['rectTiles'])
    walk |= rect_tiles([3, 20, 11, 7])  # cafe patio, 30 seats with spaced rows
    walk |= rect_tiles([15, 27, 5, 9])  # outdoor workshop stations
    walk |= rect_tiles([29, 27, 14, 8])
    for b in LAYOUT['buildings']:
        if b['kind'] == 'cottage':
            x, y = b['doorTile']
            walk |= {(x, z) for z in range(y, 12)}
        if b['kind'] not in ('garden',):
            walk -= rect_tiles(b['footprintTiles'])
        walk.add(tuple(b['doorTile']))
    # Rest slots are explicitly separate indoor positions, connected via home doors.
    for b in LAYOUT['buildings'][:6]:
        x, y = b['doorTile']
        walk |= {(a, b) for a in range(x - 2, x + 3) for b in range(y - 3, y)}
    walk -= rect_tiles([26, 17, 3, 3])
    for x in (30, 33, 36, 39, 42):
        walk -= {(x, y) for y in range(28, 34) if y != 31}
    walk -= rect_tiles([57, 0, 3, 40])
    walk |= rect_tiles(LAYOUT['bridge']['rectTiles'])
    return {(x, y) for x, y in walk if 0 <= x < WIDTH and 0 <= y < HEIGHT}


WALKABLE = ground()


def path(start, end):
    """Shortest four-direction tile route, including explicit interior door corridors."""
    start, end = tuple(start), tuple(end)
    if start not in WALKABLE or end not in WALKABLE:
        raise ValueError('Route endpoint is not walkable')
    queue, previous = deque([start]), {start: None}
    while queue:
        p = queue.popleft()
        if p == end:
            route = []
            while p is not None:
                route.append(p)
                p = previous[p]
            return route[::-1]
        for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            neighbor = (p[0] + dx, p[1] + dy)
            if neighbor in WALKABLE and neighbor not in previous:
                previous[neighbor] = p
                queue.append(neighbor)
    raise ValueError(f'No route between {start} and {end}')


def point(tile):
    return {'x': tile[0] * TILE + 8, 'y': tile[1] * TILE + 8}


def destination(index, action, tick, seed):
    if action == 'sleep':
        home, bed = index % 6, index // 6
        door = LAYOUT['buildings'][home]['doorTile']
        tile, location = (door[0] - 2 + (bed % 3) * 2,
                          door[1] - 3 + (bed // 3) * 2), f'home-{home + 1:02d}'
    elif action == 'eat':
        tile, location = (4 + (index % 10), 21 + index // 10 * 2), 'bakery'
    elif action == 'work':
        if index < 10:
            tile, location = (16 + index % 2 * 2, 27 + index // 2 * 2), 'workshop'
        elif index < 20:
            tile, location = (31 + ((index - 10) % 4) * 3, 28 + (index - 10) // 4 * 2), 'garden'
        else:
            tile, location = (22 + (index - 20) % 5 * 2, 21 + (index - 20) // 5 * 2), 'square'
    elif action == 'socialize':
        # Eight small conversational clusters; four uniquely spaced feet per cluster.
        group, seat = index // 4, index % 4
        # Keep the lower groups beside the fountain, above the square work stations.
        x, y = [(21,14),(25,14),(29,14),(33,14),
                (20,18),(23,18),(30,18),(33,18)][group]
        tile, location = (x + seat % 2, y + seat // 2 * 2), 'square'
    elif action == 'wander':
        choices = [(x, y) for x in range(44, 54, 2) for y in range(15, 26, 2)]
        # Thirty distinct park slots, with room for each resident's full silhouette.
        tile, location = choices[(index * 7 + tick * 11 + seed) % 30], 'park'
    else:
        raise ValueError('Unknown action')
    if tile not in WALKABLE:
        raise ValueError(f'Invalid {action} anchor: {tile}')
    return {'locationId': location, 'anchorId': f'{location}-{action}-{index:02d}', **point(tile)}


def world_data():
    return {**LAYOUT, 'tilePx': TILE, 'walkable': [list(p) for p in sorted(WALKABLE)],
            'interiorTiles': [list(p) for b in LAYOUT['buildings'][:6]
                              for p in WALKABLE if p in rect_tiles(b['footprintTiles'])]}
