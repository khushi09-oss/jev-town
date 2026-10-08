"""Tiny town: every NPC asks Jev what to do next, every tick.

Run with no key to use a rule-based stand-in:   python town.py
Run against Jev:  JEV_KEY=... python town.py
Provider is swappable via JEV_URL / JEV_AUTH (check your provider's docs for
the exact URL and auth header).
"""
import os
import math
import sys
import random
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

MOCK_REQUESTED = os.getenv('JEV_MOCK') == '1' or '--mock' in sys.argv
if not MOCK_REQUESTED:
    load_dotenv()  # legacy local configuration; explicit mock runs never open .env

URL = os.getenv("JEV_URL", "https://api.typesafe.ai/v1/systemone")
KEY = None if MOCK_REQUESTED else os.getenv("JEV_KEY")
AUTH = os.getenv("JEV_AUTH", f"Bearer {KEY}")  # Inworld uses "Basic <creds>"
MODEL = os.getenv("JEV_MODEL", "jev-latest")
MIN_CONFIDENCE = float(os.getenv("JEV_MIN_CONF", "0.2"))  # below this, wander instead
TRAITS = ("lazy", "social", "workaholic")
SOCIAL_MOOD = float(os.getenv('JEV_SOCIAL_MOOD', '85'))
LAZY_REST = float(os.getenv('JEV_LAZY_REST', '60'))
LAZY_WORK_MONEY = float(os.getenv('JEV_LAZY_WORK_MONEY', '15'))
for threshold in (SOCIAL_MOOD, LAZY_REST, LAZY_WORK_MONEY, MIN_CONFIDENCE):
    if not math.isfinite(threshold):
        raise ValueError('Decision thresholds must be finite')
if not (0 <= SOCIAL_MOOD <= 100 and 0 <= LAZY_REST <= 100 and
        LAZY_WORK_MONEY >= 0 and 0 <= MIN_CONFIDENCE <= 1):
    raise ValueError('Decision threshold out of range')
ERROR_FALLBACK = os.getenv('JEV_ERROR_FALLBACK', 'stop')
if ERROR_FALLBACK not in ('stop', 'mock'):
    raise ValueError('JEV_ERROR_FALLBACK must be stop or mock')

# The choice set Jev picks from. Descriptions are what Jev actually reads.
ACTIONS = {
    "eat": "Go eat. Choose this when hunger is above 60.",
    "work": f"Go to work and earn money. Choose this when money is below 30 and energy is above 40. Workaholics prefer work whenever energy is above 40, even with enough money. Lazy people work only when money is below {LAZY_WORK_MONEY:g}.",
    "sleep": f"Sleep. Choose this when energy is below 30, or when the hour is at least 22 or below 6. Lazy people also rest when energy is below {LAZY_REST:g}.",
    "socialize": f"Hang out with others. Choose this when mood is below 50 and energy is above 30. Social people seek company whenever mood is below {SOCIAL_MOOD:g} and energy is above 30.",
    "wander": "Stroll around. Choose this ONLY when nothing else is needed: hunger, energy, mood and money are all fine.",
}

# (hunger, energy, mood, money) change per action
EFFECTS = {
    "eat": (-40, 5, 3, -5),
    "work": (10, -15, -6, 20),
    "sleep": (6, 25, 0, 0),
    "socialize": (8, -6, 22, -4),
    "wander": (6, -4, -4, 0),
}
EFFECTS_PRESETS = {'lively': EFFECTS, 'legacy': {
    'eat': (-40, 5, 5, -5), 'work': (10, -15, -5, 20),
    'sleep': (5, 35, 2, 0), 'socialize': (8, -5, 20, -3), 'wander': (5, -2, 3, 0)}}
EFFECTS_PRESET = os.getenv('JEV_EFFECTS_PRESET', 'lively')
if EFFECTS_PRESET not in EFFECTS_PRESETS:
    raise ValueError('JEV_EFFECTS_PRESET must be lively or legacy')
EFFECTS = EFFECTS_PRESETS[EFFECTS_PRESET]


class DecisionError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def safe_message(text):
    for secret in (AUTH, KEY):
        if secret:
            text = text.replace(secret, '[redacted]')
    return text[:512]


@dataclass
class NPC:
    name: str
    hunger: int = 30
    energy: int = 70
    mood: int = 60
    money: int = 20
    last: str = "-"
    fell_back: bool = False
    trait: str = "lazy"
    chosen_action: str | None = None
    confidence: float | None = None
    decision_source: str = 'mock'
    error_code: str | None = None


def clamp(x):
    return max(0, min(100, x))


def mock_decide(npc, hour):
    """Rule-based stand-in so the sim runs without an API key."""
    if npc.hunger > 60:
        return "eat", 0.9
    if npc.energy < 30 or hour >= 22 or hour < 6:
        return "sleep", 0.9
    if npc.trait == "lazy" and npc.energy < LAZY_REST:
        return "sleep", 0.8
    if npc.mood < (SOCIAL_MOOD if npc.trait == "social" else 50) and npc.energy > 30:
        return "socialize", 0.8
    if npc.energy > 40 and (npc.trait == "workaholic" or
                           npc.money < (LAZY_WORK_MONEY if npc.trait == "lazy" else 30)):
        return "work", 0.7
    return "wander", 0.6


def jev_decide(npc, hour):
    body = {
        "model": MODEL,
        "state": {
            "name": npc.name,
            "hour_of_day": hour,
            "hunger_0_to_100": npc.hunger,
            "energy_0_to_100": npc.energy,
            "mood_0_to_100": npc.mood,
            "money": npc.money,
            "did_last_tick": npc.last,
            "personality": npc.trait,
        },
        "questions": {
            "next_action": {
                "type": "choice",
                "instructions": "What should this person do next? Prioritize hunger above 60, then energy below 30 or nighttime sleep, before personality preferences.",
                "criteria": ACTIONS,
            }
        },
    }
    for attempt in range(6):
        try:
            r = requests.post(
                URL, json=body, timeout=60,
                headers={"Authorization": AUTH, "Content-Type": "application/json"},
            )
        except requests.RequestException as error:
            raise DecisionError('network_error', 'Jev request failed; the last valid recording is unchanged.') from None
        if r.status_code in (429, 503, 529):  # rate limited / overloaded: back off
            try:
                wait = float(r.headers.get("Retry-After", ""))
            except ValueError:
                wait = 2 ** attempt
            if not math.isfinite(wait) or wait < 0:
                wait = 2 ** attempt
            if attempt < 5:
                time.sleep(min(wait, 60))
            continue
        if not r.ok:
            raise DecisionError(f'http_{r.status_code}', f"{r.status_code} from Jev: {safe_message(r.text)}")
        try:
            ans = r.json()["answers"]["next_action"]
            action, confidence = ans['choice'], ans['confidence']
            if (action not in ACTIONS or isinstance(confidence, bool) or
                not isinstance(confidence, (int, float)) or not math.isfinite(confidence)
                or not 0 <= confidence <= 1):
                raise ValueError('Invalid action or confidence')
        except (ValueError, KeyError, TypeError):
            raise DecisionError('invalid_response', 'Jev returned an invalid choice or confidence.') from None
        return action, confidence
    raise DecisionError('retries_exhausted', 'Jev is still rate limited or unavailable after six attempts.')


def step(npc, hour):
    npc.error_code = None
    npc.decision_source = 'jev' if KEY else 'mock'
    try:
        action, conf = (jev_decide if KEY else mock_decide)(npc, hour)
        npc.chosen_action, npc.confidence = action, conf
    except DecisionError as error:
        if ERROR_FALLBACK != 'mock':
            raise
        action, conf = mock_decide(npc, hour)
        npc.decision_source, npc.error_code = 'error-mock', error.code
        npc.chosen_action, npc.confidence = None, None
    npc.fell_back = npc.decision_source != 'error-mock' and conf < MIN_CONFIDENCE
    if npc.fell_back:
        action = "wander"
    dh, de, dm, dmoney = EFFECTS[action]
    npc.hunger = clamp(npc.hunger + dh)
    npc.energy = clamp(npc.energy + de)
    npc.mood = clamp(npc.mood + dm)
    npc.money = max(0, npc.money + dmoney)
    npc.last = action
    return conf


HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Tiny Town</title>
<style>
body{margin:0;background:#0d1117;color:#e6edf3;font-family:system-ui,sans-serif;
display:flex;flex-direction:column;align-items:center}
h1{font-size:20px;margin:14px 0 2px}
.sub{color:#8b949e;font-size:13px;margin-bottom:8px}
canvas{width:960px;max-width:96vw;height:auto;background:#161b22;border-radius:12px}
.bar{display:flex;gap:14px;align-items:center;margin:10px;font-size:13px;
flex-wrap:wrap;justify-content:center}
.chip{display:flex;align-items:center;gap:6px}
.dot{width:10px;height:10px;border-radius:50%}
button{background:#238636;color:#fff;border:0;border-radius:6px;padding:6px 14px;cursor:pointer}
</style></head><body>
<h1>Tiny Town</h1>
<div class="sub">30 people. Every hour, Jev decides what each one does next.</div>
<canvas id="c" width="1920" height="1080"></canvas>
<div class="bar" id="legend"></div>
<div class="bar"><button id="pb">Pause</button><button id="rs">Restart</button>
<label>Speed <input id="sp" type="range" min="0.5" max="6" step="0.5" value="1.5"></label>
<span id="stats"></span></div>
<script>
const D=__DATA__;
const COL={eat:"#1f77b4",work:"#ff7f0e",sleep:"#2ca02c",socialize:"#d62728",wander:"#9467bd"};
const ZONES={sleep:[30,70,290,190,"Home"],eat:[335,70,290,190,"Diner"],
work:[640,70,290,190,"Office"],socialize:[30,290,290,200,"Plaza"],
wander:[335,290,595,200,"Streets"]};
const c=document.getElementById("c"),g=c.getContext("2d");g.scale(2,2);
const N=D.frames[0].length;
let tick=0,playing=true,last=0,interval=1000/1.5,pts=[];
function r(a){const s=Math.sin(a)*43758.5453;return s-Math.floor(s)}
function target(i,act){const z=ZONES[act];
return[z[0]+16+r(i*12.9+z[0])*(z[2]-32),z[1]+34+r(i*78.2+z[1])*(z[3]-52)]}
for(let i=0;i<N;i++){const t=target(i,D.frames[0][i]);pts.push({x:t[0],y:t[1]})}
const legend=document.getElementById("legend");
Object.keys(COL).forEach(k=>{legend.insertAdjacentHTML("beforeend",
'<span class="chip"><span class="dot" style="background:'+COL[k]+'"></span>'+k+
' <b id="n_'+k+'">0</b></span>')});
function night(h){return h>=22||h<5?0.4:(h<7||h>=20?0.18:0)}
function draw(t){
const H=D.history[tick];
g.clearRect(0,0,960,540);
for(const k in ZONES){const z=ZONES[k];g.beginPath();g.roundRect(z[0],z[1],z[2],z[3],14);
g.fillStyle="rgba(255,255,255,0.04)";g.fill();g.strokeStyle=COL[k]+"88";g.lineWidth=1.5;g.stroke();
g.fillStyle="#8b949e";g.font="14px system-ui";g.fillText(z[4],z[0]+14,z[1]+22)}
g.fillStyle="rgba(5,10,40,"+night(H.hour)+")";g.fillRect(0,0,960,540);
g.fillStyle="#e6edf3";g.font="bold 22px system-ui";g.textAlign="center";
g.fillText(String(H.hour).padStart(2,"0")+":00",480,38);g.textAlign="left";
for(let i=0;i<N;i++){const act=D.frames[tick][i],tg=target(i,act),p=pts[i];
p.x+=(tg[0]-p.x)*0.07;p.y+=(tg[1]-p.y)*0.07;
const wx=Math.sin(t*0.002+i)*1.5,wy=Math.cos(t*0.0025+i*2)*1.5;
g.beginPath();g.arc(p.x+wx,p.y+wy,6,0,7);g.fillStyle=COL[act];
g.shadowColor=COL[act];g.shadowBlur=10;g.fill();g.shadowBlur=0}
for(const k in COL)document.getElementById("n_"+k).textContent=H.counts[k]||0;
document.getElementById("stats").textContent="avg hunger "+Math.round(H.hunger)+
" · energy "+Math.round(H.energy)+" · mood "+Math.round(H.mood)}
function loop(t){
if(playing&&t-last>interval){last=t;
if(tick<D.frames.length-1)tick++;else{playing=false;pb.textContent="Replay"}}
draw(t);requestAnimationFrame(loop)}
const pb=document.getElementById("pb");
pb.onclick=()=>{if(tick>=D.frames.length-1)tick=0;playing=!playing;
pb.textContent=playing?"Pause":"Play"};
document.getElementById("rs").onclick=()=>{tick=0;playing=true;pb.textContent="Pause"};
document.getElementById("sp").oninput=e=>{interval=1000/e.target.value};
requestAnimationFrame(loop);
</script></body></html>
"""


def export_html(frames, history, path="town.html"):
    """Write a self-contained animation page; open it in a browser."""
    import json

    data = json.dumps({"frames": frames, "history": history})
    with open(path, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE.replace("__DATA__", data))
    print(f"Saved {path} - open it in your browser to watch the town")


def plot(history, path='town.png', show=True):
    """Top: what the town is doing each hour. Bottom: average NPC stats."""
    import matplotlib.pyplot as plt  # pip install matplotlib

    x = list(range(len(history)))
    fig, (top, bottom, traits) = plt.subplots(3, 1, figsize=(11, 11))

    stack = [0] * len(history)
    for action in ACTIONS:
        vals = [h["counts"].get(action, 0) for h in history]
        top.bar(x, vals, bottom=stack, label=action)
        stack = [s + v for s, v in zip(stack, vals)]
    top.set_ylabel("NPCs")
    top.set_title("What the town is doing, hour by hour")
    top.legend(ncol=5, fontsize=8)

    for stat in ("hunger", "energy", "mood"):
        bottom.plot(x, [h[stat] for h in history], label=stat, marker="o", markersize=3)
    bottom.set_ylabel("average (0-100)")
    bottom.set_xlabel("hour of day")
    bottom.set_xticks(x)
    bottom.set_xticklabels([f"{h['hour']:02d}" for h in history])
    bottom.legend(fontsize=8)

    totals = {trait: {action: sum(h["trait_counts"][trait].get(action, 0)
                                for h in history) for action in ACTIONS}
              for trait in TRAITS}
    stack = [0.0] * len(TRAITS)
    for action in ACTIONS:
        shares = [100 * totals[trait][action] / max(1, sum(totals[trait].values()))
                  for trait in TRAITS]
        traits.bar(TRAITS, shares, bottom=stack, label=action)
        stack = [s + v for s, v in zip(stack, shares)]
    traits.set_ylabel("action share (%)")
    traits.set_ylim(0, 100)
    traits.set_title("How each personality spends the day")
    traits.legend(ncol=5, fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    if show:
        plt.show()
    else:
        plt.close(fig)


def main(n_npcs=30, ticks=24, *, seed=7, output_dir='.', show_chart=True):
    from dataclasses import replace
    from pathlib import Path
    from simulation.identities import manifest
    from simulation.recording import start_recording, append_frame, write_recording
    from simulation.exports import export_replay
    if not 1 <= ticks <= 24:
        raise ValueError('ticks must be between 1 and 24')
    identities = manifest(n_npcs)
    rng = random.Random(seed)
    town = [NPC(p['id'], hunger=rng.randint(10, 80), energy=rng.randint(30, 90),
                trait=p['trait']) for p in identities]
    recording = start_recording(town, identities, seed, 'jev' if KEY else 'mock')
    history = []
    frames = []  # what every NPC did each hour, for the animation
    for tick in range(ticks):
        hour = tick % 24
        # all NPCs decide in parallel; Jev's speed is the whole point
        with ThreadPoolExecutor(max_workers=int(os.getenv("JEV_WORKERS", "4"))) as pool:
            # Mutate private copies only. A failed decision cannot partially commit the hour.
            next_town = [replace(n) for n in town]
            confs = list(pool.map(lambda n: step(n, hour), next_town))
        append_frame(recording, town, next_town, tick)
        town = next_town
        counts = {}
        trait_counts = {trait: {} for trait in TRAITS}
        for n in town:
            counts[n.last] = counts.get(n.last, 0) + 1
            group = trait_counts[n.trait]
            group[n.last] = group.get(n.last, 0) + 1
        avg_conf = sum(confs) / len(confs)
        frames.append([n.last for n in town])
        fb = sum(n.fell_back for n in town)
        print(f"hour {hour:02d} | conf {avg_conf:.2f} | fallback {fb:2d} | {counts}")
        history.append({
            "hour": hour,
            "counts": counts,
            "trait_counts": trait_counts,
            "hunger": sum(n.hunger for n in town) / len(town),
            "energy": sum(n.energy for n in town) / len(town),
            "mood": sum(n.mood for n in town) / len(town),
        })
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if ticks == 24:
        write_recording(recording, output / 'run.json')
        if not export_replay(recording, output / 'town.html'):
            export_html(frames, history, str(output / 'town.html'))
    else:
        export_html(frames, history, str(output / 'town.html'))
    plot(history, path=str(output / 'town.png'), show=show_chart)
    return recording


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Tiny Town: Jev or mock recording and exports')
    parser.add_argument('--mock', action='store_true', help='Never use Jev or require a key')
    parser.add_argument('--no-show', action='store_true', help='Save chart without opening a window')
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--output-dir', default='.')
    args = parser.parse_args()
    if args.mock:
        KEY = None
    try:
        main(seed=args.seed, output_dir=args.output_dir, show_chart=not args.no_show)
    except (DecisionError, ValueError) as error:
        parser.exit(1, f'Town stopped: {safe_message(str(error))}\n')
