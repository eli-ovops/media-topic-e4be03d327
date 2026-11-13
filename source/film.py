#!/usr/bin/env python3
"""Offline, deterministic original motion film. No browser or server."""
from pathlib import Path
import math, subprocess, sys, time, json, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
W, H, FPS, N = 1920, 1080, 30, 900
FFMPEG = '/Users/USER/.local/bin/ffmpeg'
INK = (26, 33, 32)
PAPER = (232, 222, 195)
RED = (209, 61, 38)
MUTED = (154, 151, 131)
FONTS = {
    'sans': '/System/Library/Fonts/STHeiti Light.ttc',
    'bold': '/System/Library/Fonts/STHeiti Medium.ttc',
    'serif': '/System/Library/Fonts/Supplemental/Songti.ttc',
    'mono': '/System/Library/Fonts/Supplemental/Courier New.ttf',
    'num': '/System/Library/Fonts/Supplemental/Times New Roman.ttf',
}
FC = {}
def font(sz, style='sans'):
    k = (int(sz), style)
    if k not in FC: FC[k] = ImageFont.truetype(FONTS[style], int(sz))
    return FC[k]
def clamp(v): return max(0., min(1., v))
def smooth(v):
    v=clamp(v); return v*v*(3-2*v)
def out(v): return 1-(1-clamp(v))**4
def mix(a,b,p): return a+(b-a)*p
def span(t,a,b): return clamp((t-a)/(b-a))
def lerpc(a,b,p): return tuple(int(mix(x,y,p)) for x,y in zip(a,b))
def text(im, s, xy, size, color=PAPER, style='sans', anchor='la', spacing=None):
    d=ImageDraw.Draw(im)
    if spacing is None:
        d.text(xy,s,font=font(size,style),fill=color,anchor=anchor,stroke_width=0)
    else:
        advances=[d.textlength(c,font=font(size,style)) for c in s]
        total=sum(advances)+spacing*(len(s)-1)
        x,y=xy
        if anchor[0]=='m': x-=total/2
        if anchor[0]=='r': x-=total
        for c,a in zip(s,advances):
            d.text((x,y),c,font=font(size,style),fill=color,anchor='la')
            x+=a+spacing
def line(im, pts, color, width=2): ImageDraw.Draw(im).line(pts, fill=color, width=width)
def paste(im, asset, center, scale=1, angle=0, alpha=1):
    a=asset
    if abs(scale-1)>.0001:
        a=a.resize((max(1,round(a.width*scale)),max(1,round(a.height*scale))),Image.Resampling.LANCZOS)
    if abs(angle)>.001: a=a.rotate(angle,Image.Resampling.BICUBIC,expand=True)
    if alpha<.999:
        a=a.copy(); a.putalpha(a.getchannel('A').point(lambda v: int(v*clamp(alpha))))
    im.paste(a,(round(center[0]-a.width/2),round(center[1]-a.height/2)),a)
def panel_text(im,s,xy,size,color=PAPER,style='serif',fade=1):
    if fade>.999: text(im,s,xy,size,color,style); return
    lay=Image.new('RGBA',(W,H)); text(lay,s,xy,size,color+(int(255*fade),),style); im.paste(lay,(0,0),lay)
def bg(warm=False):
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
    rng=np.random.default_rng(1023 if warm else 726)
    if warm:
        light=np.exp(-(((xx-1170)/1000)**2+((yy-390)/850)**2))
        base=np.stack([54+81*light,40+66*light,29+43*light],axis=-1)
        wood=2.0*np.sin(xx*.021+2*np.sin(yy*.004))+1.1*np.sin(xx*.13+yy*.0006)
        base+=wood[:,:,None]
    else:
        light=np.exp(-(((xx-750)/1150)**2+((yy-450)/800)**2))
        base=np.stack([15+21*light,22+24*light,23+23*light],axis=-1)
    base+=rng.normal(0,1.1,(H,W,1))
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB')
DARK=bg(False); WARM=bg(True)

def disc(im,c,r,fill,outline=None,width=1):
    ImageDraw.Draw(im).ellipse((c[0]-r,c[1]-r,c[0]+r,c[1]+r),fill=fill,outline=outline,width=width)
def radial_asset(size, rings):
    yy,xx=np.mgrid[0:size,0:size].astype(np.float32)
    c=size/2; r=np.sqrt((xx-c)**2+(yy-c)**2); a=np.arctan2(yy-c,xx-c)
    outp=np.zeros((size,size,4),np.float32)
    for rad,col,amp in rings:
        mask=r<rad
        shade=amp*np.cos(a+2.2)+amp*.22*np.cos(r*.43)
        for j in range(3): outp[:,:,j]=np.where(mask,np.clip(col[j]+shade,0,255),outp[:,:,j])
        outp[:,:,3]=np.where(mask,255,outp[:,:,3])
    return Image.fromarray(outp.astype('uint8'),'RGBA')

def make_clock():
    s=1060; c=s/2
    a=radial_asset(s,[(494,(74,75,64),30),(482,(165,147,104),24),(462,(37,46,43),8),(449,PAPER,8),(427,(222,214,190),4)])
    d=ImageDraw.Draw(a)
    for rr in [489,472,456,438,419,354]: d.ellipse((c-rr,c-rr,c+rr,c+rr),outline=(85,83,66,180),width=2)
    for i in range(120):
        th=2*math.pi*i/120-math.pi/2
        r0=387 if i%10==0 else 398 if i%2==0 else 408
        col=INK+(255 if i%2==0 else 150,)
        d.line([(c+math.cos(th)*r0,c+math.sin(th)*r0),(c+math.cos(th)*416,c+math.sin(th)*416)],fill=col,width=5 if i%10==0 else 2)
    for i in range(1,13):
        th=2*math.pi*i/12-math.pi/2
        text(a,str(i),(c+math.cos(th)*329,c+math.sin(th)*329),64,INK,'num','mm')
    text(a,'时间交易所',(c,400),28,INK,'serif','mm',5)
    text(a,'EVERY SECOND COUNTS',(c,447),13,(85,84,69),'mono','mm',2)
    disc(a,(c,691),67,None,(78,83,69),2)
    for i in range(30):
        th=i/30*2*math.pi
        d.line([(c+math.cos(th)*56,691+math.sin(th)*56),(c+math.cos(th)*61,691+math.sin(th)*61)],fill=(79,83,68),width=2)
    text(a,'TE / 001',(c,774),17,(94,95,79),'mono','mm')
    for x,y in [(c-334,c-334),(c+334,c-334),(c-334,c+334),(c+334,c+334)]:
        disc(a,(x,y),9,(106,106,81),(49,55,46),2)
        d.line((x-5,y-3,x+5,y+3),fill=(42,49,43),width=2)
    return a
CLOCK=make_clock()
def hands(t,fast=1):
    a=Image.new('RGBA',CLOCK.size); d=ImageDraw.Draw(a); c=530
    ang=-math.pi/2+t*fast*.105
    for th,length,width,col in [(ang*.14-.6,238,13,INK),(ang,365,7,INK),(ang*2.1,390,3,RED)]:
        dx,dy=math.cos(th),math.sin(th); px,py=-dy,dx
        pts=[(c-dx*50+px*width,c-dy*50+py*width),(c+dx*length,c+dy*length),(c-dx*50-px*width,c-dy*50-py*width)]
        d.polygon(pts,fill=col)
    disc(a,(c,c),22,(81,83,64)); disc(a,(c,c),12,RED)
    th=t*2*math.pi/5
    d.line((c,691,c+math.cos(th)*46,691+math.sin(th)*46),fill=RED,width=3)
    disc(a,(c,691),5,RED)
    return a
def clock(im,t,center=(590,595),scale=.78,fast=1,missing=0):
    paste(im,CLOCK,center,scale)
    if missing:
        x,y=center; r=427*scale
        layer=Image.new('RGBA',(W,H)); d=ImageDraw.Draw(layer)
        d.pieslice((x-r,y-r,x+r,y+r),start=-90,end=-90+360*missing,fill=(205,58,36,225))
        im.paste(layer,(0,0),layer)
    paste(im,hands(t,fast),center,scale)

def receipt(kind='hour'):
    a=Image.new('RGBA',(570,850)); d=ImageDraw.Draw(a)
    shadow=Image.new('RGBA',a.size); sd=ImageDraw.Draw(shadow)
    sd.rectangle((32,20,553,825),fill=(0,0,0,150)); shadow=shadow.filter(ImageFilter.GaussianBlur(15)); a.alpha_composite(shadow)
    pts=[(20,12),(540,12),(540,801)]
    pts += [(x,801+(9 if (540-x)//10%2==0 else 0)) for x in range(540,19,-10)]
    pts += [(20,12)]
    d=ImageDraw.Draw(a);d.polygon(pts,fill=PAPER)
    for x in range(22,540,4): d.line((x,14,x,801),fill=(229,219,192,255),width=1)
    text(a,'时间交易所',(280,62),34,INK,'serif','mm',5)
    text(a,'TIME EXCHANGE / RECEIPT',(280,109),15,(100,103,84),'mono','mm')
    d.line((58,153,502,153),fill=INK,width=2)
    data={
        'hour':('出售时间','01','小时','+ ¥1,000','交易完成','TX—000001'),
        'weekend':('出售时间','52','个周末','+ ¥2,496,000','交易完成','TX—000052'),
        'year':('出售时间','10','年','+ ¥87,600,000','交易完成','TX—003650'),
        'buy':('购买申请','昨天','那一小时','出价：全部余额','无法成交','TX—RETURN'),
    }
    label,num,unit,amount,status,serial=data[kind]
    text(a,label,(62,192),24,INK,'sans')
    text(a,num,(280,320),100 if kind=='buy' else 132,INK,'serif' if kind=='buy' else 'num','mm')
    text(a,unit,(280,425),32,INK,'serif','mm')
    d.line((58,477,502,477),fill=(129,128,106),width=1)
    text(a,amount,(280,531),27 if kind in ['year','weekend'] else 33,INK,'mono' if kind!='buy' else 'sans','mm')
    text(a,'交易一经完成，不可撤回',(280,584),19,(110,111,91),'sans','mm')
    for i in range(87):
        x=69+i*4.9
        if (i*13+7)%9<6: d.rectangle((x,679,x+(1 if i%3==0 else 3),731),fill=INK)
    text(a,serial,(280,759),17,(91,95,77),'mono','mm',2)
    return a
RECEIPTS={k:receipt(k) for k in ['hour','weekend','year','buy']}
def stamp(im,xy,label='成 交',p=1,scale=1,red=RED):
    a=Image.new('RGBA',(350,160));d=ImageDraw.Draw(a)
    d.rounded_rectangle((15,21,329,138),radius=6,outline=red,width=5)
    d.rounded_rectangle((23,29,321,130),radius=4,outline=red,width=1)
    text(a,label,(172,79),51,red,'serif','mm')
    # Small registration wear cutouts make ink less perfectly digital.
    for i in range(53):
        x=(i*71)%320+15;y=(i*43)%115+22
        d.rectangle((x,y,x+3,y+1),fill=(0,0,0,0))
    paste(im,a,xy,scale*(1+.22*(1-out(p))),-9,clamp(p*5))

def plate_asset():
    s=820
    a=radial_asset(s,[(378,(39,31,21),9),(365,(222,207,171),7),(348,(234,220,190),8),(284,(207,193,160),6),(275,(232,219,189),4)])
    d=ImageDraw.Draw(a)
    for rr in [353,292,280]:d.ellipse((410-rr,410-rr,410+rr,410+rr),outline=(141,133,106,140),width=2)
    # Porcelain blue double rim, interrupted by modest hand-painted sprigs.
    d.ellipse((86,86,734,734),outline=(84,112,109,150),width=3)
    for k in range(7):
        th=.3+k*.12
        x=410+math.cos(th)*315;y=410+math.sin(th)*315
        d.ellipse((x-5,y-3,x+5,y+3),fill=(75,110,104,180))
    return a
PLATE=plate_asset()

def phone_asset(mode=0):
    a=Image.new('RGBA',(440,740)); d=ImageDraw.Draw(a)
    d.rounded_rectangle((9,9,427,730),radius=56,fill=(11,16,17),outline=(103,100,80),width=4)
    d.rounded_rectangle((24,23,412,716),radius=44,fill=(33,44,45),outline=(5,8,9),width=2)
    d.rounded_rectangle((155,37,283,62),radius=14,fill=(10,15,16))
    text(a,'18:30',(218,144),68,PAPER,'mono','mm')
    text(a,'昨天' if mode==2 else '今天',(218,203),24,(158,167,150),'sans','mm')
    if mode:
        d.line((54,282,382,282),fill=(114,121,103),width=1)
        text(a,'妈',(60,322),33,PAPER,'serif')
        text(a,'今晚回家',(60,405),42,PAPER,'serif')
        text(a,'吃饭吗？',(60,463),42,PAPER,'serif')
        d.line((54,548,382,548),fill=(114,121,103),width=1)
    d.rounded_rectangle((154,684,283,690),radius=3,fill=(113,123,111))
    return a
PHONES=[phone_asset(i) for i in range(3)]

def table(im,t,night=0,zoom=1):
    im.paste(WARM,(0,0))
    # Linen strip through the table: organic edges, coarse woven texture.
    lay=Image.new('RGBA',(W,H));d=ImageDraw.Draw(lay)
    d.polygon([(910,0),(1620,0),(1637,1080),(927,1080)],fill=(195,176,135,50))
    for x in range(926,1626,6):d.line((x,0,x+17,H),fill=(233,211,165,12),width=1)
    for y in range(0,H,7):d.line((915,y,1627,y),fill=(42,29,17,16),width=1)
    im.paste(lay,(0,0),lay)
    paste(im,PLATE,(1243,560),.86*zoom)
    # Second place across the table, partly outside camera, makes the absence legible.
    paste(im,PLATE,(1320,-180),.61*zoom)
    d=ImageDraw.Draw(im)
    # A pair of chopsticks is always two sticks, deliberately kept outside the plate.
    for shift in [0,29]:
        d.polygon([(1630+shift,290),(1640+shift,290),(1671+shift,815),(1666+shift,815)],fill=(26,26,20))
        d.line((1633+shift,294,1670+shift,815),fill=(117,79,45),width=3)
    # Small tea bowl upper right, warm liquid and tiny glint.
    disc(im,(1660,140),103,(24,23,17));disc(im,(1657,134),96,(179,163,124));disc(im,(1657,134),79,(79,52,25));disc(im,(1657,134),68,(96,60,26))
    d.arc((1590,67,1723,200),210,300,fill=(172,128,68),width=3)
    if night<.75:
        steam=Image.new('RGBA',(W,H));sd=ImageDraw.Draw(steam)
        for k in range(3):
            pts=[]
            for j in range(40):
                y=110-j*4.4; x=1650+k*17+math.sin(j*.1+t*.6+k)*8
                pts.append((x,y))
            sd.line(pts,fill=(231,222,190,int(48*(1-night))),width=4)
        steam=steam.filter(ImageFilter.GaussianBlur(5));im.paste(steam,(0,0),steam)
    if night:
        im.paste(Image.new('RGB',(W,H),(5,14,20)),(0,0),Image.new('L',(W,H),int(night*154)))

def furniture_caption(im,top,main,alpha=1):
    panel_text(im,top,(130,130),30,(176,180,158),'sans',alpha)
    for i,s in enumerate(main.split('\n')):
        panel_text(im,s,(126,202+i*100),76,PAPER,'serif',alpha)

def header(im,chapter='01 / 交易'):
    text(im,'假如时间可以买卖',(105,67),28,(180,183,160),'serif',spacing=4)
    text(im,chapter,(1815,69),20,(136,150,137),'sans','ra')
    line(im,[(105,120),(1815,120)],(77,90,80),1)
def subtitle(im,s,fade=1):
    # Protect narration contrast while pale receipts travel through the lower edge.
    scrim=Image.new('RGBA',(W,160)); sd=ImageDraw.Draw(scrim)
    for y in range(160):
        a=int(238*smooth(y/88))
        sd.line((0,y,W,y),fill=(18,27,27,a),width=1)
    im.paste(scrim,(0,H-160),scrim)
    text(im,s,(960,992),43,lerpc((29,35,30),PAPER,fade),'serif','mm',2)

def scene_trade(t):
    im=DARK.copy()
    if t<3.8:header(im)
    if t<3.8:
        p=out(span(t,-.45,.7))
        clock(im,t,(585,575),.78+.018*smooth(t/3.8))
        text(im,'出售',(1080,168),24,MUTED,'sans',spacing=5)
        # Paper physically feeds down; subsequent stamp coincides with audio.
        lay=Image.new('RGBA',(W,H))
        paste(lay,RECEIPTS['hour'],(1348,mix(-130,560,p)),.83)
        crop=Image.new('L',(W,H),0);ImageDraw.Draw(crop).rectangle((1020,205,1700,940),fill=255)
        lay.putalpha(Image.fromarray(np.minimum(np.array(lay.getchannel('A')),np.array(crop))))
        im.paste(lay,(0,0),lay)
        d=ImageDraw.Draw(im);d.rounded_rectangle((1085,197,1610,217),radius=8,fill=(8,14,14),outline=(71,83,72),width=2)
        if t>=1:stamp(im,(1360,723),p=span(t,1,1.24),scale=.65)
        subtitle(im,'第一次，我只卖了一小时。')
    elif t<6.7:
        q=t-3.8
        # Camera inside the market: the dial now eclipses the edge of frame.
        clock(im,t,(340,580),1.04,2,missing=.27*smooth(span(q,0,.8)))
        paste(im,RECEIPTS['hour'],(1300,530),.74,-13,.24)
        paper_y=mix(1350,566,out(q/.6))
        paste(im,RECEIPTS['weekend'],(1320,paper_y),.87,3)
        stamp(im,(1320,paper_y+180),p=span(q,.12,.35),scale=.72)
        subtitle(im,'后来，周末也卖了。',smooth(q/.3))
    else:
        q=t-6.7
        acceleration=1+q*q*2.5
        clock(im,t,(500,570),.91,acceleration,missing=mix(.27,.93,span(q,0,4.1)))
        # Calendar leaves swept along a spiral; motion communicates the loss.
        for k in range(18):
            u=(q*.33+k*.121)%1
            theta=k*2.39+q*.7;rr=320+u*700
            x=510+math.cos(theta)*rr;y=560+math.sin(theta)*rr*.6
            a=Image.new('RGBA',(145,185));d=ImageDraw.Draw(a)
            d.rectangle((5,5,138,178),fill=PAPER+(205,));d.rectangle((5,5,138,31),fill=RED+(220,))
            text(a,str(2000+k),(72,47),17,INK,'mono','mm');text(a,str(1+k%30),(72,108),57,INK,'num','mm')
            paste(im,a,(x,y),.44+u*.7,theta*180/math.pi,alpha=.7*(1-u))
        for k,start in enumerate([0,1.5,2.9]):
            if q>=start:
                kind='weekend' if k==0 else 'year'
                paste(im,RECEIPTS[kind],(1334+k*24,mix(1440,560,out(span(q,start,start+.45)))),.79,k*7-7)
        if q>=2.9:
            paper_y=mix(1440,560,out(span(q,2.9,3.35)))
            stamp(im,(1390,paper_y+179),p=span(q,2.9,3.15),scale=.73)
        subtitle(im,'钱越来越多，日历越来越薄。')
        if t>=10.6:
            # Physical circle match: dial travels to the dinner plate's exact center
            # and radius. The sound of the trading floor stops on its arrival.
            z=smooth(span(t,10.6,11.2))
            table_im=Image.new('RGB',(W,H));table(table_im,t)
            im=Image.blend(DARK,table_im,z)
            clock_lay=Image.new('RGBA',(W,H))
            clock(clock_lay,t,(mix(500,1243,z),mix(570,560,z)),mix(.91,.636,z),acceleration,missing=.93*(1-z))
            clock_lay.putalpha(clock_lay.getchannel('A').point(lambda v:int(v*(1-smooth(span(z,.8,1))))))
            im.paste(clock_lay,(0,0),clock_lay)
    return im

def scene_invitation(t):
    q=t-11.2; im=Image.new('RGB',(W,H));table(im,t)
    if q>.35:
        furniture_caption(im,'那天，妈妈问我：','',smooth(span(q,.35,.85)))
        p=out(span(q,.45,1.0))
        paste(im,PHONES[1 if q>=.8 else 0],(440,mix(1250,650,p)),.9,-8)
    # Single ticking shadow is visually shared with the old clock hand.
    if q>1.4:
        text(im,'我说，',(1243,456),34,(92,80,59),'serif','mm')
        text(im,'“等忙完',(1243,532),53,(61,59,46),'serif','mm')
        text(im,'这一阵。”',(1243,607),53,(61,59,46),'serif','mm')
    return im

def scene_absence(t):
    q=t-16.3; im=Image.new('RGB',(W,H));table(im,t,night=mix(.35,.87,smooth(q/3.9)))
    paste(im,PHONES[2],(440,650),.9,-8,alpha=.8)
    # The scene holds; warm food and time are allowed to cool.
    for i,s in enumerate(['我以为，','总还有下一次。']):
        text(im,s,(1243,505+i*82),51,(38,44,35),'serif','mm')
    text(im,'可是，那一小时已经过去了。',(132,149),30,(168,176,153),'serif')
    return im

def scene_return(t):
    q=t-20.2;im=DARK.copy();header(im,'02 / 退回')
    # New attempt at the same machine, same paper, different request.
    paste(im,RECEIPTS['buy'],(1355,mix(1390,573,out(q/.65))),.87,-3)
    text(im,'我想买回',(135,270),77,PAPER,'serif')
    text(im,'昨晚那一小时。',(135,382),77,PAPER,'serif')
    line(im,[(139,549),(789,549)],(80,92,79),1)
    text(im,'出价：全部余额',(139,588),31,MUTED,'sans')
    if t>=23.3:
        p=out(span(t,23.3,23.5));stamp(im,(1370,734),'拒 绝',p,.77)
        # The answer enters in two firm typographic strokes, not a generic fade.
        reveal=Image.new('RGBA',(W,H))
        text(reveal,'仅售未来',(139,729),58,RED,'serif')
        text(reveal,'不售过去',(489,729),58,RED,'serif')
        crop=Image.new('L',(W,H),0);ImageDraw.Draw(crop).rectangle((125,713,125+760*p,834),fill=255)
        reveal.putalpha(Image.fromarray(np.minimum(np.array(reveal.getchannel('A')),np.array(crop))))
        im.paste(reveal,(0,0),reveal)
    return im

def scene_end(t):
    q=t-25.2;im=Image.new('RGB',(W,H));table(im,t,night=.25)
    # A red second hand becomes the pair of chopsticks; the hour can still be kept.
    cover=Image.new('RGBA',(W,H));ImageDraw.Draw(cover).rectangle((0,0,860,H),fill=(16,26,26,200));im.paste(cover,(0,0),cover)
    text(im,'假如时间可以买卖',(133,145),30,(155,163,141),'serif',spacing=3)
    p=smooth(span(q,.15,.9))
    panel_text(im,'有些时间，',(128,340),80,PAPER,'serif',p)
    panel_text(im,'别留给以后。',(128,455),80,PAPER,'serif',smooth(span(q,.42,1.15)))
    line(im,[(136,630),(268,630)],RED,3)
    panel_text(im,'这一小时，留给谁？',(136,685),31,(163,172,150),'serif',smooth(span(q,1.1,1.8)))
    # Tiny red clock hand on empty porcelain moves gently, then rests.
    th=-math.pi/2+.45*smooth(q/3.4);c=(1243,560)
    d=ImageDraw.Draw(im);d.line((c[0],c[1],c[0]+math.cos(th)*215,c[1]+math.sin(th)*215),fill=RED,width=5)
    disc(im,c,8,RED)
    text(im,'A FILM ABOUT WHAT CANNOT BE BOUGHT',(136,926),16,(109,126,112),'mono',spacing=1)
    return im

def frame(n):
    t=n/FPS
    if t<11.2:im=scene_trade(t)
    elif t<16.3:im=scene_invitation(t)
    elif t<20.2:im=scene_absence(t)
    elif t<25.2:im=scene_return(t)
    else:im=scene_end(t)
    # Two fine cinematic edge rules; no black letterbox or essential text offscreen.
    d=ImageDraw.Draw(im);d.line((0,0,W,0),fill=(5,9,9),width=2);d.line((0,H-1,W,H-1),fill=(5,9,9),width=2)
    return im

KEYS=[0,30,75,113,125,175,209,250,290,326,340,368,410,469,490,530,588,620,665,707,748,773,810,870,899]
def stills():
    for n in KEYS:
        frame(n).save(ROOT/'qa'/f'frame-{n:04d}.jpg',quality=94)
    board=Image.new('RGB',(4*480,math.ceil(len(KEYS)/4)*294),(17,23,23))
    d=ImageDraw.Draw(board)
    for j,n in enumerate(KEYS):
        a=Image.open(ROOT/'qa'/f'frame-{n:04d}.jpg').resize((480,270),Image.Resampling.LANCZOS)
        x=j%4*480;y=j//4*294
        board.paste(a,(x,y));d.text((x+8,y+271),f'{n/FPS:05.2f}s  /  {n:03d}',font=font(17,'mono'),fill=PAPER)
    board.save(ROOT/'qa'/'storyboard.jpg',quality=94)
    print('saved 25 authored preview frames + storyboard',flush=True)

def render():
    target=ROOT/'exports'/'假如时间可以买卖.mp4'
    cmd=[FFMPEG,'-hide_banner','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','pipe:0','-i',str(ROOT/'audio'/'soundtrack.wav'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','256k','-ar','48000','-t','30','-movflags','+faststart','-metadata','title=假如时间可以买卖','-metadata','comment=Original offline procedural motion film, 2026-10-15','-progress',str(ROOT/'qa'/'encode-progress.txt'),str(target)]
    start=time.time()
    with open(ROOT/'qa'/'encode.log','w') as log:
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log)
        for n in range(N):
            p.stdin.write(frame(n).tobytes())
            if n%90==0:print(f'frame {n}/{N}, elapsed {time.time()-start:.1f}s',flush=True)
        p.stdin.close();rc=p.wait()
    if rc:raise RuntimeError(f'ffmpeg exited {rc}')
    print(json.dumps({'file':str(target),'bytes':target.stat().st_size,'seconds':time.time()-start,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()},ensure_ascii=False),flush=True)
if __name__=='__main__':
    if '--render' in sys.argv:render()
    else:stills()
