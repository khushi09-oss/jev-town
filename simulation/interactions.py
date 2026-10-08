"""Recorded conversation plans; no extra decisions, effects, or relationship scores."""
from .world import destination


def plan_interactions(entries, tick, seed):
    for entry in entries:
        entry['interaction'] = None
    socializers = sorted((p for p in entries if p['decision']['appliedAction'] == 'socialize'),
                         key=lambda p: p['id'])
    groups = [socializers[i:i + 4] for i in range(0, len(socializers), 4)]
    # Move one person over so an odd final group doesn't leave someone isolated.
    if len(groups) > 1 and len(groups[-1]) == 1:
        groups[-1].insert(0, groups[-2].pop())
    for group_index, group in enumerate(groups):
        for seat, entry in enumerate(group):
            entry['destination'] = destination(group_index * 4 + seat, 'socialize', tick, seed)
            entry['destination']['anchorId'] = f"square-socialize-{entry['id']}"
            partners = [p['id'] for p in group if p['id'] != entry['id']]
            if partners:
                entry['interaction'] = {'kind': 'conversation', 'partnerIds': partners}
