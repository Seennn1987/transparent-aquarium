# 胴の深さ・幅（展示の姿勢の膜）: 体軸の点から 96 方向の光線で膜の内側の最初の出口を求め、背腹の差と左右の差の最大
import numpy as np, sys
src=open('diag_profile.py').read().split("ang=np.deg2rad")[0]
exec(src)
ang=np.deg2rad(np.arange(0,360,3.75)); rs=np.arange(0,40,0.05)*MM
sel=np.arange(0,len(C),10); out=[]
for i in sel:
    dirn=np.cos(ang)[:,None]*Dp[i]+np.sin(ang)[:,None]*Ep[i]
    pts=Cp[i]+dirn[:,None,:]*rs[None,:,None]
    ins=inside(pts); fo=np.argmax(~ins,axis=1); r=rs[fo]/MM
    if not ins[:,0].all(): out.append((arc[i],np.nan,np.nan,np.nan)); continue
    a=r*np.cos(ang); b=r*np.sin(ang)
    out.append((arc[i],a.max()-a.min(),b.max()-b.min(),-a.min()))
out=np.array(out); np.save('measure_body.npy',out)
S=23.1; m=(out[:,0]>9.5)&(out[:,0]<107.5)
o=out[m]; i=np.nanargmax(o[:,1]); j=np.nanargmax(o[:,2])
print('trunk max depth %.1f mm (u=%.0f) = %.2f x skull; max width %.1f mm (u=%.0f) = %.2f x skull; axis-centre outside skin at %d sections'%(o[i,1],o[i,0],o[i,1]/S,o[j,2],o[j,0],o[j,2]/S,np.isnan(o[:,1]).sum()))
for u in (15,30,45,60,75,90,105): k=np.argmin(abs(out[:,0]-u)); print('u %3d  depth %.1f  width %.1f  dorsal %.1f'%(u,out[k,1],out[k,2],out[k,3]))
