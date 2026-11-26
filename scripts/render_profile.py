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
W,H=1000,674
COLS,ROWS=47,34
MONO="ui-monospace, SFMono-Regular, Consolas, Liberation Mono, 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans CJK KR', monospace"
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
    # Neofetch-inspired dotted leaders and restrained syntax colors.
    key_color="#c6a085" if mode=="dark" else "#91502f"
    value_color="#e0e2e4" if mode=="dark" else "#233d5c"
    leader_color="#454b53" if mode=="dark" else "#b9c5d1"
    def row(y,label,value):
        fs=15
        advance=fs*0.62
        start=442+len(label)*advance+12
        end=966-len(value)*advance-12
        assert end-start>=12,(label,value)
        dots=f'<path d="M{start:.1f} {y-4}H{end:.1f}" stroke="{leader_color}" stroke-width="1.6" stroke-dasharray="2 6" stroke-linecap="round"/>'
        return t(442,y,label,key_color,fs)+dots+t(966,y,value,value_color,fs,"end")
    def section(y,label,xend=966):
        x=442+len(label)*8.7+16
        return t(442,y,label,c["accent"],14,weight="600")+line(round(x),y-4,xend)
    def project(y,name,description,detail):
        return (f'<text x="442" y="{y}" font-size="15">'
                f'<tspan fill="{key_color}" font-weight="600">{escape(name)}</tspan>'
                + (f'<tspan fill="{value_color}"> | {escape(description)}</tspan>' if description else "") + '</text>'
                +t(454,y+18,"- "+detail,c["muted"],13))
    art=[]
    # Render the full scene with tonal glyphs. Low-density areas fade into the
    # panel, making the silhouettes easier to distinguish in both themes.
    scene_ramp=" .,:;irsXA253hMHGS#9B&@"
    tones=("#33383e","#515a61","#737d85","#98a0a8","#c1c7cd") if mode=="dark" else ("#dce0e3","#a7afb7","#737d87","#4d5760","#252d36")
    for y,l in enumerate(grid):
        runs=[]
        last=None
        for x,v in enumerate(l):
            alpha=mask[y][x]/255
            strength=v/255 if mode=="dark" else 1-v/255
            strength=(alpha*strength)**1.2
            ch=scene_ramp[round(strength*(len(scene_ramp)-1))]
            tone=tones[min(4,int(strength*5))]
            if last==tone:
                runs[-1][1]+=ch
            else:
                runs.append([tone,ch]);last=tone
        spans="".join(f'<tspan fill="{color}">{escape(chars)}</tspan>' for color,chars in runs)
        art.append(f'<text x="28" y="{127+y*12.0}" font-size="13.4" xml:space="preserve">{spans}</text>')
    pieces=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
        '<title id="title">rusoacn - terminal profile</title>',
        '<desc id="desc">ASCII account avatar beside education, completed team projects, competition results, independent work, ADsP certification, a dated contribution snapshot and a reported single-video view count.</desc>',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="{c["bg"]}" stroke="{c["border"]}"/>',
        f'<g font-family="{MONO}">',
        t(28,34,"PROFILE / 005",c["muted"],12),
        t(442,34,"rusoacn@localhost",c["accent"],18,weight="600"),
        *art,
        section(62,"- SYSTEM"),
        row(85,"Education","Hannam University"),
        row(104,"Major","Big Data Convergence"),
        row(123,"OS / IDE","Windows / VS Code"),
        row(142,"AI Agents","Codex / Claude Code"),
        row(161,"Languages","Python / R / SQL"),
        section(190,"- COMPLETED PROJECTS"),
        project(213,"G-순환","Policy Decision Support (MVP)","Finalist / In-person PT - Gyeongnam Big Data 2026 (T2)"),
        project(255,"경남 농산물 부산물 공급·활용 시뮬레이터","","Gyeongnam Big Data Competition 2026 / Track 1 entry"),
        project(297,"K League","Ranking Forecasting","2026 Big Data Day / Team project"),
        project(339,"파손 택배 탐지","YOLO / Raspberry Pi","2024 Summer Software Project / Team project"),
        section(383,"- AWARDS / RESULTS"),
        row(405,"Software Project '24","3rd place"),
        row(425,"Big Data Day '26","2nd place"),
        section(453,"- INDEPENDENT WORK"),
        row(475,"CCC-lib","AI Continuity System (WIP)"),
        row(495,"Smart Factory","Predictive Maintenance MVP"),
        row(515,"AI Creative","Generative AI Video (~40K views on IG)*"),
        section(543,"- RECORD"),
        row(565,"Certification","ADsP"),
        row(585,"Contributions (1y)","5,503 (2026-11-26)"),
        t(442,611,"* Single video; Aug 2026 record (self-reported).",c["muted"],12),
        line(28,632,972),
        t(28,657,"rusoacn:~$ ",c["accent"],15),
        f'<rect x="124" y="644" width="8" height="15" fill="{c["accent"]}"/>',
        t(966,657,"DATA / AI / SYSTEMS",c["muted"],12,"end"),
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
