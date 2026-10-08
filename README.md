# Tiny Town

A town of 30 NPCs choosing to eat, work, sleep, socialize, or wander each hour. Jev chooses an action and confidence; Python applies the consequences.

## Run (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install requests python-dotenv matplotlib
python town.py
```

Open `town.html` for the animation. `town.png` shows hourly actions, average stats, and action shares by personality.

Optional local `.env` settings:

```text
JEV_KEY=<your TypeSafe key>
JEV_URL=https://api.typesafe.ai/v1/systemone
JEV_MODEL=jev-latest
JEV_WORKERS=4
JEV_MIN_CONF=0.2
```

With no key configured, the simulation uses an offline stand-in. To force an offline run even when `.env` has a key:

```powershell
$env:JEV_KEY = ''
python town.py
Remove-Item Env:JEV_KEY
```

Never commit `.env`, credentials, or `.venv`. Markdown files other than README are kept local.

## Personalities

The default town has 10 lazy, 10 social, and 10 workaholic NPCs. Each request includes `state.personality`.

| Trait | Preference |
|---|---|
| Lazy | Rest below 60 energy; work below 15 money with energy above 40 |
| Social | Seek company below 85 mood with energy above 30 |
| Workaholic | Work whenever energy is above 40, even with enough money |

All traits prioritize hunger above 60, then exhaustion below 30 energy or sleep from 22:00 to 05:00. Otherwise, company below 50 mood and work below 30 money are the ordinary preferences. Wandering fills the remaining time. These are explicit rules in the offline stand-in and instructions to Jev; real model choices can differ. Confidence below the configured cutoff still falls back to wandering.

Wandering lowers mood by 4 and working by 6, so NPCs need company again over time. Socializing raises mood by 22. Sleep restores 25 energy without increasing mood. These consequences apply equally to all traits and are controlled by Python, not Jev.

The chart aggregates actual actions after the confidence fallback. An ordinary full run makes about 720 API requests.

A small real Jev check on October 8, 2026 used identical stats (hour 14, hunger 30, energy 45, mood 60, money 40) for each trait, twice. Lazy NPCs chose sleep (confidence 0.91, 0.90), social NPCs chose socialize (0.70, 0.68), and workaholics chose work (0.71, 0.76). No choice triggered fallback. This verifies personality differences in that scenario; the revised full-day balance has only been tested offline.

## Tests

```powershell
python -m unittest -v
```

Tests use mocked API responses and make no paid calls.
