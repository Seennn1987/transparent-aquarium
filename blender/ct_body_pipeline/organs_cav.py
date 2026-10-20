# 臓器の入れ物: 展示の姿勢での体腔（膜の内側）と、体軸に沿った座標（u: 体軸の長さ、vv: 腹へ、rr: 右へ）
import numpy as np, scipy.ndimage as nd, json, time
from scipy.spatial import cKDTree
import ribrestore
t0=time.time()
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; Mp=P['M']; k=float(P['k'])
def ct2m(p): p=np.asarray(p,float); return np.stack([p[...,1],-p[...,2],-p[...,0]],-1)*k
def ct2m_dir(d): d=np.asarray(d,float); return np.stack([d[...,1],-d[...,2],-d[...,0]],-1)
def Mof(n): return Mp[bn.index(n)]
MM=k
J=np.load('J.npy')
# 体軸の点と枠（展示の姿勢）。椎骨 k の枠を、その椎骨の動きで動かす
axp=[]; 
for kk in range(1,24):
    name=f'v{kk:02d}'
    if name not in bn: continue
    c,t,r,v=ribrestore.frame(min(kk,21))
    if kk>21:   # 仙椎: 体軸の点は椎骨の頭、向きは v21 の枠
        H=P['head'][bn.index(name)]; cm=H
    else: cm=ct2m(c*0.104)
    M=Mof(name); R=M[:3,:3]
    pos=(cm@R.T+M[:3,3]) if kk<=21 else (H@R.T+M[:3,3])
    axp.append((kk, J[kk-1] if kk-1<len(J) else J[-1], pos, R@ct2m_dir(t), R@ct2m_dir(r), R@ct2m_dir(v)))
ks=np.array([a[0] for a in axp]); arc=np.array([a[1] for a in axp]); pos=np.array([a[2] for a in axp])
T=np.array([a[3] for a in axp]); Rr=np.array([a[4] for a in axp]); Vv=np.array([a[5] for a in axp])
# 細かく補間（0.1 mm）
us=np.arange(arc.min(),arc.max(),0.1)
def interp(A): return np.stack([np.interp(us,arc,A[:,i]) for i in range(3)],1)
AP=interp(pos); AV=interp(Vv); AV/=np.linalg.norm(AV,axis=1,keepdims=True); AR=interp(Rr); AR-=AV*(AR*AV).sum(1,keepdims=True); AR/=np.linalg.norm(AR,axis=1,keepdims=True)
# 膜（展示の姿勢）の内側: 1 軸の光線の偶奇
S=np.load('skin_posed.npz'); sv=S['v'].astype(np.float64); sf=S['f']
VOX=0.25*MM
lat=AR.mean(0); ax=int(np.argmax(np.abs(lat))); others=[i for i in range(3) if i!=ax]
# 胴の範囲（体軸の点から 30 mm 以内）だけ
lo=AP.min(0)-30*MM; hi=AP.max(0)+30*MM
# 膜の箱で切らない（記録 41、2026-10-20）: 箱を膜の範囲で切ると、膜のどこか（手足）が変わるだけで格子の原点と大きさが変わり、
#   organs.py のまだらの場（格子の大きさで乱数を引く）と管の格子への落とし方が変わって、胃・結腸・中身の形が変わった。
#   格子は体軸の点（膜によらない）だけで決める
shape=tuple(np.ceil((hi-lo)/VOX).astype(int)+1)
print('grid',shape,'ray axis',ax, f'{time.time()-t0:.0f}s',flush=True)
a,b=others
tri=sv[sf]                                     # (n,3,3)
xa=(tri[...,a]-lo[a])/VOX; xb=(tri[...,b]-lo[b])/VOX; xz=(tri[...,ax]-lo[ax])/VOX
hits=[[] for _ in range(shape[a]*shape[b])]
ia0=np.floor(xa.min(1)).astype(int); ia1=np.ceil(xa.max(1)).astype(int); ib0=np.floor(xb.min(1)).astype(int); ib1=np.ceil(xb.max(1)).astype(int)
HA=[];HB=[];HZ=[]
NA=int((ia1-ia0).max())+1; NB=int((ib1-ib0).max())+1      # 三角形の広がり（升）。大きい三角形も漏らさない
for da in range(0,NA):
    for db in range(0,NB):
        ca=ia0+da; cb=ib0+db; ok=(ca<=ia1)&(cb<=ib1)
        if not ok.any(): continue
        idx=np.where(ok)[0]; pa=ca[idx]+0.0; pb=cb[idx]+0.0      # 列の中心は整数（格子点）
        A0=xa[idx,0];A1=xa[idx,1];A2=xa[idx,2];B0=xb[idx,0];B1=xb[idx,1];B2=xb[idx,2]
        den=(B1-B2)*(A0-A2)+(A2-A1)*(B0-B2)
        l0=((B1-B2)*(pa-A2)+(A2-A1)*(pb-B2))/np.where(den==0,1,den); l1=((B2-B0)*(pa-A2)+(A0-A2)*(pb-B2))/np.where(den==0,1,den); l2=1-l0-l1
        inside=(den!=0)&(l0>=0)&(l1>=0)&(l2>=0)
        z=l0*xz[idx,0]+l1*xz[idx,1]+l2*xz[idx,2]
        HA.append(pa[inside].astype(int));HB.append(pb[inside].astype(int));HZ.append(z[inside])
HA=np.concatenate(HA);HB=np.concatenate(HB);HZ=np.concatenate(HZ)
okk=(HA>=0)&(HA<shape[a])&(HB>=0)&(HB<shape[b]); HA,HB,HZ=HA[okk],HB[okk],HZ[okk]
order=np.lexsort((HZ,HB,HA)); HA,HB,HZ=HA[order],HB[order],HZ[order]
inside=np.zeros(shape,bool)
key=HA*shape[b]+HB; u_,st,cn=np.unique(key,return_index=True,return_counts=True)
zz=np.arange(shape[ax])
for kk_,s0,c_ in zip(u_,st,cn):
    if c_<2: continue
    zs=HZ[s0:s0+c_]; ca_=kk_//shape[b]; cb_=kk_%shape[b]
    col=np.zeros(shape[ax],bool)
    for i in range(0,c_-1,2): col|=(zz>=zs[i])&(zz<=zs[i+1])
    sl=[0,0,0]; sl[a]=ca_; sl[b]=cb_; sl[ax]=slice(None); inside[tuple(sl)]=col
print('inside voxels',int(inside.sum()), f'{time.time()-t0:.0f}s',flush=True)
np.savez_compressed('organs_cav.npz',inside=inside,lo=lo,vox=VOX,us=us,AP=AP,AV=AV,AR=AR,k=k,arc=arc,ks=ks,pos=pos)
