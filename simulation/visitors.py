"""Free, authored route responses. Decisions and needs remain the recorded ones."""
from .world import point


def bench_plans(recording):
    traits = {p['id']: p['trait'] for p in recording['residents']}
    plans = []
    for site_id, name, x, y in [('park-gate', 'Park gate', 44, 17),
                                ('garden-view', 'Garden view', 48, 23)]:
        frames = []
        for frame in recording['frames']:
            candidates = sorted((p for p in frame['residents']
                                 if p['decision']['appliedAction'] == 'wander' and not p.get('interaction')),
                                key=lambda p: (traits[p['id']] != 'social', p['id']))[:2]
            occupied = {(p['destination']['x'], p['destination']['y'])
                        for p in frame['residents'] if p not in candidates}
            changes = []
            slots = [point((x+dx, y+dy)) for dy in (0, 2) for dx in (0, 2)]
            for person in candidates:
                slot = next((p for p in slots if (p['x'], p['y']) not in occupied), None)
                if slot is None:
                    continue
                occupied.add((slot['x'], slot['y']))
                changes.append({'id': person['id'], 'destination': {
                    'locationId': 'park', 'anchorId': f"bench-{site_id}-{person['id']}", **slot}})
            frames.append(changes)
        plans.append({'id': site_id, 'name': name, 'x': x*16+24, 'y': y*16-8, 'frames': frames})
    return plans
