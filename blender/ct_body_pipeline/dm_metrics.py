# Digimorph（TNHC 62768）の胸郭の形の指標
import numpy as np, scipy.ndimage as nd
from scipy.spatial import cKDTree
Q=np.load('dm_uwL.npy'); z=np.load('dm_spine_s.npz'); C,arc,T,N=z['C'],z['arc'],z['T'],z['N']
tr=cKDTree(C); d,i=tr.query(Q[:,:2]); s=arc[i]; ven=-((Q[:,:2]-C[i])*N[i]).sum(1); L=Q[:,2]
ok=(i>2)&(i<len(C)-3)
print('slice s | depth | width(mid) | width/depth | tip offset/depth')
R=[]
for s0 in range(40,68,4):
    m=ok&(np.abs(s-s0)<0.6)&(ven>3)&(ven<55)&(np.abs(L)<12)
    x,y=L[m],ven[m]
    if len(y)<50: continue
    dep=np.percentile(y,99.5); mid=(y>dep*0.4)&(y<dep*0.6)
    wid=np.percentile(x[mid],97)-np.percentile(x[mid],3); tip=y>dep*0.9; off=np.median(x[tip])
    R.append((dep,wid,off)); print(s0,round(dep,1),round(wid,1),round(wid/dep,2),round(off/dep,3))
R=np.array(R); print('mean width/depth',round((R[:,1]/R[:,0]).mean(),2),'sd',round((R[:,1]/R[:,0]).std(),2))
# 肋骨の寝る角度: 矢状面で、片側の肋骨の点の向き（構造テンソル）と体軸の接線の角
for side,sel in (('L<0',L<-3),('L>0',L>3)):
    m=ok&sel&(ven>6)&(ven<35)&(s>30)&(s<64)&(np.abs(L)<12)
    # 体軸の座標 (s, ven) の 2D 画像で
    H,xe,ye=np.histogram2d(s[m],ven[m],bins=[np.arange(28,66,0.25),np.arange(4,37,0.25)])
    H=nd.gaussian_filter(H,1.0); gx=nd.sobel(H,0); gy=nd.sobel(H,1)
    Jxx=nd.gaussian_filter(gx*gx,4); Jyy=nd.gaussian_filter(gy*gy,4); Jxy=nd.gaussian_filter(gx*gy,4)
    ang=0.5*np.degrees(np.arctan2(2*Jxy,Jxx-Jyy))+90   # 線の向き（s 軸から ven 軸へ）
    w=H>H.max()*0.2
    a=((ang[w]+90)%180)-90
    hist,be=np.histogram(a,bins=np.arange(-90,91,5),weights=H[w])
    print(side,'rib line angle from body axis (deg, +=ventral-posterior), mode',be[np.argmax(hist)]+2.5,'weighted median',round(float(np.median(np.repeat(a,1))),1))
