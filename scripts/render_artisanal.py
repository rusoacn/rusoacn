#!/usr/bin/env python3
"""Reproducible procedural profile artwork; Python, Pillow and NumPy.
Uses a grayscale snapshot of the account's actual public avatar and local fonts.
No generated illustrations, and no animated changes to profile text.
"""
from pathlib import Path
import os, math, json, hashlib
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
"mono":locate(["bahnschrift.ttf","DejaVuSans.ttf"]),
"bold":locate(["bahnschrift.ttf","DejaVuSans-Bold.ttf"]),
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
def fit(d,x,y,s,color=BONE,size=24,kind="mono"):
    while width(s,kind,size)>RX-x and size>19:
        size-=1
    assert width(s,kind,size)<=RX-x,(s,size)
    text(d,x,y,s,color,size,kind)
def section(d,y,title):
    fit(d,LX,y,title,RUST,19,"bold")
def inline(d,y,label,value,size=23):
    # Natural inline text, with no artificial fill or column alignment.
    fit(d,LX,y,label+": "+value,BONE,size)
def project(d,y,name,desc,detail):
    fit(d,LX,y,name+" / "+desc,BONE,23,"bold")
    fit(d,LX,y+27,detail,MUTED,19)
def surface():
    rng=np.random.default_rng(261126)
    yy,xx=np.mgrid[0:H,0:W]
    fiber=np.sin(xx*.065+2*np.sin(yy*.011))*.8
    m=Image.fromarray(rng.integers(0,256,(28,48),dtype=np.uint8)).resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    a=20.5+fiber+(np.asarray(m,dtype=np.float32)-128)/50+rng.normal(0,.85,(H,W))
    a-=2.8*((xx-W*.52)/(W*.55))**2+1.2*((yy-H*.5)/(H*.5))**2
    return Image.fromarray(np.stack((a*1.02,a,a*.98),-1).clip(0,255).astype(np.uint8),"RGB")
def panel(data):
    im=surface();d=ImageDraw.Draw(im)
    fit(d,LX,25,"RUSOACN",BONE,43,"serif")
    for i,(k,v) in enumerate(data["system"]):
        inline(d,88+26*i,k,v)
    section(d,236,"COMPLETED PROJECTS")
    for i,(a,b,c) in enumerate(data["projects"]):
        project(d,265+54*i,a,b,c)
    section(d,493,"AWARDS")
    for i,(k,v) in enumerate(data["awards"]):
        inline(d,522+26*i,k,v)
    section(d,594,"INDEPENDENT WORK")
    for i,(k,v) in enumerate(data["independent"]):
        inline(d,623+28*i,k,v,23)
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
