# 椎骨ごとの断面（その椎骨の肋骨だけを、その椎骨の枠で）。直す前と後
import numpy as np, sys
from PIL import Image, ImageDraw
import ribrestore as rr
B=np.load(sys.argv[1]); tag=sys.argv[2]
P=np.argwhere((B>=160)&(B<202)).astype(float); L=B[tuple(P.astype(int).T)].astype(int)
Q=rr.restore(P,L)
rows=[]; panels=[]
for k in range(3,20,2):
    m=((L-160)//2+1)==k
    c,t,r,v=rr.frame(k)
    for X,name,row in ((P[m],'before',0),(Q[m],'after',1)):
        q=X-c; x=q@r*0.104; y=q@v*0.104; z=q@t*0.104
        if row==0: im=Image.new('RGB',(220,520),(20,20,20)); dr=ImageDraw.Draw(im); panels.append(im)
        oy=40+row*260
        for xx,yy in zip(x[::3],y[::3]): dr.point((110+xx*7,oy+yy*7),fill=(255,200,80) if row else (120,200,255))
        dr.line([(110,oy-30),(110,oy+220)],fill=(70,70,70)); dr.text((4,oy-36),f'v{k:02d} {name}',fill=(255,255,255))
        if len(y)>50:
            dep=np.percentile(y,99.5); mid=(y>dep*0.4)&(y<dep*0.6)
            wid=np.percentile(x[mid],97)-np.percentile(x[mid],3) if mid.sum()>10 else np.nan
            tip=y>dep*0.85; rows.append((k,name,round(dep,1),round(wid,1),round(wid/dep,2),round(np.median(x[tip]),1)))
w=Image.new('RGB',(220*len(panels),520)); [w.paste(p,(i*220,0)) for i,p in enumerate(panels)]; w.save(f'ownxsec_{tag}.png')
print('v name depth(mm) width_mid(mm) width/depth tip_lat(mm)')
for r_ in rows: print(*r_)
