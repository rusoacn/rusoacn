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
AX,AY,AW,AH=17,18,512,784
LX,RX=561,1406
N,DELAY=24,160
BONE=(222,220,212); MUTED=(163,158,151); LABEL=(187,182,171)
RUST=(177,126,115); RULE=(66,61,58); GREEN=(170,184,169); RED=(193,133,127)

def locate(names):
    dirs=[Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts",Path("/usr/share/fonts/truetype/dejavu"),Path("/usr/share/fonts/opentype/noto")]
    for d in dirs:
        for n in names:
            if (d/n).is_file():return str(d/n)
    raise FileNotFoundError("Install a matching local system font: "+str(names))
F={
"mono":locate(["consola.ttf","DejaVuSansMono.ttf"]),
"bold":locate(["consolab.ttf","DejaVuSansMono-Bold.ttf"]),
"serif":locate(["georgia.ttf","DejaVuSerif.ttf"]),
"ko":locate(["malgun.ttf","NotoSansCJK-Regular.ttc"]),
"kob":locate(["malgunbd.ttf","NotoSansCJK-Bold.ttc","malgun.ttf"])}
fonts={}
def font(k,s):
    if (k,s) not in fonts:fonts[k,s]=ImageFont.truetype(F[k],s)
    return fonts[k,s]
def parts(s,kind):
    out=[]
    for c in s:
        k=("kob" if kind=="bold" else "ko") if 0xac00<=ord(c)<=0xd7a3 else kind
        if out and out[-1][0]==k:out[-1][1]+=c
        else:out.append([k,c])
    return out
def width(s,k,n):return sum(font(a,n).getlength(b) for a,b in parts(s,k))
def text(d,x,y,s,color=BONE,size=21,kind="mono",right=False):
    w=width(s,kind,size)
    if right:x-=w
    assert x>=0 and x+w<=W-8,(s,x,w)
    for k,v in parts(s,kind):
        f=font(k,size)
        d.text((round(x),y+size),v,font=f,fill=color,anchor="ls")
        x+=f.getlength(v)
    return x
def section(d,y,title):
    x=text(d,LX,y,title,RUST,18)
    d.line((round(x+18),y+15,RX,y+15),fill=RULE,width=1)
def kv(d,y,label,value,x0=LX,x1=RX,size=21):
    x=text(d,x0,y,label,LABEL,size)
    start=round(x+13);end=round(x1-width(value,"mono",size)-13)
    assert end-start>=5,(label,value,start,end)
    for a in range(start,end,10):
        d.line((a,y+size-4,min(a+2,end),y+size-4),fill=(83,77,71),width=1)
    text(d,x1,y,value,BONE,size,right=True)
def pair(d,y,a,b,size=20):
    mid=(LX+RX)//2
    kv(d,y,*a,LX,mid-22,size)
    kv(d,y,*b,mid+19,RX,size)
def project(d,y,name,desc,detail):
    x=text(d,LX,y,name,BONE,22,"bold")
    if desc:
        s="  /  "+desc
        assert x+width(s,"mono",20)<=RX,(name,desc)
        text(d,x,y+1,s,LABEL,20)
    assert width(detail,"mono",19)<=RX-LX-13
    text(d,LX+13,y+26,detail,MUTED,19)
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
    d.line((542,24,542,H-24),fill=(53,49,46),width=1)
    text(d,LX,18,"rusoacn",BONE,39,"serif")
    text(d,RX,33,"DATA / AI / SYSTEMS",MUTED,17,right=True)
    section(d,75,"01 / SYSTEM")
    for i,(k,v) in enumerate(data["system"]):kv(d,100+24*i,k,v)
    section(d,231,"02 / COMPLETED PROJECTS")
    for i,(a,b,c) in enumerate(data["projects"]):project(d,255+47*i,a,b,c)
    section(d,449,"03 / AWARDS")
    pair(d,474,*data["awards"],size=19)
    section(d,512,"04 / INDEPENDENT WORK")
    for i,(k,v) in enumerate(data["independent"]):kv(d,537+25*i,k,v,size=20)
    section(d,622,"05 / RECORD")
    s=data["stats"]
    pair(d,648,("Repositories",s["repositories"]),("Commits",s["commits"]))
    pair(d,674,("Contributions",s["contributions"]),("Certification",s["certification"]))
    x=text(d,LX,700,"Net Lines",LABEL,20)
    x=text(d,x+17,700,s["net_lines"],BONE,20)
    x=text(d,x+18,700,"(",MUTED,20)
    x=text(d,x+5,700,s["additions"]+"++",GREEN,20)
    x=text(d,x+7,700," / ",MUTED,20)
    x=text(d,x+2,700,s["deletions"]+"--",RED,20)
    text(d,x+4,700,")",MUTED,20)
    pair(d,726,("Total Tokens",s["total_tokens"]),("Peak Tokens",s["peak_tokens"]))
    pair(d,752,("Longest Session",s["longest_session"]),("Best Streak",s["best_streak"]))
    kv(d,778,"Current Streak",s["current_streak"],size=20)
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
        d=ImageDraw.Draw(im)
        # Caption lies over a dark lower gradient, not over the figures.
        shade=Image.new("RGB",(AW,48),(20,20,20))
        im.paste(shade,(AX,H-65))
        text(d,AX+12,H-53,"RECORD / "+data["date"].replace("-","."),MUTED,15)
        if i<14:d.rectangle((AX+AW-18,H-42,AX+AW-12,H-35),fill=RUST)
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
            right.append(hashlib.sha256(r.crop((550,0,W,H)).tobytes()).hexdigest())
        assert len(set(allhash))==N and len(set(right))==1
    assert out.stat().st_size<10_000_000,out.stat().st_size
    print("ART_RENDER_PASS",W,H,N,DELAY,out.stat().st_size,flush=True)
if __name__=="__main__":main()
