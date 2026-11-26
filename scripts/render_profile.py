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
W,H=1000,585
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
    left,right=398,984
    key_x=left+16
    key_color="#ffa657" if mode=="dark" else "#953800"
    value_color="#a5d6ff" if mode=="dark" else "#0a3069"
    leader_color="#616e7f" if mode=="dark" else "#c2cfde"
    base_color="#c9d1d9" if mode=="dark" else "#24292f"
    detail_color="#9da9b8" if mode=="dark" else "#596675"
    def leader(y,start,end):
        assert end-start>=8,(start,end)
        return f'<path d="M{start:.1f} {y-4}H{end:.1f}" stroke="{leader_color}" stroke-width="1.8" stroke-dasharray="2 7" stroke-linecap="round"/>'
    def row(y,label,value):
        fs=15.5
        advance=fs*0.62
        label=label+":"
        start=key_x+len(label)*advance+8
        end=right-len(value)*advance-8
        return (t(left,y,".",leader_color,fs)+t(key_x,y,label,key_color,fs)
                +leader(y,start,end)+t(right,y,value,value_color,fs,"end"))
    def stat_pair(y,a,b):
        fs=14.5
        advance=fs*0.62
        middle=699
        def half(x0,x1,label,value):
            label=label+":"
            start=x0+len(label)*advance+6
            end=x1-len(value)*advance-6
            return t(x0,y,label,key_color,fs)+leader(y,start,end)+t(x1,y,value,value_color,fs,"end")
        return (t(left,y,".",leader_color,fs)+half(key_x,middle-13,*a)
                +t(middle,y,"|",detail_color,fs)+half(middle+16,right,*b))
    def section(y,label,xend=right):
        fs=15
        x=left+len(label)*fs*.62+12
        return t(left,y,label,base_color,fs)+f'<path d="M{x:.1f} {y-4}H{xend}" stroke="{base_color}" stroke-width=".8"/>'
    def project(y,name,description,detail):
        return (t(left,y,".",leader_color,15.5)
                +f'<text x="{key_x}" y="{y}" font-size="15.5">'
                f'<tspan fill="{key_color}">{escape(name)}</tspan>'
                + (f'<tspan fill="{value_color}"> | {escape(description)}</tspan>' if description else "") + '</text>'
                +t(key_x+12,y+16,"- "+detail,detail_color,13))
    art=[]
    # Render the full scene with tonal glyphs. Low-density areas fade into the
    # panel, making the silhouettes easier to distinguish in both themes.
    scene_ramp=" .,:;irsXA253hMHGS#9B&@"
    tones=("#59636f","#74808c","#8f9aa6","#aab4bf","#c9d1d9") if mode=="dark" else ("#a9b5c0","#81909d","#5f6d7a","#414d59","#24292f")
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
        art.append(f'<text x="15" y="{27+y*15.2}" font-size="15.2" textLength="365" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{spans}</text>')
    pieces=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
        '<title id="title">rusoacn - terminal profile</title>',
        '<desc id="desc">ASCII account avatar beside education, completed projects, competition results, independent work, ADsP certification, dated GitHub and AI usage statistics and a reported video view count.</desc>',
        f'<rect width="{W}" height="{H}" rx="15" fill="#161b22"/>' if mode=="dark" else f'<rect width="{W}" height="{H}" rx="15" fill="#f6f8fa"/>',
        f'<g font-family="{MONO}">',
        *art,
        section(27,"rusoacn"),
        row(47,"Education","Hannam University"),
        row(66,"Major","Dept. of AI and Data Science"),
        row(85,"OS / IDE","Windows / VS Code"),
        row(104,"AI Agents","Codex / Claude Code"),
        row(123,"Languages","Python / R / SQL"),
        section(150,"- Completed Projects"),
        project(170,"G-순환","Policy Decision Support (Idea Proposal)","Finalist / In-person PT - Gyeongnam Big Data 2026 (T2)"),
        project(207,"경남 농산물 부산물 공급·활용 시뮬레이터","MVP","Gyeongnam Big Data Competition 2026"),
        project(244,"K League","Ranking Forecasting","2026 Big Data Day"),
        project(281,"파손 택배 탐지","YOLO / Raspberry Pi","2024 Summer Software Project"),
        section(321,"- Awards / Results"),
        row(340,"Software Project '24","3rd place"),
        row(359,"Big Data Day '26","2nd place"),
        section(386,"- Independent Work"),
        row(405,"CCC-lib","AI Continuity System (WIP)"),
        row(424,"Smart Factory","Predictive Maintenance MVP"),
        row(443,"AI Creative","Generative AI Video (~40K views on IG)"),
        section(470,"- Stats / 2026-11-26"),
        row(489,"Certification","ADsP"),
        stat_pair(508,("Repositories","14"),("Contributions","5,503")),
        stat_pair(527,("Total Tokens","36.48B"),("Peak Tokens","1.96B")),
        row(546,"Longest Session","1d 2h"),
        stat_pair(565,("Best Streak","33d"),("Current Streak","22d")),
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
