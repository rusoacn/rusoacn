#!/usr/bin/env python3
"""Reproducible procedural profile artwork; Python, Pillow and NumPy.
Uses the user-supplied color portrait and local fonts.
No generated illustrations, and no animated changes to profile text.
"""
from pathlib import Path
import os, math, json, hashlib, ast, io, tokenize, token
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/"assets"
W,H=1440,820
# Camera-facing CRT housing; the existing W,H canvas is its signal.
OW,OH=1560,968
AX,AY,AW,AH=0,0,820,820
LX,RX=845,1414
N,DELAY=24,160
EDITOR_TOP,EDITOR_STEP=59,22
CURSOR_BLINK_FRAMES=3
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
    start_y=EDITOR_TOP
    step=EDITOR_STEP
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
    src=Image.open(A/"portrait-analog-source.jpg").convert("RGB")
    # Center the actual source portrait; do not synthesize a replacement face.
    src=ImageOps.fit(src,(AW,AH),Image.Resampling.LANCZOS,centering=(.49,.5))
    src=src.filter(ImageFilter.GaussianBlur(.48))
    return np.asarray(src,dtype=np.float32)/255

def art(t,src):
    yy,xx=np.mgrid[0:AH,0:AW]
    phase=2*math.pi*t
    # Stable film texture and gently drifting analog signal.
    displacement=np.rint(1.0*np.sin(yy*.025+phase)+.45*np.sin(yy*.11-phase)).astype(int)
    pos=np.clip(xx+displacement,0,AW-1)
    rgb=src[yy,pos].copy()
    # Fine color bleed, subdued cyan and magenta, slightly lifted black levels.
    rgb[...,0]=src[yy,np.clip(pos+1,0,AW-1),0]
    rgb[...,2]=src[yy,np.clip(pos-1,0,AW-1),2]
    lum=rgb[...,0]*.2126+rgb[...,1]*.7152+rgb[...,2]*.0722
    rgb=rgb*.69+lum[...,None]*.31
    rgb=np.power(rgb.clip(0,1),.96)*.90+.035
    # Film print color crossover, restrained rather than neon.
    shadow=(1-lum)[...,None]
    rgb+=shadow*np.array([.020,-.008,.012],dtype=np.float32)
    rgb+=lum[...,None]*np.array([.018,.008,-.012],dtype=np.float32)
    vignette=(1-.18*((xx-AW*.50)/(AW*.55))**2-.12*((yy-AH*.48)/(AH*.55))**2).clip(.55,1)
    grain=np.random.default_rng(9126).normal(0,.013,(AH,AW))
    scan=((yy%3)==0)*.018
    band=np.exp(-((yy-AH*(.50+.31*math.sin(phase)))/48)**2)*.013
    exposure=1+.017*math.sin(phase)
    rgb=(rgb*exposure*vignette[...,None]+(grain-scan+band)[...,None]).clip(0,1)
    # Very faint edge falloff, preserving the original image and skin tones.
    edge=np.minimum(np.minimum(xx,AW-1-xx),np.minimum(yy,AH-1-yy))
    f=(edge/8).clip(0,1)
    rgb=rgb*f[...,None]+.065*(1-f[...,None])
    return Image.fromarray((rgb*255).astype(np.uint8),"RGB")
class CRTGlass:
    """Procedural front-on CRT enclosure and curved glass projection.

    The source is the existing animated portrait and actual Python text,
    not a generated mockup. Glass geometry is static; animated raster effects are applied to the
    signal before projection, with reduced strength in the editor.
    """
    def __init__(self):
        yy,xx=np.mgrid[0:OH,0:OW].astype(np.float32)
        # Close, eye-level view, with a deeper lower bezel and bowed edges.
        cx,cy=OW*.5,OH*.491
        rx,ry=OW*.465,OH*.448
        u=(xx-cx)/rx
        v=(yy-cy)/ry
        au,av=np.abs(u),np.abs(v)
        # Convex rectangular glass with naturally rounded corners.
        shape=(au**12+av**12)**(1/12)
        dist=(1-shape)*min(rx,ry)
        mask=np.clip(dist+.55,0,1).astype(np.float32)
        self.mask=mask[...,None]
        rng=np.random.default_rng(200426)
        noise=rng.normal(0,.7,(OH,OW)).astype(np.float32)
        # Molded, matte charcoal case and recessed glass seating.
        rad=(u*u*.55+v*v*.45)
        outer=(17+3.2*(-v)-3.5*rad+noise).clip(3,26)
        outside=np.maximum(-dist,0)
        bevel=(17+5*(-v)+2*(-u))*np.exp(-((outside-14)/10.5)**2)
        lip=10*np.exp(-((outside-26)/7)**2)
        seam=12*np.exp(-(outside/3.8)**2)
        case=(outer+bevel+lip-seam).clip(3,48)
        # Slight directional light across the molded outer case.
        case+=5*np.exp(-((yy-12)/10)**2)*np.exp(-((xx-OW*.36)/(OW*.60))**2)
        case-=5*np.exp(-((yy-(OH-8))/10)**2)
        self.case=np.stack((case*1.04,case,case*.97),-1).clip(0,255)
        # Inverse barrel mapping. The image bows with the face of the tube.
        su=u*(1.030+.030*v*v+.020*u*u)
        sv=v*(1.028+.036*u*u+.019*v*v)
        sx=np.clip((su+1)*.5*(W-1),0,W-1)
        sy=np.clip((sv+1)*.5*(H-1),0,H-1)
        self.x0=sx.astype(np.int32); self.y0=sy.astype(np.int32)
        self.x1=np.minimum(self.x0+1,W-1)
        self.y1=np.minimum(self.y0+1,H-1)
        self.fx=(sx-self.x0).astype(np.float32)[...,None]
        self.fy=(sy-self.y0).astype(np.float32)[...,None]
        # Edge shadow follows the actual shape of the curved glass.
        edge_shadow=1-.44*np.exp(-np.maximum(dist,0)/12)
        glass_vignette=(1-.078*u*u-.055*v*v).clip(.70,1)
        scan=1-.058*(np.cos(sy*math.pi*2/3.35)+1)*.5
        self.gain=(edge_shadow*glass_vignette*scan)[...,None].astype(np.float32)
        # Broad, low-energy room reflection and a fine upper-edge glint.
        reflection=(4.6*np.exp(-((u+.61)/.51)**2-((v+.89)/.20)**2)
                    +2.4*np.exp(-((u+.84)/.16)**2-((v+.12)/.85)**2)
                    +2.0*np.exp(-((dist-8)/3.2)**2)*np.clip(-v,0,1))
        reflection+=.42*noise
        self.reflection=np.stack((reflection*1.04,reflection,reflection*.98),-1).astype(np.float32)
    def render(self,signal):
        assert signal.size==(W,H)
        # Gentle analog halation; preserve the high-frequency code text.
        raw=np.asarray(signal,dtype=np.float32)
        bloom=np.asarray(signal.filter(ImageFilter.GaussianBlur(2.1)),dtype=np.float32)
        raw=raw*.965+bloom*.035
        a=raw[self.y0,self.x0]*(1-self.fx)+raw[self.y0,self.x1]*self.fx
        b=raw[self.y1,self.x0]*(1-self.fx)+raw[self.y1,self.x1]*self.fx
        curved=a*(1-self.fy)+b*self.fy
        curved=curved*self.gain+self.reflection
        composite=curved*self.mask+self.case*(1-self.mask)
        return Image.fromarray(composite.clip(0,255).astype(np.uint8),"RGB")

class RasterSignal:
    """A rolling camera-versus-CRT refresh band, with analog sync drift.

    Motion is periodic, not random flashing. The two panels share the same
    moving raster; distortion and contrast are weaker over the code.
    """
    def __init__(self):
        self.y,self.x=np.mgrid[0:H,0:W].astype(np.float32)
        # Preserve text legibility without splitting the moving raster.
        self.strength=.35*(1-.64*np.clip((self.x-(AW-20))/100,0,1))
        self.yi=self.y.astype(np.int32)
    def render(self,im,t):
        phase=2*math.pi*t
        # A wide dark retrace band and its softer luminous leading edge.
        # Wrap in normalized screen coordinates for a continuous loop.
        u=(self.y/H-t+.5)%1-.5
        dark=np.exp(-(u/.078)**2)
        bright=np.exp(-(((u+.103+.5)%1-.5)/.039)**2)
        sync=np.exp(-(u/.047)**2)
        drift=2.6*np.sin(self.y*.021-phase)+1.7*np.sin(self.y*.068+phase)
        tear=(7.0*np.sin(self.y*.108-phase)+2.4*np.sin(self.y*.23+phase))*sync
        sx=np.clip(self.x+(drift+tear)*self.strength,0,W-1)
        x0=sx.astype(np.int32)
        x1=np.minimum(x0+1,W-1)
        f=(sx-x0).astype(np.float32)[...,None]
        raw=np.asarray(im,dtype=np.float32)
        warped=raw[self.yi,x0]*(1-f)+raw[self.yi,x1]*f
        # Phosphor raster and a visible rolling exposure wave. No full-screen
        # flashes, abrupt strobe, or changes to the underlying code content.
        ripple=.032*np.sin(self.y*.24-phase*2)
        gain=1+self.strength*(-.29*dark+.16*bright+ripple)
        lift=self.strength*(7.5*bright-1.0*dark)
        out=warped*gain[...,None]+lift[...,None]
        return Image.fromarray(out.clip(0,255).astype(np.uint8),"RGB")

def draw_block_cursor(im,data):
    # A terminal-style insertion cursor on the blank line after the code.
    # Draw before the CRT projection so it shares the screen's glass and glow.
    y=EDITOR_TOP+len(profile_code(data).splitlines())*EDITOR_STEP+3
    x=LX
    cw=round(font("mono",22).getlength("M"))
    assert y+19<H and x+cw<RX
    d=ImageDraw.Draw(im)
    d.rectangle((x,y,x+cw-1,y+18),fill=(220,218,208))

def main():
    data=json.loads((A/"profile-record.json").read_text(encoding="utf-8"))
    s=data["stats"];n=lambda k:int(s[k].replace(",",""))
    assert n("additions")-n("deletions")==n("net_lines")
    bg=panel(data);src=source();frames=[];crt=CRTGlass();raster=RasterSignal()
    for i in range(N):
        im=bg.copy();im.paste(art(i/N,src),(AX,AY))
        if (i//CURSOR_BLINK_FRAMES)%2==0:
            draw_block_cursor(im,data)
        frames.append(crt.render(raster.render(im,i/N)))
    palette=frames[0].quantize(colors=160,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    converted=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    converted[0].save(A/"profile-artisanal.png",optimize=True)
    out=A/"profile-artisanal.gif"
    converted[0].save(out,save_all=True,append_images=converted[1:],duration=DELAY,loop=0,optimize=True,disposal=1)
    with Image.open(out) as im:
        assert im.n_frames==N and im.size==(OW,OH) and im.info.get("loop")==0
        allhash=[];cursor_levels=[];edge_hash=[];editor_hash=[]
        for i in range(N):
            im.seek(i);r=im.convert("RGB")
            assert im.info["duration"]==DELAY
            allhash.append(hashlib.sha256(r.tobytes()).hexdigest())
            # The outer bezel must remain still. The active screen may move.
            edge_hash.append(hashlib.sha256(r.crop((0,0,32,32)).tobytes()).hexdigest())
            editor_hash.append(hashlib.sha256(r.crop((1000,100,OW-75,800)).tobytes()).hexdigest())
            cursor=np.asarray(r.crop((895,855,920,883)),dtype=np.float32)
            cursor_levels.append(float(cursor.mean(axis=2).max()))
        assert len(set(allhash))==N and len(set(edge_hash))==1
        assert len(set(editor_hash))>N//2
        on=[v for i,v in enumerate(cursor_levels) if (i//CURSOR_BLINK_FRAMES)%2==0]
        off=[v for i,v in enumerate(cursor_levels) if (i//CURSOR_BLINK_FRAMES)%2==1]
        assert min(on)>max(off)+35,(min(on),max(off))
        print("RASTER_CURSOR_PASS",round(min(on),1),round(max(off),1),flush=True)
    assert out.stat().st_size<10_000_000,out.stat().st_size
    print("CRT_RENDER_PASS",OW,OH,N,DELAY,out.stat().st_size,flush=True)
if __name__=="__main__":main()
