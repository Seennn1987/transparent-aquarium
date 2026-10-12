import numpy as np
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw
Q=np.load('dm_uwL.npy'); z=np.load('dm_spine_s.npz'); C,arc,T,N=z['C'],z['arc'],z['T'],z['N']
# 体軸に垂直な断面: 各点を体軸の最も近い点へ（矢状面内）、腹側 = -N
tr=cKDTree(C); d,i=tr.query(Q[:,:2]); s=arc[i]; ven=-((Q[:,:2]-C[i])*N[i]).sum(1); L=Q[:,2]
# 体軸の延長（体軸の先より後ろの点は使わない）
ok=(i>2)&(i<len(C)-3)
panels=[]; rows=[]
for s0 in range(20,68,6):
    m=ok&(np.abs(s-s0)<0.6)&(ven>-12)&(ven<75)
    x,y=L[m],ven[m]
    im=Image.new("RGB",(300,560),(20,20,20)); dr=ImageDraw.Draw(im)
    for xx,yy in zip(x[::2],y[::2]): dr.point((150+xx*6,60+yy*6),fill=(255,200,80))
    dr.line([(150,0),(150,560)],fill=(70,70,70)); dr.line([(0,60),(300,60)],fill=(70,70,70)); dr.text((5,5),f'DM s={s0}mm',fill=(255,255,255))
    panels.append(im)
    # 胸郭: 背骨より腹側 3mm 以上の点
    c=y>3
    if c.sum()>50:
        dep=np.percentile(y[c],99.5); mid=(y>dep*0.4)&(y<dep*0.6)
        wid=np.ptp(x[mid]) if mid.sum()>10 else np.nan
        tip=(y>dep*0.85); off=np.median(x[tip]) if tip.sum()>5 else np.nan
        rows.append((s0,round(dep,1),round(wid,1),round(off,1)))
w=Image.new("RGB",(300*len(panels),560)); [w.paste(p,(k*300,0)) for k,p in enumerate(panels)]; w.save('dm_xsec.png')
print('s, depth(ventral, mm), width at mid-depth (mm), ventral tip offset from midline (mm)')
for r in rows: print(r)
