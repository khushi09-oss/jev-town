# Tiny Town

A cozy pixel town of 30 autonomous human residents. Watch them eat, work, sleep, socialize and wander; select a neighbor, inspect their needs, follow them, or open the population and day summary.

Python chooses actions, applies effects and assigns destinations. The TypeScript/Vite/Phaser viewer only replays a recording. Playback, seek, speed, loop, restart and screenshots make zero Jev decisions. No backend is needed.

## See the town

Screenshots from the seeded, staged mock replay used for visual testing.

**Daytime — select a resident to see their portrait, personality, needs and day.**

![Tiny Town during the day with Bea selected and her resident inspector open](frontend/browser-tests/replay.spec.ts-snapshots/desktop-bea-win32.png)

**Nighttime — residents head home, with warm windows and street lamps.**

![Tiny Town at 23:00 with illuminated cottages and street lamps](frontend/browser-tests/replay.spec.ts-snapshots/desktop-night-win32.png)

**Mobile — pan around the town and inspect residents in the bottom sheet.**

<img src="frontend/browser-tests/replay.spec.ts-snapshots/mobile-bea-win32.png" alt="Tiny Town on mobile with Bea selected and playback controls visible" width="390">

## Try it (PowerShell)

The included `town.html` is a complete seeded **mock simulation**, with recording, engine, styles and artwork embedded. It opens without a server, key, CDN or sibling-file fetch:

```powershell
Start-Process .\town.html
```

`town.png` is its chart; `run.json` is its portable recording. Previous exports were backed up locally under `.artifacts/legacy-exports` during the upgrade.

## Develop or generate a recording

Validated with Node 24.11.1 and Python 3.14. Reuse the existing virtual environment if installed. From the root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install requests python-dotenv matplotlib
npm --prefix frontend ci
npm --prefix frontend run build
python town.py --mock --no-show --seed 7
Start-Process .\town.html
```

`--mock` bypasses both Jev and `.env` loading. `--no-show` saves the chart without a blocking window. `--output-dir .\my-run` writes the three exports elsewhere. If `frontend/dist` is absent, Python explicitly reports that it is using the retained legacy five-zone self-contained exporter, `export_html(frames, history, path)`.

```powershell
Set-Location .\frontend
npm run dev
```

Open the local URL printed by Vite. Development starts with an explicitly labeled **Mock · sample** recording staged for art review, rather than claiming those actions came from Jev or the mock policy. `?stage=six` opens the six-resident neighborhood. Use **Load recording** to open Python's `run.json`. Invalid imports leave the current replay available.

## Jev configuration

The existing `python town.py` entrypoint, TypeSafe endpoint, request shape and four-worker default remain. With no key, it still uses mock decisions. Normal CLI runs retain local `.env` loading; keep that file private. Never put credentials in browser code, recordings, source, screenshots or chat. Example settings, with a placeholder key:

```text
JEV_KEY=<your TypeSafe key>
JEV_URL=https://api.typesafe.ai/v1/systemone
JEV_MODEL=jev-latest
JEV_WORKERS=4
JEV_MIN_CONF=0.2
JEV_EFFECTS_PRESET=lively
JEV_ERROR_FALLBACK=stop
JEV_SOCIAL_MOOD=85
JEV_LAZY_REST=60
JEV_LAZY_WORK_MONEY=15
```

```powershell
Remove-Item Env:JEV_MOCK -ErrorAction SilentlyContinue
python town.py --no-show
```

A full real run makes about **720 decisions**, plus retries. `JEV_MOCK=1` forces offline mode before module import. HTTP 429/503/529 retries are limited to six attempts, requests time out after 60 seconds, and numeric `Retry-After` waits are honored up to a 60-second cap. Diagnostic body messages redact the configured key and authorization value. Invalid choices/confidence are errors.

Low confidence applies `wander` and sets `fellBack`. HTTP/schema failures stop by default, preserving previous complete exports. Explicit `JEV_ERROR_FALLBACK=mock` recovery records `decisionSource=error-mock`, `errorCode`, and null API choice/confidence; it is separate from confidence fallback and the run is labeled mixed. Hourly decisions mutate private NPC copies; the hour commits only when every result succeeds.

## People and effects

Stable IDs remain `npc00`–`npc29`. The supplied design explicitly maps the first six to Bea/social/teal curls, Milo/workaholic/rust, Ada/lazy/silver bun, Finn/social/blue cap, Noor/workaholic/plum bob, and Otto/lazy/ginger overalls. This replaces the previous ID-to-trait order. All 30 looks, names and homes are authored in `simulation/identities.py`; each cottage houses five residents with individual bed slots.

| Trait | Default preference |
|---|---|
| Lazy | Rest below 60 energy; work below 15 money with energy above 40 |
| Social | Seek company below 85 mood with energy above 30 |
| Workaholic | Work with energy above 40 even with enough money |

Hunger above 60 takes priority, followed by energy below 30 or sleep between 22:00 and 05:00. Configurable thresholds also appear in Jev's criteria. The earlier six-call real Jev comparison chose sleep/socialize/work for these matched-stat traits; no billed experiment was made for this visual upgrade.

`lively` retains the already-implemented rebalancing; `legacy` restores the original effects. All traits share consequences:

| Action | Hunger | Energy | Mood | Money |
|---|---:|---:|---:|---:|
| Eat | -40 | +5 | +3 | -5 |
| Work | +10 | -15 | -6 | +20 |
| Sleep | +6 | +25 | 0 | 0 |
| Socialize | +8 | -6 | +22 | -4 |
| Wander | +6 | -4 | -4 | 0 |

Needs stay within 0–100 and money stays at least zero. No debt or new eligibility restriction is introduced.

## Recording and playback

`schemaVersion=1` records run ID, seed, mode, world ID, 24 hours, start hour, immutable identities, initial snapshot and 24 ordered frames: **25 boundaries**. Each frame contains BEFORE stats, chosen/applied action, confidence, separate fallback/error metadata, AFTER stats and a Python destination. Interval `[h,h+1)` shows before stats; after stats commit at h+1. At t=24 the final stats and completed-day state are shown. Loop reuses the same day.

The browser validates sequences, identity sets, finite bounded stats/confidence, continuity and walkable destinations. Deterministic four-direction shortest routes start at the initial position or preceding destination. Seek reconstructs directly from time/seed/ID. Stagger uses the first 15% of a 12-second hour at 1×. Travel starts at 48 world pixels/second and compresses up to 180 to arrive before the final 5%; routes beyond that cap are rejected. The viewer applies no effects.

`simulation/world-layout.json` preserves the supplied 64×40 layout and 16-pixel tiles. `world.py` authors connected roads, bridge-only crossing, fountain/crop obstacles and explicit indoor door corridors. Every action has 30 unique anchors: communal bakery seats, workshop/garden/market stations, small social groups, park waypoints, and five beds per cottage. Outdoor paths cannot cross building fronts/roofs; indoor routes enter through authored doors. Selecting a sleeper or their home reveals the beds.

Desktop has a 64-pixel header, 88-pixel playback area and 320-pixel inspector. Mobile has a 56-pixel header, 128-pixel toolbar to preserve 40-pixel controls, native 1× pan and a sheet capped at 45% height. Full-map fit uses integer zoom whenever possible; narrow desktop windows use nearest-neighbor fractional fit. Camera offsets are rounded. Zoom options are 1×/2×/3×.

Space toggles playback outside form controls; Escape closes overlays; arrows pan the focused map and cancel follow. Population rows provide equivalent keyboard selection and sorting. Reduced motion disables camera easing and cosmetic idle bobbing. Captions report observed actions/locations, never invented dialogue or Jev explanations. Sound and live transport are out of scope.

## Art and locked screenshots

The scene uses separate assets, never the concept board as a background. `art/source/scenery-atlas.png` retains the original generated scenery family. `scripts/build_art.py` authors native resident/portrait art and slices scenery into independent objects and cottage roof/front layers. Each person has **74 native 24×32 cells**: four-direction walking, idle, eat, work and social gestures, plus two sleep poses. All 30 portraits are 64×64 and use the same hair, skin and outfits as their sprites. Dimensions, pivots, animation rates, anchors and provenance are in `frontend/src/assets/manifest.json` and `LICENSES.json`. No commercial game assets were extracted.

The handoff is mirrored locally in `docs/tiny-town`. Its Markdown and root `AGENTS.md` stay ignored; only this root README is intended for GitHub. The original art board remains a reference image, and its numerical constraints are retained in tracked JSON files.

Fixed **1440×900** and **390×844** screenshots cover 14:00, selected Bea, 23:00, population and summary. Baselines live in `frontend/browser-tests/replay.spec.ts-snapshots`, with hashes in `docs/tiny-town/baseline.json`. They lock the agent-inspected implementation, not a claim of user-approved visual parity. Comparisons use pinned Windows/Chromium tooling.

Remaining visual differences: human sprites/portraits are simpler than the concept faces; ground, garden and bridge are more visibly gridded; landscaping is less dense/organic; the specified 0.35 night overlay is gentler than the board. Native 1× fit leaves sage margins on large desktop screens. These are explicit differences, not hidden placeholder substitutions.

## Tests (PowerShell, from root)

To regenerate the navigation grid, original human rigs, and staged visual fixtures after editing their Python sources, install Pillow in the virtual environment and run:

```powershell
python -m pip install Pillow
python scripts/build_world.py
python scripts/build_art.py
python scripts/make_visual_fixture.py
```

The scenery source atlas stays in `art/source`; these commands do not regenerate it or call an image service.

```powershell
python -m unittest -v
npm --prefix frontend test
npm --prefix frontend run build
Set-Location .\frontend
npx playwright install chromium
Set-Location ..
python town.py --mock --no-show --output-dir .\.artifacts\export
npm --prefix frontend run test:browser
npm --prefix frontend run test:visual
```

Coverage includes clamping, fallback/error distinctions, payloads/redaction/invalid responses/retries, recording continuity and atomic failure, all-action capacity, bridge/path obstacles, pause/seek/end/loop/speed, keyboard/follow/pan, mobile/reduced motion, hostile names, invalid imports, offline HTML and fixed screenshots. No real Jev calls are made. The original project has no Python lint/type-check configuration; the frontend build runs strict TypeScript checking.

Vite reports the expected large-bundle warning: Phaser plus inline assets make a roughly 2.4 MB script needed for the self-contained export. No warning threshold or test was disabled. Update screenshots only after intentional visual review:

```powershell
npm --prefix frontend run test:visual -- --update-snapshots
```

Technical references: [Phaser 3.90 configuration](https://docs.phaser.io/api-documentation/3.90.0/typedef/types-core), [cameras](https://docs.phaser.io/phaser/concepts/cameras), [Vite](https://vite.dev/guide/), [Playwright visual comparisons](https://playwright.dev/docs/test-snapshots). Installed Phaser source was inspected for manual resize behavior.
