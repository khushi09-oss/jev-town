"""Small, explicitly scripted exchanges. No model calls, effects or persistent memory."""


def scripted_conversations(entries, identities, tick, seed):
    people = {p['id']: p for p in identities}
    by_id = {p['id']: p for p in entries}
    chats = []
    for entry in sorted(entries, key=lambda p: p['id']):
        interaction = entry.get('interaction')
        if not interaction:
            continue
        ids = sorted([entry['id'], *interaction['partnerIds']])
        if entry['id'] != ids[0]:
            continue
        topic = ('flowers by the garden', 'bread at the bakery', 'water in the fountain')[(seed + tick + int(ids[0][-2:])) % 3]
        opening = {
            'social': f"{people[ids[1]]['name']}, come sit with us! Have you noticed the {topic}?",
            'lazy': f"{people[ids[1]]['name']}, let's take a quiet break and enjoy the {topic}.",
            'workaholic': f"{people[ids[1]]['name']}, a quick break from work? I'd like to hear about the {topic}.",
        }[people[ids[0]]['trait']]
        turns = [{'speakerId': ids[0], 'text': opening}]
        for resident_id in ids[1:]:
            needs = by_id[resident_id]['before']
            if needs['energy'] < 35:
                response = "I'm tired today. A little company while I catch my breath sounds lovely."
            elif needs['hunger'] > 60:
                response = "I'd like that! I'm hungry, though. Shall we stop by the bakery afterward?"
            elif needs['mood'] < 50:
                response = "It's been a rough day. I'm glad you stopped to talk."
            else:
                response = {
                    'social': "I'd love to! It's always nicer sharing these little things with a neighbor.",
                    'lazy': "That sounds lovely. No rushing, though; I'm enjoying this slower pace.",
                    'workaholic': "A short break sounds good. Then I'll be ready to get back to my work.",
                }[people[resident_id]['trait']]
            turns.append({'speakerId': resident_id, 'text': response})
        if len(ids) == 2:
            turns.extend([
                {'speakerId': ids[0], 'text': "Let's stay a little while. The town can wait a moment."},
                {'speakerId': ids[1], 'text': "Deal. It's good to have someone to share a break with."},
            ])
        chats.append({'id': f'chat-{tick}-{ids[0]}', 'source': 'scripted',
                      'participantIds': ids, 'turns': turns})
    return chats
