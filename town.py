"""Tiny town: every NPC asks Jev what to do next, every tick.

Run with no key to use a rule-based stand-in:   python town.py
Run against Jev:  JEV_KEY=... python town.py
Provider is swappable via JEV_URL / JEV_AUTH (check your provider's docs for
the exact URL and auth header).
"""
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv()  # reads a .env file in this folder, if there is one

URL = os.getenv("JEV_URL", "https://api.typesafe.ai/v1/systemone")
KEY = os.getenv("JEV_KEY")
AUTH = os.getenv("JEV_AUTH", f"Bearer {KEY}")  # Inworld uses "Basic <creds>"
MODEL = os.getenv("JEV_MODEL", "jev-latest")
MIN_CONFIDENCE = float(os.getenv("JEV_MIN_CONF", "0.2"))  # below this, wander instead

# The choice set Jev picks from. Descriptions are what Jev actually reads.
ACTIONS = {
    "eat": "Go eat. Choose this when hunger is above 60.",
    "work": "Go to work and earn money. Choose this when money is below 30 and energy is above 40.",
    "sleep": "Sleep. Choose this when energy is below 30, or when the hour is between 22 and 6.",
    "socialize": "Hang out with others. Choose this when mood is below 50 and energy is above 30.",
    "wander": "Stroll around. Choose this ONLY when nothing else is needed: hunger, energy, mood and money are all fine.",
}

# (hunger, energy, mood, money) change per action
EFFECTS = {
    "eat": (-40, 5, 5, -5),
    "work": (10, -15, -5, 20),
    "sleep": (5, 35, 2, 0),
    "socialize": (8, -5, 20, -3),
    "wander": (5, -2, 3, 0),
}


@dataclass
class NPC:
    name: str
    hunger: int = 30
    energy: int = 70
    mood: int = 60
    money: int = 20
    last: str = "-"
    fell_back: bool = False


def clamp(x):
    return max(0, min(100, x))


def mock_decide(npc, hour):
    """Rule-based stand-in so the sim runs without an API key."""
    if npc.hunger > 70:
        return "eat", 0.9
    if npc.energy < 25 or hour >= 23 or hour < 6:
        return "sleep", 0.9
    if npc.mood < 35:
        return "socialize", 0.8
    if npc.money < 15:
        return "work", 0.7
    return random.choice(["work", "socialize", "wander"]), 0.6


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
        },
        "questions": {
            "next_action": {
                "type": "choice",
                "instructions": "What should this person do next?",
                "criteria": ACTIONS,
            }
        },
    }
    for attempt in range(6):
        r = requests.post(
            URL, json=body, timeout=60,
            headers={"Authorization": AUTH, "Content-Type": "application/json"},
        )
        if r.status_code in (429, 503, 529):  # rate limited / overloaded: back off
            try:
                wait = float(r.headers.get("Retry-After", ""))
            except ValueError:
                wait = 2 ** attempt
            time.sleep(wait)
            continue
        if not r.ok:
            raise RuntimeError(f"{r.status_code} from {URL}: {r.text}")
        ans = r.json()["answers"]["next_action"]
        return ans["choice"], ans["confidence"]
    r.raise_for_status()  # still limited after all retries: raise the error


def step(npc, hour):
    action, conf = (jev_decide if KEY else mock_decide)(npc, hour)
    npc.fell_back = conf < MIN_CONFIDENCE
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


def plot(history):
    """Top: what the town is doing each hour. Bottom: average NPC stats."""
    import matplotlib.pyplot as plt  # pip install matplotlib

    x = list(range(len(history)))
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

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

    fig.tight_layout()
    fig.savefig("town.png", dpi=150)
    plt.show()


def main(n_npcs=30, ticks=24):
    names = [f"npc{i:02d}" for i in range(n_npcs)]
    town = [NPC(n, hunger=random.randint(10, 80), energy=random.randint(30, 90)) for n in names]
    history = []
    frames = []  # what every NPC did each hour, for the animation
    for tick in range(ticks):
        hour = tick % 24
        # all NPCs decide in parallel; Jev's speed is the whole point
        with ThreadPoolExecutor(max_workers=int(os.getenv("JEV_WORKERS", "4"))) as pool:
            confs = list(pool.map(lambda n: step(n, hour), town))
        counts = {}
        for n in town:
            counts[n.last] = counts.get(n.last, 0) + 1
        avg_conf = sum(confs) / len(confs)
        frames.append([n.last for n in town])
        fb = sum(n.fell_back for n in town)
        print(f"hour {hour:02d} | conf {avg_conf:.2f} | fallback {fb:2d} | {counts}")
        history.append({
            "hour": hour,
            "counts": counts,
            "hunger": sum(n.hunger for n in town) / len(town),
            "energy": sum(n.energy for n in town) / len(town),
            "mood": sum(n.mood for n in town) / len(town),
        })
    export_html(frames, history)
    plot(history)


if __name__ == "__main__":
    main()