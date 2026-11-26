#!/usr/bin/env python3
"""Reproducible procedural profile artwork; Python, Pillow and NumPy.
Uses a grayscale snapshot of the account's actual public avatar and local fonts.
No generated illustrations, and no animated changes to profile text.
"""
from pathlib import Path
import os, math, json, hashlib, ast, io, tokenize, token
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/"assets"
W,H=1440,820
AX,AY,AW,AH=0,0,820,820
LX,RX=845,1414
N,DELAY=24,160
BONE=(222,220,212); MUTED=(163,158,151); LABEL=(187,182,171)
RUST=(177,126,115); RULE=(66,61,58); GREEN=(170,184,169); RED=(193,133,127)

def locate(names):
    dirs=[Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts",Path("/usr/share/fonts/truetype/dejavu"),Path("/usr/share/fonts/opentype/noto")]
    for d in dirs:
        for n in names:
            if (d/n).is_file():return str(d/n)
    raise FileNotFoundError("Install a matching local system font: "+str(names))
# Local industrial sans, with a deliberately condensed display cut.
# No font binaries are distributed with the artwork.
F={
"mono":locate(["consola.ttf","DejaVuSansMono.ttf"]),
"bold":locate(["consolab.ttf","DejaVuSansMono-Bold.ttf"]),
"serif":locate(["bahnschrift.ttf","DejaVuSans.ttf"]),
"ko":locate(["NotoSansKR-VF.ttf","malgun.ttf","NotoSansCJK-Regular.ttc"]),
"kob":locate(["NotoSansKR-VF.ttf","malgunbd.ttf","NotoSansCJK-Bold.ttc"])}
fonts={}
def font(k,s):
    if (k,s) not in fonts:
        f=ImageFont.truetype(F[k],s)
        n=Path(F[k]).name.lower()
        if n=="bahnschrift.ttf":
            f.set_variation_by_axes({"mono":[400,100],"bold":[550,100],"serif":[350,75]}[k])
        elif n=="notosanskr-vf.ttf":
            f.set_variation_by_axes([500 if k=="kob" else 400])
        fonts[k,s]=f
    return fonts[k,s]
def parts(s,kind):
    out=[]
    for c in s:
        k=("kob" if kind=="bold" else "ko") if 0xac00<=ord(c)<=0xd7a3 else kind
        if out and out[-1][0]==k:out[-1][1]+=c
        else:out.append([k,c])
    return out
def width(s,k,n):return sum(font(a,n).getlength(b) for a,b in parts(s,k))
def text(d,x,y,s,color=BONE,size=22,kind="mono",right=False):
    w=width(s,kind,size)
    if right:x-=w
    assert x>=0 and x+w<=W-8,(s,x,w)
    for k,v in parts(s,kind):
        f=font(k,size)
        d.text((round(x),y+size),v,font=f,fill=color,anchor="ls")
        x+=f.getlength(v)
    return x
# VS Code Dark+ inspired source rendering. The displayed Python is valid,
# generated from the existing profile record, and does not execute anything.
EDITOR_BG=(24,24,24)
EDITOR_FG=(212,212,212)
EDITOR_NAME=(156,220,254)
EDITOR_STR=(206,145,120)
EDITOR_COMMENT=(106,153,85)
EDITOR_BRACKET=(255,215,0)
EDITOR_DIM=(128,128,128)
def profile_code(data):
    q=lambda s:json.dumps(s,ensure_ascii=False)
    keys=["education","major","os_ide","agents","languages"]
    lines=['name = '+q("JunYoungJeon")]
    lines.extend(k+" = "+q(v) for k,(_,v) in zip(keys,data["system"]))
    lines+=["","# Completed projects","projects = ["]
    for i,(name,desc,detail) in enumerate(data["projects"]):
        if i==0:
            lines+=["    "+q(name+" / Policy Decision Support")+",",
                    "    # Idea Proposal / Finalist / In-person PT",
                    "    # Gyeongnam Big Data 2026 (T2)"]
        else:
            lines+=["    "+q(name+" / "+desc)+",","    # "+detail]
    lines+=["]","","# Awards","awards = ["]
    lines+=["    "+q(k+": "+v)+"," for k,v in data["awards"]]
    lines+=["]","","# Independent work","independent = ["]
    for k,v in data["independent"]:
        if k=="AI Creative" and " (" in v:
            lead,tail=v.split(" (",1)
            lines+=["    "+q(k+": "+lead), "    "+q(" ("+tail)+","]
        else:
            lines.append("    "+q(k+": "+v)+",")
    lines+=["]"]
    source="\n".join(lines)+"\n"
    tree=ast.parse(source)
    vals={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)}
    assert vals["name"]=="JunYoungJeon"
    assert len(vals["projects"])==4 and len(vals["awards"])==2 and len(vals["independent"])==3
    assert vals["awards"]==[k+": "+v for k,v in data["awards"]]
    assert vals["independent"]==[k+": "+v for k,v in data["independent"]]
    assert vals["projects"][1:]==[k+" / "+v for k,v,_ in data["projects"][1:]]
    return source
def token_color(t):
    if t.type==token.STRING:return EDITOR_STR
    if t.type==token.NAME:return EDITOR_NAME
    if t.type==tokenize.COMMENT:return EDITOR_COMMENT
    if t.type==token.OP and t.string in "[]{}()":return EDITOR_BRACKET
    return EDITOR_FG
def code_panel(d,data):
    # Minimal editor tab and gutter, no toolbar clutter or dotted leaders.
    d.rectangle((820,0,W,H),fill=EDITOR_BG)
    d.rectangle((820,0,W,43),fill=(30,30,30))
    d.rectangle((820,0,1004,42),fill=EDITOR_BG)
    d.line((821,1,1003,1),fill=(86,156,214),width=2)
    text(d,840,8,"profile.py",(204,204,204),22,"mono")
    text(d,RX,10,"Python",EDITOR_DIM,19,"mono",right=True)
    source=profile_code(data)
    lines=source.splitlines()
    groups={}
    for t in tokenize.generate_tokens(io.StringIO(source).readline):
        if t.type in (token.NAME,token.STRING,token.OP,tokenize.COMMENT):
            if t.start[0]==t.end[0]:groups.setdefault(t.start[0],[]).append(t)
    start_y=59
    step=22
    assert start_y+(len(lines)-1)*step+23<=H-8,(len(lines),H)
    for i,line in enumerate(lines,1):
        y=start_y+(i-1)*step
        if not line:continue
        size=22
        while width(line,"mono",size)>RX-LX and size>18:size-=1
        assert width(line,"mono",size)<=RX-LX,(line,size)
        x=LX;end=0
        if line.startswith("    "):
            d.line((LX+1,y-1,LX+1,y+step-1),fill=(57,57,57),width=1)
        for t in groups.get(i,[]):
            l,r=t.start[1],t.end[1]
            if l>end:x+=width(line[end:l],"mono",size)
            frag=line[l:r]
            kind="bold" if i==1 and t.type==token.STRING else "mono"
            x=text(d,x,y,frag,token_color(t),size,kind)
            end=r
        if end<len(line):x=text(d,x,y,line[end:],EDITOR_FG,size)
        assert x<=RX+1,(i,line,x)
def surface():
    rng=np.random.default_rng(261126)
    yy,xx=np.mgrid[0:H,0:W]
    fiber=np.sin(xx*.065+2*np.sin(yy*.011))*.8
    m=Image.fromarray(rng.integers(0,256,(28,48),dtype=np.uint8)).resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    a=20.5+fiber+(np.asarray(m,dtype=np.float32)-128)/50+rng.normal(0,.85,(H,W))
    a-=2.8*((xx-W*.52)/(W*.55))**2+1.2*((yy-H*.5)/(H*.5))**2
    return Image.fromarray(np.stack((a*1.02,a,a*.98),-1).clip(0,255).astype(np.uint8),"RGB")
def panel(data):
    im=surface()
    code_panel(ImageDraw.Draw(im),data)
    return im
def source():
    src=Image.open(A/"avatar-art-source.png").convert("L")
    # Preserve the actual figures and their proportions. Soft side crop only.
    src=ImageOps.fit(src,(AW,AH),Image.Resampling.LANCZOS,centering=(.5,.50))
    return np.asarray(ImageOps.autocontrast(src,cutoff=1),dtype=np.float32)/255
def art(t,src):
    yy,xx=np.mgrid[0:AH,0:AW]
    th=2*math.pi*t
    shift=np.rint(1.5*np.sin(yy*.031+th)+.55*np.sin(yy*.115-th)).astype(int)
    raw=src[yy,np.clip(xx+shift,0,AW-1)]
    lum=(raw**1.3+.018*math.sin(th)+.012*np.sin(yy*.012-th)).clip(0,1)
    bayer=np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]],dtype=np.float32)
    pattern=(bayer[yy%4,xx%4]+.5)/16-.5
    q=np.floor(np.clip(lum*12+pattern*.9,0,12))/12
    grain=np.random.default_rng(905).normal(0,2,(AH,AW))
    vign=(1-.30*((xx-AW*.49)/(AW*.53))**2-.18*((yy-AH*.43)/(AH*.58))**2).clip(.25,1)
    light=(18+q*176)*vign+grain+.9*(yy%2)
    center=AH*(.5+.27*math.sin(th))
    light+=np.exp(-((yy-center)/48)**2)*3.4
    edge=np.minimum(np.minimum(xx,AW-1-xx),np.minimum(yy,AH-1-yy))
    fade=(edge/19).clip(0,1);fade=fade*fade*(3-2*fade)
    light=20*(1-fade)+light*fade
    rgb=np.stack((light*1.015,light,light*.975),-1).clip(0,255).astype(np.uint8)
    return Image.fromarray(rgb,"RGB")
def main():
    data=json.loads((A/"profile-record.json").read_text(encoding="utf-8"))
    s=data["stats"];n=lambda k:int(s[k].replace(",",""))
    assert n("additions")-n("deletions")==n("net_lines")
    bg=panel(data);src=source();frames=[]
    for i in range(N):
        im=bg.copy();im.paste(art(i/N,src),(AX,AY))
        frames.append(im)
    palette=frames[0].quantize(colors=128,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    converted=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    converted[0].save(A/"profile-artisanal.png",optimize=True)
    out=A/"profile-artisanal.gif"
    converted[0].save(out,save_all=True,append_images=converted[1:],duration=DELAY,loop=0,optimize=True,disposal=1)
    with Image.open(out) as im:
        assert im.n_frames==N and im.size==(W,H) and im.info.get("loop")==0
        allhash=[];right=[]
        for i in range(N):
            im.seek(i);r=im.convert("RGB")
            allhash.append(hashlib.sha256(r.tobytes()).hexdigest())
            right.append(hashlib.sha256(r.crop((LX-8,0,W,H)).tobytes()).hexdigest())
        assert len(set(allhash))==N and len(set(right))==1
    assert out.stat().st_size<10_000_000,out.stat().st_size
    print("ART_RENDER_PASS",W,H,N,DELAY,out.stat().st_size,flush=True)
if __name__=="__main__":main()
