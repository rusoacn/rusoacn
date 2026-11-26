#!/usr/bin/env python3
"""Generate self-contained SVGs with public GitHub metadata and an ASCII avatar."""
import json
import os
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OWNER="rusoacn"
W,H=1000,540
COLS,ROWS=47,34
MONO="ui-monospace, SFMono-Regular, Consolas, Liberation Mono, monospace"
RAMP=" .,:;irsXA253hMHGS#9B&@"
PALETTES={
    "dark":{"bg":"#101215","border":"#292e35","text":"#d4d6d8","muted":"#818992","label":"#a6adb5","line":"#353a41","accent":"#f1eee8","pixel":"#b9c0c5"},
    "light":{"bg":"#f6f8fa","border":"#d9dee3","text":"#24292f","muted":"#65707b","label":"#59616b","line":"#d3d9df","accent":"#20252b","pixel":"#38414b"},
}
def api(path):
    headers={"Accept":"application/vnd.github+json","User-Agent":"rusoacn-profile","X-GitHub-Api-Version":"2022-11-28"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"]="Bearer "+os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request("https://api.github.com"+path,headers=headers),timeout=30) as f:
        return json.load(f)
def public_stats():
    u=api("/users/"+OWNER)
    if u.get("login")!=OWNER: raise ValueError("Unexpected GitHub user")
    public=[]
    for page in range(1,101):
        batch=api(f"/users/{OWNER}/repos?type=owner&per_page=100&page={page}")
        if not isinstance(batch,list):raise ValueError("Expected public repository list")
        public.extend(r for r in batch if r.get("private") is False and r.get("owner",{}).get("login")==OWNER)
        if len(batch)<100:break
    else:raise ValueError("Public repo pagination incomplete")
    if len(public)!=u["public_repos"]:raise ValueError("Public repository count changed during query")
    return {"public_repos":u["public_repos"],"followers":u["followers"],"following":u["following"],"stars_received":sum(r["stargazers_count"] for r in public)}
def render(mode,data,grid,mask):
    c=PALETTES[mode]
    def t(x,y,s,color=None,fs=15,anchor="start",weight=None,extra=""):
        return f'<text x="{x}" y="{y}" font-size="{fs}" fill="{color or c["text"]}" text-anchor="{anchor}"'+(f' font-weight="{weight}"' if weight else "")+f'{extra}>{escape(str(s))}</text>'
    def line(x1,y,x2):return f'<path d="M{x1} {y}H{x2}" stroke="{c["line"]}" stroke-width="1"/>'
    def row(y,label,value):
        return t(442,y,label,c["label"],15)+t(966,y,value,c["text"],15,"end")
    def section(y,label,xend=966):
        x=442+len(label)*9.1+20
        return t(442,y,label,c["accent"],14,weight="600")+line(round(x),y-4,xend)
    art=[]
    for y,l in enumerate(grid):
        chars=[]
        for x,v in enumerate(l):
            alpha=mask[y][x]/255
            strength=v/255 if mode=="dark" else 1-v/255
            strength=alpha*(0.13+0.87*strength)**.85
            chars.append(RAMP[round(strength*(len(RAMP)-1))])
        art.append(t(28,81+y*12.0,"".join(chars),c["pixel"],13.4,extra=' xml:space="preserve"'))
    pieces=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
        '<title id="title">rusoacn ? terminal profile</title>',
        '<desc id="desc">ASCII rendering of the account avatar beside system information and verified public GitHub statistics.</desc>',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="{c["bg"]}" stroke="{c["border"]}"/>',
        f'<g font-family="{MONO}">',
        t(28,34,"rusoacn@localhost",c["accent"],18,weight="600"),
        t(966,34,"PROFILE / 001",c["muted"],12,"end"),
        line(28,51,972),
        f'<path d="M416 67V485" stroke="{c["line"]}" stroke-width="1"/>',
        *art,
        section(85,"SYSTEM"),
        row(110,"OS","Windows"),
        row(134,"Editor","VS Code"),
        row(158,"Languages","Python / R / SQL"),
        row(182,"Field","Data Science / AI"),
        row(206,"Focus","Machine Learning"),
        row(230,"Build","Automation / Systems"),
        section(271,"GITHUB / PUBLIC"),
        row(296,"Repositories",f'{data["public_repos"]:,}'),
        row(320,"Stars received",f'{data["stars_received"]:,}'),
        row(344,"Followers",f'{data["followers"]:,}'),
        row(368,"Following",f'{data["following"]:,}'),
        section(409,"STATUS"),
        t(442,435,"Building systems.",c["text"],16),
        t(442,459,"Exploring data, code and form.",c["muted"],14),
        line(28,493,972),
        t(28,518,"rusoacn:~$ ",c["accent"],15),
        f'<rect x="124" y="505" width="8" height="15" fill="{c["accent"]}"/>',
        t(966,518,"PUBLIC PROFILE  /  DATA + SYSTEMS",c["muted"],12,"end"),
        '</g></svg>'
    ]
    result="\n".join(pieces)+"\n"
    ET.fromstring(result)
    return result
def main():
    portrait=json.loads((ROOT/"assets/avatar-grid.json").read_text(encoding="utf-8"))
    grid=portrait["luma"]
    mask=portrait["mask"]
    assert len(mask)==ROWS and all(len(r)==COLS and all(type(v) is int and 0<=v<=255 for v in r) for r in mask)
    assert len(grid)==ROWS and all(len(r)==COLS and all(type(v) is int and 0<=v<=255 for v in r) for r in grid)
    if "--initial" in sys.argv:
        data=json.loads((ROOT/"assets/public-stats.json").read_text(encoding="utf-8"))
    else:
        data=public_stats()
    assert set(data)=={"public_repos","followers","following","stars_received"}
    assert all(type(v) is int and v>=0 for v in data.values())
    for mode in PALETTES:
        (ROOT/f"assets/profile-{mode}.svg").write_text(render(mode,data,grid,mask),encoding="utf-8",newline="\n")
    (ROOT/"assets/public-stats.json").write_text(json.dumps(data,sort_keys=True,indent=2)+"\n",encoding="utf-8",newline="\n")
    print("PROFILE_RENDER_OK",data)
if __name__=="__main__":main()
