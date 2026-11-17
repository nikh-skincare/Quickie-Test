from PIL import Image, ImageDraw, ImageFont, ImageStat
import numpy as np, os, sys, json
FN='/home/user/fnt/'
XB=FN+'Inter-ExtraBold.otf'; BD=FN+'Inter-Bold.otf'; MD=FN+'Inter-Medium.otf'
RAW='/home/user/raw2/'; BFD='/home/user/bf/'
OUT='/home/user/bf2out/'; os.makedirs(OUT,exist_ok=True)
W,H=1080,1350
IVORY=(247,246,242); INK=(17,17,17); EUC=(143,174,155); DEEP=(69,95,80)

def F(p,s): return ImageFont.truetype(p,s)
def tw(d,t,f,sp): return sum(d.textlength(c,font=f)+sp for c in t)-sp
def tr(d,xy,t,f,fill,sp=0,anchor='c'):
    w=tw(d,t,f,sp)
    x=xy[0]-w/2 if anchor=='c' else (xy[0]-w if anchor=='r' else xy[0])
    for c in t:
        d.text((x,xy[1]),c,font=f,fill=fill); x+=d.textlength(c,font=f)+sp
    return w

def load(src,mode):
    im=Image.open(src).convert('RGB')
    if mode=='pad':   # portraits: scale down, reflect sides, replicate top
        s=0.84; w=int(1080*s); h=int(1350*s)
        p=im.resize((w,h),Image.LANCZOS)
        a=np.array(p); side=(1080-w)//2
        a=np.pad(a,((0,0),(side,1080-w-side),(0,0)),mode='reflect')
        top=1350-h
        a=np.pad(a,((top,0),(0,0),(0,0)),mode='edge')
        return Image.fromarray(a)
    return im.resize((W,H),Image.LANCZOS)

def lum(im,box): return ImageStat.Stat(im.crop(box).convert('L')).mean[0]

def grad(h,a0,a1,color,up=False):
    g=Image.new('RGBA',(W,h))
    px=g.load()
    for y in range(h):
        t=y/(h-1); a=a0+(a1-a0)*min(1,t/0.6)
        if up: a=a1+(a0-a1)*min(1,t/0.6)
        for x in range(W): px[x,y]=color+(int(255*a),)
    return g

def build(spec):
    im=load(spec['src'],spec.get('layout','full'))
    base=im.convert('RGBA')
    bl=lum(im,(0,H-340,W,H)); tl=lum(im,(0,0,W,330))
    bdark=bl<135; tdark=tl<135
    # scrims
    bc=INK if bdark else IVORY
    base.alpha_composite(grad(360,0.0,spec.get('scrim',0.88),bc),(0,H-360))
    topc=INK if tdark else IVORY
    t=grad(300,0.0,0.5,topc); t=t.transpose(Image.FLIP_TOP_BOTTOM)
    base.alpha_composite(t,(0,0))
    d=ImageDraw.Draw(base,'RGBA')
    tcol=IVORY if tdark else INK; tsub=EUC if tdark else DEEP
    bcol=IVORY if bdark else INK
    # label
    tr(d,(W/2,46),spec.get('label','BLACK FRIDAY'),F(BD,24),tsub,9)
    # headline
    lines=spec['head']; hs=spec.get('hmax',108)
    while True:
        f=F(XB,hs)
        if max(tw(d,l,f,2) for l in lines)<=W-110: break
        hs-=2
    y=86
    for l in lines:
        tr(d,(W/2,y),l,f,tcol,2); y+=int(hs*1.06)
    if spec.get('support'):
        tr(d,(W/2,y+6),spec['support'],F(BD,32),tsub,6); y+=50
    # price block
    side=spec.get('side','left')   # price on left, badge on right
    px=64 if side=='left' else W-64
    anc='l' if side=='left' else 'r'
    if not spec.get('badge'): px=W/2; anc='c'
    old=spec['old']; new=spec['new']
    fo=F(MD,46); fn=F(XB,spec.get('nsize',122))
    oy=H-322
    ow=tr(d,(px,oy),old,fo,bcol,0,anc)
    x0=px if anc=='l' else (px-ow if anc=='r' else px-ow/2)
    d.rectangle([x0-4,oy+31,x0+ow+4,oy+36],fill=bcol)   # single strike-through
    nw=tr(d,(px,oy+52),new,fn,bcol,0,anc)
    if spec.get('suffix'):
        sx=(px+nw+8) if side=='left' else px+0
        if side=='left': d.text((sx,oy+52+spec.get('nsize',122)-46),spec['suffix'],font=F(BD,34),fill=bcol)
    # badge
    if spec.get('badge'):
        r=114
        bx=(W-64-r) if side=='left' else (64+r)
        by=spec.get('by',H-250)
        if 'bpos' in spec: bx,by=spec['bpos']
        fill=IVORY if bdark and by>H-500 else None
        # choose contrasting fill vs local area
        local=lum(im,(int(bx-r),int(by-r),int(bx+r),int(by+r)))
        dark_local=local<135
        if spec.get('bfill')=='ink': fillc,txt,acc=INK,IVORY,EUC
        elif spec.get('bfill')=='ivory': fillc,txt,acc=IVORY,INK,DEEP
        else: fillc,txt,acc=(IVORY,INK,DEEP) if dark_local else (INK,IVORY,EUC)
        d.ellipse([bx-r,by-r,bx+r,by+r],fill=fillc+(255,))
        d.ellipse([bx-r+8,by-r+8,bx+r-8,by+r-8],outline=acc+(255,),width=3)
        b=spec['badge']
        if b=='BUY2':
            tr(d,(bx,by-84),"BUY 2,",F(BD,34),txt,2); tr(d,(bx,by-48),"GET 2",F(BD,34),txt,2)
            tr(d,(bx,by-8),"FREE",F(XB,76),acc,0)
        else:  # 30% OFF
            tr(d,(bx,by-76),"30%",F(XB,86),acc,0); tr(d,(bx,by+16),"OFF",F(XB,46),txt,3)
            tr(d,(bx,by+68),"EVERY BOX",F(BD,21),txt,2)
    # footer + qualifier
    tr(d,(W/2,H-112),spec['foot'],F(BD,26),bcol,3)
    if spec.get('qual'): tr(d,(W/2,H-68),spec['qual'],F(MD,21),bcol,1)
    out=OUT+spec['name']+'.jpg'
    base.convert('RGB').save(out,quality=93); return out

BF=dict(old='$111.96',new='$55.98',badge='BUY2')
SUB=dict(old='$27.99',new='$19.59',suffix='/MO',badge='SUB')
DAILY="Based on one wipe daily."
S=[
 dict(name='bf2_c1a_towel_ivory',scrim=0.0,src=RAW+'n1c.png',layout='pad',head=["SKINCARE FOR","70¢ A DAY."],foot="80 WIPES · FREE SHIPPING",qual=DAILY,bpos=(900,520),**BF),
 dict(name='bf2_c1b_towel_green',scrim=0.0,src=RAW+'n1d.png',layout='pad',head=["SKINCARE FOR","70¢ A DAY."],foot="80 WIPES · FREE SHIPPING",qual=DAILY,bpos=(900,520),**BF),
 dict(name='bf2_c2_spa_hero',src=RAW+'n2a.png',head=["80 DAYS.","70¢ A DAY."],foot="4 BOXES · 80 WIPES · FREE SHIPPING",qual=DAILY,**BF),
 dict(name='bf2_mtA_daily',src=RAW+'n2b.png',head=["SKINCARE FOR","70¢ A DAY."],foot="80 WIPES · FREE SHIPPING",qual=DAILY,**BF),
 dict(name='bf2_mtB_supply',src=RAW+'n2b.png',head=["YOUR NEXT 2½ MONTHS","OF SKINCARE. SORTED."],foot="80 WIPES · 70¢ PER WIPE · FREE SHIPPING",qual=DAILY,**BF),
 dict(name='bf2_mtC_straight',src=RAW+'n2b.png',head=["BUY 2.","GET 2 FREE."],support="JUST 70¢ PER WIPE",foot="4 BOXES · 80 WIPES · FREE SHIPPING",old='$111.96',new='$55.98'),
 dict(name='bf2_c3a_fourpack_ivory',src=RAW+'n3a.png',layout='pad',head=["BUY 2.","GET 2 FREE."],support="JUST 70¢ PER WIPE",foot="4 BOXES · 80 WIPES · FREE SHIPPING",old='$111.96',new='$55.98',hmax=120),
 dict(name='bf2_c3b_fourpack_sage',src=RAW+'n3b.png',layout='pad',head=["BUY 2.","GET 2 FREE."],support="JUST 70¢ PER WIPE",foot="4 BOXES · 80 WIPES · FREE SHIPPING",old='$111.96',new='$55.98',hmax=120),
 dict(name='bf2_c4a_keepgift_warm',src=RAW+'n4a.png',head=["KEEP TWO.","GIFT TWO."],support="JUST 70¢ PER WIPE",foot="80 WIPES · FREE SHIPPING",**BF),
 dict(name='bf2_c4b_keepgift_green',src=RAW+'n4b.png',head=["KEEP TWO.","GIFT TWO."],support="JUST 70¢ PER WIPE",foot="80 WIPES · FREE SHIPPING",**BF),
 dict(name='bf2_sub1_hero',src=RAW+'n2a.png',head=["30% OFF","EVERY BOX."],foot="20 WIPES · DELIVERED MONTHLY · + SHIPPING",qual="Subscription price per box. Shipping extra.",label="BLACK FRIDAY · SUBSCRIBE & SAVE",**SUB),
 dict(name='bf2_sub2_carton',src=RAW+'s1.png',head=["ON REPEAT.","30% OFF."],foot="20 WIPES · DELIVERED MONTHLY · + SHIPPING",qual="Subscription price per box. Shipping extra.",label="BLACK FRIDAY · SUBSCRIBE & SAVE",**SUB),
 dict(name='bf2_sub3_shelf',src=RAW+'s2.png',head=["YOUR QUICKIE,","EVERY MONTH."],foot="20 WIPES · DELIVERED MONTHLY · + SHIPPING",qual="Subscription price per box. Shipping extra.",label="BLACK FRIDAY · SUBSCRIBE & SAVE",**SUB),
 dict(name='bf2_sub4_towel',scrim=0.0,src=RAW+'n1d.png',layout='pad',head=["SUBSCRIBE.","SAVE 30%."],foot="20 WIPES · DELIVERED MONTHLY · + SHIPPING",qual="Subscription price per box. Shipping extra.",label="BLACK FRIDAY · SUBSCRIBE & SAVE",bpos=(900,520),**SUB),
 dict(name='bf2_sub5_towel_ivory',src=RAW+'n1c.png',layout='pad',scrim=0.0,head=["SKINCARE ON","AUTOPILOT."],foot="20 WIPES · DELIVERED MONTHLY · + SHIPPING",qual="Subscription price per box. Shipping extra.",label="BLACK FRIDAY · SUBSCRIBE & SAVE",bpos=(900,520),**SUB),
 dict(name='bf2_sub6_hero_dark',src=RAW+'n2b.png',head=["30% OFF","EVERY BOX."],foot="20 WIPES · DELIVERED MONTHLY · + SHIPPING",qual="Subscription price per box. Shipping extra.",label="BLACK FRIDAY · SUBSCRIBE & SAVE",**SUB),
]
only=sys.argv[1:]
for s in S:
    if only and s['name'] not in only: continue
    print(build(s))
