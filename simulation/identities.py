"""Authored identities: stable IDs, looks, and home assignments."""

NAMES = ['Bea', 'Milo', 'Ada', 'Finn', 'Noor', 'Otto', 'June', 'Theo', 'Iris', 'Sam',
         'Lena', 'Hugo', 'Mae', 'Eli', 'Rosa', 'Arun', 'Hazel', 'Kit', 'Nina', 'Owen',
         'Pia', 'Remy', 'Sage', 'Tess', 'Uma', 'Vera', 'Wren', 'Yara', 'Zoe', 'Luca']
TRAITS = ('social', 'workaholic', 'lazy')
# hair, skin, outfit, hair style; first six match the design board.
LOOKS = [('#3b241d', '#b77d54', '#398477', 'curls'),
         ('#673a25', '#dfab7d', '#b45e42', 'short'),
         ('#bbb9ac', '#e6b889', '#c8a14e', 'bun'),
         ('#252a30', '#dca16a', '#eadac0', 'cap'),
         ('#33252f', '#b77b56', '#8d496b', 'bob'),
         ('#ac532c', '#d99c71', '#65835b', 'beard')]


def manifest(count=30):
    if not 1 <= count <= 30:
        raise ValueError('Town size must be between 1 and 30 residents')
    result = []
    for i, name in enumerate(NAMES[:count]):
        hair, skin, outfit, style = LOOKS[i % 6]
        if i >= 6:
            outfits = ['#668aaa', '#a97c54', '#78924c', '#b77581', '#6f6e96', '#bf9954']
            outfit = outfits[(i // 6 + i) % 6]
            skin = ['#e6b889', '#9f694a', '#c48a60', '#dba574', '#bd825f'][(i // 6 + i) % 5]
        result.append({'id': f'npc{i:02d}', 'name': name, 'trait': TRAITS[i % 3],
                       'appearanceId': f'resident-{i:02d}', 'homeId': f'home-{i % 6 + 1:02d}',
                       'hair': hair, 'skin': skin, 'outfit': outfit, 'hairStyle': style})
    return result
