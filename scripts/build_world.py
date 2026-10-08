"""Export the Python navigation grid used by deterministic browser playback."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from simulation.world import world_data, destination, path

for action in ('eat', 'work', 'sleep', 'socialize', 'wander'):
    for index in range(30):
        anchor = destination(index, action, 14, 7)
        path((21, 15), (anchor['x'] // 16, anchor['y'] // 16))
(ROOT / 'frontend/src/world.json').write_text(json.dumps(world_data()), encoding='utf-8')
print('Exported validated Python navigation and all-action capacity')
